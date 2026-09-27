import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import os

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

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
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
        if (predictions.get("in_trouble") in actuals.get("in_trouble", [])) and (predictions.get("in_trouble") != actuals.get("eliminated")):
            score += 2  # Balanced down from 3
            
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

DEFAULT_ROSTER = [
    "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", 
    "Taliah", "Tressa", "AI Brian"
]

# Streamlit Session State Initialization
if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for name in DEFAULT_ROSTER:
        st.session_state.league_members[name] = {
            "total_score": 0,
            "weekly_picks": {},
            "season_picks": {},
            "weekly_breakdown": {},
            "password": "1234"
        }

# Ensure all 15 roster members exist and have passwords
for name in DEFAULT_ROSTER:
    if name not in st.session_state.league_members:
        st.session_state.league_members[name] = {
            "total_score": 0,
            "weekly_picks": {},
            "season_picks": {},
            "weekly_breakdown": {},
            "password": "1234"
        }
    if "password" not in st.session_state.league_members[name]:
        st.session_state.league_members[name]["password"] = "1234"

if "current_week" not in st.session_state:
    st.session_state.current_week = 2

# Automatically determine active prediction week based on published Admin results
if st.session_state.weekly_results:
    latest_published = max(st.session_state.weekly_results.keys())
    st.session_state.current_week = min(latest_published + 1, 10)
else:
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
        return {
            "show_champion": champion,
            "tech_rank": tech_rank
        }
    elif week == 9:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            eliminated = random.sample([b for b in active_bakers if b != star_baker], 2)
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank
        }
    elif week == 8:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            eliminated = random.sample([b for b in active_bakers if b != star_baker], 2)
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
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
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bottom, min(3, len(rem_bottom))) if len(rem_bottom) >= 3 else tech_top_3
        
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
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

