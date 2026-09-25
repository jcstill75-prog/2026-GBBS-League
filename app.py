import streamlit as st
import pandas as pd
import random
import os
import base64
import json
import glob
from PIL import Image
import io

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for a beautiful, cozy baking theme
st.markdown("""
<style>
    .reportview-container {
        background: #FFF9F2;
    }
    .stButton>button {
        background-color: #D36B5F;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #B54E43;
        color: white;
    }
    h1, h2, h3 {
        color: #5D4037;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
    # --- A. Main Episode Results ---
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") == actuals.get("star_baker") and predictions.get("star_baker") not in [None, "--Select Baker--"]:
            score += 5
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim and p not in [None, "--Select Baker--"]:
                        score += 5
            elif isinstance(pred_elim, str) and pred_elim not in [None, "--Select Baker--"]:
                if pred_elim in act_elim:
                    score += 5
        elif act_elim == "None":
            pass
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim == act_elim and pred_elim not in [None, "--Select Baker--"]:
                score += 5
            
    # --- B. Technical Challenge ---
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b and b not in [None, "--Select Baker--"])
            if exact_count == 5:
                score += 25
            else:
                for idx, b in enumerate(pred_rank):
                    if b not in [None, "--Select Baker--"] and act_rank[idx] == b:
                        if idx in [0, 4]:
                            score += 3
                        else:
                            score += 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b and b not in [None, "--Select Baker--"])
            if exact_count == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if b not in [None, "--Select Baker--"] and act_rank[idx] == b:
                        if idx in [0, 3]:
                            score += 3
                        else:
                            score += 2
                    
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b and b not in [None, "--Select Baker--"])
            if exact_count == 3:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if b not in [None, "--Select Baker--"] and act_rank[idx] == b:
                        if idx == 0:
                            score += 3
                        else:
                            score += 2
    else:
        # Standard Weeks 2-7
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        
        if len(pred_top3) == 3 and len(act_top3) == 3 and all(b not in [None, "--Select Baker--"] for b in pred_top3):
            if pred_top3 == act_top3:
                score += 10
            else:
                if pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] == act_top3[2]: score += 2
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3 and baker != act_top3[idx]:
                        score += 1
                        
        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        
        if len(pred_bottom3) == 3 and len(act_bottom3) == 3 and all(b not in [None, "--Select Baker--"] for b in pred_bottom3):
            if pred_bottom3 == act_bottom3:
                score += 10
            else:
                if pred_bottom3[0] == act_bottom3[0]: score += 2
                if pred_bottom3[1] == act_bottom3[1]: score += 2
                if pred_bottom3[2] == act_bottom3[2]: score += 3
                for idx, baker in enumerate(pred_bottom3):
                    if baker in act_bottom3 and baker != act_bottom3[idx]:
                        score += 1

    # --- C. Consolations ---
    if week < 9:
        p_inline = predictions.get("in_line_sb")
        if p_inline and p_inline not in [None, "--Select Baker--"]:
            if p_inline in actuals.get("in_line_sb", []) and p_inline != actuals.get("star_baker"):
                score += 2
                
        p_trouble = predictions.get("in_trouble")
        if p_trouble and p_trouble not in [None, "--Select Baker--"]:
            act_trouble_list = actuals.get("in_trouble", [])
            if isinstance(act_trouble_list, list) and p_trouble in act_trouble_list:
                score += 2
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner not in [None, "--Select Baker--"]:
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker not in [None, "--Select Baker--"] and baker in act_semis and baker != pred_winner:
            score += 10
            
    pred_handshakes = predictions.get("handshakes")
    act_handshakes = actuals.get("handshakes")
    if pred_handshakes is not None and act_handshakes is not None:
        if pred_handshakes == act_handshakes:
            score += 20
        elif abs(pred_handshakes - act_handshakes) <= 1:
            score += 10
            
    pred_crying = predictions.get("crying")
    act_crying = actuals.get("crying")
    if pred_crying is not None and act_crying is not None:
        if pred_crying == act_crying:
            score += 20
        elif abs(pred_crying - act_crying) <= 5:
            score += 10
            
    pred_innuendos = predictions.get("innuendos")
    act_innuendos = actuals.get("innuendos")
    if pred_innuendos is not None and act_innuendos is not None:
        if pred_innuendos == act_innuendos:
            score += 20
        elif abs(pred_innuendos - act_innuendos) <= 5:
            score += 10
            
    return score


def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        path = os.path.join("assets", target + ext)
        if os.path.exists(path):
            try:
                return Image.open(path)
            except Exception:
                pass
    try:
        for filename in os.listdir("assets"):
            stem, _ = os.path.splitext(filename)
            if stem.lower().strip() == target:
                full_path = os.path.join("assets", filename)
                return Image.open(full_path)
    except Exception:
        pass
    return None

# --- 3. CORE BAKERS LIST & DATABASE INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

BAKER_INFO = {
    "Clara": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-clara/"},
    "Connie": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-connie/"},
    "Danni": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-danni/"},
    "Gabe": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-gabe/"},
    "Gary": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-gary/"},
    "Mo": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-mo/"},
    "Molly": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-molly/"},
    "Moyin": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-moyin/"},
    "Nikki": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-nikki/"},
    "Shannon": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-shannon/"},
    "Tom": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-tom/"},
    "Yannis": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-yannis/"}
}

ROSTER_ALPHABETICAL = [
    "AI Brian", "Ana", "Becca", "Brian", "Cassie", 
    "Emma", "Gisselle", "Jasmine", "Jennifer", "Mark", 
    "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

eliminated_bakers_by_week = {
    1: [],
    2: ["Yannis"],
    3: ["Yannis", "Nikki"],
    4: ["Yannis", "Nikki", "Connie"],
    5: ["Yannis", "Nikki", "Connie", "Gary"],
    6: ["Yannis", "Nikki", "Connie", "Gary", "Moyin"],
    7: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara"],
    8: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon"],
    9: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly"],
    10: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly", "Danni"]
}

if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for name in ROSTER_ALPHABETICAL:
        st.session_state.league_members[name] = {
            "avatar": "🤖" if name == "AI Brian" else None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None
        }

# Ensure pin key exists for all members safely
for name in st.session_state.league_members:
    if "pin" not in st.session_state.league_members[name]:
        st.session_state.league_members[name]["pin"] = None

brian_avatar_img = None
for brian_path in ["ai_brian.jpg", "AI Brian.jpg", "assets/ai_brian.jpg", "assets/AI_Brian.jpg", "assets/ai_brian.png", "assets/AI_Brian.png"]:
    if os.path.exists(brian_path):
        try:
            brian_avatar_img = Image.open(brian_path)
            break
        except Exception:
            pass

if brian_avatar_img is not None:
    st.session_state.league_members["AI Brian"]["avatar"] = brian_avatar_img

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

# Dynamic active competition week progression
# Highest week that has published results + 1
completed_weeks = sorted(list(st.session_state.weekly_results.keys()))
if not completed_weeks:
    unlocked_max_week = 1
else:
    unlocked_max_week = min(max(completed_weeks) + 1, 10)

if "current_week" not in st.session_state:
    st.session_state.current_week = unlocked_max_week

# --- 4. DYNAMIC AUTOMATION: "AI BRIAN" PICK GENERATOR ---
def generate_ai_brian_season_picks():
    winner = random.choice(ALL_BAKERS)
    remaining_pool = [b for b in ALL_BAKERS if b != winner]
    semis = random.sample(remaining_pool, 3)
    return {
        "winner": winner,
        "semifinalists": semis,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    if week == 10:
        champion = random.choice(active_bakers)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"show_champion": champion, "tech_rank": tech_rank}
    elif week == 9:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if is_double_elim else random.choice(elim_pool)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if is_double_elim else random.choice(elim_pool)
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_rank": tech_rank
        }
    else:
        star_baker = random.choice(active_bakers)
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if is_double_elim else random.choice(elim_pool)
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        tech_top_3 = random.sample(active_bakers, 3)
        rem_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bottom, min(3, len(rem_bottom)))
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. APP INTERFACE LAYOUT ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("normanbeaver.jpg"):
        st.image("normanbeaver.jpg", width=90)
    elif os.path.exists("assets/normanbeaver.jpg"):
        st.image("assets/normanbeaver.jpg", width=90)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: COMPETITION PROGRESS & POINTS GUIDE ---
with st.sidebar:
    st.header("📌 Competition Progress")
    if unlocked_max_week == 1:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**

Submit your Season-Long Predictions now! Week 2 predictions will unlock automatically once Week 1 results are posted.")
    else:
        st.success(f"🟢 **Active Status: Week {unlocked_max_week} Open**

Weekly predictions are open up through Week {unlocked_max_week}.")

    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of what points are at stake for each prediction!")
    st.warning("⏰ **Weekly voting window ends on Tuesdays right before the show airs in the UK.**")
    
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        *   **Season Winner:** 40 pts
        *   **Finalist Consolation:** 15 pts *(if picked winner makes Top 3 but loses)*
        *   **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        *   **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        *   **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        *   **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Standard Weeks (Weeks 2-7)", expanded=False):
        st.markdown("""
        *   **Star Baker:** 5 pts
        *   **Eliminated Baker:** 5 pts
        *   **In Line (Star Baker consolation):** 2 pts
        *   **In Trouble (Elimination consolation):** 2 pts
        *   **Top 3 Technical Challenge:**
            *   *Exact:* 3 pts for 1st, 2 pts for 2nd/3rd
            *   *Wrong Spot:* 1 pt for any correct Top 3 baker
            *   *Combo Sweep:* **10 pts** *(flat)*
        *   **Bottom 3 Technical Challenge:**
            *   *Exact:* 2 pts for 9th/10th, 3 pts for 11th
            *   *Wrong Spot:* 1 pt for any correct Bottom 3 baker
            *   *Combo Sweep:* **10 pts** *(flat)*
        *   **Star League Member:** +5 pts *(weekly high scorer)*
        """)
        
    with st.expander("🏁 Weeks 8, 9 & 10 (Dynamic Scaling)", expanded=False):
        st.markdown("""
        *   **Week 8 (Quarterfinal episodic - 5 bakers):**
            *   *Star Baker:* 5 pts
            *   *Eliminated:* 5 pts
            *   *Technical:* Exact positions 1st/5th (3 pts), 2nd/3rd/4th (2 pts)
            *   *Perfect 5-for-5 Sweep:* **25 pts** *(flat)*
        *   **Week 9 (Semifinal episodic - 4 bakers):**
            *   *Star Baker:* 5 pts
            *   *Eliminated:* 5 pts
            *   *Technical:* Exact positions 1st/4th (3 pts), 2nd/3rd (2 pts)
            *   *Perfect 4-for-4 Sweep:* **20 pts** *(flat)*
        *   **Week 10 (Grand Finale episodic - 3 bakers):**
            *   *Show Champion:* 15 pts
            *   *Technical:* Exact positions 1st (3 pts), 2nd/3rd (2 pts)
            *   *Perfect 3-for-3 Sweep:* **15 pts** *(flat)*
        """)

# --- MAIN TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Contestant Analytics", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_data = []
    for name, data in st.session_state.league_members.items():
        tot_pts = data.get("total_score", 0)
        lb_data.append({
            "member": name,
            "points": tot_pts,
            "data": data
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        
        display_rows = []
        for idx, row in df_lb.iterrows():
            rank_num = idx + 1
            rank_str = f"#{rank_num}"
            if rank_num == 1: rank_str = "🥇 #1"
            elif rank_num == 2: rank_str = "🥈 #2"
            elif rank_num == 3: rank_str = "🥉 #3"
            
            display_rows.append({
                "Rank": rank_str,
                "League Member": row["member"],
                "Total Points": f"{row['points']} pts"
            })
            
        df_display = pd.DataFrame(display_rows)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    scorecard_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="sc_player_select")
    p_data = st.session_state.league_members.get(scorecard_player, {})
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})
    
    st.markdown(f"### **Scorecard for {scorecard_player} — Total Score: {p_pts} pts**")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### **🌟 Season-Long Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
        
    with col_s2:
        st.markdown("#### **📅 Weekly Predictions Log**")
        if p_weekly:
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                t3 = ", ".join(w_picks.get("tech_top_3", [])) if w_picks.get("tech_top_3") else (" ,".join(w_picks.get("tech_rank", [])) if w_picks.get("tech_rank") else "N/A")
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Placement": t3
                })
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No weekly predictions logged yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps (Verify Counts)")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1 is logged!")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_cnt = w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_cnt = w_act.get("crying_count", 0)
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"

            tot_hs += hs_cnt
            tot_cry += cry_cnt
            tot_inn += inn_cnt

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{hs_cnt} ({hs_stamps})",
                "Crying Scenes": f"{cry_cnt} ({cry_stamps})",
                "Innuendos": f"{inn_cnt} ({inn_stamps})"
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

        st.markdown(f"**Cumulative Broadcast Totals Across Logged Weeks:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Sexual Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_ALPHABETICAL, key="disp_player_sel")
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 1", "Week 2"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Video Evidence (e.g., 'At 28:14 in Episode 3, Paul clearly shakes Tom's hand during Showstopper judging')")
            disp_correction = st.text_input("Requested Correction (e.g., 'Add +1 Handshake for Tom in Week 3')")
            
            sub_disp = st.form_submit_button("Submit Dispute for League Vote")
            if sub_disp:
                st.session_state.disputes.append({
                    "Player": disp_player,
                    "Week": disp_week,
                    "Category": disp_cat,
                    "Evidence": disp_evidence,
                    "Correction": disp_correction,
                    "Status": "Pending GroupMe Vote 🗳️"
                })
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        df_disp = pd.DataFrame(st.session_state.disputes)
        st.dataframe(df_disp, use_container_width=True, hide_index=True)


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Weekly & Season Predictions")
    
    st.subheader("🔑 Player Login & Authentication")
    selected_player = st.selectbox("Select Your Player Profile:", ROSTER_ALPHABETICAL, key="login_player_select")
    p_info = st.session_state.league_members[selected_player]
    
    is_authenticated = False
    
    if p_info.get("pin") is None:
        st.info(f"Welcome {selected_player}! Set your 4-digit PIN to lock in your ballots.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            new_pin = st.text_input("Create 4-Digit Password PIN:", type="password", max_chars=4, key="create_pin_1")
        with col_p2:
            confirm_pin = st.text_input("Confirm 4-Digit Password PIN:", type="password", max_chars=4, key="create_pin_2")
            
        if st.button("Save Password PIN"):
            if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                st.session_state.league_members[selected_player]["pin"] = new_pin
                st.success("PIN saved successfully! You are now logged in.")
                st.rerun()
            else:
                st.error("PINs must be exactly 4 digits and match!")
    else:
        entered_pin = st.text_input(f"Enter 4-Digit PIN for {selected_player}:", type="password", max_chars=4, key="login_pin_input")
        if entered_pin == p_info.get("pin"):
            is_authenticated = True
            st.success(f"Authenticated as {selected_player}!")
        elif entered_pin != "":
            st.error("Incorrect PIN!")

    st.markdown("---")

    if is_authenticated:
        with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
            cols = st.columns(4)
            for idx, baker in enumerate(ALL_BAKERS):
                info = BAKER_INFO.get(baker, {"url": "#"})
                with cols[idx % 4]:
                    st.markdown(f"**{baker}**")
                    img = load_baker_image(baker)
                    if img is not None:
                        st.image(img, use_container_width=True)
                    else:
                        st.info(f"📸 Photograph of {baker}")
                        st.markdown(f"[🔗 Official Show Profile]({info['url']})")
                    st.markdown("<br>", unsafe_allow_html=True)

        st.subheader("📅 Select Prediction Target Week")
        pred_week_choice = st.selectbox(
            "Select Week to Submit Predictions For:", 
            [f"Week {w}" for w in range(2, 11)],
            index=max(0, unlocked_max_week - 2),
            key="pred_week_selectbox"
        )
        target_week = int(pred_week_choice.split(" ")[1])

        if target_week > unlocked_max_week:
            st.error(f"🔒 Week {target_week} Predictions Are Currently Locked!")
            st.warning(f"Predictions for Week {target_week} will unlock automatically once the Administrator posts official broadcast results for Week {target_week - 1}.")
        else:
            current_eliminated = eliminated_bakers_by_week.get(target_week, [])
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            
            st.info(f"Active Bakers in the Tent for Week {target_week}: " + ", ".join(active_bakers))
            
            # 1. Season long entry if target_week is 2 and scouting phase is active
            if target_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    baker_opts = ["--Select Baker--"] + active_bakers
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_opts, key="user_win_pick")
                    
                    st.write("Predict Other 3 Semifinalists [10 pts each | 30 pts max]:")
                    s1 = st.selectbox("Semifinalist #1", baker_opts, key="s1_pick")
                    s2 = st.selectbox("Semifinalist #2", baker_opts, key="s2_pick")
                    s3 = st.selectbox("Semifinalist #3", baker_opts, key="s3_pick")
                    user_semis = [s1, s2, s3]
                    
                    user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                    user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)
                    
                    if st.button("Lock Season-Long Predictions"):
                        all_season_picks = [user_winner] + user_semis
                        if any(b == "--Select Baker--" for b in all_season_picks):
                            st.error("⚠️ Please select a valid baker for all season-long prediction fields!")
                        elif len(set(all_season_picks)) != len(all_season_picks):
                            st.error("❌ Duplicate Selection Error: You cannot select the same baker twice across Season Winner and Semifinalists!")
                        else:
                            st.session_state.league_members[selected_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                            st.success(f"Season long predictions saved successfully for {selected_player}!")

            # 2. Weekly Form based on target week
            st.markdown(f"### Weekly Ballot for Week {target_week}")
            
            prev_week_results = st.session_state.weekly_results.get(target_week - 1, {})
            prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
            
            is_double_elim = False
            if target_week < 10:
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, key=f"is_double_chk_w{target_week}")
            
            baker_options = ["--Select Baker--"] + active_bakers

            with st.form(key=f"weekly_form_w{target_week}"):
                weekly_picks = {}
                
                if target_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_options, index=0)
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place", baker_options, index=0, key="t1_w10")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, index=0, key="t2_w10")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, index=0, key="t3_w10")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                    
                elif target_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, index=0)
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, index=0, key="e1_w9")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, index=0, key="e2_w9")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options, index=0, key="e_w9")
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place", baker_options, index=0, key="t1_w9")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, index=0, key="t2_w9")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, index=0, key="t3_w9")
                    t4 = st.selectbox("Technical 4th Place", baker_options, index=0, key="t4_w9")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]

                elif target_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, index=0, key="sb_w8")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, index=0, key="inline_w8")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, index=0, key="e1_w8")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, index=0, key="e2_w8")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, index=0, key="tr_w8")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, index=0, key="e_w8")
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, index=0, key="tr_w8")
                    
                    st.write("Predict Technical Challenge Final Rank (1st through 5th):")
                    t1 = st.selectbox("Technical 1st Place", baker_options, index=0, key="t1_w8")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, index=0, key="t2_w8")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, index=0, key="t3_w8")
                    t4 = st.selectbox("Technical 4th Place", baker_options, index=0, key="t4_w8")
                    t5 = st.selectbox("Technical 5th Place", baker_options, index=0, key="t5_w8")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    
                else:
                    # Standard Weeks 2-7
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, index=0, key=f"sb_w{target_week}")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, index=0, key=f"inline_w{target_week}")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, index=0, key=f"e1_w{target_week}")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, index=0, key=f"e2_w{target_week}")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, index=0, key=f"tr_w{target_week}")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, index=0, key=f"e_w{target_week}")
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, index=0, key=f"tr_w{target_week}")
                        
                    st.markdown("---")
                    st.write("Predict Top 3 Technical Challenge Placements:")
                    t1 = st.selectbox("Technical 1st Place", baker_options, index=0, key=f"t1_w{target_week}")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, index=0, key=f"t2_w{target_week}")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, index=0, key=f"t3_w{target_week}")
                    
                    st.write("Predict Bottom 3 Technical Challenge Placements:")
                    b1 = st.selectbox("Technical 3rd-to-Last Place", baker_options, index=0, key=f"b1_w{target_week}")
                    b2 = st.selectbox("Technical 2nd-to-Last Place", baker_options, index=0, key=f"b2_w{target_week}")
                    b3 = st.selectbox("Technical Last Place", baker_options, index=0, key=f"b3_w{target_week}")
                    
                    weekly_picks["tech_top_3"] = [t1, t2, t3]
                    weekly_picks["tech_bottom_3"] = [b1, b2, b3]

                submit_ballot = st.form_submit_button(f"Submit Predictions for Week {target_week}")
                
                if submit_ballot:
                    # Collect episodic picks
                    episodic_picks = []
                    if "star_baker" in weekly_picks: episodic_picks.append(weekly_picks["star_baker"])
                    if "show_champion" in weekly_picks: episodic_picks.append(weekly_picks["show_champion"])
                    if "in_line_sb" in weekly_picks: episodic_picks.append(weekly_picks["in_line_sb"])
                    if "in_trouble" in weekly_picks: episodic_picks.append(weekly_picks["in_trouble"])
                    
                    elim_p = weekly_picks.get("eliminated")
                    if isinstance(elim_p, list):
                        episodic_picks.extend(elim_p)
                    elif elim_p is not None:
                        episodic_picks.append(elim_p)
                        
                    tech_picks = weekly_picks.get("tech_rank", []) + weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])

                    if "--Select Baker--" in episodic_picks or "--Select Baker--" in tech_picks:
                        st.error("⚠️ Please select a valid baker for all prediction fields!")
                    elif len(set(episodic_picks)) != len(episodic_picks):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    elif len(set(tech_picks)) != len(tech_picks):
                        st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                    else:
                        st.session_state.league_members[selected_player]["weekly_picks"][target_week] = weekly_picks
                        
                        ai_picks = generate_ai_brian_weekly_picks(target_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][target_week] = ai_picks
                        
                        st.success(f"Predictions submitted successfully for {selected_player} for Week {target_week}! AI Brian has also submitted his randomized picks.")


# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles for the Series 17 Bakers:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS, key="analytics_baker_select")
    
    col_img, col_details = st.columns([1, 2])
    with col_img:
        b_img = load_baker_image(selected_baker)
        if b_img is not None:
            st.image(b_img, caption=selected_baker, use_container_width=True)
        else:
            st.info(f"No image file found for {selected_baker} in assets/.")
    with col_details:
        st.subheader(f"Baker Profile: {selected_baker}")
        b_info = BAKER_INFO.get(selected_baker, {})
        st.markdown(f"[🔗 Official Show Profile Page]({b_info.get('url', '#')})")


# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Use this tab to input the actual results from the broadcast. Submitting actual results will score the predictions and update the leaderboard!")
    
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.info("🔒 Admin Panel Locked. Please enter the Administrator PIN to access controls.")
        admin_pin_input = st.text_input("Enter Admin PIN:", type="password", max_chars=4, key="admin_pin_gate")
        if st.button("Unlock Admin Panel"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN!")
    else:
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.markdown("---")
        
        admin_week_choice = st.selectbox("Select Week to Input Broadcast Results For:", [f"Week {w}" for w in range(1, 11)], key="admin_week_selectbox")
        admin_week = int(admin_week_choice.split(" ")[1])

        current_eliminated = eliminated_bakers_by_week.get(admin_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        with st.form(key=f"admin_actuals_form_w{admin_week}"):
            st.subheader(f"Input Broadcast Results for Week {admin_week}")
            actuals = {}
            
            if admin_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers, index=0)
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0, key="act_t1_w10")
                act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0, key="act_t2_w10")
                act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="act_t3_w10")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
                
            elif admin_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0, key="act_sb_w9")
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")], index=0, key="act_e_w9")
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week. Consolation and other categories are scored normally.")
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], index=0, key="admin_act_elim_1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), act_elim_1]], index=0, key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0, key="act_t1_w9")
                act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0, key="act_t2_w9")
                act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="act_t3_w9")
                act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="act_t4_w9")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

            elif admin_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0, key="act_sb_w8")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")], key="act_inline_w8")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0, key="act_e_w8")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_tr_w8")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_tr_grace_w8")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key="admin_act_elim_1_w8")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], index=0, key="admin_act_elim_2_w8")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_tr_dbl_w8")
                    
                st.write("Actual Technical Challenge Rankings (1st through 5th):")
                act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0, key="act_t1_w8")
                act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0, key="act_t2_w8")
                act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="act_t3_w8")
                act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="act_t4_w8")
                act_t5 = st.selectbox("Actual Technical 5th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], index=0, key="act_t5_w8")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
                
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0, key=f"act_sb_w{admin_week}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")], key=f"act_inline_w{admin_week}")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{admin_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0, key=f"act_e_w{admin_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"act_tr_w{admin_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"act_tr_grace_w{admin_week}")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key=f"admin_act_elim_1_w{admin_week}")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], index=0, key=f"admin_act_elim_2_w{admin_week}")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"act_tr_dbl_w{admin_week}")
                    
                st.write("Actual Top 3 Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0, key=f"act_t1_w{admin_week}")
                act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0, key=f"act_t2_w{admin_week}")
                act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key=f"act_t3_w{admin_week}")
                actuals["tech_top_3"] = [act_t1, act_t2, act_t3]
                
                st.write("Actual Bottom 3 Technical Challenge Rankings:")
                rem_bottom_bakers = [b for b in active_bakers if b not in actuals["tech_top_3"]]
                act_b1 = st.selectbox("Actual Technical 3rd-to-Last", rem_bottom_bakers, index=0, key=f"act_b1_w{admin_week}")
                act_b2 = st.selectbox("Actual Technical 2nd-to-Last", [b for b in rem_bottom_bakers if b != act_b1], index=0, key=f"act_b2_w{admin_week}")
                act_b3 = st.selectbox("Actual Technical Last", [b for b in rem_bottom_bakers if b not in [act_b1, act_b2]], index=0, key=f"act_b3_w{admin_week}")
                actuals["tech_bottom_3"] = [act_b1, act_b2, act_b3]
                
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            act_hs_cnt = st.number_input("Handshakes Count", min_value=0, value=0, key=f"hs_cnt_w{admin_week}")
            act_hs_stamps = st.text_input("Handshake Descriptions & Timestamps", value="", key=f"hs_stamps_w{admin_week}")

            st.markdown("### 😢 Crying Incidents")
            act_cry_cnt = st.number_input("Crying Incidents Count", min_value=0, value=0, key=f"cry_cnt_w{admin_week}")
            act_cry_stamps = st.text_input("Crying Descriptions & Timestamps", value="", key=f"cry_stamps_w{admin_week}")

            st.markdown("### 💬 Sexual Innuendos")
            act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=0, key=f"inn_cnt_w{admin_week}")
            act_inn_stamps = st.text_input("Sexual Innuendos Descriptions & Timestamps", value="", key=f"inn_stamps_w{admin_week}")

            actuals["handshake_count"] = act_hs_cnt
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt
            actuals["innuendo_timestamps"] = act_inn_stamps
                
            if admin_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", active_bakers, key="act_win_w10")
                
                st.write("Actual Semifinalists (Select 4):")
                a_s1 = st.selectbox("Semifinalist #1", ALL_BAKERS, key="a_s1")
                a_s2 = st.selectbox("Semifinalist #2", ALL_BAKERS, key="a_s2")
                a_s3 = st.selectbox("Semifinalist #3", ALL_BAKERS, key="a_s3")
                a_s4 = st.selectbox("Semifinalist #4", ALL_BAKERS, key="a_s4")
                act_semis = [a_s1, a_s2, a_s3, a_s4]
                
                st.write("Actual Finalists (Select 3):")
                a_f1 = st.selectbox("Finalist #1", ALL_BAKERS, key="a_f1")
                a_f2 = st.selectbox("Finalist #2", ALL_BAKERS, key="a_f2")
                a_f3 = st.selectbox("Finalist #3", ALL_BAKERS, key="a_f3")
                act_finalists = [a_f1, a_f2, a_f3]
                
                act_handshakes = st.number_input("Actual Total Handshakes", min_value=0, value=5, key="act_hs_tot")
                act_crying = st.number_input("Actual Total Crying Scenes", min_value=0, value=12, key="act_cry_tot")
                act_innuendos = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48, key="act_inn_tot")
                
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }
                
            submit_actuals = st.form_submit_button(f"Publish Actual Results for Week {admin_week} & Recalculate Standings")
            
            if submit_actuals:
                st.session_state.weekly_results[admin_week] = actuals
                if admin_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # TRIGGER RECALCULATION
                for member_name in st.session_state.league_members:
                    st.session_state.league_members[member_name]["total_score"] = 0
                    st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                    
                all_weeks_scored = sorted(list(st.session_state.weekly_results.keys()))
                
                for w in all_weeks_scored:
                    act_w = st.session_state.weekly_results[w]
                    
                    weekly_raw = {}
                    for m_name, m_data in st.session_state.league_members.items():
                        pred_w = m_data["weekly_picks"].get(w, {})
                        raw_score = calculate_weekly_score(pred_w, act_w, w)
                        weekly_raw[m_name] = raw_score
                        m_data["weekly_breakdown"][w] = raw_score
                        
                    if weekly_raw:
                        max_raw = max(weekly_raw.values())
                        for m_name, raw_s in weekly_raw.items():
                            if raw_s == max_raw:
                                st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                
                if st.session_state.season_results:
                    for m_name, m_data in st.session_state.league_members.items():
                        season_pred = m_data["season_picks"]
                        season_score = calculate_season_score(season_pred, st.session_state.season_results)
                        m_data["season_score"] = season_score
                        
                for m_name, m_data in st.session_state.league_members.items():
                    weekly_total = sum(m_data["weekly_breakdown"].values())
                    season_total = m_data.get("season_score", 0)
                    m_data["total_score"] = weekly_total + season_total
                    
                st.success(f"Results published for Week {admin_week}! Leaderboard updated successfully.")
                st.rerun()

        # --- PLAYER PASSWORD RESET ---
        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_ALPHABETICAL, key="admin_pwd_reset_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"Password PIN for {reset_player} has been cleared! They can now set a new 4-digit PIN on the Submit Predictions tab.")

        # --- ERASE ALL SAVED DATA ---
        st.markdown("---")
        st.markdown("### 🚨 Erase All Saved Data (Reset App State)")
        st.write("Use this feature after testing to wipe all test predictions, weekly broadcast actuals, disputes, and player passwords back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords", key="confirm_erase_chk")
        if st.button("Erase All Saved Data & Reset Application", type="primary"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["weekly_picks"] = {}
                    st.session_state.league_members[m_name]["season_picks"] = {}
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    st.session_state.league_members[m_name]["pin"] = None
                    st.session_state.league_members[m_name]["season_score"] = 0
                st.success("All saved data, test predictions, actuals, disputes, and player PINs have been permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed with erasing all data.")
