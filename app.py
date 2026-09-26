import streamlit as st
import pandas as pd
import random
import os
import json
import base64
from PIL import Image
import io

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for cozy baking theme & high-contrast dark/light mode legibility
st.markdown("""
<style>
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
    .status-box {
        background-color: rgba(255, 243, 224, 0.15);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FFB74D;
        margin-bottom: 15px;
    }
    .lb-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .lb-table th {
        background-color: #5D4037;
        color: #FFFFFF !important;
        padding: 12px 14px;
        text-align: left;
        font-size: 1.05rem;
        font-weight: 700;
    }
    .lb-table td {
        padding: 12px 14px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        vertical-align: middle;
    }
    .lb-rank, .lb-name {
        font-weight: 800;
        font-size: 1.15rem;
    }
    .lb-pts {
        font-weight: 800;
        font-size: 1.25rem;
        color: #D36B5F !important;
        text-align: right;
    }
    [data-theme="dark"] .lb-name,
    [data-theme="dark"] .lb-rank,
    .stApp[data-theme="dark"] .lb-name,
    .stApp[data-theme="dark"] .lb-rank {
        color: #FFFFFF !important;
    }
    [data-theme="light"] .lb-name,
    [data-theme="light"] .lb-rank,
    .stApp[data-theme="light"] .lb-name,
    .stApp[data-theme="light"] .lb-rank {
        color: #2C1810 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENCE ENGINE ---
DATA_FILE = "league_data.json"

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_league_data():
    try:
        data = {
            "league_members": st.session_state.league_members,
            "weekly_results": st.session_state.weekly_results,
            "season_results": st.session_state.season_results,
            "disputes": st.session_state.disputes
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

# --- 3. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    # Main Episode
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
                    if p in act_elim: score += 5
            elif isinstance(pred_elim, str) and pred_elim in act_elim:
                score += 5
        elif act_elim != "None" and act_elim is not None:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: score += 5
            elif pred_elim == act_elim:
                score += 5
                
    # Technical Challenge Position Scoring
    pred_rank = predictions.get("tech_rank", [])
    act_rank = actuals.get("tech_rank", [])
    if pred_rank and act_rank and len(pred_rank) == len(act_rank):
        n = len(pred_rank)
        exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b and b != "--Select Baker--")
        if exact_count == n and n > 0:
            score += (n * 5)  # Perfect sweep bonus
        else:
            for idx, b in enumerate(pred_rank):
                if b != "--Select Baker--" and act_rank[idx] == b:
                    if idx in [0, n - 1]:
                        score += 3
                    else:
                        score += 2
                        
    # Consolations
    if week < 9:
        if predictions.get("in_line_sb") and (predictions.get("in_line_sb") in actuals.get("in_line_sb", [])) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2
        if predictions.get("in_trouble") and (predictions.get("in_trouble") in actuals.get("in_trouble", [])) and (predictions.get("in_trouble") != actuals.get("eliminated")):
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
    if pred_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and pred_winner in act_finalists:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    pred_hs = predictions.get("handshakes")
    act_hs = actuals.get("handshakes")
    if pred_hs is not None and act_hs is not None:
        if pred_hs == act_hs: score += 20
        elif abs(pred_hs - act_hs) <= 1: score += 10
        
    pred_cry = predictions.get("crying")
    act_cry = actuals.get("crying")
    if pred_cry is not None and act_cry is not None:
        if pred_cry == act_cry: score += 20
        elif abs(pred_cry - act_cry) <= 5: score += 10
        
    pred_inn = predictions.get("innuendos")
    act_inn = actuals.get("innuendos")
    if pred_inn is not None and act_inn is not None:
        if pred_inn == act_inn: score += 20
        elif abs(pred_inn - act_inn) <= 5: score += 10
        
    return score

# --- 4. ROSTER & INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo",
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle",
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.",
    "Stacy C.", "Taliah", "Tressa"
]

ROSTER_ALPHABETICAL = sorted(["AI Brian"] + ROSTER_HUMANS)

# Initialize Session State
saved_state = load_league_data()
if "league_members" not in st.session_state:
    if saved_state and "league_members" in saved_state:
        st.session_state.league_members = saved_state["league_members"]
    else:
        st.session_state.league_members = {}
        for m in ROSTER_ALPHABETICAL:
            st.session_state.league_members[m] = {
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None,
                "season_score": 0
            }

# Ensure pins and structure for all members
for m in ROSTER_ALPHABETICAL:
    if m not in st.session_state.league_members:
        st.session_state.league_members[m] = {
            "weekly_picks": {}, "season_picks": {}, "total_score": 0,
            "weekly_breakdown": {}, "pin": None, "season_score": 0
        }
    else:
        st.session_state.league_members[m].setdefault("pin", None)
        st.session_state.league_members[m].setdefault("season_score", 0)

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_state.get("weekly_results", {}) if saved_state else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_state.get("season_results", {}) if saved_state else {}

if "disputes" not in st.session_state:
    st.session_state.disputes = saved_state.get("disputes", []) if saved_state else []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# AI Brian Season Picks Generator
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

def generate_ai_brian_weekly_picks(week, active_bakers):
    if len(active_bakers) < 2:
        return {}
    if week == 10:
        champion = random.choice(active_bakers)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"show_champion": champion, "tech_rank": tech_rank}
    elif week == 9:
        star_baker = random.choice(active_bakers)
        eliminated = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble = random.choice([b for b in active_bakers if b != eliminated])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker, "eliminated": eliminated,
            "in_line_sb": in_line, "in_trouble": in_trouble,
            "tech_rank": tech_rank
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# Elimination Tracking
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

# Determine Active Prediction Week driven by Admin
all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
active_prediction_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_prediction_week > 10: active_prediction_week = 10

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🧁 GBBS League")
    st.markdown("---")
    st.subheader("📌 Competition Progress")
    if not st.session_state.weekly_results:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nSeason-wide predictions & Week 2 ballots unlock together once Week 1 results are posted!")
    else:
        latest_w = max(st.session_state.weekly_results.keys())
        st.success(f"🟢 **Active Competition Week: Week {latest_w + 1}**\n\n(Week {latest_w} Results Published)")
        
    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.warning("⏰ **Weekly voting window ends on Tuesdays right before the show airs in the UK.**")
    
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        *   **Season Winner:** 40 pts
        *   **Finalist Consolation:** 15 pts *(Top 3)*
        *   **Other 3 Semifinalists:** 10 pts each
        *   **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        *   **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        *   **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Weekly Predictions", expanded=False):
        st.markdown("""
        *   **Star Baker:** 5 pts
        *   **Eliminated Baker:** 5 pts
        *   **In Line / In Trouble:** 2 pts each
        *   **Technical Exact Positions:** 3 pts (1st/Last), 2 pts (middle)
        *   **Perfect Technical Sweep:** Flat Sweep Bonus!
        *   **Star Member Bonus:** +5 pts to weekly high scorer
        """)

# --- 6. MAIN APP TABS ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
tab_lead, tab_submit, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "👑 Admin Panel"])

# ==============================================================================
# TAB 1: LEADERBOARD & STANDINGS
# ==============================================================================
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    # 1. Compile Leaderboard
    lb_data = []
    for name, data in st.session_state.league_members.items():
        lb_data.append({
            "member": name,
            "points": data.get("total_score", 0),
            "data": data
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        html_rows = []
        for rank, row in df_lb.iterrows():
            m_name = row["member"]
            m_pts = row["points"]
            rank_badge = f"#{rank}"
            if rank == 1: rank_badge = "🥇 #1"
            elif rank == 2: rank_badge = "🥈 #2"
            elif rank == 3: rank_badge = "🥉 #3"
            
            html_rows.append(f"""<tr>
<td class="lb-rank">{rank_badge}</td>
<td class="lb-name">{m_name}</td>
<td class="lb-pts">{m_pts} pts</td>
</tr>""")
            
        table_html = f"""<table class="lb-table">
<thead>
<tr>
<th style="width: 100px;">Rank</th>
<th>League Member</th>
<th style="text-align: right; width: 140px;">Total Points</th>
</tr>
</thead>
<tbody>
{''.join(html_rows)}
</tbody>
</table>"""
        st.markdown(table_html, unsafe_allow_html=True)
        
    # 2. RUNNING CHAOS CATEGORIES TOTALS (Placed BELOW Leaderboard, ABOVE Scorecards)
    st.markdown("---")
    st.markdown("### 🌀 Running Broadcast Chaos Categories Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    
    if st.session_state.weekly_results:
        for w_act in st.session_state.weekly_results.values():
            tot_hs += len(w_act.get("handshake_bakers", []))
            if w_act.get("crying_timestamps"):
                tot_cry += len([s for s in w_act.get("crying_timestamps").split(",") if s.strip()])
            tot_inn += w_act.get("innuendo_count", 0)
            
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🤝 Hollywood Handshakes", f"{tot_hs}")
    with c2:
        st.metric("😢 Crying Incidents", f"{tot_cry}")
    with c3:
        st.metric("💬 Sexual Innuendos", f"{tot_inn}")
        
    # 3. INDIVIDUAL PLAYER SCORECARDS & PROJECTIONS
    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="lb_player_card_sel")
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"#### 👤 **{selected_card_player}'s Scorecard — Total Score: {p_pts} pts**")
        
        # Season Projections - Password Protected
        st.markdown(f"##### **🌟 {selected_card_player}'s Season-Wide Projections**")
        if selected_card_player == "AI Brian":
            st.info("🤖 **AI Brian's Season Projections:**")
            win_pick = p_season.get("winner", "Not submitted yet")
            semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
            st.write(f"🤝 **Predicted Handshakes:** {p_season.get('handshakes', 'N/A')} | 😢 **Crying:** {p_season.get('crying', 'N/A')} | 💬 **Innuendos:** {p_season.get('innuendos', 'N/A')}")
        else:
            card_pin = st.text_input(f"Enter PIN to view {selected_card_player}'s Season Projections:", type="password", key=f"card_pin_{selected_card_player}")
            if p_data.get("pin") and card_pin == p_data.get("pin"):
                win_pick = p_season.get("winner", "Not submitted yet")
                semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
                st.success(f"🔓 Season Projections Unlocked for {selected_card_player}:")
                st.write(f"🏆 **Predicted Winner:** {win_pick}")
                st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
                st.write(f"🤝 **Predicted Handshakes:** {p_season.get('handshakes', 'N/A')} | 😢 **Crying:** {p_season.get('crying', 'N/A')} | 💬 **Innuendos:** {p_season.get('innuendos', 'N/A')}")
            else:
                st.warning(f"🔒 {selected_card_player}'s season-wide predictions are password protected. Enter their 4-digit PIN above to view.")
                
        # Weekly Predictions - Unlocked for everyone to view
        st.markdown(f"##### **📅 {selected_card_player}'s Weekly Predictions Log (Public):**")
        if p_weekly:
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                tr = ", ".join(w_picks.get("tech_rank", [])) if w_picks.get("tech_rank") else "N/A"
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Placement Sequence": tr
                })
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True, hide_index=True)
        else:
            st.info(f"No weekly prediction ballots logged yet for {selected_card_player}.")

    # 4. Broadcast Audit & Disputes
    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Audit logs will appear here after Week 1 results are posted!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshake Recipients": hs_bakers,
                "Handshake Timestamps": w_act.get("handshake_timestamps", "N/A"),
                "Crying Timestamps": w_act.get("crying_timestamps", "N/A"),
                "Innuendos": w_act.get("innuendo_count", 0)
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 2: SUBMIT PREDICTIONS
# ==============================================================================
with tab_submit:
    st.header("📝 Submit Predictions")
    
    # Player Login
    pred_player = st.selectbox("Select Your Player Profile to Submit Predictions:", ROSTER_HUMANS, key="pred_player_login_sel")
    p_info = st.session_state.league_members[pred_player]
    
    # 4-Digit PIN Authentication
    auth_success = False
    if p_info.get("pin") is None:
        st.info(f"Welcome {pred_player}! Please set a 4-digit security PIN for your account profile:")
        new_pin = st.text_input("Create 4-Digit Security PIN:", type="password", key=f"create_pin_{pred_player}")
        confirm_pin = st.text_input("Confirm 4-Digit Security PIN:", type="password", key=f"confirm_pin_{pred_player}")
        if st.button("Set Security PIN & Login"):
            if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                p_info["pin"] = new_pin
                save_league_data()
                st.success("Security PIN saved successfully!")
                st.rerun()
            else:
                st.error("PIN must be exactly 4 numeric digits and match in both fields.")
    else:
        entered_pin = st.text_input(f"Enter 4-Digit Security PIN for {pred_player}:", type="password", key=f"enter_pin_{pred_player}")
        if entered_pin == p_info.get("pin"):
            auth_success = True
            st.success(f"🔓 Authenticated as {pred_player}!")
        elif entered_pin:
            st.error("Incorrect PIN. Please try again.")
            
    if auth_success:
        st.markdown("---")
        
        # WEEK 1 / SCOUTING PHASE: Season predictions locked until Week 2
        if not st.session_state.weekly_results:
            st.warning("🔒 **Week 1 Scouting Phase Notice:** Season-wide predictions and Week 2 ballots are currently locked. They will unlock together as soon as the Administrator posts the broadcast results for Week 1!")
            st.info("💡 **Scouting Tip:** Use this Week 1 Scouting Phase to evaluate all 12 bakers in the tent before locking in your season-wide projections!")
        else:
            # Active Bakers for current prediction week
            curr_elim = eliminated_bakers_by_week.get(active_prediction_week, [])
            active_bakers = [b for b in ALL_BAKERS if b not in curr_elim]
            
            st.subheader(f"📅 Prediction Ballot: Week {active_prediction_week}")
            
            # SECTION A: SEASON-WIDE PREDICTIONS (Unlocked in Week 2, locked from Week 3 onward)
            if active_prediction_week == 2:
                st.markdown("### 🌟 Season-Long Projections (Locks Now! | 130 pts total at stake)")
                st.write("Submit your season-wide projections below alongside your Week 2 ballot:")
                
                s_win = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if finalist]", ["--Select Baker--"] + active_bakers, key="sw_win")
                s_semi1 = st.selectbox("Predict Semifinalist #1 [10 pts]", ["--Select Baker--"] + active_bakers, key="sw_s1")
                s_semi2 = st.selectbox("Predict Semifinalist #2 [10 pts]", ["--Select Baker--"] + active_bakers, key="sw_s2")
                s_semi3 = st.selectbox("Predict Semifinalist #3 [10 pts]", ["--Select Baker--"] + active_bakers, key="sw_s3")
                
                s_hs = st.number_input("Predict Seasonal Handshakes [20 pts spot-on, 10 pts +/-1]", min_value=0, value=None, placeholder="e.g. 5", key="sw_hs")
                s_cry = st.number_input("Predict Seasonal Crying [20 pts spot-on, 10 pts +/-5]", min_value=0, value=None, placeholder="e.g. 12", key="sw_cry")
                s_inn = st.number_input("Predict Seasonal Innuendos [20 pts spot-on, 10 pts +/-5]", min_value=0, value=None, placeholder="e.g. 45", key="sw_inn")
            elif active_prediction_week > 2:
                st.info("🔒 **Season-Long Projections are Locked** (Submitted in Week 2).")
                
            # SECTION B: WEEKLY EPISODIC BALLOT
            st.markdown(f"### 📅 Week {active_prediction_week} Episodic Predictions")
            with st.form("weekly_ballot_form"):
                weekly_picks = {}
                
                if active_prediction_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", ["--Select Baker--"] + active_bakers, key="p_champ")
                    t1 = st.selectbox("Technical 1st Place", ["--Select Baker--"] + active_bakers, key="pt_1")
                    t2 = st.selectbox("Technical 2nd Place", ["--Select Baker--"] + active_bakers, key="pt_2")
                    t3 = st.selectbox("Technical 3rd Place", ["--Select Baker--"] + active_bakers, key="pt_3")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", ["--Select Baker--"] + active_bakers, key="p_sb")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", ["--Select Baker--"] + active_bakers, key="p_inline")
                    with col2:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", ["--Select Baker--"] + active_bakers, key="p_elim")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", ["--Select Baker--"] + active_bakers, key="p_introuble")
                        
                    st.markdown("#### **Predict Technical Challenge Placements:**")
                    tech_picks = []
                    if active_prediction_week == 9: # 4 Bakers
                        t1 = st.selectbox("Technical 1st Place", ["--Select Baker--"] + active_bakers, key="pt_1")
                        t2 = st.selectbox("Technical 2nd Place", ["--Select Baker--"] + active_bakers, key="pt_2")
                        t3 = st.selectbox("Technical 3rd Place", ["--Select Baker--"] + active_bakers, key="pt_3")
                        t4 = st.selectbox("Technical 4th Place", ["--Select Baker--"] + active_bakers, key="pt_4")
                        tech_picks = [t1, t2, t3, t4]
                    elif active_prediction_week == 8: # 5 Bakers
                        t1 = st.selectbox("Technical 1st Place", ["--Select Baker--"] + active_bakers, key="pt_1")
                        t2 = st.selectbox("Technical 2nd Place", ["--Select Baker--"] + active_bakers, key="pt_2")
                        t3 = st.selectbox("Technical 3rd Place", ["--Select Baker--"] + active_bakers, key="pt_3")
                        t4 = st.selectbox("Technical 4th Place", ["--Select Baker--"] + active_bakers, key="pt_4")
                        t5 = st.selectbox("Technical 5th Place", ["--Select Baker--"] + active_bakers, key="pt_5")
                        tech_picks = [t1, t2, t3, t4, t5]
                    else: # Standard Weeks 2-7
                        t1 = st.selectbox("Technical 1st Place", ["--Select Baker--"] + active_bakers, key="pt_1")
                        t2 = st.selectbox("Technical 2nd Place", ["--Select Baker--"] + active_bakers, key="pt_2")
                        t3 = st.selectbox("Technical 3rd Place", ["--Select Baker--"] + active_bakers, key="pt_3")
                        t4 = st.selectbox("Technical 3rd-to-Last Place", ["--Select Baker--"] + active_bakers, key="pt_4")
                        t5 = st.selectbox("Technical 2nd-to-Last Place", ["--Select Baker--"] + active_bakers, key="pt_5")
                        t6 = st.selectbox("Technical Last Place", ["--Select Baker--"] + active_bakers, key="pt_6")
                        tech_picks = [t1, t2, t3, t4, t5, t6]
                    weekly_picks["tech_rank"] = tech_picks
                    
                submit_btn = st.form_submit_button("Submit Prediction Ballot")
                if submit_btn:
                    errors = []
                    
                    # 1. Check Missing Selections
                    if active_prediction_week == 10:
                        if weekly_picks.get("show_champion") == "--Select Baker--":
                            errors.append("Please select a valid baker for Show Champion.")
                    else:
                        for field, label in [("star_baker", "Star Baker"), ("eliminated", "Eliminated Baker"), ("in_line_sb", "In Line"), ("in_trouble", "In Trouble")]:
                            if weekly_picks.get(field) == "--Select Baker--":
                                errors.append(f"Please select a valid baker for {label}.")
                                
                    for idx, t in enumerate(weekly_picks.get("tech_rank", [])):
                        if t == "--Select Baker--":
                            errors.append(f"Please select a valid baker for Technical Position #{idx+1}.")
                            
                    # 2. Check Duplicates in Main Picks
                    if active_prediction_week < 10:
                        main_picks = [weekly_picks.get("star_baker"), weekly_picks.get("eliminated"), weekly_picks.get("in_line_sb"), weekly_picks.get("in_trouble")]
                        valid_main = [p for p in main_picks if p and p != "--Select Baker--"]
                        if len(valid_main) != len(set(valid_main)):
                            errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                            
                    # 3. Check Duplicates in Technical Picks
                    valid_tech = [t for t in weekly_picks.get("tech_rank", []) if t and t != "--Select Baker--"]
                    if len(valid_tech) != len(set(valid_tech)):
                        errors.append("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        
                    # Season Picks Validation if Week 2
                    season_picks_dict = {}
                    if active_prediction_week == 2:
                        if s_win == "--Select Baker--" or s_semi1 == "--Select Baker--" or s_semi2 == "--Select Baker--" or s_semi3 == "--Select Baker--":
                            errors.append("Please select valid bakers for all Season-Long Projections.")
                        if s_hs is None or s_cry is None or s_inn is None:
                            errors.append("Please enter valid numerical estimates for Handshakes, Crying, and Innuendos.")
                            
                        semis_list = [s_semi1, s_semi2, s_semi3]
                        all_season_bakers = [s_win] + semis_list
                        valid_season = [b for b in all_season_bakers if b != "--Select Baker--"]
                        if len(valid_season) != len(set(valid_season)):
                            errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Season Winner and Semifinalists!")
                            
                        season_picks_dict = {
                            "winner": s_win,
                            "semifinalists": semis_list,
                            "handshakes": s_hs,
                            "crying": s_cry,
                            "innuendos": s_inn
                        }
                        
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        # SAVE VALIDATED PICKS
                        p_info["weekly_picks"][active_prediction_week] = weekly_picks
                        if active_prediction_week == 2:
                            p_info["season_picks"] = season_picks_dict
                            
                        # AI Brian Picks Generation
                        ai_picks = generate_ai_brian_weekly_picks(active_prediction_week, active_bakers)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][active_prediction_week] = ai_picks
                        
                        save_league_data()
                        st.success(f"🎉 Predictions successfully submitted and locked for Week {active_prediction_week}! AI Brian has also submitted his randomized picks.")

# ==============================================================================
# TAB 3: ADMIN PANEL
# ==============================================================================
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        st.write("Enter the Administrator PIN to unlock league controls:")
        admin_pin_input = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_chk")
        if st.button("Unlock Admin Console"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Console Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Administrator PIN.")
    else:
        col_title, col_lock = st.columns([3, 1])
        with col_lock:
            if st.button("🔒 Lock Admin Panel"):
                st.session_state.admin_authenticated = False
                st.rerun()
                
        st.markdown("### 📅 Select Episode Results to Input / Update")
        default_admin_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
        if default_admin_week > 10: default_admin_week = 10
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=default_admin_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        current_eliminated = eliminated_bakers_by_week.get(admin_selected_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        num_active = len(active_bakers)
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", ["--Select Baker--"] + active_bakers, key="act_champ")
                st.write("Actual Technical Challenge Final Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st Place", ["--Select Baker--"] + active_bakers, key="act_t1")
                act_t2 = st.selectbox("Actual Technical 2nd Place", ["--Select Baker--"] + active_bakers, key="act_t2")
                act_t3 = st.selectbox("Actual Technical 3rd Place", ["--Select Baker--"] + active_bakers, key="act_t3")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", ["--Select Baker--"] + active_bakers, key="act_sb")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, key="act_inline")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)"], horizontal=True, key=f"elim_type_{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", ["--Select Baker--"] + active_bakers, key="act_elim")
                    else:
                        actuals["eliminated"] = "None"
                        st.info("No baker was eliminated this week.")
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key="act_introuble")
                    
                st.markdown(f"#### **Actual Technical Challenge Rankings (All {num_active} Bakers):**")
                act_tech_list = []
                for pos in range(1, num_active + 1):
                    t_val = st.selectbox(f"Actual Technical Position #{pos}", ["--Select Baker--"] + active_bakers, key=f"act_tech_pos_{pos}_{admin_selected_week}")
                    act_tech_list.append(t_val)
                actuals["tech_rank"] = act_tech_list
                
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"act_hs_bakers_{admin_selected_week}")
            act_hs_stamps = st.text_input("Handshake Video Timestamps & Context", value="", placeholder="e.g. Clara @ 14:22 Signature", key=f"act_hs_stamps_{admin_selected_week}")
            
            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            act_cry_stamps = st.text_input("Crying Scene Video Timestamps & Context", value="", placeholder="e.g. Gabe @ 24:15 Technical", key=f"act_cry_stamps_{admin_selected_week}")
            
            st.markdown("### 💬 Weekly Sexual Innuendos Count")
            act_inn_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0, key=f"act_inn_cnt_{admin_selected_week}")
            
            actuals["handshake_bakers"] = act_hs_bakers
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt
            
            if admin_selected_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner", ["--Select Baker--"] + active_bakers, key="act_season_win")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4, key="act_season_semis")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3, key="act_season_finals")
                act_handshakes = st.number_input("Actual Total Handshakes", min_value=0, value=5, key="act_season_hs")
                act_crying = st.number_input("Actual Total Crying Scenes", min_value=0, value=12, key="act_season_cry")
                act_innuendos = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48, key="act_season_inn")
                
                actuals_season = {
                    "winner": act_winner, "semifinalists": act_semis,
                    "finalists": act_finalists, "handshakes": act_handshakes,
                    "crying": act_crying, "innuendos": act_innuendos
                }
                
            pub_btn = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if pub_btn:
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # RECALCULATE LEADERBOARD SCORES
                for m in st.session_state.league_members:
                    st.session_state.league_members[m]["total_score"] = 0
                    st.session_state.league_members[m]["weekly_breakdown"] = {}
                    
                all_weeks = sorted(list(st.session_state.weekly_results.keys()))
                for w in all_weeks:
                    act_w = st.session_state.weekly_results[w]
                    raw_scores = {}
                    for m, m_data in st.session_state.league_members.items():
                        p_w = m_data["weekly_picks"].get(w, {})
                        s_val = calculate_weekly_score(p_w, act_w, w)
                        raw_scores[m] = s_val
                        m_data["weekly_breakdown"][w] = s_val
                        
                    if raw_scores:
                        max_s = max(raw_scores.values())
                        if max_s > 0:
                            for m, s_val in raw_scores.items():
                                if s_val == max_s:
                                    m_data["weekly_breakdown"][w] += 5 # Star Member Bonus
                                    
                if st.session_state.season_results:
                    for m, m_data in st.session_state.league_members.items():
                        s_score = calculate_season_score(m_data["season_picks"], st.session_state.season_results)
                        m_data["season_score"] = s_score
                        
                for m, m_data in st.session_state.league_members.items():
                    w_tot = sum(m_data["weekly_breakdown"].values())
                    s_tot = m_data.get("season_score", 0)
                    m_data["total_score"] = w_tot + s_tot
                    
                save_league_data()
                st.success(f"🎉 Results for Week {admin_selected_week} successfully published! All predictions scored and standings recalculated.")
                st.rerun()

        # PLAYER PASSWORD RESET
        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their security PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_HUMANS, key="admin_pwd_reset_sel")
        if st.button(f"Reset Security PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            save_league_data()
            st.success(f"Password PIN for {reset_player} has been cleared! They can set a new 4-digit PIN upon next login.")

        # RESET APP STATE / ERASE ALL DATA
        st.markdown("---")
        st.markdown("### 🚨 Erase All Saved Data (Reset App State)")
        st.write("Use this feature after testing to wipe all test predictions, broadcast actuals, disputes, and player passwords back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords", key="confirm_erase_chk")
        if st.button("Erase All Saved Data & Reset Application", type="primary"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                for m in st.session_state.league_members:
                    st.session_state.league_members[m]["weekly_picks"] = {}
                    st.session_state.league_members[m]["season_picks"] = {}
                    st.session_state.league_members[m]["total_score"] = 0
                    st.session_state.league_members[m]["weekly_breakdown"] = {}
                    st.session_state.league_members[m]["pin"] = None
                    st.session_state.league_members[m]["season_score"] = 0
                if os.path.exists(DATA_FILE):
                    try: os.remove(DATA_FILE)
                    except Exception: pass
                st.success("All saved data permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed.")
