import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import os
import base64
import glob

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
    .status-box {
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FFB74D;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. THE 2026 OFFICIAL SCORING ENGINE (INTERNALIZED FOR PORTABILITY) ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
    # --- A. Main Episode Results ---
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15  # Buffed show champion prediction
    else:
        if predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
        
        # Sickness / Double Elimination Safe Scoring for standard weeks
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim:
                        score += 5
            elif isinstance(pred_elim, str):
                if pred_elim in act_elim:
                    score += 5
        elif act_elim == "None":
            pass # 0 points for elimination in a grace week
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim == act_elim:
                score += 5
            
    # --- B. Technical Challenge (Dynamic Scaling) ---
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 5:
                score += 25  # Flat 25 pts for perfect sweep of 5 bakers
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 4]:
                            score += 3  # 1st and 5th
                        else:
                            score += 2  # 2nd, 3rd, 4th
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                score += 20  # Flat 20 pts for perfect sweep
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 3]:
                            score += 3  # 1st and 4th
                        else:
                            score += 2  # 2nd and 3rd
                    
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
                score += 15  # Flat 15 pts for perfect sweep
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx == 0:
                            score += 3
                        else:
                            score += 2
    else:
        # Standard Weeks 2-7
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        
        if len(pred_top3) == 3 and len(act_top3) == 3:
            if pred_top3 == act_top3:
                score += 10  # Perfect Top 3 Combo Bonus
            else:
                if pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] == act_top3[2]: score += 2
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3 and baker != act_top3[idx]:
                        score += 1
                        
        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        
        if len(pred_bottom3) == 3 and len(act_bottom3) == 3:
            if pred_bottom3 == act_bottom3:
                score += 10  # Perfect Bottom 3 Combo Bonus
            else:
                if pred_bottom3[0] == act_bottom3[0]: score += 2
                if pred_bottom3[1] == act_bottom3[1]: score += 2
                if pred_bottom3[2] == act_bottom3[2]: score += 3
                for idx, baker in enumerate(pred_bottom3):
                    if baker in act_bottom3 and baker != act_bottom3[idx]:
                        score += 1

    # --- C. Consolations ---
    if week < 9:
        if (predictions.get("in_line_sb") in actuals.get("in_line_sb", [])) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2  # Balanced down from 3
        # UPDATED: In trouble matching any nominee awards +2 points, regardless of elimination status
        if predictions.get("in_trouble") in actuals.get("in_trouble", []):
            score += 2  # +2 pts whenever baker was nominated in trouble
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    # 1. Season Winner (40 points) or finalist consolation (15 points)
    pred_winner = predictions.get("winner")
    if pred_winner == act_winner:
        score += 40
    elif pred_winner in act_finalists:
        score += 15
        
    # 2. Other 3 Semifinalists (10 pts each)
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
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
    """Smart case-insensitive image loader for show bakers."""
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    for fname in os.listdir("assets"):
        stem, ext = os.path.splitext(fname)
        if stem.lower().strip() == target and ext.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
            try:
                return Image.open(os.path.join("assets", fname))
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

# 15 Official Fantasy Roster Members - Alphabetized
ROSTER_ALPHABETICAL = [
    "AI Brian", "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", 
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

# Global Eliminated Bakers Mapping by Week
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

# Streamlit Session State Initialization for persistence
if "league_members" not in st.session_state:
    st.session_state.league_members = {}

# Ensure all 15 roster members exist in session state
for m_name in ROSTER_ALPHABETICAL:
    if m_name not in st.session_state.league_members:
        st.session_state.league_members[m_name] = {
            "pin": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

if "current_week" not in st.session_state:
    st.session_state.current_week = 2

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

# Generate AI Brian's long-term picks if empty
if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. APP INTERFACE LAYOUT ---
# Header with Norman Beaver Logo
header_col1, header_col2 = st.columns([1, 5])
with header_col1:
    norman_path = "normanbeaver.jpg"
    if not os.path.exists(norman_path):
        norman_path = "assets/normanbeaver.jpg"
    if os.path.exists(norman_path):
        try:
            norman_img = Image.open(norman_path)
            st.image(norman_img, width=110)
        except Exception:
            st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with header_col2:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: GAME CONTROLS & PERSISTENT POINTS REFERENCE GUIDE ---
with st.sidebar:
    st.header("⚙️ Game Controls")
    selected_week = st.slider("Select App Active Week", min_value=1, max_value=10, value=st.session_state.current_week)
    st.session_state.current_week = selected_week

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

# --- MAIN TABS (Admin Panel on the far right) ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Contestant Analytics",
    "👑 Admin Panel"
])

