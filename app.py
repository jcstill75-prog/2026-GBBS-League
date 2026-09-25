import streamlit as st
import pandas as pd
import random
import os
import base64
import json
import glob
from PIL import Image

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for a baking theme
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
</style>
""", unsafe_allow_html=True)


# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
    # --- A. Main Episode Results ---
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion != "--Select Baker--" and pred_champion == act_champion:
            score += 15  # Buffed show champion prediction
    else:
        pred_sb = predictions.get("star_baker")
        act_sb = actuals.get("star_baker")
        if pred_sb and act_sb and pred_sb != "--Select Baker--" and pred_sb == act_sb:
            score += 5
        
        # Elimination scoring
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p != "--Select Baker--" and p in act_elim:
                        score += 5
            elif isinstance(pred_elim, str) and pred_elim != "--Select Baker--":
                if pred_elim in act_elim:
                    score += 5
        elif act_elim == "None":
            pass # 0 points for elimination in a grace week
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim and act_elim != "--Select Baker--":
                    score += 5
            elif pred_elim == act_elim and pred_elim != "--Select Baker--":
                score += 5
            
    # --- B. Technical Challenge ---
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        # Filter out placeholders
        clean_pred = [b for b in pred_rank if b != "--Select Baker--"]
        clean_act = [b for b in act_rank if b != "--Select Baker--"]
        
        if week == 8 and len(clean_pred) == 5 and len(clean_act) == 5:
            exact_count = sum(1 for idx, b in enumerate(clean_pred) if clean_act[idx] == b)
            if exact_count == 5:
                score += 25  # Flat 25 pts for perfect sweep
            else:
                for idx, b in enumerate(clean_pred):
                    if clean_act[idx] == b:
                        if idx in [0, 4]:
                            score += 3
                        else:
                            score += 2
        elif week == 9 and len(clean_pred) == 4 and len(clean_act) == 4:
            exact_count = sum(1 for idx, b in enumerate(clean_pred) if clean_act[idx] == b)
            if exact_count == 4:
                score += 20  # Flat 20 pts for perfect sweep
            else:
                for idx, b in enumerate(clean_pred):
                    if clean_act[idx] == b:
                        if idx in [0, 3]:
                            score += 3
                        else:
                            score += 2
                    
        elif week == 10 and len(clean_pred) == 3 and len(clean_act) == 3:
            exact_count = sum(1 for idx, b in enumerate(clean_pred) if clean_act[idx] == b)
            if exact_count == 3:
                score += 15  # Flat 15 pts for perfect sweep
            else:
                for idx, b in enumerate(clean_pred):
                    if clean_act[idx] == b:
                        if idx == 0:
                            score += 3
                        else:
                            score += 2
    else:
        # Standard Weeks 2-7
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        
        clean_pred_top = [b for b in pred_top3 if b != "--Select Baker--"]
        clean_act_top = [b for b in act_top3 if b != "--Select Baker--"]
        
        if len(clean_pred_top) == 3 and len(clean_act_top) == 3:
            if clean_pred_top == clean_act_top:
                score += 10  # Perfect Top 3 Combo Bonus
            else:
                if clean_pred_top[0] == clean_act_top[0]: score += 3
                if clean_pred_top[1] == clean_act_top[1]: score += 2
                if clean_pred_top[2] == clean_act_top[2]: score += 2
                for idx, baker in enumerate(clean_pred_top):
                    if baker in clean_act_top and baker != clean_act_top[idx]:
                        score += 1
                        
        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        
        clean_pred_bot = [b for b in pred_bottom3 if b != "--Select Baker--"]
        clean_act_bot = [b for b in act_bottom3 if b != "--Select Baker--"]
        
        if len(clean_pred_bot) == 3 and len(clean_act_bot) == 3:
            if clean_pred_bot == clean_act_bot:
                score += 10  # Perfect Bottom 3 Combo Bonus
            else:
                if clean_pred_bot[0] == clean_act_bot[0]: score += 2
                if clean_pred_bot[1] == clean_act_bot[1]: score += 2
                if clean_pred_bot[2] == clean_act_bot[2]: score += 3
                for idx, baker in enumerate(clean_pred_bot):
                    if baker in clean_act_bot and baker != clean_act_bot[idx]:
                        score += 1

    # --- C. Consolations ---
    if week < 9:
        p_in_line = predictions.get("in_line_sb")
        a_in_line = actuals.get("in_line_sb", [])
        if p_in_line and p_in_line != "--Select Baker--" and (p_in_line in a_in_line) and (p_in_line != actuals.get("star_baker")):
            score += 2
            
        p_in_trouble = predictions.get("in_trouble")
        a_in_trouble = actuals.get("in_trouble", [])
        if p_in_trouble and p_in_trouble != "--Select Baker--" and (p_in_trouble in a_in_trouble):
            score += 2  # +2 pts so long as predicted baker matches an actual in_trouble nominee
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    # 1. Season Winner (40 points) or finalist consolation (15 points)
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner != "--Select Baker--":
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
        
    # 2. Other 3 Semifinalists (10 pts each)
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker != "--Select Baker--" and baker in act_semis and baker != pred_winner:
            score += 10
            
    # 3. Hollywood Handshakes (Spot-on = 20 pts, +/- 1 = 10 pts)
    pred_handshakes = predictions.get("handshakes")
    act_handshakes = actuals.get("handshakes")
    if pred_handshakes is not None and act_handshakes is not None:
        if pred_handshakes == act_handshakes:
            score += 20
        elif abs(pred_handshakes - act_handshakes) <= 1:
            score += 10
            
    # 4. Crying Events (Spot-on = 20 pts, +/- 5 = 10 pts)
    pred_crying = predictions.get("crying")
    act_crying = actuals.get("crying")
    if pred_crying is not None and act_crying is not None:
        if pred_crying == act_crying:
            score += 20
        elif abs(pred_crying - act_crying) <= 5:
            score += 10
            
    # 5. Sexual Innuendos (Spot-on = 20 pts, +/- 5 = 10 pts)
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
    for ext in ["jpg", "jpeg", "png", "webp"]:
        filename = f"{target}.{ext}"
        filepath = os.path.join("assets", filename)
        if os.path.exists(filepath):
            try:
                return Image.open(filepath)
            except Exception:
                pass
    try:
        for f in os.listdir("assets"):
            if f.lower().startswith(target) and f.lower().split(".")[-1] in ["jpg", "jpeg", "png", "webp"]:
                return Image.open(os.path.join("assets", f))
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

# Alphabetical Roster (15 Members)
ROSTER_ALPHABETICAL = [
    "AI Brian", "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", 
    "Stacy C.", "Taliah", "Tressa"
]

# Human Player Roster (Excludes AI Brian)
ROSTER_HUMANS = [m for m in ROSTER_ALPHABETICAL if m != "AI Brian"]

# Streamlit Session State Initialization for persistence
if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for m in ROSTER_ALPHABETICAL:
        st.session_state.league_members[m] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None
        }

# Ensure all profiles have safe keys
for m in ROSTER_ALPHABETICAL:
    if m not in st.session_state.league_members:
        st.session_state.league_members[m] = {
            "weekly_picks": {}, "season_picks": {}, "total_score": 0, "weekly_breakdown": {}, "pin": None
        }
    else:
        st.session_state.league_members[m].setdefault("pin", None)
        st.session_state.league_members[m].setdefault("weekly_picks", {})
        st.session_state.league_members[m].setdefault("season_picks", {})
        st.session_state.league_members[m].setdefault("total_score", 0)
        st.session_state.league_members[m].setdefault("weekly_breakdown", {})

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}  # {week_num: actuals_dict}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []  # [{week, category, timestamp_evidence, correction, player, status}]

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False


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
    elim_pool = list(active_bakers)
    star_baker = random.choice(active_bakers)
    elim_pool = [b for b in elim_pool if b != star_baker]
    
    if week == 10:
        champion = random.choice(active_bakers)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"show_champion": champion, "tech_rank": tech_rank}
    elif week == 9:
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_rank": tech_rank
        }
    else:
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        
        top3_pool = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bot = [b for b in active_bakers if b not in top3_pool]
        bot3_pool = random.sample(rem_bot, min(3, len(rem_bot)))
        
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_top_3": top3_pool,
            "tech_bottom_3": bot3_pool
        }


# Auto-generate AI Brian's long-term picks if empty
if not st.session_state.league_members["AI Brian"].get("season_picks"):
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()


# --- 5. APP INTERFACE LAYOUT & HEADER ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    for norman_path in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "assets/normanbeaver.png"]:
        if os.path.exists(norman_path):
            try:
                st.image(norman_path, width=100)
                break
            except Exception:
                pass

with col_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")


# Determine current competition week based on published results
if not st.session_state.weekly_results:
    st.session_state.current_week = 2  # Week 1 is scouting phase; Week 2 ballot is active
else:
    latest_published_week = max(st.session_state.weekly_results.keys())
    st.session_state.current_week = min(10, latest_published_week + 1)


# --- SIDEBAR: PERSISTENT POINTS REMINDER ---
with st.sidebar:
    st.header("📌 Competition Progress")
    if not st.session_state.weekly_results:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nPost-Week 1 Season Predictions & Week 2 Ballot are now open!")
    else:
        last_w = max(st.session_state.weekly_results.keys())
        st.success(f"✅ **Results Published Through: Week {last_w}**\n\nPredictions for **Week {st.session_state.current_week}** are currently active.")

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
        *   **In Trouble (Elimination consolation):** 2 pts *(if nominee matches)*
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
    
    # Compile scoring for all 15 members
    lb_data = []
    for name in ROSTER_ALPHABETICAL:
        data = st.session_state.league_members.get(name, {})
        tot_pts = data.get("total_score", 0)
        lb_data.append({
            "member": name,
            "points": tot_pts,
            "data": data
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        
        # Build clean leaderboard table
        lb_display_rows = []
        for rank_idx, row in df_lb.iterrows():
            rank_num = rank_idx + 1
            rank_badge = f"#{rank_num}"
            if rank_num == 1: rank_badge = "🥇 #1"
            elif rank_num == 2: rank_badge = "🥈 #2"
            elif rank_num == 3: rank_badge = "🥉 #3"
            
            lb_display_rows.append({
                "Rank": rank_badge,
                "League Member": row["member"],
                "Total Points": f"{row['points']} pts"
            })
            
        df_lb_display = pd.DataFrame(lb_display_rows)
        st.dataframe(df_lb_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    st.write("Select a player below from the dropdown menu to inspect their season-long projections and weekly predictions log:")
    
    sc_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="scorecard_player_sel")
    if sc_player:
        p_data = st.session_state.league_members.get(sc_player, {})
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### 👤 **Scorecard: {sc_player}** (Total Score: `{p_pts} pts`)")
        
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
                    
                    w_rows.append({
                        "Week": f"Week {w_num}",
                        "Star Baker Pick": sb,
                        "Eliminated Pick": el
                    })
                st.dataframe(pd.DataFrame(w_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No weekly prediction ballots recorded yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Broadcast logs will appear here after Episode 2 results are posted!")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count") or 0
            hs_cnt = w_act.get("handshake_count") or len(w_act.get("handshake_bakers", []))
            cry_cnt = w_act.get("crying_count") or 0

            tot_hs += hs_cnt
            tot_cry += cry_cnt
            tot_inn += inn_cnt

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshake Count": hs_cnt,
                "Handshake Details": hs_stamps,
                "Crying Count": cry_cnt,
                "Crying Details": cry_stamps,
                "Innuendos Count": inn_cnt
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

        st.markdown("### 🔥 Cumulative Broadcast Totals")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("🤝 Total Hollywood Handshakes", tot_hs)
        with col_m2:
            st.metric("😢 Total Crying Incidents", tot_cry)
        with col_m3:
            st.metric("💬 Total Sexual Innuendos", tot_inn)

    st.markdown("---")
    st.header("📝 Submit a Result Dispute / Timestamp Correction")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction Form", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ["--Select Your Name--"] + ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 2"])
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
                if disp_player == "--Select Your Name--":
                    st.error("Please select your player profile name before submitting a dispute.")
                else:
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
                    st.markdown(f"[🔗 View {baker}'s Photo Page]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🔐 Player Login & Prediction Ballot")
    
    # Human Player Selection (AI Brian removed)
    sel_player = st.selectbox("Select Your Player Profile:", ["--Select Your Name--"] + ROSTER_HUMANS, key="pred_player_select")
    
    if sel_player != "--Select Your Name--":
        p_info = st.session_state.league_members[sel_player]
        saved_pin = p_info.get("pin")
        
        authenticated = False
        if saved_pin is None:
            st.info(f"👋 First time logging in as **{sel_player}**? Please create your 4-digit PIN below:")
            col_p1, col_s2 = st.columns(2)
            with col_p1:
                new_pin = st.text_input("Create 4-Digit Password PIN:", type="password", max_chars=4, key="new_pin_input")
            with col_s2:
                confirm_pin = st.text_input("Confirm 4-Digit Password PIN:", type="password", max_chars=4, key="confirm_pin_input")
                
            if st.button("Set PIN & Unlock Ballot"):
                if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                    p_info["pin"] = new_pin
                    st.success("4-digit PIN created successfully! Your ballot is now unlocked.")
                    st.rerun()
                else:
                    st.error("PINs must be exactly 4 digits and match!")
        else:
            entered_pin = st.text_input(f"Enter 4-Digit PIN for {sel_player}:", type="password", max_chars=4, key="enter_pin_input")
            if entered_pin == saved_pin:
                authenticated = True
                st.success(f"Welcome back, **{sel_player}**!")
            elif entered_pin:
                st.error("Incorrect PIN! Please try again or ask the Admin to reset your PIN.")
                
        if authenticated:
            st.markdown("---")
            
            # Competition active week determination
            eliminated_bakers_by_week = {
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
            
            active_week = st.session_state.current_week
            current_eliminated = eliminated_bakers_by_week.get(active_week, [])
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            
            baker_dropdown_options = ["--Select Baker--"] + active_bakers
            
            st.subheader(f"📅 Submit Predictions: Week {active_week}")
            st.info(f"Active Bakers in the Tent for Week {active_week}: " + ", ".join(active_bakers))
            
            # Post-Week 1 Season-Long Entry (Available if week is 2)
            if active_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_dropdown_options, key="user_win_pick")
                    user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", active_bakers, max_selections=3)
                    
                    user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=None, placeholder="0", key="user_hs_cnt")
                    user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="0", key="user_cry_cnt")
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="0", key="user_inn_cnt")
                    
                    if st.button("Lock Season-Long Predictions"):
                        if user_winner == "--Select Baker--":
                            st.error("Please select a predicted Season Winner.")
                        elif len(user_semis) != 3:
                            st.error("Please select exactly 3 other semifinalists.")
                        else:
                            p_info["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_handshakes if user_handshakes is not None else 0,
                                "crying": user_crying if user_crying is not None else 0,
                                "innuendos": user_innuendos if user_innuendos is not None else 0
                            }
                            st.success("Season-long predictions saved successfully!")

            # Weekly Ballot
            st.markdown("### Weekly Ballot")
            
            # Toggle for Double Elimination Week predictions
            prev_week_results = st.session_state.weekly_results.get(active_week - 1, {})
            prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
            is_double_elim = False
            if active_week < 10:
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, help="Automatically checked if the previous week was a sickness grace week with no elimination!")

            with st.form("weekly_predictions_form"):
                weekly_picks = {}
                
                if active_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_dropdown_options)
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="p_t1_w10")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="p_t2_w10")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="p_t3_w10")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                    
                elif active_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_dropdown_options)
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_dropdown_options, key="pred_elim_1_w9")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_dropdown_options, key="pred_elim_2_w9")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        e = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_dropdown_options, key="pred_elim_w9")
                        weekly_picks["eliminated"] = e
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="p_t1_w9")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="p_t2_w9")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="p_t3_w9")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", baker_dropdown_options, key="p_t4_w9")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]

                elif active_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_dropdown_options, key="sb_w8")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", baker_dropdown_options, key="inline_w8")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_dropdown_options, key="pred_elim_1_w8")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_dropdown_options, key="pred_elim_2_w8")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated]", baker_dropdown_options, key="trouble_w8_dbl")
                        else:
                            e = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_dropdown_options, key="pred_elim_w8")
                            weekly_picks["eliminated"] = e
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated]", baker_dropdown_options, key="trouble_w8")
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="t1_w8")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="t2_w8")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="t3_w8")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", baker_dropdown_options, key="t4_w8")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", baker_dropdown_options, key="t5_w8")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    
                else:
                    # Standard Weeks 2-7
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_dropdown_options, key="sb_std")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", baker_dropdown_options, key="inline_std")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_dropdown_options, key="pred_elim_1_std")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_dropdown_options, key="pred_elim_2_std")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated]", baker_dropdown_options, key="trouble_std_dbl")
                        else:
                            e = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_dropdown_options, key="pred_elim_std")
                            weekly_picks["eliminated"] = e
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated]", baker_dropdown_options, key="trouble_std")
                        
                    st.markdown("---")
                    st.write("Predict Technical Challenge Placements:")
                    col_t1, col_t2, col_t3 = st.columns(3)
                    with col_t1:
                        top1 = st.selectbox("1st Place Technical", baker_dropdown_options, key="top1_std")
                    with col_t2:
                        top2 = st.selectbox("2nd Place Technical", baker_dropdown_options, key="top2_std")
                    with col_t3:
                        top3 = st.selectbox("3rd Place Technical", baker_dropdown_options, key="top3_std")
                    weekly_picks["tech_top_3"] = [top1, top2, top3]
                    
                    col_b1, col_b2, col_b3 = st.columns(3)
                    with col_b1:
                        bot1 = st.selectbox("3rd-to-Last Technical", baker_dropdown_options, key="bot1_std")
                    with col_b2:
                        bot2 = st.selectbox("2nd-to-Last Technical", baker_dropdown_options, key="bot2_std")
                    with col_b3:
                        bot3 = st.selectbox("Last Place Technical", baker_dropdown_options, key="bot3_std")
                    weekly_picks["tech_bottom_3"] = [bot1, bot2, bot3]

                submitted = st.form_submit_button("Submit Predictions Ballot")
                if submitted:
                    # Check for unselected baker fields
                    all_selected_values = []
                    for k, v in weekly_picks.items():
                        if isinstance(v, list):
                            all_selected_values.extend(v)
                        else:
                            all_selected_values.append(v)
                            
                    if "--Select Baker--" in all_selected_values:
                        st.error("⚠️ Please select a valid baker for all prediction fields!")
                    else:
                        # Check duplicate picks
                        episodic_picks = []
                        for k in ["star_baker", "in_line_sb", "in_trouble"]:
                            if k in weekly_picks: episodic_picks.append(weekly_picks[k])
                        if "eliminated" in weekly_picks:
                            if isinstance(weekly_picks["eliminated"], list):
                                episodic_picks.extend(weekly_picks["eliminated"])
                            else:
                                episodic_picks.append(weekly_picks["eliminated"])
                                
                        tech_picks = []
                        if "tech_rank" in weekly_picks: tech_picks.extend(weekly_picks["tech_rank"])
                        if "tech_top_3" in weekly_picks: tech_picks.extend(weekly_picks["tech_top_3"])
                        if "tech_bottom_3" in weekly_picks: tech_picks.extend(weekly_picks["tech_bottom_3"])
                        
                        has_episodic_dup = len(episodic_picks) != len(set(episodic_picks))
                        has_tech_dup = len(tech_picks) != len(set(tech_picks))
                        
                        if has_episodic_dup:
                            st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                        elif has_tech_dup:
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            p_info["weekly_picks"][active_week] = weekly_picks
                            
                            # Automatically trigger AI Brian picks
                            ai_picks = generate_ai_brian_weekly_picks(active_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][active_week] = ai_picks
                            
                            st.success(f"Predictions submitted successfully for Week {active_week}! AI Brian has also logged his automated picks.")


# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles and show website links for the Series 17 Bakers:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS, key="analytics_baker_sel")
    
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
    
    # Password Protection Check
    if not st.session_state.admin_authenticated:
        st.info("🔒 Admin Panel Locked. Please enter the Administrator PIN to access controls.")
        admin_pin_input = st.text_input("Enter Admin PIN:", type="password", max_chars=4, key="admin_pin_input")
        if st.button("Unlock Admin Panel"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN!")
    else:
        if st.button("🔒 Lock Admin Panel", key="lock_admin_btn"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.write("Input official broadcast results below to score predictions and update the live standings!")
        
        eliminated_bakers_by_week = {
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
        
        active_week = st.session_state.current_week
        current_eliminated = eliminated_bakers_by_week.get(active_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        # Baker options dropdown (does not remove baker names from dropdowns)
        admin_baker_options = ["--Select Baker--"] + active_bakers
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {active_week}")
            actuals = {}
            
            if active_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_baker_options, key="act_champ_w10")
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_baker_options, key="act_t1_w10")
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_baker_options, key="act_t2_w10")
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_baker_options, key="act_t3_w10")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
                
            elif active_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key="act_sb_w9")
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, key="act_elim_w9")
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week. Consolation and other categories are scored normally.")
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, key="admin_act_elim_1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_baker_options, key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st", admin_baker_options, key="act_t1_w9")
                act_t2 = st.selectbox("Actual Technical 2nd", admin_baker_options, key="act_t2_w9")
                act_t3 = st.selectbox("Actual Technical 3rd", admin_baker_options, key="act_t3_w9")
                act_t4 = st.selectbox("Actual Technical 4th", admin_baker_options, key="act_t4_w9")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

            elif active_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key="act_sb_w8")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, key="act_inline_w8")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, key="act_elim_w8")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_trouble_w8")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("No baker was eliminated this week. Predicting elimination scores 0.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, key="act_trouble_w8_sick")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, key="admin_act_elim_1_w8")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_baker_options, key="admin_act_elim_2_w8")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_trouble_w8_dbl")
                    
                st.write("Actual Technical Challenge Rankings (1st through 5th):")
                act_t1 = st.selectbox("Actual Technical 1st", admin_baker_options, key="act_t1_w8")
                act_t2 = st.selectbox("Actual Technical 2nd", admin_baker_options, key="act_t2_w8")
                act_t3 = st.selectbox("Actual Technical 3rd", admin_baker_options, key="act_t3_w8")
                act_t4 = st.selectbox("Actual Technical 4th", admin_baker_options, key="act_t4_w8")
                act_t5 = st.selectbox("Actual Technical 5th", admin_baker_options, key="act_t5_w8")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
                
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key="act_sb_std")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, key="act_inline_std")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_std")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, key="act_elim_std")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_trouble_std")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("No baker was eliminated this week. Predicting elimination scores 0.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, key="act_trouble_std_sick")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, key="admin_act_elim_1_std")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_baker_options, key="admin_act_elim_2_std")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_trouble_std_dbl")
                    
                st.markdown("---")
                st.write("Actual Technical Challenge Placements:")
                col_at1, col_at2, col_at3 = st.columns(3)
                with col_at1:
                    act_top1 = st.selectbox("Actual 1st Place Technical", admin_baker_options, key="act_top1_std")
                with col_at2:
                    act_top2 = st.selectbox("Actual 2nd Place Technical", admin_baker_options, key="act_top2_std")
                with col_at3:
                    act_top3 = st.selectbox("Actual 3rd Place Technical", admin_baker_options, key="act_top3_std")
                actuals["tech_top_3"] = [act_top1, act_top2, act_top3]
                
                col_ab1, col_ab2, col_ab3 = st.columns(3)
                with col_ab1:
                    act_bot1 = st.selectbox("Actual 3rd-to-Last Technical", admin_baker_options, key="act_bot1_std")
                with col_ab2:
                    act_bot2 = st.selectbox("Actual 2nd-to-Last Technical", admin_baker_options, key="act_bot2_std")
                with col_ab3:
                    act_bot3 = st.selectbox("Actual Last Place Technical", admin_baker_options, key="act_bot3_std")
                actuals["tech_bottom_3"] = [act_bot1, act_bot2, act_bot3]
                
            # --- WEEKLY CHAOS CATEGORIES ---
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns([1, 2])
            with col_hs1:
                act_hs_cnt = st.number_input("Handshakes Count in Episode", min_value=0, value=None, placeholder="0", key=f"hs_cnt_w{active_week}")
            with col_hs2:
                act_hs_stamps = st.text_input("Handshake Descriptions & Timestamps", value="", placeholder="e.g., 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper'", key=f"hs_stamps_w{active_week}")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns([1, 2])
            with col_cry1:
                act_cry_cnt = st.number_input("Crying Incidents Count in Episode", min_value=0, value=None, placeholder="0", key=f"cry_cnt_w{active_week}")
            with col_cry2:
                act_cry_stamps = st.text_input("Crying Descriptions & Timestamps", value="", placeholder="e.g., 'Gabe @ 24:15 Technical, Molly @ 54:02 Elimination'", key=f"cry_stamps_w{active_week}")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns([1, 2])
            with col_inn1:
                act_inn_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=None, placeholder="0", key=f"inn_cnt_w{active_week}")
            with col_inn2:
                act_inn_stamps = st.text_input("Innuendos Descriptions & Timestamps", value="", placeholder="e.g., 'Paul @ 18:05 Soggy Bottom, Prue @ 31:40 Soggy Sponge'", key=f"inn_stamps_w{active_week}")

            act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"hs_bakers_w{active_week}")

            actuals["handshake_count"] = act_hs_cnt if act_hs_cnt is not None else 0
            actuals["handshake_bakers"] = act_hs_bakers
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt if act_cry_cnt is not None else 0
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt if act_inn_cnt is not None else 0
            actuals["innuendo_timestamps"] = act_inn_stamps
                
            # If Week 10, also input overall season outcomes
            if active_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", admin_baker_options, key="act_season_winner")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4, key="act_season_semis")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3, key="act_season_finalists")
                
                act_handshakes = st.number_input("Actual Total Handshakes", min_value=0, value=None, placeholder="0", key="act_season_hs")
                act_crying = st.number_input("Actual Total Crying Scenes", min_value=0, value=None, placeholder="0", key="act_season_cry")
                act_innuendos = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=None, placeholder="0", key="act_season_inn")
                
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes if act_handshakes is not None else 0,
                    "crying": act_crying if act_crying is not None else 0,
                    "innuendos": act_innuendos if act_innuendos is not None else 0
                }
                
            submit_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if submit_actuals:
                # Check for unselected required baker options in actuals
                admin_selected_bakers = []
                for k, v in actuals.items():
                    if isinstance(v, str) and v == "--Select Baker--":
                        admin_selected_bakers.append(v)
                    elif isinstance(v, list):
                        if "--Select Baker--" in v:
                            admin_selected_bakers.append("--Select Baker--")
                            
                if admin_selected_bakers:
                    st.error("⚠️ Please select a valid baker for all actual result fields!")
                else:
                    st.session_state.weekly_results[active_week] = actuals
                    if active_week == 10:
                        st.session_state.season_results = actuals_season
                        
                    # Recalculate Standings
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
                            
                        # High scorer bonus (+5 pts)
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
                        
                    st.success(f"Week {active_week} broadcast results published successfully! Standings recalculated.")
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
