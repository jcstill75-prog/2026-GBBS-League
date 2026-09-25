import streamlit as st
import pandas as pd
import random
from PIL import Image
import os
import base64
import json
import io

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
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

# --- 2. GLOBAL ROSTER & CONTESTANT DATA ---
ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]
ROSTER_HUMANS.sort()

ROSTER_ALL_15 = ["AI Brian"] + ROSTER_HUMANS
ROSTER_ALL_15.sort()

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

# --- 3. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
    # --- A. Main Episode Results ---
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") and predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
        
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
            pass
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim and pred_elim == act_elim:
                score += 5
            
    # --- B. Technical Challenge ---
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 5:
                score += 25
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 4]:
                            score += 3
                        else:
                            score += 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 3]:
                            score += 3
                        else:
                            score += 2
                    
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
                score += 15
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
        act_top3 = actuals.get("tech_top_3", actuals.get("tech_rank", [])[:3])
        
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
                        
        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", actuals.get("tech_rank", [])[-3:])
        
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
        if (predictions.get("in_line_sb") in actuals.get("in_line_sb", [])) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2
        # In Trouble Scoring Rule: +2 points if predicted baker matches any nominated in_trouble baker
        pred_trouble = predictions.get("in_trouble")
        act_trouble = actuals.get("in_trouble", [])
        if pred_trouble and pred_trouble in act_trouble:
            score += 2
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and pred_winner in act_finalists:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
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

# --- 4. SESSION STATE INITIALIZATION ---
if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for name in ROSTER_ALL_15:
        st.session_state.league_members[name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

if "player_passwords" not in st.session_state:
    st.session_state.player_passwords = {name: None for name in ROSTER_HUMANS}

if "current_week" not in st.session_state:
    st.session_state.current_week = 2

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

# --- 5. AI BRIAN PICK GENERATOR ---
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
        tech_bottom_3 = random.sample(rem_bottom, 3)
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3
        }

if not st.session_state.league_members["AI Brian"].get("season_picks"):
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 6. APP INTERFACE LAYOUT ---
# Header
col_logo, col_title = st.columns([1, 4])
with col_logo:
    logo_path = None
    for p in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.jpeg", "assets/normanbeaver.png"]:
        if os.path.exists(p):
            logo_path = p
            break
    if logo_path:
        st.image(logo_path, width=110)
    else:
        st.markdown("<h1 style='font-size: 60px;'>🦫</h1>", unsafe_allow_html=True)