# ==========================================
# --- TAB 1: LEADERBOARD & STANDINGS ---
# ==========================================
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_rows = []
    for m_name in ROSTER_ALPHABETICAL:
        m_data = st.session_state.league_members.get(m_name, {})
        lb_rows.append({
            "member": m_name,
            "points": m_data.get("total_score", 0),
            "data": m_data
        })
        
    df_lb = pd.DataFrame(lb_rows).sort_values(by="points", ascending=False).reset_index(drop=True)
    
    # Format table strictly with Rank, League Member, Total Points
    display_lb = []
    for idx, row in df_lb.iterrows():
        rank_num = idx + 1
        rank_str = f"#{rank_num}"
        if rank_num == 1: rank_str = "🥇 #1"
        elif rank_num == 2: rank_str = "🥈 #2"
        elif rank_num == 3: rank_str = "🥉 #3"
        
        display_lb.append({
            "Rank": rank_str,
            "League Member": row["member"],
            "Total Points": f"{row['points']} pts"
        })
        
    st.dataframe(pd.DataFrame(display_lb), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecard & Projections")
    
    sc_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="sb_scorecard_player")
    p_data = st.session_state.league_members.get(sc_player, {})
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(f"### **{sc_player}'s Season Projections**")
        st.write(f"🏆 **Predicted Winner:** {p_season.get('winner', 'Not submitted yet')}")
        semis_str = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        st.write(f"🏅 **Predicted Semifinalists:** {semis_str}")
        st.write(f"🤝 **Predicted Handshakes:** {p_season.get('handshakes', 'N/A')}")
        st.write(f"😢 **Predicted Crying Incidents:** {p_season.get('crying', 'N/A')}")
        st.write(f"💬 **Predicted Sexual Innuendos:** {p_season.get('innuendos', 'N/A')}")
        
    with col_s2:
        st.markdown("### **Weekly Predictions Log**")
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
            st.info("No weekly prediction ballots submitted yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Review logged broadcast outcomes, video timestamps, and total category occurrences:")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet.")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_cnt = w_act.get("handshake_count", 0)
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
                "Crying Incidents": f"{cry_cnt} ({cry_stamps})",
                "Innuendos": f"{inn_cnt} ({inn_stamps})"
            })

        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
        st.markdown(f"### **Cumulative Category Occurrences:** 🤝 Total Handshakes: `{tot_hs}` | 😢 Total Crying Incidents: `{tot_cry}` | 💬 Total Sexual Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("📝 Submit a Result Dispute / Timestamp Correction")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene, submit a dispute below for democratic GroupMe review:")

    with st.expander("📝 Submit Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile:", ROSTER_ALPHABETICAL, key="disp_player_sel")
            disp_week = st.selectbox("Week to Contest:", [f"Week {w}" for w in range(1, 11)], key="disp_week_sel")
            disp_cat = st.selectbox("Category Contested:", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Context (e.g. 'At 28:14 in Episode 3, Paul clearly shakes Tom's hand')")
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
                st.success("Dispute logged successfully! It is now visible below for democratic review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)


# ==========================================
# --- TAB 2: SUBMIT PREDICTIONS ---
# ==========================================
with tab_submit:
    st.header("📝 Submit Player Predictions")
    
    # 1. Player Authentication
    auth_player = st.selectbox("Select Your Player Profile:", ROSTER_ALPHABETICAL, key="auth_player_select")
    player_pin = st.session_state.league_members[auth_player].get("pin")
    
    authenticated = False
    if player_pin is None:
        st.info(f"Welcome {auth_player}! Please create a 4-digit password PIN to unlock your prediction ballot.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            new_pin = st.text_input("Create 4-Digit Password PIN:", type="password", key="new_pin_input")
        with col_p2:
            confirm_pin = st.text_input("Confirm 4-Digit Password PIN:", type="password", key="confirm_pin_input")
            
        if st.button(f"Save Password PIN for {auth_player}"):
            if len(new_pin) == 4 and new_pin.isdigit():
                if new_pin == confirm_pin:
                    st.session_state.league_members[auth_player]["pin"] = new_pin
                    st.success("Password PIN created successfully! Your ballot is now unlocked.")
                    st.rerun()
                else:
                    st.error("Passwords do not match! Please verify your 4-digit PIN.")
            else:
                st.error("PIN must be exactly 4 numeric digits!")
    else:
        entered_pin = st.text_input(f"Enter 4-Digit Password PIN for {auth_player}:", type="password", key="login_pin_input")
        if entered_pin == player_pin:
            authenticated = True
            st.success(f"🔓 Authenticated as {auth_player}")
        elif entered_pin:
            st.error("Incorrect Password PIN!")

    if authenticated:
        st.markdown("---")
        # Visual Baker Gallery
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
                        st.info(f"📸 {baker}")
                        st.markdown(f"[🔗 Profile]({info['url']})")

        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_options = ["--Select Baker--"] + active_bakers

        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")

        st.subheader(f"📅 Prediction Ballot: Week {st.session_state.current_week}")
        st.info(f"Active Bakers in the Tent: " + ", ".join(active_bakers))

        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)

        # Season Long Projections if Week 2
        if st.session_state.current_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Projections (Locks Now! | 130 pts total at stake)", expanded=True):
                s_win = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts runner-up]", baker_options, key="s_win_sel")
                s_rem = [b for b in active_bakers if b != s_win]
                s_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", s_rem, max_selections=3)
                s_hs = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                s_cry = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                s_inn = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)

                if st.button("Lock Season-Long Predictions"):
                    if s_win == "--Select Baker--" or len(s_semis) != 3:
                        st.error("Please select a valid winner and exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members[auth_player]["season_picks"] = {
                            "winner": s_win,
                            "semifinalists": s_semis,
                            "handshakes": s_hs,
                            "crying": s_cry,
                            "innuendos": s_inn
                        }
                        st.success("Season-long projections locked successfully!")

        st.markdown("### Weekly Ballot")
        with st.form("weekly_ballot_form"):
            weekly_picks = {}
            
            if st.session_state.current_week == 10:
                champ = st.selectbox("Predict Show Champion [15 pts]", baker_options)
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="t1_w10")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="t2_w10")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="t3_w10")
                weekly_picks["show_champion"] = champ
                weekly_picks["tech_rank"] = [t1, t2, t3]
            elif st.session_state.current_week == 9:
                sb = st.selectbox("Predict Star Baker [5 pts]", baker_options)
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="e1_w9")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="e2_w9")
                    weekly_picks["eliminated"] = [e1, e2]
                else:
                    e = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="e_w9")
                    weekly_picks["eliminated"] = e
                sb_val = sb
                weekly_picks["star_baker"] = sb_val

                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="t1_w9")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="t2_w9")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="t3_w9")
                t4 = st.selectbox("Technical 4th Place [3 pts]", baker_options, key="t4_w9")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]
            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    sb = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="sb_w8")
                    inl = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="inl_w8")
                    weekly_picks["star_baker"] = sb
                    weekly_picks["in_line_sb"] = inl
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="e1_w8")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="e2_w8")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        e = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="e_w8")
                        weekly_picks["eliminated"] = e
                    intr = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="intr_w8")
                    weekly_picks["in_trouble"] = intr

                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", baker_options, key="t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", baker_options, key="t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    sb = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="sb_std")
                    inl = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="inl_std")
                    weekly_picks["star_baker"] = sb
                    weekly_picks["in_line_sb"] = inl
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="e1_std")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="e2_std")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        e = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="e_std")
                        weekly_picks["eliminated"] = e
                    intr = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="intr_std")
                    weekly_picks["in_trouble"] = intr

                st.write("Top 3 Technical Placements:")
                tt1 = st.selectbox("1st Place", baker_options, key="tt1_std")
                tt2 = st.selectbox("2nd Place", baker_options, key="tt2_std")
                tt3 = st.selectbox("3rd Place", baker_options, key="tt3_std")
                
                st.write("Bottom 3 Technical Placements:")
                tb1 = st.selectbox("3rd-to-Last Place", baker_options, key="tb1_std")
                tb2 = st.selectbox("2nd-to-Last Place", baker_options, key="tb2_std")
                tb3 = st.selectbox("Last Place", baker_options, key="tb3_std")

                weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]

            sub_ballot = st.form_submit_button("Submit Predictions")
            if sub_ballot:
                # Validation 1: Unselected placeholders
                all_picks_list = []
                for k, v in weekly_picks.items():
                    if isinstance(v, list): all_picks_list.extend(v)
                    else: all_picks_list.append(v)
                    
                if "--Select Baker--" in all_picks_list:
                    st.error("⚠️ Please select a valid baker for all prediction fields!")
                else:
                    # Validation 2: Duplicate check in main picks
                    main_picks = []
                    for k in ["star_baker", "in_line_sb", "in_trouble", "show_champion"]:
                        if k in weekly_picks: main_picks.append(weekly_picks[k])
                    if "eliminated" in weekly_picks:
                        if isinstance(weekly_picks["eliminated"], list): main_picks.extend(weekly_picks["eliminated"])
                        else: main_picks.append(weekly_picks["eliminated"])
                        
                    if len(main_picks) != len(set(main_picks)):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    else:
                        # Validation 3: Duplicate check in technical picks
                        tech_picks = []
                        if "tech_rank" in weekly_picks: tech_picks = weekly_picks["tech_rank"]
                        else: tech_picks = weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])
                        
                        if len(tech_picks) != len(set(tech_picks)):
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            # Save Picks
                            st.session_state.league_members[auth_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                            
                            # Trigger AI Brian
                            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                            
                            st.success(f"Predictions successfully submitted for Week {st.session_state.current_week}! AI Brian has also submitted his picks.")


# ==========================================
# --- TAB 3: CONTESTANT ANALYTICS ---
# ==========================================
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles for the Series 17 Bakers:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS)
    
    col_img, col_details = st.columns([1, 2])
    with col_img:
        b_img = load_baker_image(selected_baker)
        if b_img is not None:
            st.image(b_img, caption=selected_baker, use_container_width=True)
        else:
            st.info(f"📸 {selected_baker}")
    with col_details:
        st.subheader(f"Baker Profile: {selected_baker}")
        b_info = BAKER_INFO.get(selected_baker, {})
        st.markdown(f"[🔗 Official Show Profile Page]({b_info.get('url', '#')})")


