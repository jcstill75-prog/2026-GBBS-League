import streamlit as st
import pandas as pd
import random
from PIL import Image
import os
import io

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for cozy baking theme
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
    .status-box {
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FFB74D;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    # --- A. Main Episode Results ---
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion != "--Select Baker--" and pred_champion == act_champion:
            score += 15
    else:
        p_sb = predictions.get("star_baker")
        a_sb = actuals.get("star_baker")
        if p_sb and a_sb and p_sb != "--Select Baker--" and p_sb == a_sb:
            score += 5
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if act_elim == "None" or act_elim == "--Select Baker--":
            pass
        elif isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p != "--Select Baker--" and p in act_elim:
                        score += 5
            elif isinstance(pred_elim, str) and pred_elim != "--Select Baker--":
                if pred_elim in act_elim:
                    score += 5
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim != "--Select Baker--" and pred_elim == act_elim:
                score += 5
            
    # --- B. Technical Challenge (Dynamic Scaling) ---
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        clean_p = [b for b in pred_rank if b and b != "--Select Baker--"]
        clean_a = [b for b in act_rank if b and b != "--Select Baker--"]
        
        if week == 8 and len(clean_p) == 5 and len(clean_a) == 5:
            exact_count = sum(1 for idx, b in enumerate(clean_p) if clean_a[idx] == b)
            if exact_count == 5:
                score += 25
            else:
                for idx, b in enumerate(clean_p):
                    if clean_a[idx] == b:
                        if idx in [0, 4]:
                            score += 3
                        else:
                            score += 2
        elif week == 9 and len(clean_p) == 4 and len(clean_a) == 4:
            exact_count = sum(1 for idx, b in enumerate(clean_p) if clean_a[idx] == b)
            if exact_count == 4:
                score += 20
            else:
                for idx, b in enumerate(clean_p):
                    if clean_a[idx] == b:
                        if idx in [0, 3]:
                            score += 3
                        else:
                            score += 2
        elif week == 10 and len(clean_p) == 3 and len(clean_a) == 3:
            exact_count = sum(1 for idx, b in enumerate(clean_p) if clean_a[idx] == b)
            if exact_count == 3:
                score += 15
            else:
                for idx, b in enumerate(clean_p):
                    if clean_a[idx] == b:
                        if idx == 0:
                            score += 3
                        else:
                            score += 2
    else:
        # Standard Weeks 2-7
        pred_top3 = [b for b in predictions.get("tech_top_3", []) if b != "--Select Baker--"]
        act_top3 = [b for b in actuals.get("tech_top_3", []) if b != "--Select Baker--"]
        
        if len(pred_top3) == 3 and len(act_top3) == 3:
            if pred_top3 == act_top3:
                score += 10
            else:
                if pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] == act_top3[2]: score += 2
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3 and baker != act_top3[idx]:
                        score += 1
                        
        pred_bottom3 = [b for b in predictions.get("tech_bottom_3", []) if b != "--Select Baker--"]
        act_bottom3 = [b for b in actuals.get("tech_bottom_3", []) if b != "--Select Baker--"]
        
        if len(pred_bottom3) == 3 and len(act_bottom3) == 3:
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
        p_in_line = predictions.get("in_line_sb")
        a_in_line = actuals.get("in_line_sb", [])
        a_sb = actuals.get("star_baker")
        if p_in_line and p_in_line != "--Select Baker--" and (p_in_line in a_in_line) and (p_in_line != a_sb):
            score += 2
            
        p_trouble = predictions.get("in_trouble")
        a_trouble = actuals.get("in_trouble", [])
        if p_trouble and p_trouble != "--Select Baker--" and (p_trouble in a_trouble):
            score += 2
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return 0
        
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner != "--Select Baker--":
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
        
    pred_semis = [b for b in predictions.get("semifinalists", []) if b != "--Select Baker--"]
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
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
    """Smart case-insensitive and multi-extension image loader."""
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    try:
        for filename in os.listdir("assets"):
            stem, ext = os.path.splitext(filename)
            if stem.lower().strip() == target and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                full_path = os.path.join("assets", filename)
                try:
                    return Image.open(full_path)
                except Exception:
                    pass
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

ROSTER_HUMANS = [
    "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", 
    "Taliah", "Tressa"
]