with col_title:
    st.title("Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: GAME CONTROLS & PERSISTENT POINTS REMINDER ---
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

# --- MAIN TABS (ADMIN PANEL ON FAR RIGHT) ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Contestant Analytics",
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_rows = []
    for member_name in ROSTER_ALL_15:
        data = st.session_state.league_members.get(member_name, {})
        tot_pts = data.get("total_score", 0)
        win_pick = data.get("season_picks", {}).get("winner", "Not locked")
        lb_rows.append({
            "League Member": member_name,
            "Total Points": tot_pts,
            "Winner Prediction": win_pick
        })
        
    df_lb = pd.DataFrame(lb_rows).sort_values(by="Total Points", ascending=False).reset_index(drop=True)
    
    # Format Rank
    ranks = []
    for i in range(1, len(df_lb) + 1):
        if i == 1: ranks.append("🥇 #1")
        elif i == 2: ranks.append("🥈 #2")
        elif i == 3: ranks.append("🥉 #3")
        else: ranks.append(f"#{i}")
    df_lb.insert(0, "Rank", ranks)
    
    df_lb["Total Points"] = df_lb["Total Points"].apply(lambda p: f"{p} pts")
    
    st.dataframe(df_lb, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    selected_score_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALL_15, key="scorecard_player_select")
    
    p_data = st.session_state.league_members.get(selected_score_player, {})
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})
    
    st.markdown(f"### **{selected_score_player}'s Performance Overview (Total Score: {p_pts} pts)**")
    
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        st.markdown("#### **🌟 Season-Long Projections**")
        st.write(f"🏆 **Predicted Winner:** {p_season.get('winner', 'Not submitted')}")
        semis_str = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted"
        st.write(f"🏅 **Predicted Semifinalists:** {semis_str}")
        st.write(f"🤝 **Predicted Handshakes:** {p_season.get('handshakes', 'N/A')}")
        st.write(f"😢 **Predicted Crying Scenes:** {p_season.get('crying', 'N/A')}")
        st.write(f"💬 **Predicted Sexual Innuendos:** {p_season.get('innuendos', 'N/A')}")

    with col_sc2:
        st.markdown("#### **📅 Weekly Predictions Log**")
        if not p_weekly:
            st.info(f"{selected_score_player} has not submitted any weekly prediction ballots yet.")
        else:
            for w_num in sorted(p_weekly.keys()):
                w_pick = p_weekly[w_num]
                w_pts = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                with st.expander(f"Week {w_num} Ballot — Earned: {w_pts} pts"):
                    st.json(w_pick)

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    # Calculate cumulative running totals across all logged weeks
    tot_hs = sum(w.get("handshake_count", 0) for w in st.session_state.weekly_results.values())
    tot_cry = sum(w.get("crying_count", 0) for w in st.session_state.weekly_results.values())
    tot_inn = sum(w.get("innuendo_count", 0) for w in st.session_state.weekly_results.values())

    st.markdown(f"**Cumulative Broadcast Totals Across Logged Weeks:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Sexual Innuendos: `{tot_inn}`")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Broadcast logs will appear here after Episode 2!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": str(w_act.get("star_baker", "N/A")),
                "Eliminated": str(w_act.get("eliminated", "N/A")),
                "Handshakes Count": w_act.get("handshake_count", 0),
                "Handshake Timestamps & Details": w_act.get("handshake_timestamps", "N/A") or "N/A",
                "Crying Count": w_act.get("crying_count", 0),
                "Crying Timestamps & Details": w_act.get("crying_timestamps", "N/A") or "N/A",
                "Innuendos Count": w_act.get("innuendo_count", 0),
                "Innuendo Timestamps & Details": w_act.get("innuendo_timestamps", "N/A") or "N/A"
            })
        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("⚖️ Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS, key="disp_player_sel")
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
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Weekly & Seasonal Predictions")
    
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
            
        if st.button("Set 4-Digit PIN & Unlock Ballot"):
            if len(new_p1) != 4 or not new_p1.isdigit():
                st.error("PIN must be exactly 4 numeric digits!")
            elif new_p1 != new_p2:
                st.error("PINs do not match! Please check and try again.")
            else:
                st.session_state.player_passwords[submitting_player] = new_p1
                st.success(f"PIN created successfully for {submitting_player}! Your ballot is unlocked.")
                st.rerun()
    else:
        entered_pwd = st.text_input("Enter Your 4-Digit PIN", type="password", max_chars=4, key=f"login_pwd_{submitting_player}")
        if entered_pwd == saved_pwd:
            st.success(f"🔓 Authenticated as **{submitting_player}**!")
            authenticated = True
        elif entered_pwd != "":
            st.error("❌ Incorrect 4-digit PIN! Please try again or ask the Admin to reset your password.")

    if authenticated:
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
        st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
        st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
        
        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_options = ["--Select Baker--"] + active_bakers
        
        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
        
        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, help="Automatically checked if the previous week was a sickness grace week with no elimination!")
        
        # 1. Season long entry if week is 2
        if st.session_state.current_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_options, key="user_win_pick")
                
                rem_bakers_semis = [b for b in active_bakers if b != user_winner]
                st.write("Predict Other 3 Semifinalists [10 pts each | 30 pts max]:")
                s1 = st.selectbox("Semifinalist #1", ["--Select Baker--"] + rem_bakers_semis, key="s1_pick")
                s2 = st.selectbox("Semifinalist #2", ["--Select Baker--"] + [b for b in rem_bakers_semis if b != s1], key="s2_pick")
                s3 = st.selectbox("Semifinalist #3", ["--Select Baker--"] + [b for b in rem_bakers_semis if b not in [s1, s2]], key="s3_pick")
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)
                
                if st.button("Lock Season-Long Predictions"):
                    semis_picks = [s1, s2, s3]
                    if "--Select Baker--" in [user_winner] + semis_picks:
                        st.error("⚠️ Please select a valid baker for all Season-Long prediction fields!")
                    elif len(set(semis_picks)) != 3:
                        st.error("❌ Duplicate Selection Error: You must select 3 distinct semifinalists!")
                    else:
                        st.session_state.league_members[submitting_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": semis_picks,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        st.success("Season long predictions saved successfully!")

        # 2. Weekly Form
        st.markdown("### Weekly Ballot")
        with st.form("weekly_predictions_form"):
            weekly_picks = {}
            
            if st.session_state.current_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_options, key="p_champ")
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w10")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w10")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w10")
                weekly_picks["tech_rank"] = [t1, t2, t3]
                
            elif st.session_state.current_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, key="p_sb_w9")
                if is_double_elim:
                    elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="p_elim_1_w9")
                    elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="p_elim_2_w9")
                    weekly_picks["eliminated"] = [elim_1, elim_2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options, key="p_elim_w9")
                
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w9")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w9")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w9")
                t4 = st.selectbox("Technical 4th Place [3 pts]", baker_options, key="p_t4_w9")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, key="p_sb_w8")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", baker_options, key="p_inline_w8")
                with col2:
                    if is_double_elim:
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="p_elim_1_w8")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="p_elim_2_w8")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if nominated]", baker_options, key="p_trouble_w8_d")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options, key="p_elim_w8")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if nominated]", baker_options, key="p_trouble_w8")
                
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", baker_options, key="p_t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", baker_options, key="p_t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                
            else:
                # Standard Weeks 2-7
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, key="p_sb_std")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", baker_options, key="p_inline_std")
                with col2:
                    if is_double_elim:
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="p_elim_1_std")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="p_elim_2_std")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if nominated]", baker_options, key="p_trouble_std_d")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options, key="p_elim_std")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if nominated]", baker_options, key="p_trouble_std")
                    
                st.markdown("---")
                st.write("Predict Top 3 Technical Placements [Exact Match: 1st=3pts, 2nd/3rd=2pts, wrong spot=1pt; Perfect Top 3 sequence = 10 pts flat!]:")
                tt1 = st.selectbox("Top 3 Technical: 1st Place", baker_options, key="p_tt1_std")
                tt2 = st.selectbox("Top 3 Technical: 2nd Place", baker_options, key="p_tt2_std")
                tt3 = st.selectbox("Top 3 Technical: 3rd Place", baker_options, key="p_tt3_std")
                weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                
                st.write("Predict Bottom 3 Technical Placements [Exact Match: 9th=2pts, 10th=2pts, 11th=3pts, wrong spot=1pt; Perfect Bottom 3 sequence = 10 pts flat!]:")
                tb1 = st.selectbox("Bottom 3 Technical: 3rd-to-Last Place", baker_options, key="p_tb1_std")
                tb2 = st.selectbox("Bottom 3 Technical: 2nd-to-Last Place", baker_options, key="p_tb2_std")
                tb3 = st.selectbox("Bottom 3 Technical: Last Place", baker_options, key="p_tb3_std")
                weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]
                
            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                # 1. Unselected placeholder check
                all_selected = []
                for k, v in weekly_picks.items():
                    if isinstance(v, list):
                        all_selected.extend(v)
                    else:
                        all_selected.append(v)
                        
                if "--Select Baker--" in all_selected:
                    st.error("⚠️ Please select a valid baker for all prediction fields!")
                else:
                    # 2. Episodic Duplicate Validation
                    episodic_picks = []
                    if st.session_state.current_week == 10:
                        episodic_picks = [weekly_picks.get("show_champion")]
                    else:
                        sb = weekly_picks.get("star_baker")
                        inline = weekly_picks.get("in_line_sb")
                        trouble = weekly_picks.get("in_trouble")
                        elim = weekly_picks.get("eliminated")
                        
                        if sb: episodic_picks.append(sb)
                        if inline: episodic_picks.append(inline)
                        if trouble: episodic_picks.append(trouble)
                        if isinstance(elim, list):
                            episodic_picks.extend(elim)
                        elif elim:
                            episodic_picks.append(elim)
                            
                    if len(episodic_picks) != len(set(episodic_picks)):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    else:
                        # 3. Technical Duplicate Validation
                        tech_picks = []
                        if "tech_rank" in weekly_picks:
                            tech_picks = weekly_picks["tech_rank"]
                        else:
                            tech_picks = weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])
                            
                        if len(tech_picks) != len(set(tech_picks)):
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            st.session_state.league_members[submitting_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                            st.success(f"Predictions successfully submitted for {submitting_player} (Week {st.session_state.current_week})! AI Brian has also submitted his randomized picks.")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles and career trajectories for the Series 17 Bakers:")
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

# --- TAB 4: ADMIN PANEL (FAR RIGHT) ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Use this tab to input official broadcast results, publish episode actuals, manage passwords, or reset testing data.")
    
    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    admin_baker_options = ["--Select Baker--"] + active_bakers
    
    with st.form("admin_actuals_form"):
        st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
        actuals = {}
        
        if st.session_state.current_week == 10:
            actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers, key="adm_champ")
            st.write("Actual Technical Challenge Rankings:")
            act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, key="adm_t1_w10")
            act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], key="adm_t2_w10")
            act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], key="adm_t3_w10")
            actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            
        elif st.session_state.current_week == 9:
            actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, key="adm_sb_w9")
            elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
            if elim_type == "Single Elimination":
                actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")], key="adm_elim_w9")
            elif elim_type == "No Elimination (Sickness/Grace Week)":
                actuals["eliminated"] = "None"
                st.info("No baker was eliminated this week. Consolation and other categories are scored normally.")
            else:
                act_elim_1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], key="admin_act_elim_1_w9")
                act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), act_elim_1]], key="admin_act_elim_2_w9")
                actuals["eliminated"] = [act_elim_1, act_elim_2]
            
            st.write("Actual Technical Challenge Rankings:")
            act_t1 = st.selectbox("Actual Technical 1st", active_bakers, key="adm_t1_w9")
            act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], key="adm_t2_w9")
            act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], key="adm_t3_w9")
            act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], key="adm_t4_w9")
            actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

        elif st.session_state.current_week == 8:
            col1, col2 = st.columns(2)
            with col1:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, key="adm_sb_w8")
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")], key="adm_inline_w8")
            with col2:
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, key="adm_elim_w8")
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")], key="adm_trouble_w8")
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week.")
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, key="adm_trouble_w8_grace")
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_w8")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_w8")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]], key="adm_trouble_w8_d")
                
            st.write("Actual Technical Challenge Rankings (1st through 5th):")
            act_t1 = st.selectbox("Actual Technical 1st", active_bakers, key="adm_t1_w8")
            act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], key="adm_t2_w8")
            act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], key="adm_t3_w8")
            act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], key="adm_t4_w8")
            act_t5 = st.selectbox("Actual Technical 5th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], key="adm_t5_w8")
            actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
            
        else:
            col1, col2 = st.columns(2)
            with col1:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, key="adm_sb_std")
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")], key="adm_inline_std")
            with col2:
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_std")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, key="adm_elim_std")
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")], key="adm_trouble_std")
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week.")
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, key="adm_trouble_std_grace")
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_std")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_std")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]], key="adm_trouble_std_d")
                
            st.write("Actual Technical Challenge Rankings (Every Position Entered Separately):")
            # Dynamic separate selectbox for EVERY active baker position
            act_tech_rank = []
            available_tech = list(active_bakers)
            for pos_idx in range(len(active_bakers)):
                pos_label = f"Actual Technical {pos_idx + 1}th Place"
                if pos_idx == 0: pos_label = "Actual Technical 1st Place"
                elif pos_idx == 1: pos_label = "Actual Technical 2nd Place"
                elif pos_idx == 2: pos_label = "Actual Technical 3rd Place"
                
                t_pos = st.selectbox(pos_label, available_tech, key=f"adm_tech_pos_{pos_idx}_w{st.session_state.current_week}")
                act_tech_rank.append(t_pos)
                available_tech = [b for b in available_tech if b != t_pos]
                
            actuals["tech_rank"] = act_tech_rank
            if len(act_tech_rank) >= 6:
                actuals["tech_top_3"] = act_tech_rank[:3]
                actuals["tech_bottom_3"] = act_tech_rank[-3:]
            
        # --- REQUIREMENT 4: TWO FIELDS FOR ALL CHAOS CATEGORIES ---
        st.markdown("---")
        st.markdown("### 🤝 Hollywood Handshakes")
        col_hs1, col_hs2 = st.columns([1, 2])
        with col_hs1:
            act_hs_count = st.number_input("Field 1: Handshakes Count", min_value=0, value=0, key=f"hs_cnt_w{st.session_state.current_week}")
        with col_hs2:
            act_hs_stamps = st.text_input("Field 2: Handshakes Descriptions & Timestamps", value="", placeholder="e.g. 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper'", key=f"hs_desc_w{st.session_state.current_week}")

        st.markdown("### 😢 Crying Incidents")
        col_cry1, col_cry2 = st.columns([1, 2])
        with col_cry1:
            act_cry_count = st.number_input("Field 1: Crying Incidents Count", min_value=0, value=0, key=f"cry_cnt_w{st.session_state.current_week}")
        with col_cry2:
            act_cry_stamps = st.text_input("Field 2: Crying Descriptions & Timestamps", value="", placeholder="e.g. 'Gabe @ 24:15 Technical, Molly @ 54:02 Elimination'", key=f"cry_desc_w{st.session_state.current_week}")

        st.markdown("### 💬 Sexual Innuendos")
        col_inn1, col_inn2 = st.columns([1, 2])
        with col_inn1:
            act_inn_count = st.number_input("Field 1: Sexual Innuendos Count", min_value=0, value=0, key=f"inn_cnt_w{st.session_state.current_week}")
        with col_inn2:
            act_inn_stamps = st.text_input("Field 2: Sexual Innuendos Descriptions & Timestamps", value="", placeholder="e.g. 'Paul @ 18:05 Soggy Bottom, Prue @ 31:40 Soggy Sponge'", key=f"inn_desc_w{st.session_state.current_week}")

        actuals["handshake_count"] = act_hs_count
        actuals["handshake_timestamps"] = act_hs_stamps
        actuals["crying_count"] = act_cry_count
        actuals["crying_timestamps"] = act_cry_stamps
        actuals["innuendo_count"] = act_inn_count
        actuals["innuendo_timestamps"] = act_inn_stamps
            
        if st.session_state.current_week == 10:
            st.markdown("### 🏆 Final Seasonal Broadcast Totals")
            act_winner = st.selectbox("Actual Season Winner (Show Champion)", active_bakers, key="adm_season_win")
            act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4, key="adm_season_semis")
            act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3, key="adm_season_finals")
            
            act_handshakes = st.number_input("Actual Total Seasonal Handshakes", min_value=0, value=5, key="adm_s_hs")
            act_crying = st.number_input("Actual Total Seasonal Crying Scenes", min_value=0, value=12, key="adm_s_cry")
            act_innuendos = st.number_input("Actual Total Seasonal Sexual Innuendos", min_value=0, value=48, key="adm_s_inn")
            
            actuals_season = {
                "winner": act_winner,
                "semifinalists": act_semis,
                "finalists": act_finalists,
                "handshakes": act_handshakes,
                "crying": act_crying,
                "innuendos": act_innuendos
            }
            
        submit_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
        if submit_actuals:
            st.session_state.weekly_results[st.session_state.current_week] = actuals
            if st.session_state.current_week == 10:
                st.session_state.season_results = actuals_season
                
            # RECALCULATE LEADERBOARD
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
                
            st.success("Leaderboard updated! All predictions scored and verified against the 2026 rule constraints.")

    # --- REQUIREMENT 2: DATA WIPE FEATURE ---
    st.markdown("---")
    st.subheader("🚨 Erase All Saved Data (Reset App State)")
    st.write("Use this button after testing with fake predictions or test entries to reset all app data back to a fresh, clean state.")
    
    confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords.")
    if st.button("Erase All Saved Data & Reset Application"):
        if not confirm_erase:
            st.error("Please check the confirmation box above before erasing data!")
        else:
            st.session_state.weekly_results = {}
            st.session_state.season_results = {}
            st.session_state.disputes = []
            st.session_state.player_passwords = {name: None for name in ROSTER_HUMANS}
            
            for name in ROSTER_ALL_15:
                st.session_state.league_members[name] = {
                    "weekly_picks": {},
                    "season_picks": {},
                    "total_score": 0,
                    "weekly_breakdown": {}
                }
            st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()
            st.success("All application data, test predictions, actuals, disputes, and player passwords have been completely erased! The app is reset.")
            st.rerun()

    # --- REQUIREMENT 1: PASSWORD RESET AT THE VERY BOTTOM ---
    st.markdown("---")
    st.subheader("🔑 Player Password Management")
    st.write("If a player forgets their 4-digit PIN, select their name below to reset it. They will be prompted to create a new 4-digit PIN on their next login.")
    
    reset_player_target = st.selectbox("Select Player to Reset Password:", ROSTER_HUMANS, key="admin_pwd_reset_select")
    if st.button("Reset Player Password"):
        st.session_state.player_passwords[reset_player_target] = None
        st.success(f"Password for **{reset_player_target}** has been successfully reset! They will be prompted to set a new 4-digit PIN on their next login.")
