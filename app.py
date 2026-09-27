import streamlit as st
import pandas as pd
import random
import os
import json
import base64
import datetime
from zoneinfo import ZoneInfo
from PIL import Image

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for cozy baking theme & high-contrast legibility
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
    h1, h2, h3 {
        color: #5D4037;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENCE ENGINE ---
DATA_FILE = "league_data.json"

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    w_res = {}
                    for k, v in data.get("weekly_results", {}).items():
                        try:
                            w_res[int(k)] = v
                        except Exception:
                            w_res[k] = v
                    data["weekly_results"] = w_res
                    return data
        except Exception:
            pass
    return {}

def save_league_data():
    try:
        payload = {
            "league_members": st.session_state.get("league_members", {}),
            "weekly_results": st.session_state.get("weekly_results", {}),
            "season_results": st.session_state.get("season_results", {}),
            "disputes": st.session_state.get("disputes", [])
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

# --- 3. DEADLINE & SCORING ENGINE ---
def is_weekly_voting_closed():
    """Returns True ONLY on Tuesday at or after 2:00 PM Houston time."""
    try:
        now = datetime.datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        now = datetime.datetime.now()
        
    weekday = now.weekday()  # 0:Mon, 1:Tue, 2:Wed, 3:Thu, 4:Fri, 5:Sat, 6:Sun
    if weekday == 1 and now.hour >= 14:
        return True
    return False

def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return score
    
    if week == 10:
        if predictions.get("show_champion") and predictions.get("show_champion") == actuals.get("show_champion"):
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
        elif act_elim == "None":
            pass
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: score += 5
            elif pred_elim == act_elim:
                score += 5

        # Technical challenge scoring
        act_tech_rank = actuals.get("tech_rank", [])
        if week >= 8:
            pred_rank = predictions.get("tech_rank", [])
            if pred_rank and act_tech_rank:
                for idx, b in enumerate(pred_rank):
                    if idx < len(act_tech_rank) and act_tech_rank[idx] == b and b != "--Select Baker--":
                        score += 3 if idx in [0, len(act_tech_rank)-1] else 2
        else:
            act_top3 = act_tech_rank[:3] if len(act_tech_rank) >= 3 else act_tech_rank
            act_bot3 = act_tech_rank[-3:] if len(act_tech_rank) >= 3 else act_tech_rank
            
            pred_top3 = predictions.get("tech_top_3", [])
            if len(pred_top3) == 3 and len(act_top3) == 3:
                if pred_top3 == act_top3:
                    score += 6
                else:
                    if pred_top3[0] == act_top3[0] and pred_top3[0] != "--Select Baker--": score += 3
                    for idx, baker in enumerate(pred_top3):
                        if baker in act_top3 and baker != "--Select Baker--" and baker != act_top3[idx]:
                            score += 1
                            
            pred_bot3 = predictions.get("tech_bottom_3", [])
            if len(pred_bot3) == 3 and len(act_bot3) == 3:
                if pred_bot3 == act_bot3:
                    score += 6
                else:
                    if pred_bot3[2] == act_bot3[2] and pred_bot3[2] != "--Select Baker--": score += 3
                    for idx, baker in enumerate(pred_bot3):
                        if baker in act_bot3 and baker != "--Select Baker--" and baker != act_bot3[idx]:
                            score += 1

    return score

def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return score
    
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner == act_winner:
        score += 40
    elif pred_winner in act_finalists:
        score += 15
        
    for baker in predictions.get("semifinalists", []):
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    for key, exact_pts, buffer_pts, buf in [("handshakes", 20, 10, 1), ("crying", 20, 10, 5), ("innuendos", 20, 10, 5)]:
        p_val = predictions.get(key)
        a_val = actuals.get(key)
        if p_val is not None and a_val is not None:
            if p_val == a_val: score += exact_pts
            elif abs(p_val - a_val) <= buf: score += buffer_pts
            
    return score

# --- 4. ROSTER & STATE INITIALIZATION ---
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

saved_state = load_league_data()

if "league_members" not in st.session_state:
    st.session_state.league_members = saved_state.get("league_members", {})

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
    st.session_state.weekly_results = saved_state.get("weekly_results", {})
if "season_results" not in st.session_state:
    st.session_state.season_results = saved_state.get("season_results", {})
if "disputes" not in st.session_state:
    st.session_state.disputes = saved_state.get("disputes", [])
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "admin_verification_msg" not in st.session_state:
    st.session_state.admin_verification_msg = ""

def generate_ai_brian_season_picks():
    winner = random.choice(ALL_BAKERS)
    remaining_pool = [b for b in ALL_BAKERS if b != winner]
    semis = random.sample(remaining_pool, 3)
    return {
        "winner": winner, "semifinalists": semis,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

def get_eliminated_bakers_by_week():
    elim_map = {}
    elim_list = []
    for w in sorted(st.session_state.weekly_results.keys()):
        res = st.session_state.weekly_results[w]
        act_el = res.get("eliminated")
        if isinstance(act_el, list):
            for b in act_el:
                if b and b != "None" and b not in elim_list: elim_list.append(b)
        elif isinstance(act_el, str) and act_el and act_el != "None":
            if act_el not in elim_list: elim_list.append(act_el)
        elim_map[w + 1] = list(elim_list)
    return elim_map

eliminated_bakers_by_week = get_eliminated_bakers_by_week()
all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
active_prediction_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_prediction_week > 10: active_prediction_week = 10

# --- 5. SIDEBAR (Branding Header, No Sliders) ---
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
    st.warning("⏰ **Weekly voting window ends on Tuesdays at 2:00 PM Houston time.**")
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(Top 3)*
        * **Other 3 Semifinalists:** 10 pts each
        * **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        * **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        * **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
    with st.expander("📅 Weekly Predictions", expanded=False):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts
        * **In Line / In Trouble:** 2 pts each
        * **Technical Exact Positions:** 3 pts (1st/Last), 2 pts (middle)
        * **Star Member Bonus:** +5 pts to weekly high scorer
        """)

# --- 6. MAIN NAVIGATION TABS ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
tab_lead, tab_submit, tab_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📺 Show Results", 
    "👑 Admin Panel"
])

# ==============================================================================
# TAB 1: LEADERBOARD & STANDINGS
# ==============================================================================
with tab_lead:
    st.header("🏆 Live Leaderboard & Standings")
    
    lb_data = []
    for name, data in st.session_state.league_members.items():
        lb_data.append({"member": name, "points": data.get("total_score", 0), "data": data})
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        html_rows = []
        for idx, row in df_lb.iterrows():
            badge = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"#{idx}"))
            html_rows.append(f"<tr><td><b>{badge}</b></td><td>{row['member']}</td><td style='text-align: right;'><b>{row['points']} pts</b></td></tr>")
            
        st.markdown(f"""
        <table style="width: 100%; border-collapse: collapse;">
            <thead><tr><th style="width: 100px;">Rank</th><th>League Member</th><th style="text-align: right;">Total Points</th></tr></thead>
            <tbody>{''.join(html_rows)}</tbody>
        </table>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="lb_player_card_sel")
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Weekly Predictions Log**")
        if p_weekly:
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                w_pts = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                with st.expander(f"Week {w_num} Ballot (Earned: {w_pts} pts)"):
                    sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                    inl = w_picks.get("in_line_sb", "N/A")
                    
                    elim = w_picks.get("eliminated", "N/A")
                    if isinstance(elim, list):
                        elim_str = ", ".join([str(b) for b in elim if b])
                    else:
                        elim_str = str(elim)
                        
                    trb = w_picks.get("in_trouble", "N/A")
                    
                    tech_top = w_picks.get("tech_top_3", [])
                    tech_bot = w_picks.get("tech_bottom_3", [])
                    tech_rank = w_picks.get("tech_rank", [])
                    
                    if tech_top or tech_bot:
                        tech_str = f"Top 3: {', '.join(tech_top)} | Bottom 3: {', '.join(tech_bot)}"
                    elif tech_rank:
                        tech_str = " -> ".join([f"#{i+1}: {b}" for i, b in enumerate(tech_rank) if b])
                    else:
                        tech_str = "N/A"
                        
                    st.write(f"🌟 **Star Baker / Champion:** {sb}")
                    st.write(f"⭐ **In Line Nominee:** {inl}")
                    st.write(f"🚪 **Eliminated:** {elim_str}")
                    st.write(f"⚠️ **In Trouble Nominee:** {trb}")
                    st.write(f"📊 **Technical Challenge:** {tech_str}")
        else:
            st.info("No weekly prediction ballots submitted yet.")

        st.markdown("---")
        st.markdown(f"### **{selected_card_player}'s Season Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_list = p_season.get("semifinalists", [])
        semis_pick = ", ".join(semis_list) if semis_list else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick}")
        st.write(f"😢 **Predicted Crying Incidents:** {cry_pick}")
        st.write(f"💬 **Predicted Sexual Innuendos:** {inn_pick}")

# ==============================================================================
# TAB 2: SUBMIT PREDICTIONS
# ==============================================================================
with tab_submit:
    st.header("📝 Submit Predictions")
    pred_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="pred_player_login_sel")
    p_info = st.session_state.league_members[pred_player]
    
    auth_success = False
    
    if p_info.get("pin") is None:
        st.info(f"Welcome {pred_player}! Please create a 4-digit security PIN for your account:")
        with st.form(f"pin_create_form_{pred_player}"):
            p1 = st.text_input("Create 4-Digit Security PIN:", type="password")
            p2 = st.text_input("Confirm 4-Digit Security PIN:", type="password")
            submitted_pin = st.form_submit_button("Save Security PIN & Unlock")
            if submitted_pin:
                if p1 and p1 == p2 and len(p1) == 4 and p1.isdigit():
                    p_info["pin"] = p1
                    save_league_data()
                    st.success("Security PIN saved successfully! Ballot unlocked.")
                    st.rerun()
                else:
                    st.error("PIN must be exactly 4 numeric digits and match in both fields.")
    else:
        auth_key = f"auth_verified_{pred_player}"
        if st.session_state.get(auth_key, False):
            auth_success = True
            st.success(f"🔓 Authenticated as {pred_player}!")
        else:
            with st.form(f"pin_login_form_{pred_player}"):
                entered_pin = st.text_input(f"Enter 4-Digit Security PIN for {pred_player}:", type="password")
                submitted_login = st.form_submit_button("Unlock Ballot")
                if submitted_login:
                    if entered_pin == p_info.get("pin"):
                        st.session_state[auth_key] = True
                        st.success(f"🔓 Authenticated as {pred_player}!")
                        st.rerun()
                    else:
                        st.error("Incorrect PIN. Please try again.")
            if st.session_state.get(auth_key, False):
                auth_success = True

    if auth_success:
        st.markdown("---")
        if not st.session_state.weekly_results:
            st.warning("🔒 **Week 1 Scouting Phase:** Season-wide projections and Week 2 ballots unlock together once Week 1 results are published by the Admin!")
        elif is_weekly_voting_closed():
            st.error("⏰ **Weekly Voting Closed:** The weekly voting deadline (Tuesdays at 2:00 PM Houston time) has passed. Ballot submissions and edits are locked.")
        else:
            curr_elim = eliminated_bakers_by_week.get(active_prediction_week, [])
            active_bakers = [b for b in ALL_BAKERS if b not in curr_elim]
            
            prev_w = active_prediction_week - 1
            prev_res = st.session_state.weekly_results.get(prev_w, st.session_state.weekly_results.get(str(prev_w), {}))
            is_grace_week_catchup = (prev_res.get("eliminated") == "None")
            
            if is_grace_week_catchup:
                st.warning(f"⚠️ **Grace Week Catch-Up Active:** Because Week {prev_w} had no elimination, Week {active_prediction_week} is a **Double Elimination** week! You must predict **two** eliminated bakers.")

            saved_season = p_info.get("season_picks", {})
            saved_weekly = p_info.get("weekly_picks", {}).get(active_prediction_week, {})
            has_submitted = bool(saved_weekly) or (active_prediction_week == 2 and bool(saved_season and saved_season.get("winner")))

            if active_prediction_week == 2:
                st.subheader("🌟 Week 2 Ballot & Season-Long Projections")
                with st.form("week_2_combined_form"):
                    st.markdown("### 🌟 Season-Long Projections")
                    s_win_def = saved_season.get("winner", "--Select Baker--")
                    s_win_idx = (["--Select Baker--"] + ALL_BAKERS).index(s_win_def) if s_win_def in (["--Select Baker--"] + ALL_BAKERS) else 0
                    s_win = st.selectbox("Season Winner (40 pts):", ["--Select Baker--"] + ALL_BAKERS, index=s_win_idx)
                    
                    s_semis_def = [b for b in saved_season.get("semifinalists", []) if b in ALL_BAKERS]
                    s_semis = st.multiselect("3 Other Semifinalists (10 pts each - Select 3):", ALL_BAKERS, default=s_semis_def, max_selections=3)
                    
                    s_hs = st.number_input("Total Handshakes:", min_value=0, value=int(saved_season.get("handshakes", 0)), placeholder="e.g. 5")
                    s_cry = st.number_input("Total Crying Incidents:", min_value=0, value=int(saved_season.get("crying", 0)), placeholder="e.g. 12")
                    s_inn = st.number_input("Total Sexual Innuendos:", min_value=0, value=int(saved_season.get("innuendos", 0)), placeholder="e.g. 45")
                    
                    st.markdown("---")
                    st.markdown("### 📅 Week 2 Episodic Predictions")
                    weekly_picks = {}
                    col1, col2 = st.columns(2)
                    with col1:
                        sb_def = saved_weekly.get("star_baker", "--Select Baker--")
                        sb_idx = (["--Select Baker--"] + active_bakers).index(sb_def) if sb_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["star_baker"] = st.selectbox("Star Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=sb_idx)
                        
                        inl_def = saved_weekly.get("in_line_sb", "--Select Baker--")
                        inl_idx = (["--Select Baker--"] + active_bakers).index(inl_def) if inl_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["in_line_sb"] = st.selectbox("'In Line' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=inl_idx)
                    with col2:
                        el_def = saved_weekly.get("eliminated", "--Select Baker--")
                        el_idx = (["--Select Baker--"] + active_bakers).index(el_def) if el_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["eliminated"] = st.selectbox("Eliminated Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=el_idx)
                            
                        trb_def = saved_weekly.get("in_trouble", "--Select Baker--")
                        trb_idx = (["--Select Baker--"] + active_bakers).index(trb_def) if trb_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["in_trouble"] = st.selectbox("'In Trouble' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=trb_idx)
                    
                    st.markdown("#### Technical Challenge Predictions:")
                    col_t1, col_t2 = st.columns(2)
                    saved_top = saved_weekly.get("tech_top_3", [])
                    saved_bot = saved_weekly.get("tech_bottom_3", [])
                    with col_t1:
                        st.write("**Top 3 Technical:**")
                        tp_defaults = [b for b in saved_top if b in active_bakers]
                        tp1 = st.selectbox("1st Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[0]) if len(tp_defaults)>0 and tp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="tp_1")
                        tp2 = st.selectbox("2nd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[1]) if len(tp_defaults)>1 and tp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="tp_2")
                        tp3 = st.selectbox("3rd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[2]) if len(tp_defaults)>2 and tp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="tp_3")
                        weekly_picks["tech_top_3"] = [tp1, tp2, tp3]
                    with col_t2:
                        st.write("**Bottom 3 Technical:**")
                        bp_defaults = [b for b in saved_bot if b in active_bakers]
                        bp1 = st.selectbox("3rd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[0]) if len(bp_defaults)>0 and bp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="bp_1")
                        bp2 = st.selectbox("2nd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[1]) if len(bp_defaults)>1 and bp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="bp_2")
                        bp3 = st.selectbox("Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[2]) if len(bp_defaults)>2 and bp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="bp_3")
                        weekly_picks["tech_bottom_3"] = [bp1, bp2, bp3]
                    
                    edit_conf = True
                    if has_submitted:
                        edit_conf = st.checkbox("⚠️ Check this box to confirm you want to edit your previously submitted Week 2 Ballot & Season Projections.")

                    sub_w2 = st.form_submit_button("Submit Week 2 Ballot & Season Projections")
                    if sub_w2:
                        errors = []
                        if has_submitted and not edit_conf:
                            errors.append("❌ Please check the confirmation box to edit your previously submitted ballot.")
                        if s_win == "--Select Baker--":
                            errors.append("Please select a valid Season Winner.")
                        
                        main_picks = [weekly_picks.get("star_baker"), weekly_picks.get("eliminated"), weekly_picks.get("in_line_sb"), weekly_picks.get("in_trouble")]
                        valid_main = [p for p in main_picks if p and p != "--Select Baker--"]
                        if len(valid_main) != len(set(valid_main)):
                            errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                            
                        valid_top = [t for t in weekly_picks.get("tech_top_3", []) if t and t != "--Select Baker--"]
                        valid_bot = [t for t in weekly_picks.get("tech_bottom_3", []) if t and t != "--Select Baker--"]
                        if len(valid_top) != len(set(valid_top)):
                            errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Top 3 Technical picks!")
                        if len(valid_bot) != len(set(valid_bot)):
                            errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Bottom 3 Technical picks!")
                        if any(b in valid_bot for b in valid_top):
                            errors.append("❌ Duplicate Selection Error: A baker cannot appear in both Top 3 and Bottom 3 technical predictions!")
                            
                        if errors:
                            for err in errors:
                                st.error(err)
                        else:
                            p_info["season_picks"] = {"winner": s_win, "semifinalists": s_semis, "handshakes": s_hs, "crying": s_cry, "innuendos": s_inn}
                            p_info["weekly_picks"][2] = weekly_picks
                            if 2 not in st.session_state.league_members["AI Brian"]["weekly_picks"]:
                                st.session_state.league_members["AI Brian"]["weekly_picks"][2] = {
                                    "star_baker": random.choice(active_bakers),
                                    "eliminated": random.choice(active_bakers),
                                    "tech_top_3": random.sample(active_bakers, min(3, len(active_bakers))),
                                    "tech_bottom_3": random.sample(active_bakers, min(3, len(active_bakers)))
                                }
                            save_league_data()
                            st.success("Week 2 Ballot and Season Projections successfully saved!")

            else:
                st.markdown(f"### 📅 Week {active_prediction_week} Prediction Ballot")
                with st.form("weekly_ballot_form"):
                    weekly_picks = {}
                    if active_prediction_week == 10:
                        champ_def = saved_weekly.get("show_champion", "--Select Baker--")
                        champ_idx = (["--Select Baker--"] + active_bakers).index(champ_def) if champ_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["show_champion"] = st.selectbox("Show Champion (15 pts):", ["--Select Baker--"] + active_bakers, index=champ_idx)
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            sb_def = saved_weekly.get("star_baker", "--Select Baker--")
                            sb_idx = (["--Select Baker--"] + active_bakers).index(sb_def) if sb_def in (["--Select Baker--"] + active_bakers) else 0
                            weekly_picks["star_baker"] = st.selectbox("Star Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=sb_idx)
                            
                            inl_def = saved_weekly.get("in_line_sb", "--Select Baker--")
                            inl_idx = (["--Select Baker--"] + active_bakers).index(inl_def) if inl_def in (["--Select Baker--"] + active_bakers) else 0
                            weekly_picks["in_line_sb"] = st.selectbox("'In Line' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=inl_idx)
                        with col2:
                            if is_grace_week_catchup:
                                el_def = [b for b in saved_weekly.get("eliminated", []) if b in active_bakers]
                                weekly_picks["eliminated"] = st.multiselect("Predicted 2 Eliminated Bakers (5 pts each - Select 2):", active_bakers, default=el_def, max_selections=2)
                            else:
                                el_def = saved_weekly.get("eliminated", "--Select Baker--")
                                el_idx = (["--Select Baker--"] + active_bakers).index(el_def) if el_def in (["--Select Baker--"] + active_bakers) else 0
                                weekly_picks["eliminated"] = st.selectbox("Eliminated Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=el_idx)
                                
                            trb_def = saved_weekly.get("in_trouble", "--Select Baker--")
                            trb_idx = (["--Select Baker--"] + active_bakers).index(trb_def) if trb_def in (["--Select Baker--"] + active_bakers) else 0
                            weekly_picks["in_trouble"] = st.selectbox("'In Trouble' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=trb_idx)
                    
                    st.markdown("#### Technical Challenge Predictions:")
                    if active_prediction_week >= 8:
                        num_b = len(active_bakers)
                        st.write(f"Rank all {num_b} Bakers (1st through {num_b}th):")
                        tech_ranks = []
                        saved_tech = saved_weekly.get("tech_rank", [])
                        for i in range(num_b):
                            t_def = saved_tech[i] if (isinstance(saved_tech, list) and i < len(saved_tech) and saved_tech[i] in active_bakers) else "--Select Baker--"
                            t_idx = (["--Select Baker--"] + active_bakers).index(t_def) if t_def in (["--Select Baker--"] + active_bakers) else 0
                            rank_str = "1st" if i==0 else ("2nd" if i==1 else ("3rd" if i==2 else f"{i+1}th"))
                            sel = st.selectbox(f"Technical {rank_str} Place", ["--Select Baker--"] + active_bakers, index=t_idx, key=f"tech_rank_{i}")
                            tech_ranks.append(sel)
                        weekly_picks["tech_rank"] = tech_ranks
                    else:
                        saved_top = saved_weekly.get("tech_top_3", [])
                        saved_bot = saved_weekly.get("tech_bottom_3", [])
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            st.write("**Top 3 Technical:**")
                            tp_defaults = [b for b in saved_top if b in active_bakers]
                            tp1 = st.selectbox("1st Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[0]) if len(tp_defaults)>0 and tp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="tp_1")
                            tp2 = st.selectbox("2nd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[1]) if len(tp_defaults)>1 and tp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="tp_2")
                            tp3 = st.selectbox("3rd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[2]) if len(tp_defaults)>2 and tp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="tp_3")
                            weekly_picks["tech_top_3"] = [tp1, tp2, tp3]
                        with col_t2:
                            st.write("**Bottom 3 Technical:**")
                            bp_defaults = [b for b in saved_bot if b in active_bakers]
                            bp1 = st.selectbox("3rd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[0]) if len(bp_defaults)>0 and bp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="bp_1")
                            bp2 = st.selectbox("2nd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[1]) if len(bp_defaults)>1 and bp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="bp_2")
                            bp3 = st.selectbox("Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[2]) if len(bp_defaults)>2 and bp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="bp_3")
                            weekly_picks["tech_bottom_3"] = [bp1, bp2, bp3]
                    
                    edit_conf = True
                    if has_submitted:
                        edit_conf = st.checkbox(f"⚠️ Check this box to confirm you want to edit your previously submitted Week {active_prediction_week} ballot.")

                    sub_weekly = st.form_submit_button(f"Submit Week {active_prediction_week} Ballot")
                    if sub_weekly:
                        errors = []
                        if has_submitted and not edit_conf:
                            errors.append(f"❌ Please check the confirmation box to edit your previously submitted Week {active_prediction_week} ballot.")
                        
                        if active_prediction_week < 10:
                            main_picks = []
                            sb = weekly_picks.get("star_baker")
                            if sb and sb != "--Select Baker--": main_picks.append(sb)
                            
                            inl = weekly_picks.get("in_line_sb")
                            if inl and inl != "--Select Baker--": main_picks.append(inl)
                            
                            elim = weekly_picks.get("eliminated")
                            if isinstance(elim, list):
                                for e in elim:
                                    if e and e != "--Select Baker--": main_picks.append(e)
                            elif elim and elim != "--Select Baker--":
                                main_picks.append(elim)
                                
                            trb = weekly_picks.get("in_trouble")
                            if trb and trb != "--Select Baker--": main_picks.append(trb)
                            
                            if len(main_picks) != len(set(main_picks)):
                                errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                                
                        if active_prediction_week >= 8:
                            valid_tech = [t for t in weekly_picks.get("tech_rank", []) if t and t != "--Select Baker--"]
                            if len(valid_tech) != len(set(valid_tech)):
                                errors.append("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            valid_top = [t for t in weekly_picks.get("tech_top_3", []) if t and t != "--Select Baker--"]
                            valid_bot = [t for t in weekly_picks.get("tech_bottom_3", []) if t and t != "--Select Baker--"]
                            if len(valid_top) != len(set(valid_top)):
                                errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Top 3 Technical picks!")
                            if len(valid_bot) != len(set(valid_bot)):
                                errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Bottom 3 Technical picks!")
                            if any(b in valid_bot for b in valid_top):
                                errors.append("❌ Duplicate Selection Error: A baker cannot appear in both Top 3 and Bottom 3 technical predictions!")
                            
                        if errors:
                            for err in errors:
                                st.error(err)
                        else:
                            p_info["weekly_picks"][active_prediction_week] = weekly_picks
                            if active_prediction_week not in st.session_state.league_members["AI Brian"]["weekly_picks"]:
                                st.session_state.league_members["AI Brian"]["weekly_picks"][active_prediction_week] = {
                                    "star_baker": random.choice(active_bakers),
                                    "eliminated": random.sample(active_bakers, 2) if is_grace_week_catchup else random.choice(active_bakers),
                                    "tech_top_3": random.sample(active_bakers, min(3, len(active_bakers))),
                                    "tech_bottom_3": random.sample(active_bakers, min(3, len(active_bakers)))
                                }
                            save_league_data()
                            st.success(f"Week {active_prediction_week} ballot submitted successfully!")

# ==============================================================================
# TAB 3: SHOW RESULTS
# ==============================================================================
with tab_results:
    st.header("📺 Official Broadcast Results")
    
    weekly_res_map = st.session_state.get("weekly_results", {})
    
    if weekly_res_map:
        st.subheader("📋 Published Weekly Results")
        sel_res_week = st.selectbox("Select Week to View Results:", sorted(weekly_res_map.keys()), key="show_res_week_sel")
        if sel_res_week:
            w_act = weekly_res_map[sel_res_week]
            
            st.markdown(f"### 🧁 Episode Week {sel_res_week} Results")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                if sel_res_week == 10:
                    st.write(f"🏆 **Show Champion:** {w_act.get('show_champion', 'N/A')}")
                else:
                    st.write(f"🌟 **Star Baker:** {w_act.get('star_baker', 'N/A')}")
                    
                    inline_val = w_act.get('in_line_sb', 'N/A')
                    if isinstance(inline_val, list):
                        inline_str = ", ".join([str(b) for b in inline_val if b])
                    else:
                        inline_str = str(inline_val)
                    st.write(f"⭐ **'In Line' for Star Baker:** {inline_str}")
                    
                    elim_val = w_act.get('eliminated', 'N/A')
                    if isinstance(elim_val, list):
                        elim_str = ", ".join([str(b) for b in elim_val if b])
                    else:
                        elim_str = str(elim_val)
                    st.write(f"🚪 **Eliminated:** {elim_str}")
                    
                    trouble_val = w_act.get('in_trouble', 'N/A')
                    if isinstance(trouble_val, list):
                        trouble_str = ", ".join([str(b) for b in trouble_val if b])
                    else:
                        trouble_str = str(trouble_val)
                    st.write(f"⚠️ **'In Trouble':** {trouble_str}")
            with col_res2:
                hs_bakers = w_act.get('handshake_bakers', [])
                hs_str = ", ".join([str(b) for b in hs_bakers if b]) if hs_bakers else "None"
                st.write(f"🤝 **Hollywood Handshakes:** {hs_str}")
                st.write(f"😢 **Crying Incidents ({w_act.get('crying_count', 0)}):** {w_act.get('crying_timestamps', 'None recorded')}")
                st.write(f"💬 **Sexual Innuendos ({w_act.get('innuendo_count', 0)}):** {w_act.get('innuendo_timestamps', 'None recorded')}")
            
            tech_r = w_act.get('tech_rank', [])
            tech_top = w_act.get('tech_top_3', [])
            tech_bot = w_act.get('tech_bottom_3', [])
            if tech_r:
                st.markdown("**Technical Challenge Standings:**")
                st.write(" -> ".join([f"**#{i+1}** {b}" for i, b in enumerate(tech_r)]))
            elif tech_top or tech_bot:
                st.markdown("**Technical Challenge Standings:**")
                st.write(f"Top 3: {', '.join(tech_top)} | Bottom 3: {', '.join(tech_bot)}")
    else:
        st.info("No official broadcast results published yet by the administrator.")

    st.markdown("---")
    st.subheader("🔥 Cumulative Season Chaos Counters")
    
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    if weekly_res_map:
        for w_data in weekly_res_map.values():
            tot_hs += len(w_data.get("handshake_bakers", []))
            tot_cry += int(w_data.get("crying_count", 0))
            tot_inn += int(w_data.get("innuendo_count", 0))
            
    c_col1, c_col2, c_col3 = st.columns(3)
    c_col1.metric("🤝 Total Hollywood Handshakes", tot_hs)
    c_col2.metric("😢 Total Crying Incidents", tot_cry)
    c_col3.metric("💬 Total Sexual Innuendos", tot_inn)

    st.markdown("---")
    st.subheader("⚖️ Result Dispute & Timestamp Correction")
    
    dispute_player_choice = st.selectbox("Select Your Name to Log a Dispute:", ["-- Select Name --"] + ROSTER_HUMANS, key="dispute_player_dropdown")
    
    if dispute_player_choice != "-- Select Name --":
        st.success(f"Logging dispute as **{dispute_player_choice}**")
        with st.form("dispute_form"):
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(weekly_res_map.keys())] if weekly_res_map else ["Week 1"])
            disp_evidence = st.text_area("Video Timestamp & Evidence Description:")
            disp_correction = st.text_input("Requested Correction:")
            
            if st.form_submit_button("Submit Dispute"):
                st.session_state.disputes.append({
                    "Player": dispute_player_choice, "Week": disp_week,
                    "Evidence": disp_evidence, "Correction": disp_correction,
                    "Status": "Pending Review 🗳️"
                })
                save_league_data()
                st.success("Dispute submitted successfully for league review!")
    else:
        st.info("👆 Please select your player name from the dropdown above to open the dispute submission form.")

    st.markdown("---")
    st.subheader("📋 Logged Disputes & Status")
    if st.session_state.get("disputes"):
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)
    else:
        st.info("No disputes submitted yet.")

# ==============================================================================
# TAB 4: ADMIN PANEL
# ==============================================================================
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        admin_pin = st.text_input("Enter Administrator PIN:", type="password")
        if st.button("Unlock Admin Panel"):
            if admin_pin == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN.")
    else:
        st.success("🔓 Authenticated as Administrator")
        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        
        if st.session_state.admin_verification_msg:
            st.success(st.session_state.admin_verification_msg)
            
        admin_selected_week = st.selectbox("Select Episode Week:", list(range(1, 11)), key="adm_w_sel")
        
        saved_w = st.session_state.weekly_results.get(admin_selected_week, st.session_state.weekly_results.get(str(admin_selected_week), {}))
        is_published = bool(saved_w)
        
        edit_allowed = True
        if is_published:
            st.warning(f"⚠️ Week {admin_selected_week} results are already published.")
            edit_allowed = st.checkbox(f"Unlock Week {admin_selected_week} to edit published results and modify historical scoring", value=False, key=f"unlock_w{admin_selected_week}")
            if not edit_allowed:
                st.info("Form fields are locked to protect existing historical scoring. Check the box above to enable editing.")
        
        elim_type = st.radio("Elimination Format:", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key=f"adm_elim_type_w{admin_selected_week}")
        
        active_bakers = [b for b in ALL_BAKERS if b not in eliminated_bakers_by_week.get(admin_selected_week, [])]
        baker_opts = ["-- Select Baker --"] + active_bakers
        
        with st.form("admin_results_form"):
            st.subheader(f"Input Official Results for Week {admin_selected_week}")
            actuals = {}
            if admin_selected_week == 10:
                def_champ = saved_w.get("show_champion")
                def_champ_i = baker_opts.index(def_champ) if def_champ in baker_opts else 0
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts, index=def_champ_i)
            else:
                st.markdown("#### 🌟 Star Baker & Elimination Group")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    def_sb = saved_w.get("star_baker")
                    def_sb_i = baker_opts.index(def_sb) if def_sb in baker_opts else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=def_sb_i, key=f"adm_sb_w{admin_selected_week}")
                    
                    def_inline = saved_w.get("in_line_sb")
                    def_inline_i = baker_opts.index(def_inline) if def_inline in baker_opts else 0
                    actuals["in_line_sb"] = st.selectbox("Actual 'In Line' for Star Baker", baker_opts, index=def_inline_i, key=f"adm_inline_w{admin_selected_week}")
                with col_g2:
                    if elim_type == "Single Elimination":
                        def_elim = saved_w.get("eliminated")
                        def_elim_i = baker_opts.index(def_elim) if def_elim in baker_opts else 0
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=def_elim_i, key=f"adm_elim_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("Grace week active: No elimination.")
                    else:
                        el_list = saved_w.get("eliminated", [])
                        def_e1 = el_list[0] if isinstance(el_list, list) and len(el_list) > 0 else baker_opts[0]
                        def_e2 = el_list[1] if isinstance(el_list, list) and len(el_list) > 1 else baker_opts[0]
                        e1 = st.selectbox("Eliminated #1", baker_opts, index=baker_opts.index(def_e1) if def_e1 in baker_opts else 0, key=f"adm_elim1_w{admin_selected_week}")
                        e2 = st.selectbox("Eliminated #2", baker_opts, index=baker_opts.index(def_e2) if def_e2 in baker_opts else 0, key=f"adm_elim2_w{admin_selected_week}")
                        actuals["eliminated"] = [e1, e2]
                        
                    def_introuble = saved_w.get("in_trouble")
                    def_introuble_i = baker_opts.index(def_introuble) if def_introuble in baker_opts else 0
                    actuals["in_trouble"] = st.selectbox("Actual 'In Trouble' for Elimination", baker_opts, index=def_introuble_i, key=f"adm_introuble_w{admin_selected_week}")
            
            # ADMIN TECHNICAL CHALLENGE: Always enter every single technical placement available for all active bakers
            st.markdown(f"#### Technical Challenge Rankings (Enter all {len(active_bakers)} active bakers 1st through {len(active_bakers)}th):")
            act_tech = []
            saved_tech_rank = saved_w.get("tech_rank", [])
            for idx, b in enumerate(active_bakers):
                def_t = saved_tech_rank[idx] if (isinstance(saved_tech_rank, list) and idx < len(saved_tech_rank)) else baker_opts[0]
                def_t_i = baker_opts.index(def_t) if def_t in baker_opts else 0
                rank_str = "1st" if idx==0 else ("2nd" if idx==1 else ("3rd" if idx==2 else f"{idx+1}th"))
                sel = st.selectbox(f"Actual Technical {rank_str} Place", baker_opts, index=def_t_i, key=f"adm_t_{idx}_{admin_selected_week}")
                act_tech.append(sel)
            actuals["tech_rank"] = act_tech
            
            st.markdown("#### Chaos Categories & Timestamps:")
            def_hs_bakers = saved_w.get("handshake_bakers", [])
            actuals["handshake_bakers"] = st.multiselect("Bakers Receiving Handshakes", active_bakers, default=[b for b in def_hs_bakers if b in active_bakers])
            
            st.markdown("##### 😢 Crying Incidents")
            actuals["crying_count"] = st.number_input("Number of Crying Occurrences", min_value=0, value=int(saved_w.get("crying_count", 0)), key=f"adm_cry_count_{admin_selected_week}")
            actuals["crying_timestamps"] = st.text_input("Description of Crying Occurrence", value=saved_w.get("crying_timestamps", ""), placeholder="e.g. Molly @ 14:00", key=f"adm_cry_desc_{admin_selected_week}")
            
            st.markdown("##### 💬 Sexual Innuendos")
            actuals["innuendo_count"] = st.number_input("Number of Innuendo Occurrences", min_value=0, value=int(saved_w.get("innuendo_count", 0)), key=f"adm_inn_count_{admin_selected_week}")
            actuals["innuendo_timestamps"] = st.text_input("Description of Innuendos", value=saved_w.get("innuendo_timestamps", ""), placeholder="e.g. Soggy bottom @ 18:45", key=f"adm_inn_desc_{admin_selected_week}")
            
            if admin_selected_week == 10:
                st.markdown("---")
                st.subheader("Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner", baker_opts, key=f"adm_season_winner_w{admin_selected_week}")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4, key=f"adm_season_semis_w{admin_selected_week}")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3, key=f"adm_season_fin_w{admin_selected_week}")
                act_handshakes = st.number_input("Actual Season Total Handshakes", min_value=0, value=5, key=f"adm_season_hs_w{admin_selected_week}")
                act_crying = st.number_input("Actual Season Total Crying Incidents", min_value=0, value=12, key=f"adm_season_cry_w{admin_selected_week}")
                act_innuendos = st.number_input("Actual Season Total Sexual Innuendos", min_value=0, value=48, key=f"adm_season_inn_w{admin_selected_week}")

                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }

            pub_btn = st.form_submit_button("Publish Results & Recalculate Standings")
            if pub_btn:
                if is_published and not edit_allowed:
                    st.error("❌ Week results are locked. Please check the 'Unlock to Edit' box above before publishing changes.")
                else:
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
                    
                    action_type = "republished and updated" if is_published else "published"
                    st.session_state.admin_verification_msg = f"✅ **Verification Confirmed:** Week {admin_selected_week} results successfully {action_type}! All player scores, standings, and scorecards have been successfully recalculated."
                    st.rerun()

        st.markdown("---")
        st.subheader("🗳️ Resolve League Disputes")
        st.write("Review active disputes submitted by players, vote in GroupMe, and record the final ruling below:")
        if st.session_state.get("disputes"):
            for idx, disp in enumerate(st.session_state.disputes):
                st.markdown(f"**Dispute #{idx+1}** | Player: **{disp.get('Player')}** | Week: **{disp.get('Week')}** | Status: `{disp.get('Status')}`")
                st.markdown(f"*Evidence:* {disp.get('Evidence')}")
                st.markdown(f"*Correction Requested:* {disp.get('Correction')}")
                
                c_res1, c_res2 = st.columns(2)
                with c_res1:
                    if st.button(f"Accept Dispute #{idx+1}", key=f"accept_disp_{idx}"):
                        st.session_state.disputes[idx]["Status"] = "Accepted ✅"
                        save_league_data()
                        st.success(f"Dispute #{idx+1} marked as Accepted!")
                        st.rerun()
                with c_res2:
                    if st.button(f"Reject Dispute #{idx+1}", key=f"reject_disp_{idx}"):
                        st.session_state.disputes[idx]["Status"] = "Rejected ❌"
                        save_league_data()
                        st.success(f"Dispute #{idx+1} marked as Rejected!")
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No active disputes to resolve.")

        st.subheader("🔑 Reset Forgotten Player Security PIN")
        human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
        reset_sel_player = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + human_players, key="admin_pin_reset_dropdown")
        if reset_sel_player != "-- Select Player --":
            if st.button(f"Reset PIN for {reset_sel_player}"):
                st.session_state.league_members[reset_sel_player]["pin"] = None
                save_league_data()
                st.success(f"Security PIN for {reset_sel_player} has been cleared! They can set a new 4-digit PIN upon next login.")
                st.rerun()

        st.markdown("---")
        st.subheader("🚨 Emergency Reset & Delete All App Data")
        confirm_erase = st.checkbox("I understand this will permanently erase all player prediction ballots, PINs, and published broadcast results.", key="confirm_erase_check")
        if st.button("🗑️ Erase All Competition Data", type="primary"):
            if confirm_erase:
                if os.path.exists(DATA_FILE):
                    try:
                        os.remove(DATA_FILE)
                    except Exception:
                        pass
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("All competition data successfully erased!")
                st.rerun()
            else:
                st.error("Please check the confirmation box above first.")