# --- 5. APP INTERFACE LAYOUT ---
col_head1, col_head2 = st.columns([1, 5])
with col_head1:
    norman_img = load_baker_image("normanbeaver") or load_baker_image("norman_beaver")
    if norman_img is not None:
        st.image(norman_img, width=110)
    else:
        st.markdown("<h1 style='font-size: 70px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_head2:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: POINTS REFERENCE GUIDE ONLY ---
with st.sidebar:
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
tab_lead, tab_submit, tab_admin, tab_analytics = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "👑 Admin Panel", 
    "📈 Contestant Analytics"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_rows = []
    for name, data in st.session_state.league_members.items():
        lb_rows.append({
            "League Member": name,
            "Total Points": f"{data.get('total_score', 0)} pts",
            "_pts_num": data.get('total_score', 0),
            "data": data
        })
        
    df_lb = pd.DataFrame(lb_rows).sort_values(by="_pts_num", ascending=False).reset_index(drop=True)
    df_lb.index = df_lb.index + 1
    
    # Assign Rank Badges
    ranks = []
    for idx in range(1, len(df_lb) + 1):
        if idx == 1: ranks.append("🥇 #1")
        elif idx == 2: ranks.append("🥈 #2")
        elif idx == 3: ranks.append("🥉 #3")
        else: ranks.append(f"#{idx}")
    df_lb.insert(0, "Rank", ranks)
    
    # Display Leaderboard
    st.dataframe(df_lb[["Rank", "League Member", "Total Points"]], hide_index=True, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    selected_sc_player = st.selectbox("Select Player to View Scorecard:", [m for m in st.session_state.league_members.keys()], key="sc_player_select")
    p_data = st.session_state.league_members[selected_sc_player]
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})
    
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        st.markdown(f"### **{selected_sc_player}'s Season Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
        
    with col_sc2:
        st.markdown(f"### **{selected_sc_player}'s Weekly Predictions Log**")
        if p_weekly:
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                w_pts = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                with st.expander(f"Week {w_num} Ballot (Earned: {w_pts} pts)"):
                    st.json(w_picks)
        else:
            st.info("No weekly prediction ballots submitted yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps (Verify Counts)")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    tot_hs = 0
    tot_cry = 0
    tot_inn = 0

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 2!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            
            hs_count = len(w_act.get("handshake_bakers", []))
            tot_hs += hs_count
            
            if w_act.get("crying_timestamps"):
                cry_count = len([s for s in w_act.get("crying_timestamps").split(",") if s.strip()])
            else:
                cry_count = 0
            tot_cry += cry_count
            
            tot_inn += inn_cnt
            
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", "N/A"),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshake Bakers": hs_bakers,
                "Handshake Timestamps": hs_stamps,
                "Crying Timestamps": cry_stamps,
                "Innuendos": inn_cnt
            })
            
        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True)

    # --- CHAOS CATEGORIES RUNNING TOTALS ---
    st.markdown("### 🔥 Chaos Categories Running Totals")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Total Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Total Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Total Sexual Innuendos", f"{tot_inn}")

    # --- RESULT DISPUTE / TIMESTAMP CORRECTION FEATURE ---
    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", [m for m in st.session_state.league_members.keys() if m != "AI Brian"])
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
        st.dataframe(df_disp, use_container_width=True)


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    # Player Selection & Password Authentication
    human_players = [m for m in st.session_state.league_members.keys() if m != "AI Brian"]
    sel_player = st.selectbox("Select Your Player Profile:", human_players, key="submit_player_authenticated")
    
    player_pwd_input = st.text_input(f"Enter Password for {sel_player}:", type="password", key=f"pwd_input_{sel_player}")
    actual_pwd = st.session_state.league_members[sel_player].get("password", "1234")
    
    if player_pwd_input != actual_pwd:
        st.warning(f"🔒 Please enter the correct password for **{sel_player}** to unlock prediction forms.")
        st.info("💡 Default password for all players is `1234`. If you forgot your password, ask the League Admin to reset it.")
    else:
        st.success(f"🔓 Welcome **{sel_player}**! Your prediction ballot is unlocked.")
        st.markdown("---")
        
        # 1. VISUAL BAKER GALLERY
        with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
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
        st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
        st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")

        # Dynamic active bakers list
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

        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]

        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")

        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))

        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)

        # Season long entry if week is 2 (Blank default placeholders)
        if st.session_state.current_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                season_baker_opts = ["-- Select Baker --"] + active_bakers
                user_winner_sel = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", season_baker_opts, index=0, key=f"user_win_pick_{sel_player}")
                user_winner = user_winner_sel if user_winner_sel != "-- Select Baker --" else None
                
                remaining_for_semis = [b for b in active_bakers if b != user_winner]
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", remaining_for_semis, default=[], max_selections=3, placeholder="-- Select 3 Semifinalists --", key=f"user_semis_pick_{sel_player}")

                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key=f"user_hs_{sel_player}")
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key=f"user_cry_{sel_player}")
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key=f"user_inn_{sel_player}")

                if st.button("Lock Season-Long Predictions"):
                    if not user_winner:
                        st.error("Please select a Season Winner.")
                    elif len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    elif user_handshakes is None or user_crying is None or user_innuendos is None:
                        st.error("Please enter predicted counts for Handshakes, Crying, and Innuendos.")
                    else:
                        st.session_state.league_members[sel_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        st.success(f"Season-long predictions saved for {sel_player}!")

        # Weekly Form (Blank Placeholders for all fields)
        st.markdown("### Weekly Ballot")
        with st.form(f"weekly_predictions_form_{sel_player}_w{st.session_state.current_week}"):
            weekly_picks = {}
            pred_baker_opts = ["-- Select Baker --"] + active_bakers

            if st.session_state.current_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", pred_baker_opts, index=0)
                st.write("Predict Technical Challenge Final Rank:")
                tech_1st = st.selectbox("Technical 1st Place [3 pts]", pred_baker_opts, index=0)
                tech_2nd = st.selectbox("Technical 2nd Place [2 pts]", pred_baker_opts, index=0, key="w10_p2")
                tech_3rd = st.selectbox("Technical 3rd Place [2 pts]", pred_baker_opts, index=0, key="w10_p3")
                weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]

            elif st.session_state.current_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", pred_baker_opts, index=0)
                if is_double_elim:
                    elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", pred_baker_opts, index=0, key="pred_elim_1_w9")
                    elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", pred_baker_opts, index=0, key="pred_elim_2_w9")
                    weekly_picks["eliminated"] = [elim_1, elim_2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", pred_baker_opts, index=0)

                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", pred_baker_opts, index=0, key="w9_t1")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", pred_baker_opts, index=0, key="w9_t2")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", pred_baker_opts, index=0, key="w9_t3")
                t4 = st.selectbox("Technical 4th Place [3 pts]", pred_baker_opts, index=0, key="w9_t4")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", pred_baker_opts, index=0)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", pred_baker_opts, index=0, key="w8_inline")
                with col2:
                    if is_double_elim:
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", pred_baker_opts, index=0, key="pred_elim_1_w8")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", pred_baker_opts, index=0, key="pred_elim_2_w8")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", pred_baker_opts, index=0, key="w8_trouble_db")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", pred_baker_opts, index=0, key="w8_elim")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", pred_baker_opts, index=0, key="w8_trouble")

                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", pred_baker_opts, index=0, key="t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", pred_baker_opts, index=0, key="t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", pred_baker_opts, index=0, key="t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", pred_baker_opts, index=0, key="t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", pred_baker_opts, index=0, key="t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]

            else:
                # Standard Weeks 2-7
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", pred_baker_opts, index=0, key="std_sb")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", pred_baker_opts, index=0, key="std_inline")
                with col2:
                    if is_double_elim:
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", pred_baker_opts, index=0, key="pred_elim_1_std")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", pred_baker_opts, index=0, key="pred_elim_2_std")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", pred_baker_opts, index=0, key="std_trb_db")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", pred_baker_opts, index=0, key="std_elim")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", pred_baker_opts, index=0, key="std_trb")

                st.markdown("---")
                st.write("Predict Top 3 Technical Challenge Placements:")
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    std_t1 = st.selectbox("Technical 1st Place [3 pts]", pred_baker_opts, index=0, key="std_t1")
                with col_t2:
                    std_t2 = st.selectbox("Technical 2nd Place [2 pts]", pred_baker_opts, index=0, key="std_t2")
                with col_t3:
                    std_t3 = st.selectbox("Technical 3rd Place [2 pts]", pred_baker_opts, index=0, key="std_t3")

                st.write("Predict Bottom 3 Technical Challenge Placements:")
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    std_b3_last = st.selectbox("Technical 3rd-to-Last Place [2 pts]", pred_baker_opts, index=0, key="std_b3_last")
                with col_b2:
                    std_b2_last = st.selectbox("Technical 2nd-to-Last Place [2 pts]", pred_baker_opts, index=0, key="std_b2_last")
                with col_b3:
                    std_blast = st.selectbox("Technical Last Place [3 pts]", pred_baker_opts, index=0, key="std_blast")

                weekly_picks["tech_top_3"] = [std_t1, std_t2, std_t3]
                weekly_picks["tech_bottom_3"] = [std_b3_last, std_b2_last, std_blast]

            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                st.session_state.league_members[sel_player]["weekly_picks"][st.session_state.current_week] = weekly_picks

                # Automatically trigger AI Brian to submit his random predictions
                ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks

                st.success(f"Predictions submitted for {sel_player} in Week {st.session_state.current_week}! AI Brian has also logged his picks.")


# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    # Password Protection (PIN 6284)
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Console is Password Protected**")
        with st.form("admin_login_form"):
            admin_pin_input = st.text_input("Enter Administrator Security PIN", type="password")
            if st.form_submit_button("Unlock Admin Panel"):
                if admin_pin_input == "6284":
                    st.session_state.admin_authenticated = True
                    st.success("Administrator Console Unlocked!")
                    st.rerun()
                else:
                    st.error("Incorrect Admin Security PIN!")
    else:
        st.success("🔓 **Authenticated as League Administrator**")
        col_act1, col_act2 = st.columns(2)
        with col_act2:
            if st.button("🔒 Lock Console"):
                st.session_state.admin_authenticated = False
                st.rerun()

        st.markdown("---")
        with st.expander("🔑 Reset Player Security PINs", expanded=False):
            human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
            p_to_reset = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + human_players)
            if p_to_reset != "-- Select Player --":
                cur_status = "Set 🔒" if st.session_state.league_members[p_to_reset].get("pin") else "Unset 🔓"
                st.write(f"Current PIN status for **{p_to_reset}**: `{cur_status}`")
                if st.button(f"Reset PIN for {p_to_reset}"):
                    st.session_state.league_members[p_to_reset]["pin"] = None
                    if p_to_reset in st.session_state.authenticated_players:
                        st.session_state.authenticated_players[p_to_reset] = False
                    st.success(f"Security PIN reset for {p_to_reset}!")
                    st.rerun()

        st.markdown("---")
        
        # =========================================================================
        # STEP 1: EPISODE SELECTION & ELIMINATION FORMAT
        # =========================================================================
        st.subheader("⚙️ Step 1: Select Episode & Elimination Format")
        st.write("Select the episode week and elimination rule below. Every field in Step 2 updates INSTANTLY on screen!")
        
        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            admin_selected_week = st.selectbox(
                "Select Episode Week:",
                list(range(1, 11)),
                index=0,
                key="admin_week_selector_dropdown"
            )
            
        saved_w = st.session_state.weekly_results.get(admin_selected_week, st.session_state.weekly_results.get(str(admin_selected_week), {}))
        is_published = bool(saved_w)
        
        if is_published:
            st.success(f"🟢 **Week {admin_selected_week} Results Recorded & Saved in System**")
        else:
            st.info(f"🔵 **Week {admin_selected_week} Results Pending Input**")

        # Determine saved elimination index
        saved_elim = saved_w.get("eliminated")
        def_elim_idx = 0
        if saved_elim == "None":
            def_elim_idx = 1
        elif isinstance(saved_elim, list):
            def_elim_idx = 2

        elim_type = "Single Elimination"
        if admin_selected_week < 10:
            elim_type = st.radio(
                f"Set Elimination Format for Episode {admin_selected_week}:",
                ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"],
                index=def_elim_idx,
                horizontal=True,
                key=f"admin_elim_type_w{admin_selected_week}"
            )

        active_bakers = get_active_bakers(admin_selected_week)
        baker_opts = ["-- Select Baker --"] + active_bakers

        st.markdown("---")

        # =========================================================================
        # STEP 2: DEDICATED BROADCAST RESULTS INPUTS (DIRECT INTERACTIVE CONTROLS)
        # =========================================================================
        st.subheader(f"📝 Step 2: Input Official Broadcast Results for Week {admin_selected_week}")
        st.info(f"📋 **Active Config:** Week {admin_selected_week} | **Elimination Format:** `{elim_type}`")

        actuals = {}

        if admin_selected_week == 10:
            st.markdown("### 🏆 Final Show Champion")
            def_champ = saved_w.get("show_champion")
            def_champ_i = baker_opts.index(def_champ) if def_champ in baker_opts else 0
            actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts, index=def_champ_i, key=f"adm_champ_w{admin_selected_week}")
        else:
            # --- SECTION A: STAR BAKER & NOMINEES ---
            st.markdown("### 🌟 Section A: Star Baker & Nominees")
            col_sb1, col_sb2 = st.columns(2)
            with col_sb1:
                def_sb = saved_w.get("star_baker")
                def_sb_i = baker_opts.index(def_sb) if def_sb in baker_opts else 0
                actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=def_sb_i, key=f"adm_sb_w{admin_selected_week}")
            with col_sb2:
                def_inl = [b for b in saved_w.get("in_line_sb", []) if b in active_bakers]
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, default=def_inl, key=f"adm_inl_w{admin_selected_week}")

            # --- SECTION B: ELIMINATION RESULTS (DYNAMIC REACTIVE INTERFACE) ---
            st.markdown("---")
            st.markdown(f"### 🚪 Section B: Elimination Results ({elim_type})")
            
            if elim_type == "Single Elimination":
                def_elim = saved_w.get("eliminated")
                if isinstance(def_elim, list) and len(def_elim) > 0:
                    def_elim = def_elim[0]
                def_elim_i = baker_opts.index(def_elim) if def_elim in baker_opts else 0
                actuals["eliminated"] = st.selectbox(
                    "Actual Eliminated Baker", 
                    baker_opts, 
                    index=def_elim_i, 
                    key=f"adm_elim_single_w{admin_selected_week}"
                )
                
            elif elim_type == "No Elimination (Grace Week)":
                actuals["eliminated"] = "None"
                st.success("🟢 **NO ELIMINATION THIS WEEK (Grace Week / Sickness Exemption Active)** - No baker was eliminated in this episode. All active bakers advance to the next week!")
                
            else: # Double Elimination
                def_e1, def_e2 = None, None
                if isinstance(saved_w.get("eliminated"), list):
                    el_list = saved_w.get("eliminated")
                    if len(el_list) > 0: def_e1 = el_list[0]
                    if len(el_list) > 1: def_e2 = el_list[1]
                def_e1_i = baker_opts.index(def_e1) if def_e1 in baker_opts else 0
                def_e2_i = baker_opts.index(def_e2) if def_e2 in baker_opts else 0
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts, index=def_e1_i, key=f"adm_elim_1_w{admin_selected_week}")
                with col_e2:
                    e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts, index=def_e2_i, key=f"adm_elim_2_w{admin_selected_week}")
                actuals["eliminated"] = [e1, e2]
                
            def_trb = [b for b in saved_w.get("in_trouble", []) if b in active_bakers]
            actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=def_trb, key=f"adm_trb_w{admin_selected_week}")

        # --- SECTION C: TECHNICAL CHALLENGE RANKINGS ---
        st.markdown("---")
        st.markdown(f"### 📊 Section C: Technical Challenge Rankings (1st through {len(active_bakers)}th Place)")
        
        num_bakers = len(active_bakers)
        cols_per_row = 3
        actual_tech_ranks = []
        
        for i in range(num_bakers):
            rank_num = i + 1
            ord_str = "1st" if rank_num == 1 else ("2nd" if rank_num == 2 else ("3rd" if rank_num == 3 else f"{rank_num}th"))
            if i % cols_per_row == 0:
                t_cols = st.columns(min(cols_per_row, num_bakers - i))
            col = t_cols[i % cols_per_row]
            
            saved_t_list = saved_w.get("tech_rank", [])
            def_t = saved_t_list[i] if (isinstance(saved_t_list, list) and i < len(saved_t_list)) else None
            def_t_i = baker_opts.index(def_t) if def_t in baker_opts else 0
            
            with col:
                sel_b = st.selectbox(
                    f"Actual Technical {ord_str} Place",
                    baker_opts,
                    index=def_t_i,
                    key=f"adm_tech_w{admin_selected_week}_r{rank_num}"
                )
                actual_tech_ranks.append(sel_b)

        actuals["tech_rank"] = actual_tech_ranks
        clean_ranks = [b for b in actual_tech_ranks if b and not str(b).startswith("-- Select")]
        actuals["tech_top_3"] = clean_ranks[:3]
        actuals["tech_bottom_3"] = clean_ranks[-3:] if len(clean_ranks) >= 3 else clean_ranks

        # --- SECTION D: CHAOS CATEGORIES & VIDEO TIMESTAMPS ---
        st.markdown("---")
        st.markdown("### 🌀 Section D: Chaos Categories & Video Timestamps")
        
        def_hs_bakers = [b for b in saved_w.get("handshake_bakers", []) if b in active_bakers]
        act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshake(s)", active_bakers, default=def_hs_bakers, key=f"adm_hs_bakers_w{admin_selected_week}")
        act_handshake_cnt = len(act_handshake_bakers)
        st.info(f"🤝 **Calculated Handshake Count for Week {admin_selected_week}:** `{act_handshake_cnt} Handshake(s)`")
        
        def_hs_stamps = saved_w.get("handshake_timestamps", "")
        act_handshake_stamps = st.text_input("Handshake Circumstances & Video Timestamps", value=def_hs_stamps, placeholder="e.g., Tom @ 14:22 Signature, Clara @ 42:10 Showstopper", key=f"adm_hs_stamps_w{admin_selected_week}")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            def_cry_cnt = saved_w.get("crying_count", 0)
            act_crying_cnt = st.number_input("Number of Crying Occurrences", min_value=0, value=def_cry_cnt, key=f"adm_cry_cnt_w{admin_selected_week}")
        with col_c2:
            def_cry_stamps = saved_w.get("crying_timestamps", "")
            act_crying_stamps = st.text_input("Crying Circumstances & Video Timestamps", value=def_cry_stamps, placeholder="e.g., Mo after the technical @ 34:12", key=f"adm_cry_stamps_w{admin_selected_week}")

        col_i1, col_i2 = st.columns(2)
        with col_i1:
            def_inn_cnt = saved_w.get("innuendo_count", 0)
            act_innuendo_cnt = st.number_input("Number of Innuendo Occurrences", min_value=0, value=def_inn_cnt, key=f"adm_inn_cnt_w{admin_selected_week}")
        with col_i2:
            def_inn_stamps = saved_w.get("innuendo_timestamps", "")
            act_innuendo_stamps = st.text_input("Innuendo Circumstances & Video Timestamps", value=def_inn_stamps, placeholder="e.g., Paul soggy bottom comment @ 18:45", key=f"adm_inn_stamps_w{admin_selected_week}")

        actuals["handshake_bakers"] = act_handshake_bakers
        actuals["handshake_count"] = act_handshake_cnt
        actuals["handshake_timestamps"] = act_handshake_stamps
        actuals["crying_count"] = act_crying_cnt
        actuals["crying_timestamps"] = act_crying_stamps
        actuals["innuendo_count"] = act_innuendo_cnt
        actuals["innuendo_timestamps"] = act_innuendo_stamps

        if admin_selected_week == 10:
            st.markdown("---")
            st.subheader("Final Seasonal Broadcast Totals")
            def_s_win = st.session_state.season_results.get("winner")
            def_s_win_i = baker_opts.index(def_s_win) if def_s_win in baker_opts else 0
            act_winner = st.selectbox("Actual Season Winner", baker_opts, index=def_s_win_i, key=f"adm_season_winner_w{admin_selected_week}")
            
            def_s_semis = [b for b in st.session_state.season_results.get("semifinalists", []) if b in ALL_BAKERS]
            act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, default=def_s_semis, max_selections=4, key=f"adm_season_semis_w{admin_selected_week}")
            
            def_s_fin = [b for b in st.session_state.season_results.get("finalists", []) if b in ALL_BAKERS]
            act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, default=def_s_fin, max_selections=3, key=f"adm_season_fin_w{admin_selected_week}")
            
            act_handshakes = st.number_input("Actual Season Total Handshakes", min_value=0, value=st.session_state.season_results.get("handshakes", 5), key=f"adm_season_hs_w{admin_selected_week}")
            act_crying = st.number_input("Actual Season Total Crying Incidents", min_value=0, value=st.session_state.season_results.get("crying", 12), key=f"adm_season_cry_w{admin_selected_week}")
            act_innuendos = st.number_input("Actual Season Total Sexual Innuendos", min_value=0, value=st.session_state.season_results.get("innuendos", 48), key=f"adm_season_inn_w{admin_selected_week}")

            actuals_season = {
                "winner": act_winner,
                "semifinalists": act_semis,
                "finalists": act_finalists,
                "handshakes": act_handshakes,
                "crying": act_crying,
                "innuendos": act_innuendos
            }

        st.markdown("---")
        if st.button(f"💾 Save Official Week {admin_selected_week} Results & Recalculate Standings", type="primary", key=f"save_btn_w{admin_selected_week}"):
            st.session_state.weekly_results[admin_selected_week] = actuals
            if admin_selected_week == 10:
                st.session_state.season_results = actuals_season

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

            save_league_data()
            st.success(f"🎉 Official results successfully published for Week {admin_selected_week}! All standings updated.")
            st.rerun()

        st.markdown("---")
        st.subheader("🚨 Emergency Reset Competition Data")
        confirm_erase = st.checkbox("I understand this will permanently erase all player prediction ballots, PINs, and published broadcast results.", key="confirm_erase_check")
        if st.button("🗑️ Erase All Competition Data", type="primary"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["weekly_picks"] = {}
                    st.session_state.league_members[m_name]["season_picks"] = {}
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["season_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    st.session_state.league_members[m_name]["pin"] = None
                
                if os.path.exists(DATA_FILE):
                    try: os.remove(DATA_FILE)
                    except Exception: pass
                    
                # Delete form/widget keys from st.session_state
                for k in list(st.session_state.keys()):
                    if k not in ["admin_authenticated", "data_erased_confirmation", "league_members"]:
                        try:
                            del st.session_state[k]
                        except Exception:
                            pass
                            
                st.session_state["data_erased_confirmation"] = True
                save_league_data()
                st.rerun()
            else:
                st.error("Please check the confirmation box above first.")


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
            st.info(f"No image file found for {selected_baker} in assets/.")
    with col_details:
        st.subheader(f"Baker Profile: {selected_baker}")
        b_info = BAKER_INFO.get(selected_baker, {})
        st.markdown(f"[🔗 Official Show Profile Page]({b_info.get('url', '#')})")