ROSTER_MEMBERS = ROSTER_HUMANS + ["AI Brian"]

def get_current_eliminated_bakers(week):
    elim_schedule = {
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
    return elim_schedule.get(week, [])

# Initialize session state cleanly
if "league_members" not in st.session_state:
    st.session_state.league_members = {}

for m in ROSTER_MEMBERS:
    if m not in st.session_state.league_members:
        st.session_state.league_members[m] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

if "player_passwords" not in st.session_state:
    st.session_state.player_passwords = {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

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
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank,
            "in_line_sb": in_line_sb,
            "in_trouble": in_trouble
        }
    else:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        remaining_for_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(remaining_for_bottom, min(3, len(remaining_for_bottom))) if remaining_for_bottom else []
            
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3,
            "in_line_sb": in_line_sb,
            "in_trouble": in_trouble
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. HEADER LAYOUT ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    logo_path = None
    for bp in ["normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.jpg", "assets/normanbeaver.png"]:
        if os.path.exists(bp):
            logo_path = bp
            break
    if logo_path:
        st.image(logo_path, width=110)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)

with col_title:
    st.title("Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: POINTS REFERENCE GUIDE ONLY ---
with st.sidebar:
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of what points are at stake for each prediction!")
    st.warning("⏰ **Weekly voting window ends on Tuesdays right before the show airs in the UK.**")
    
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(if picked winner makes Top 3 but loses)*
        * **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        * **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        * **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        * **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Standard Weeks (Weeks 2-7)", expanded=False):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts
        * **In Line (Star Baker consolation):** 2 pts
        * **In Trouble (Elimination consolation):** 2 pts
        * **Top 3 Technical Challenge:**
            * *Exact:* 3 pts for 1st, 2 pts for 2nd/3rd
            * *Wrong Spot:* 1 pt for any correct Top 3 baker
            * *Combo Sweep:* **10 pts** *(flat)*
        * **Bottom 3 Technical Challenge:**
            * *Exact:* 2 pts for 9th/10th, 3 pts for 11th
            * *Wrong Spot:* 1 pt for any correct Bottom 3 baker
            * *Combo Sweep:* **10 pts** *(flat)*
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)
        
    with st.expander("🏁 Weeks 8, 9 & 10 (Dynamic Scaling)", expanded=False):
        st.markdown("""
        * **Week 8 (Quarterfinal episodic - 5 bakers):**
            * *Star Baker:* 5 pts
            * *Eliminated:* 5 pts
            * *Technical:* Exact positions 1st/5th (3 pts), 2nd/3rd/4th (2 pts)
            * *Perfect 5-for-5 Sweep:* **25 pts** *(flat)*
        * **Week 9 (Semifinal episodic - 4 bakers):**
            * *Star Baker:* 5 pts
            * *Eliminated:* 5 pts
            * *Technical:* Exact positions 1st/4th (3 pts), 2nd/3rd (2 pts)
            * *Perfect 4-for-4 Sweep:* **20 pts** *(flat)*
        * **Week 10 (Grand Finale episodic - 3 bakers):**
            * *Show Champion:* 15 pts
            * *Technical:* Exact positions 1st (3 pts), 2nd/3rd (2 pts)
            * *Perfect 3-for-3 Sweep:* **15 pts** *(flat)*
        """)