# ==========================================
# --- TAB 4: ADMIN PANEL (Password Protected PIN 6284) ---
# ==========================================
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
        
    if not st.session_state.admin_authenticated:
        st.info("🔒 Admin Panel is locked. Please enter the Administrator PIN to access controls.")
        admin_pin_input = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_prompt")
        if st.button("Unlock Admin Panel"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN! Access denied.")
    else:
        col_adm1, col_adm2 = st.columns([4, 1])
        with col_adm1:
            st.success("🔓 Authenticated as Administrator")
        with col_adm2:
            if st.button("🔒 Lock Admin Panel"):
                st.session_state.admin_authenticated = False
                st.rerun()
                
        st.write("Input official broadcast outcomes to score player predictions and update the Live Leaderboard:")
        
        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
            actuals = {}
            
            if st.session_state.current_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers, index=0)
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0)
                act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0)
                act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0)
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            elif st.session_state.current_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")], index=0)
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    e1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], index=0, key="adm_e1_w9")
                    e2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), e1]], index=0, key="adm_e2_w9")
                    actuals["eliminated"] = [e1, e2]
                
                st.write("Actual Technical Challenge Rankings (Every Position Separately):")
                tech_p = []
                for p_idx in range(len(active_bakers)):
                    rem_b = [b for b in active_bakers if b not in tech_p]
                    sel_b = st.selectbox(f"Actual Technical Position #{p_idx+1}", rem_b, index=0, key=f"adm_tech_p{p_idx}_w9")
                    tech_p.append(sel_b)
                actuals["tech_rank"] = tech_p
            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0)
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")])
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key="adm_e1_w8")
                        e2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != e1], index=0, key="adm_e2_w8")
                        actuals["eliminated"] = [e1, e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])

                st.write("Actual Technical Challenge Rankings (Every Position Separately):")
                tech_p = []
                for p_idx in range(len(active_bakers)):
                    rem_b = [b for b in active_bakers if b not in tech_p]
                    sel_b = st.selectbox(f"Actual Technical Position #{p_idx+1}", rem_b, index=0, key=f"adm_tech_p{p_idx}_w8")
                    tech_p.append(sel_b)
                actuals["tech_rank"] = tech_p
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_std")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0)
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")])
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key="adm_e1_std")
                        e2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != e1], index=0, key="adm_e2_std")
                        actuals["eliminated"] = [e1, e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])

                st.write("Actual Technical Challenge Rankings (Every Position Separately):")
                tech_p = []
                for p_idx in range(len(active_bakers)):
                    rem_b = [b for b in active_bakers if b not in tech_p]
                    sel_b = st.selectbox(f"Actual Technical Position #{p_idx+1}", rem_b, index=0, key=f"adm_tech_p{p_idx}_std")
                    tech_p.append(sel_b)
                
                actuals["tech_top_3"] = tech_p[:3] if len(tech_p) >= 3 else tech_p
                actuals["tech_bottom_3"] = tech_p[-3:] if len(tech_p) >= 3 else tech_p
                actuals["full_tech_rank"] = tech_p

            # --- CHAOS CATEGORIES (2 FIELDS EACH) ---
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            act_hs_cnt = st.number_input("Handshakes Count in Episode", min_value=0, value=0, key="adm_hs_cnt")
            act_hs_stamps = st.text_input("Handshakes Descriptions & Timestamps (e.g. 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper')", key="adm_hs_stamps")

            st.markdown("### 😢 Crying Incidents")
            act_cry_cnt = st.number_input("Crying Incidents Count in Episode", min_value=0, value=0, key="adm_cry_cnt")
            act_cry_stamps = st.text_input("Crying Descriptions & Timestamps (e.g. 'Gabe @ 24:15 Technical, Molly @ 54:02 Elimination')", key="adm_cry_stamps")

            st.markdown("### 💬 Sexual Innuendos")
            act_inn_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0, key="adm_inn_cnt")
            act_inn_stamps = st.text_input("Sexual Innuendos Descriptions & Timestamps (e.g. 'Paul @ 18:05 Soggy Bottom, Prue @ 31:40 Soggy Sponge')", key="adm_inn_stamps")

            actuals["handshake_count"] = act_hs_cnt
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt
            actuals["innuendo_timestamps"] = act_inn_stamps

            if st.session_state.current_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", active_bakers)
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
                act_handshakes = st.number_input("Actual Total Handshakes", min_value=0, value=5)
                act_crying = st.number_input("Actual Total Crying Scenes", min_value=0, value=12)
                act_innuendos = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48)
                
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }

            sub_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if sub_actuals:
                st.session_state.weekly_results[st.session_state.current_week] = actuals
                if st.session_state.current_week == 10:
                    st.session_state.season_results = actuals_season

                # Recalculate Standings
                for m_name in ROSTER_ALPHABETICAL:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}

                scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
                for w in scored_weeks:
                    act_w = st.session_state.weekly_results[w]
                    weekly_raw = {}
                    for m_name in ROSTER_ALPHABETICAL:
                        m_data = st.session_state.league_members[m_name]
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
                    for m_name in ROSTER_ALPHABETICAL:
                        m_data = st.session_state.league_members[m_name]
                        s_pred = m_data["season_picks"]
                        s_score = calculate_season_score(s_pred, st.session_state.season_results)
                        m_data["season_score"] = s_score

                for m_name in ROSTER_ALPHABETICAL:
                    m_data = st.session_state.league_members[m_name]
                    w_tot = sum(m_data["weekly_breakdown"].values())
                    s_tot = m_data.get("season_score", 0)
                    m_data["total_score"] = w_tot + s_tot

                st.success("Leaderboard updated! All player predictions scored cleanly.")

        # --- PLAYER PASSWORD RESET (BOTTOM SECTION 1) ---
        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their 4-digit password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_ALPHABETICAL, key="adm_pwd_reset_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"Password PIN for {reset_player} has been cleared! They can now create a new 4-digit PIN on the Submit Predictions tab.")

        # --- ERASE ALL SAVED DATA (VERY BOTTOM SECTION 2) ---
        st.markdown("---")
        st.markdown("### 🚨 Erase All Saved Data (Reset App State)")
        st.write("Use this feature after testing to wipe all test predictions, weekly broadcast actuals, disputes, and player passwords back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords", key="confirm_erase_chk")
        if st.button("Erase All Saved Data & Reset Application", type="primary"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                for m_name in ROSTER_ALPHABETICAL:
                    st.session_state.league_members[m_name] = {
                        "pin": None,
                        "weekly_picks": {},
                        "season_picks": {},
                        "total_score": 0,
                        "weekly_breakdown": {}
                    }
                st.success("All saved data, test predictions, actuals, disputes, and player PINs have been permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed with erasing all data.")