# --- MAIN TABS ---
tab_lead, tab_submit, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "👑 Admin Panel"])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_data = []
    for name, data in st.session_state.league_members.items():
        tot_pts = data.get("total_score", 0)
        lb_data.append({
            "member": name,
            "points": tot_pts
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        
        lb_table_data = []
        for rank_idx, row in df_lb.iterrows():
            rank = rank_idx + 1
            m_name = row["member"]
            m_pts = row["points"]
            rank_badge = f"#{rank}"
            if rank == 1: rank_badge = "🥇 #1"
            elif rank == 2: rank_badge = "🥈 #2"
            elif rank == 3: rank_badge = "🥉 #3"
            
            lb_table_data.append({
                "Rank": rank_badge,
                "League Member": m_name,
                "Total Points": f"{m_pts} pts"
            })
            
        df_lb_show = pd.DataFrame(lb_table_data)
        st.dataframe(df_lb_show, hide_index=True, use_container_width=True)

    # Cumulative Season Chaos Totals
    st.markdown("---")
    st.subheader("🔥 Cumulative Season Chaos Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    
    for w_num, w_act in st.session_state.weekly_results.items():
        tot_hs += w_act.get("handshakes", len(w_act.get("handshake_bakers", [])))
        tot_cry += w_act.get("crying", len(w_act.get("crying_bakers", [])))
        tot_inn += w_act.get("innuendos", 0)
        
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Total Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Total Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Total Sexual Innuendos", f"{tot_inn}")

    st.markdown("---")
    st.subheader("📋 View Individual Player Scorecards")
    
    selected_sc_player = st.selectbox("Select Player to View Scorecard:", ROSTER_MEMBERS, index=0)
    
    if selected_sc_player:
        p_data = st.session_state.league_members[selected_sc_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### 👤 **{selected_sc_player}'s Scorecard** — Total Score: `{p_pts} pts`")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("#### **🌟 Season-Long Projections**")
            win_pick = p_season.get("winner", "Not submitted yet")
            semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
            hs_pick = p_season.get("handshakes", "N/A")
            cry_pick = p_season.get("crying", "N/A")
            inn_pick = p_season.get("innuendos", "N/A")
            
            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🏅 **Predicted Other Semifinalists:** {semis_pick}")
            st.write(f"🤝 **Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        with col_s2:
            st.markdown("#### **📅 Weekly Predictions Log**")
            if p_weekly:
                for w_num in sorted(p_weekly.keys()):
                    w_picks = p_weekly[w_num]
                    w_score = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                    with st.expander(f"Week {w_num} Picks ({w_score} pts earned)", expanded=False):
                        st.json(w_picks)
            else:
                st.info(f"No weekly predictions logged for {selected_sc_player} yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Contestants can review episode logging, including video timestamps for Hollywood Handshakes and Crying incidents.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_bakers = ", ".join(w_act.get("crying_bakers", [])) if w_act.get("crying_bakers") else "None"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", "N/A"),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshakes', 0)} ({hs_bakers} @ {hs_stamps})",
                "Crying Events": f"{w_act.get('crying', 0)} ({cry_bakers} @ {cry_stamps})",
                "Innuendos": w_act.get("innuendos", 0)
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)

    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, submit a dispute below. Disputes are reviewed democratically by league members on GroupMe.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 1", "Week 2"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Evidence (e.g. 'At 28:14 in Episode 3, Paul clearly shakes Tom's hand')")
            disp_correction = st.text_input("Requested Correction (e.g. 'Add +1 Handshake for Tom in Week 3')")

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
                st.success("Dispute submitted successfully!")

    if st.session_state.disputes:
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Weekly & Seasonal Predictions")
    
    # Automatically calculate active player prediction week based on published Admin broadcast results
    if st.session_state.weekly_results:
        latest_published_week = max(st.session_state.weekly_results.keys())
        active_player_week = min(max(latest_published_week + 1, 2), 10)
    else:
        active_player_week = 2
        
    st.subheader("👤 Player Login & Authentication")
    submitting_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="submit_player_login_select")
    
    saved_pwd = st.session_state.player_passwords.get(submitting_player)
    authenticated = False
    
    if saved_pwd is None:
        st.info(f"Welcome, **{submitting_player}**! Create a 4-digit PIN password to secure your prediction ballot.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            new_p1 = st.text_input("Create 4-Digit PIN", type="password", max_chars=4, key=f"create_p1_{submitting_player}")
        with col_p2:
            new_p2 = st.text_input("Confirm 4-Digit PIN", type="password", max_chars=4, key=f"create_p2_{submitting_player}")
            
        if st.button("Set 4-Digit PIN & Unlock Ballot", key=f"btn_set_pin_{submitting_player}"):
            if len(new_p1) != 4 or not new_p1.isdigit():
                st.error("PIN must be exactly 4 numeric digits!")
            elif new_p1 != new_p2:
                st.error("PINs do not match! Please check and try again.")
            else:
                st.session_state.player_passwords[submitting_player] = new_p1
                st.session_state[f"authenticated_player_{submitting_player}"] = True
                st.success(f"PIN created successfully for {submitting_player}! Your ballot is unlocked.")
                st.rerun()
    else:
        with st.form(f"player_login_form_{submitting_player}"):
            entered_pwd = st.text_input("Enter Your 4-Digit PIN", type="password", max_chars=4, key=f"login_pwd_{submitting_player}")
            login_submitted = st.form_submit_button("Submit Password / Unlock Ballot")
            
            if login_submitted:
                if entered_pwd == saved_pwd:
                    st.session_state[f"authenticated_player_{submitting_player}"] = True
                    st.success(f"🔓 Authenticated as **{submitting_player}**!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect 4-digit PIN! Please try again or ask the Admin to reset your password.")

    if st.session_state.get(f"authenticated_player_{submitting_player}", False):
        authenticated = True
        
    if authenticated:
        col_auth_msg, col_auth_logout = st.columns([4, 1])
        with col_auth_msg:
            st.success(f"🔓 Currently Unlocked Ballot for: **{submitting_player}**")
        with col_auth_logout:
            if st.button("🔒 Lock Profile", key=f"btn_logout_{submitting_player}"):
                st.session_state[f"authenticated_player_{submitting_player}"] = False
                st.rerun()
                
        st.markdown("---")
        with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
            st.write("Review photographs and official show links for the Series 17 bakers:")
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
                        st.markdown(f"[🔗 View {baker}'s Show Profile]({info['url']})")
                    st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(f"📅 Submit Predictions: Week {active_player_week}")
        st.info(f"ℹ️ **Voting Notice:** Accepting predictions for **Week {active_player_week}** (Week 1 was the scouting phase). Ballots lock prior to the broadcast on Tuesdays.")
        
        current_eliminated = get_current_eliminated_bakers(active_player_week)
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_options = ["--Select Baker--"] + active_bakers
        
        prev_week_num = active_player_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        st.info(f"Active Bakers in the Tent for Week {active_player_week}: " + ", ".join(active_bakers))
        
        is_double_elim = False
        if active_player_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, help="Check to enable picking 2 eliminated bakers for double elimination!")
        
        # 1. Post-Week 1 Season Long Predictions (Locks in Week 2)
        if active_player_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_options, key="user_win_pick")
                
                rem_bakers_semis = [b for b in active_bakers if b != user_winner]
                st.write("Predict Other 3 Semifinalists [10 pts each | 30 pts max]:")
                s1 = st.selectbox("Semifinalist #1", ["--Select Baker--"] + rem_bakers_semis, key="s1_pick")
                s2 = st.selectbox("Semifinalist #2", ["--Select Baker--"] + [b for b in rem_bakers_semis if b != s1], key="s2_pick")
                s3 = st.selectbox("Semifinalist #3", ["--Select Baker--"] + [b for b in rem_bakers_semis if b not in [s1, s2]], key="s3_pick")
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key="user_hs_num")
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key="user_cry_num")
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key="user_inn_num")
                
                if st.button("Lock Season-Long Predictions"):
                    semis_picks = [s1, s2, s3]
                    if "--Select Baker--" in [user_winner] + semis_picks:
                        st.error("⚠️ Please select a valid baker for all Season-Long prediction fields!")
                    elif None in [user_handshakes, user_crying, user_innuendos]:
                        st.error("⚠️ Please enter a predicted count for Handshakes, Crying, and Innuendos!")
                    else:
                        st.session_state.league_members[submitting_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": semis_picks,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        st.success(f"Season-Long Predictions locked successfully for {submitting_player}!")

        # 2. Weekly Ballot
        st.markdown("### Weekly Predictions Ballot")
        with st.form(f"weekly_ballot_form_{submitting_player}_w{active_player_week}"):
            weekly_picks = {}
            
            if active_player_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_options)
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, index=0, key="w10_t1")
                t2_opts = ["--Select Baker--"] + [b for b in active_bakers if b != t1]
                t2 = st.selectbox("Technical 2nd Place [2 pts]", t2_opts, index=0, key="w10_t2")
                t3_opts = ["--Select Baker--"] + [b for b in active_bakers if b not in [t1, t2]]
                t3 = st.selectbox("Technical 3rd Place [2 pts]", t3_opts, index=0, key="w10_t3")
                weekly_picks["tech_rank"] = [t1, t2, t3]
                
            elif active_player_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options)
                if is_double_elim:
                    elim1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="w9_el1")
                    elim2_opts = ["--Select Baker--"] + [b for b in active_bakers if b != elim1]
                    elim2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", elim2_opts, key="w9_el2")
                    weekly_picks["eliminated"] = [elim1, elim2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w9_el")
                    
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, index=0, key="w9_t1")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", ["--Select Baker--"] + [b for b in active_bakers if b != t1], index=0, key="w9_t2")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", ["--Select Baker--"] + [b for b in active_bakers if b not in [t1, t2]], index=0, key="w9_t3")
                t4 = st.selectbox("Technical 4th Place [3 pts]", ["--Select Baker--"] + [b for b in active_bakers if b not in [t1, t2, t3]], index=0, key="w9_t4")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]
                
            elif active_player_week == 8:
                col_w8_1, col_w8_2 = st.columns(2)
                with col_w8_1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="w8_sb")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="w8_inline")
                with col_w8_2:
                    if is_double_elim:
                        elim1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="w8_el1")
                        elim2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", ["--Select Baker--"] + [b for b in active_bakers if b != elim1], key="w8_el2")
                        weekly_picks["eliminated"] = [elim1, elim2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="w8_trbl")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w8_el")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="w8_trbl")
                        
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, index=0, key="w8_t1")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", ["--Select Baker--"] + [b for b in active_bakers if b != t1], index=0, key="w8_t2")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", ["--Select Baker--"] + [b for b in active_bakers if b not in [t1, t2]], index=0, key="w8_t3")
                t4 = st.selectbox("Technical 4th Place [2 pts]", ["--Select Baker--"] + [b for b in active_bakers if b not in [t1, t2, t3]], index=0, key="w8_t4")
                t5 = st.selectbox("Technical 5th Place [3 pts]", ["--Select Baker--"] + [b for b in active_bakers if b not in [t1, t2, t3, t4]], index=0, key="w8_t5")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                
            else:
                # Standard Weeks 2-7
                col_std1, col_std2 = st.columns(2)
                with col_std1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key=f"std_sb_w{active_player_week}")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key=f"std_inline_w{active_player_week}")
                with col_std2:
                    if is_double_elim:
                        elim1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key=f"std_el1_w{active_player_week}")
                        elim2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", ["--Select Baker--"] + [b for b in active_bakers if b != elim1], key=f"std_el2_w{active_player_week}")
                        weekly_picks["eliminated"] = [elim1, elim2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key=f"std_trbl_w{active_player_week}")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key=f"std_el_w{active_player_week}")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key=f"std_trbl_w{active_player_week}")
                        
                st.markdown("---")
                st.write("Predict Technical Challenge Individual Positions:")
                col_top1, col_top2, col_top3 = st.columns(3)
                with col_top1:
                    std_t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key=f"t1_pos_w{active_player_week}")
                with col_top2:
                    t2_avail = ["--Select Baker--"] + [b for b in active_bakers if b != std_t1]
                    std_t2 = st.selectbox("Technical 2nd Place [2 pts]", t2_avail, key=f"t2_pos_w{active_player_week}")
                with col_top3:
                    t3_avail = ["--Select Baker--"] + [b for b in active_bakers if b not in [std_t1, std_t2]]
                    std_t3 = st.selectbox("Technical 3rd Place [2 pts]", t3_avail, key=f"t3_pos_w{active_player_week}")
                    
                col_bot1, col_bot2, col_bot3 = st.columns(3)
                with col_bot1:
                    b3_avail = ["--Select Baker--"] + [b for b in active_bakers if b not in [std_t1, std_t2, std_t3]]
                    std_b3 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", b3_avail, key=f"b3_pos_w{active_player_week}")
                with col_bot2:
                    b2_avail = ["--Select Baker--"] + [b for b in active_bakers if b not in [std_t1, std_t2, std_t3, std_b3]]
                    std_b2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", b2_avail, key=f"b2_pos_w{active_player_week}")
                with col_bot3:
                    blast_avail = ["--Select Baker--"] + [b for b in active_bakers if b not in [std_t1, std_t2, std_t3, std_b3, std_b2]]
                    std_blast = st.selectbox("Technical Last Place [3 pts]", blast_avail, key=f"blast_pos_w{active_player_week}")
                    
                weekly_picks["tech_top_3"] = [std_t1, std_t2, std_t3]
                weekly_picks["tech_bottom_3"] = [std_b3, std_b2, std_blast]
                
            submit_ballot = st.form_submit_button(f"Submit Week {active_player_week} Predictions Ballot")
            
            if submit_ballot:
                has_blank = False
                for k, v in weekly_picks.items():
                    if isinstance(v, list):
                        if "--Select Baker--" in v:
                            has_blank = True
                    elif v == "--Select Baker--":
                        has_blank = True
                        
                if has_blank:
                    st.error("⚠️ Please select a valid baker for all weekly prediction fields!")
                else:
                    st.session_state.league_members[submitting_player]["weekly_picks"][active_player_week] = weekly_picks
                    ai_picks = generate_ai_brian_weekly_picks(active_player_week, active_bakers, is_double_elim=is_double_elim)
                    st.session_state.league_members["AI Brian"]["weekly_picks"][active_player_week] = ai_picks
                    st.success(f"Predictions successfully submitted for {submitting_player} (Week {active_player_week})!")


# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Use this tab to input broadcast actuals, score predictions, and manage player PIN passwords.")
    
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Lock Screen**")
        with st.form("admin_login_form"):
            admin_pin_input = st.text_input("Enter Admin Security PIN Password", type="password", max_chars=4, key="admin_pin_login_input")
            admin_login_btn = st.form_submit_button("Unlock Admin Panel")
            if admin_login_btn:
                if admin_pin_input == "6284":
                    st.session_state.admin_authenticated = True
                    st.success("Admin Security PIN verified! Unlocking console...")
                    st.rerun()
                else:
                    st.error("❌ Incorrect Admin PIN. Access denied!")
    else:
        st.success("🔓 **Authenticated as League Administrator**")
        if st.button("🔒 Lock Admin Console", key="btn_lock_admin"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        with st.expander("🔑 Player Password PIN Management & Reset", expanded=False):
            p_to_reset = st.selectbox("Select Player Profile to Reset Password PIN:", ["--Select Player--"] + ROSTER_HUMANS, key="admin_reset_player_select")
            if p_to_reset != "--Select Player--":
                cur_p_status = "Locked 🔒" if st.session_state.player_passwords.get(p_to_reset) else "Unset 🔓"
                st.write(f"Current PIN Status for **{p_to_reset}**: `{cur_p_status}`")
                if st.button(f"Clear Password PIN for {p_to_reset}", key=f"btn_clear_pin_{p_to_reset}"):
                    st.session_state.player_passwords[p_to_reset] = None
                    st.session_state[f"authenticated_player_{p_to_reset}"] = False
                    st.success(f"Password PIN for {p_to_reset} cleared! They can now set a new PIN on their next visit.")
                    st.rerun()

        st.markdown("---")
        st.write("Select week to record or review official broadcast results:")
        
        # Default index to latest published week or 0 (Week 1)
        default_admin_idx = 0
        if st.session_state.weekly_results:
            default_admin_idx = min(max(st.session_state.weekly_results.keys()) - 1, 9)
            
        admin_selected_week = st.selectbox(
            "Select Week to Record or Review Official Broadcast Results:",
            list(range(1, 11)),
            index=default_admin_idx,
            key="admin_week_selectbox"
        )
        
        admin_eliminated = get_current_eliminated_bakers(admin_selected_week)
        admin_active_bakers = [b for b in ALL_BAKERS if b not in admin_eliminated]
        admin_baker_options = ["--Select Baker--"] + admin_active_bakers
        
        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_baker_options, key="adm_sc_w10")
                st.write("Actual Technical Challenge Final Ranks:")
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_baker_options, index=0, key="adm_w10_t1")
                act_t2 = st.selectbox("Actual Technical 2nd Place", ["--Select Baker--"] + [b for b in admin_active_bakers if b != act_t1], index=0, key="adm_w10_t2")
                act_t3 = st.selectbox("Actual Technical 3rd Place", ["--Select Baker--"] + [b for b in admin_active_bakers if b not in [act_t1, act_t2]], index=0, key="adm_w10_t3")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
                
                st.markdown("### 🏆 Final Seasonal Broadcast Totals (Week 10)")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", admin_baker_options, index=0, key="act_winner_w10")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, default=[], key="act_semis_w10")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, default=[], key="act_finalists_w10")
                act_handshakes_tot = st.number_input("Actual Total Handshakes across Season", min_value=0, value=5, key="act_hs_tot_w10")
                act_crying_tot = st.number_input("Actual Total Crying Scenes across Season", min_value=0, value=12, key="act_cry_tot_w10")
                act_innuendos_tot = st.number_input("Actual Total Sexual Innuendos across Season", min_value=0, value=48, key="act_inn_tot_w10")
                
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes_tot,
                    "crying": act_crying_tot,
                    "innuendos": act_innuendos_tot
                }
                
            elif admin_selected_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key="adm_sb_w9")
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", ["--Select Baker--"] + [b for b in admin_active_bakers if b != actuals.get("star_baker")], key="adm_el_w9")
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    el1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, key="adm_el1_w9")
                    el2 = st.selectbox("Actual Eliminated Baker #2", ["--Select Baker--"] + [b for b in admin_active_bakers if b != el1], key="adm_el2_w9")
                    actuals["eliminated"] = [el1, el2]
                    
                st.write("Actual Technical Challenge Final Ranks:")
                act_t1 = st.selectbox("Actual Technical 1st", admin_baker_options, index=0, key="adm_w9_t1")
                act_t2 = st.selectbox("Actual Technical 2nd", ["--Select Baker--"] + [b for b in admin_active_bakers if b != act_t1], index=0, key="adm_w9_t2")
                act_t3 = st.selectbox("Actual Technical 3rd", ["--Select Baker--"] + [b for b in admin_active_bakers if b not in [act_t1, act_t2]], index=0, key="adm_w9_t3")
                act_t4 = st.selectbox("Actual Technical 4th", ["--Select Baker--"] + [b for b in admin_active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="adm_w9_t4")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

            elif admin_selected_week == 8:
                col_adm1, col_adm2 = st.columns(2)
                with col_adm1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key="adm_sb_w8")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in admin_active_bakers if b != actuals.get("star_baker")], key="adm_inline_w8")
                with col_adm2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, key="adm_el_w8")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in admin_active_bakers if b != actuals.get("eliminated")], key="adm_trbl_w8")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", admin_active_bakers, key="adm_trbl_w8")
                    else:
                        el1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, key="adm_el1_w8")
                        el2 = st.selectbox("Actual Eliminated Baker #2", ["--Select Baker--"] + [b for b in admin_active_bakers if b != el1], key="adm_el2_w8")
                        actuals["eliminated"] = [el1, el2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in admin_active_bakers if b not in actuals["eliminated"]], key="adm_trbl_w8")
                        
                st.write("Actual Technical Challenge Final Ranks (1st through 5th):")
                act_t1 = st.selectbox("Actual Technical 1st", admin_baker_options, index=0, key="adm_w8_t1")
                act_t2 = st.selectbox("Actual Technical 2nd", ["--Select Baker--"] + [b for b in admin_active_bakers if b != act_t1], index=0, key="adm_w8_t2")
                act_t3 = st.selectbox("Actual Technical 3rd", ["--Select Baker--"] + [b for b in admin_active_bakers if b not in [act_t1, act_t2]], index=0, key="adm_w8_t3")
                act_t4 = st.selectbox("Actual Technical 4th", ["--Select Baker--"] + [b for b in admin_active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="adm_w8_t4")
                act_t5 = st.selectbox("Actual Technical 5th", ["--Select Baker--"] + [b for b in admin_active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], index=0, key="adm_w8_t5")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
                
            else:
                col_adm1, col_adm2 = st.columns(2)
                with col_adm1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key=f"adm_sb_w{admin_selected_week}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in admin_active_bakers if b != actuals.get("star_baker")], key=f"adm_inline_w{admin_selected_week}")
                with col_adm2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, key=f"adm_el_w{admin_selected_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in admin_active_bakers if b != actuals.get("eliminated")], key=f"adm_trbl_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", admin_active_bakers, key=f"adm_trbl_w{admin_selected_week}")
                    else:
                        el1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, key=f"adm_el1_w{admin_selected_week}")
                        el2 = st.selectbox("Actual Eliminated Baker #2", ["--Select Baker--"] + [b for b in admin_active_bakers if b != el1], key=f"adm_el2_w{admin_selected_week}")
                        actuals["eliminated"] = [el1, el2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in admin_active_bakers if b not in actuals["eliminated"]], key=f"adm_trbl_w{admin_selected_week}")
                        
                st.markdown("---")
                st.markdown(f"### 📊 Actual Technical Challenge Rankings (1st through {len(admin_active_bakers)}th Place)")
                num_bakers = len(admin_active_bakers)
                cols_per_row = 3
                admin_tech_ranks = []
                
                for i in range(num_bakers):
                    rank_num = i + 1
                    ord_str = "1st" if rank_num == 1 else ("2nd" if rank_num == 2 else ("3rd" if rank_num == 3 else f"{rank_num}th"))
                    if i % cols_per_row == 0:
                        t_cols = st.columns(min(cols_per_row, num_bakers - i))
                    col = t_cols[i % cols_per_row]
                    with col:
                        key_r = f"adm_full_tech_w{admin_selected_week}_r{rank_num}"
                        already_picked = [b for b in admin_tech_ranks if b != "--Select Baker--"]
                        avail_opts = ["--Select Baker--"] + [b for b in admin_active_bakers if b not in already_picked]
                        sel_b = st.selectbox(f"Actual Technical {ord_str} Place", avail_opts, index=0, key=key_r)
                        admin_tech_ranks.append(sel_b)
                        
                actuals["tech_rank"] = admin_tech_ranks
                if len(admin_tech_ranks) >= 3:
                    actuals["tech_top_3"] = admin_tech_ranks[:3]
                    actuals["tech_bottom_3"] = admin_tech_ranks[-3:]
                else:
                    actuals["tech_top_3"] = admin_tech_ranks
                    actuals["tech_bottom_3"] = admin_tech_ranks

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes Logging")
            col_hs1, col_hs2 = st.columns(2)
            with col_hs1:
                act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", admin_active_bakers, key=f"hs_bakers_w{admin_selected_week}")
                act_hs_count = st.number_input("Field 1: Handshakes Count (Auto-calculated from selections)", min_value=0, value=len(act_hs_bakers), key=f"hs_cnt_w{admin_selected_week}")
            with col_hs2:
                act_hs_stamps = st.text_input("Field 2: Handshakes Descriptions & Timestamps", value="", placeholder="e.g. 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper'", key=f"hs_desc_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents Logging")
            col_cry1, col_cry2 = st.columns(2)
            with col_cry1:
                act_cry_count = st.number_input("Field 1: Crying Incidents Count in Episode", min_value=0, value=0, key=f"cry_cnt_w{admin_selected_week}")
            with col_cry2:
                act_cry_stamps = st.text_input("Field 2: Crying Descriptions & Timestamps (Circumstances)", value="", placeholder="e.g. 'Mo after the technical @ 34:12'", key=f"cry_desc_w{admin_selected_week}")

            st.markdown("### 💬 Sexual Innuendos Logging")
            col_inn1, col_inn2 = st.columns(2)
            with col_inn1:
                act_inn_count = st.number_input("Field 1: Sexual Innuendos Count in Episode", min_value=0, value=0, key=f"inn_cnt_w{admin_selected_week}")
            with col_inn2:
                act_inn_stamps = st.text_input("Field 2: Sexual Innuendos Descriptions & Timestamps", value="", placeholder="e.g. 'Paul @ 18:05 Soggy Bottom, Prue @ 31:40 Soggy Sponge'", key=f"inn_desc_w{admin_selected_week}")

            actuals["handshake_bakers"] = act_hs_bakers
            actuals["handshakes"] = act_hs_count
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying"] = act_cry_count
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendos"] = act_inn_count
            actuals["innuendo_timestamps"] = act_inn_stamps

            submit_actuals = st.form_submit_button("Publish Broadcast Results & Recalculate Standings")
            if submit_actuals:
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # Recalculate standings across all scored weeks
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}

                scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
                for w in scored_weeks:
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
                            if raw_s == max_raw and raw_s > 0:
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

                st.success(f"Broadcast results published for Week {admin_selected_week}! All player predictions scored and standings recalculated.")
