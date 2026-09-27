import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import os
import base64
import json

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for high contrast and cozy theme
st.markdown("""
<style>
    .reportview-container { background: #FFF9F2; }
    .stButton>button {
        background-color: #D36B5F;
        color: white !important;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #B54E43;
        color: white !important;
    }
    h1, h2, h3 { color: #5D4037; }
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3,
    .stApp[data-theme="dark"] h1, .stApp[data-theme="dark"] h2, .stApp[data-theme="dark"] h3 {
        color: #FFCC80 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & SYSTEM CONSTANTS ---
DATA_FILE = "league_data.json"

ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo",
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ALL_HUMANS_AND_AI = sorted(ROSTER_HUMANS) + ["AI Brian"]

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

def load_baker_image(baker_name):
    filename = f"assets/{baker_name.lower()}.jpg"
    if os.path.exists(filename):
        try: return Image.open(filename)
        except Exception: pass
    return None

def normalize_dict_keys(d):
    if not isinstance(d, dict): return d
    new_d = {}
    for k, v in d.items():
        try:
            nk = int(k)
        except (ValueError, TypeError):
            nk = k
        new_d[nk] = v
    return new_d

def save_league_data():
    data = {
        "league_members": st.session_state.get("league_members", {}),
        "weekly_results": normalize_dict_keys(st.session_state.get("weekly_results", {})),
        "season_results": st.session_state.get("season_results", {}),
        "disputes": st.session_state.get("disputes", []),
        "player_pins": st.session_state.get("player_pins", {})
    }
    try:
        clean_members = {}
        for m, mdata in data["league_members"].items():
            clean_members[m] = {
                "weekly_picks": normalize_dict_keys(mdata.get("weekly_picks", {})),
                "season_picks": mdata.get("season_picks", {}),
                "total_score": mdata.get("total_score", 0),
                "weekly_breakdown": normalize_dict_keys(mdata.get("weekly_breakdown", {}))
            }
        data["league_members"] = clean_members
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception: pass

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception: return None
    return None

saved_data = load_league_data()

if "league_members" not in st.session_state:
    if saved_data and "league_members" in saved_data:
        st.session_state.league_members = saved_data["league_members"]
    else:
        st.session_state.league_members = {}
        for name in ALL_HUMANS_AND_AI:
            st.session_state.league_members[name] = {
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {}
            }

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = normalize_dict_keys(saved_data.get("weekly_results", {})) if saved_data else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_data.get("season_results", {}) if saved_data else {}

if "disputes" not in st.session_state:
    st.session_state.disputes = saved_data.get("disputes", []) if saved_data else []

if "player_pins" not in st.session_state:
    st.session_state.player_pins = saved_data.get("player_pins", {}) if saved_data else {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

for name in ALL_HUMANS_AND_AI:
    if name not in st.session_state.league_members:
        st.session_state.league_members[name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

def get_active_bakers(week_num):
    elim = []
    for w in sorted(list(st.session_state.weekly_results.keys())):
        if int(w) < int(week_num):
            w_res = st.session_state.weekly_results[w]
            act_el = w_res.get("eliminated")
            if isinstance(act_el, list):
                for b in act_el:
                    if b and b != "None" and b not in elim: elim.append(b)
            elif isinstance(act_el, str) and act_el and act_el != "None":
                if act_el not in elim: elim.append(act_el)
    return [b for b in ALL_BAKERS if b not in elim]

# --- 3. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=1):
    score = 0
    if not predictions or not actuals: return 0
    
    if int(week) == 10:
        if predictions.get("show_champion") == actuals.get("show_champion") and predictions.get("show_champion"):
            score += 15
    else:
        if predictions.get("star_baker") == actuals.get("star_baker") and predictions.get("star_baker"):
            score += 5
        if predictions.get("in_line_sb") and actuals.get("in_line_sb"):
            if predictions.get("in_line_sb") in actuals.get("in_line_sb"):
                score += 2
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim: score += 5
            elif isinstance(pred_elim, str) and pred_elim in act_elim:
                score += 5
        elif act_elim != "None":
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: score += 5
            elif pred_elim == act_elim and pred_elim:
                score += 5
                
        if predictions.get("in_trouble") and actuals.get("in_trouble"):
            if predictions.get("in_trouble") in actuals.get("in_trouble"):
                score += 2
                
    # Technical scoring
    pred_rank = predictions.get("tech_rank", [])
    act_rank = actuals.get("tech_rank", [])
    if pred_rank and act_rank and len(pred_rank) == len(act_rank):
        exact_cnt = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
        if exact_cnt == len(pred_rank):
            score += (25 if int(week) == 8 else (20 if int(week) == 9 else (15 if int(week) == 10 else 10)))
        else:
            for idx, b in enumerate(pred_rank):
                if act_rank[idx] == b:
                    if idx in [0, len(pred_rank)-1]: score += 3
                    else: score += 2
    return score

def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals: return 0
    if predictions.get("winner") == actuals.get("winner") and predictions.get("winner"):
        score += 40
    elif predictions.get("winner") in actuals.get("finalists", []):
        score += 15
    for semi in predictions.get("semifinalists", []):
        if semi in actuals.get("semifinalists", []):
            score += 10
    return score

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    if not active_bakers: return {}
    sb = random.choice(active_bakers)
    rem = [b for b in active_bakers if b != sb]
    el = random.sample(rem, 2) if (is_double_elim and len(rem) >= 2) else (random.choice(rem) if rem else sb)
    tr = random.sample(active_bakers, len(active_bakers))
    return {"star_baker": sb, "eliminated": el, "tech_rank": tr}

# --- 4. HEADER & SIDEBAR ---
col_head1, col_head2 = st.columns([1, 5])
with col_head1:
    st.markdown("# 🧁")
with col_head2:
    st.title("Great British Baking Show Fantasy League 2026")
    st.markdown("### Powered by the Official 2026 Competition Rules Engine")

with st.sidebar:
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of points at stake for each prediction!")
    st.warning("⏰ **Weekly voting window ends on Tuesdays right before the show airs in the UK.**")
    
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(Top 3 runner-up)*
        * **Other 3 Semifinalists:** 10 pts each
        """)
        
    with st.expander("📅 Standard Weeks (Weeks 1-7)", expanded=False):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts
        * **In Line (Consolation):** 2 pts
        * **In Trouble (Consolation):** 2 pts
        * **Technical Challenge (Exact Spot):** 1st/Last (3 pts), 2nd/3rd (2 pts)
        * **Perfect Technical Sweep:** Flat Bonus
        """)

# --- 5. MAIN NAVIGATION TABS ---
tab_lead, tab_submit, tab_show_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📺 Show Results", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_data = []
    for name in ALL_HUMANS_AND_AI:
        data = st.session_state.league_members.get(name, {})
        tot_pts = data.get("total_score", 0)
        lb_data.append({
            "Rank": 0,
            "League Member": name,
            "Total Points": f"{tot_pts} pts",
            "pts_num": tot_pts
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="pts_num", ascending=False).reset_index(drop=True)
        for idx, row in df_lb.iterrows():
            rk = idx + 1
            badge = f"🥇 #{rk}" if rk == 1 else ("🥈 #" + str(rk) if rk == 2 else ("🥉 #" + str(rk) if rk == 3 else f"#{rk}"))
            df_lb.at[idx, "Rank"] = badge
            
        df_display = df_lb[["Rank", "League Member", "Total Points"]]
        st.dataframe(df_display, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    sel_card_player = st.selectbox("Select Player Scorecard to View:", ALL_HUMANS_AND_AI, key="lb_card_player_sel")
    
    if sel_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[sel_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{sel_card_player}'s Scorecard (Total Points: {p_pts} pts)**")
        win_p = p_season.get("winner", "Not submitted yet")
        semis_p = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        st.write(f"🏆 **Predicted Winner:** {win_p}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_p}")
        
        if p_weekly:
            st.markdown("#### **Weekly Predictions Log:**")
            w_rows = []
            for w_num in sorted(list(p_weekly.keys())):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                t_rank = w_picks.get("tech_rank", [])
                t_str = ", ".join(t_rank) if t_rank else "N/A"
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Rankings": t_str
                })
            st.dataframe(pd.DataFrame(w_rows), hide_index=True, use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    # Calculate active week based on published results
    published_weeks = sorted([int(w) for w in st.session_state.weekly_results.keys()])
    sub_week = max(published_weeks) + 1 if published_weeks else 1
    if sub_week > 10: sub_week = 10
    
    active_bakers = get_active_bakers(sub_week)
    
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
        cols = st.columns(4)
        for idx, baker in enumerate(active_bakers):
            info = BAKER_INFO.get(baker, {"url": "#"})
            with cols[idx % 4]:
                img = load_baker_image(baker)
                if img is not None:
                    st.image(img, use_container_width=True)
                    st.markdown(f"**{baker}**")
                else:
                    st.markdown(f"**{baker}**")
                    st.markdown(f"[🔗 View Photo Page]({info['url']})")

    st.markdown("---")
    st.subheader(f"📅 Prediction Ballot for Week {sub_week}")
    
    sel_player = st.selectbox("Select Your Name / Player Profile:", ["-- Select Your Name --"] + ROSTER_HUMANS, key="pred_player_select")
    
    if sel_player != "-- Select Your Name --":
        p_pin = st.session_state.player_pins.get(sel_player)
        authenticated = False
        
        if not p_pin:
            st.info(f"🔒 First-time PIN setup for **{sel_player}**. Create a 4-digit security PIN to lock your ballot:")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                new_pin = st.text_input("Create 4-Digit PIN", type="password", key="create_pin_1")
            with col_p2:
                conf_pin = st.text_input("Confirm 4-Digit PIN", type="password", key="create_pin_2")
            if st.button("Set PIN & Unlock Ballot"):
                if len(new_pin) == 4 and new_pin.isdigit() and new_pin == conf_pin:
                    st.session_state.player_pins[sel_player] = new_pin
                    save_league_data()
                    st.success("Security PIN created successfully!")
                    st.rerun()
                else:
                    st.error("PINs must be exactly 4 digits and match!")
        else:
            entered_pin = st.text_input(f"Enter 4-Digit Security PIN for **{sel_player}**:", type="password", key="login_pin_input")
            if entered_pin == p_pin:
                authenticated = True
                st.success(f"🔓 Authenticated as **{sel_player}**!")
            elif entered_pin != "":
                st.error("Incorrect security PIN!")

        if authenticated:
            st.markdown("---")
            baker_opts = ["-- Select Baker --"] + active_bakers
            
            with st.form(f"ballot_form_w{sub_week}_{sel_player}"):
                weekly_picks = {}
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=False)
                
                if sub_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_opts)
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts)
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts)
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key="p_e1")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key="p_e2")
                            weekly_picks["eliminated"] = [e1, e2]
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, key="p_elim")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_opts, key="p_trouble")

                st.markdown("#### **Predict Technical Challenge Placements:**")
                tech_inputs = []
                for i in range(len(active_bakers)):
                    pos_num = i + 1
                    ord_s = "1st" if pos_num == 1 else ("2nd" if pos_num == 2 else ("3rd" if pos_num == 3 else f"{pos_num}th"))
                    t_val = st.selectbox(f"Technical {ord_s} Place", baker_opts, key=f"p_tech_{pos_num}")
                    tech_inputs.append(t_val)
                weekly_picks["tech_rank"] = tech_inputs

                sub_ballot = st.form_submit_button("Lock In & Submit Prediction Ballot")
                if sub_ballot:
                    st.session_state.league_members[sel_player]["weekly_picks"][sub_week] = weekly_picks
                    ai_picks = generate_ai_brian_weekly_picks(sub_week, active_bakers, is_double_elim=is_double_elim)
                    st.session_state.league_members["AI Brian"]["weekly_picks"][sub_week] = ai_picks
                    save_league_data()
                    st.success(f"Predictions successfully saved for {sel_player} (Week {sub_week})!")

# --- TAB 3: SHOW RESULTS ---
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # 1. CHAOS CATEGORIES RUNNING TOTALS
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = sum([w.get("handshake_count", len(w.get("handshake_bakers", []))) for w in st.session_state.weekly_results.values()])
    tot_cry = sum([w.get("crying_count", 0) for w in st.session_state.weekly_results.values()])
    tot_inn = sum([w.get("innuendo_count", 0) for w in st.session_state.weekly_results.values()])
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1: st.metric("🤝 Hollywood Handshakes", f"{tot_hs} total")
    with col_c2: st.metric("😢 Crying Incidents", f"{tot_cry} total")
    with col_c3: st.metric("💬 Sexual Innuendos", f"{tot_inn} total")

    st.markdown("---")
    # 2. WEEKLY BROADCAST RESULTS BREAKDOWN
    st.subheader("📅 Weekly Broadcast Results Breakdown")
    
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        for w_num in sorted(list(st.session_state.weekly_results.keys())):
            w_act = st.session_state.weekly_results[w_num]
            with st.expander(f"📺 Week {w_num} Official Broadcast Results", expanded=(w_num == max(st.session_state.weekly_results.keys()))):
                sb = w_act.get("star_baker", w_act.get("show_champion", "N/A"))
                st.markdown(f"🌟 **Star Baker / Champion:** `{sb}`")
                
                in_lines = ", ".join(w_act.get("in_line_sb", [])) if w_act.get("in_line_sb") else "None"
                st.markdown(f"🎖️ **In Line for Star Baker:** `{in_lines}`")
                
                el = w_act.get("eliminated", "None")
                if isinstance(el, list): el = ", ".join(el)
                st.markdown(f"🚪 **Eliminated Baker(s):** `{el}`")
                
                in_trb = ", ".join(w_act.get("in_trouble", [])) if w_act.get("in_trouble") else "None"
                st.markdown(f"⚠️ **In Trouble of Elimination:** `{in_trb}`")
                
                st.markdown("---")
                st.markdown("**📊 Technical Challenge Rankings:**")
                t_ranks = w_act.get("tech_rank", [])
                if t_ranks:
                    t_items = []
                    for idx, b in enumerate(t_ranks):
                        p_num = idx + 1
                        if p_num == 1: t_items.append(f"🥇 **1st Place:** {b}")
                        elif p_num == 2: t_items.append(f"🥈 **2nd Place:** {b}")
                        elif p_num == 3: t_items.append(f"🥉 **3rd Place:** {b}")
                        else: t_items.append(f"**{p_num}th Place:** {b}")
                    st.markdown(" | ".join(t_items))
                else:
                    st.markdown("N/A")
                    
                st.markdown("---")
                hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
                cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
                inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"
                
                st.markdown(f"🤝 **Handshakes ({w_act.get('handshake_count', 0)}):** {hs_bakers} | *Timestamps:* `{hs_stamps}`")
                st.markdown(f"😢 **Crying ({w_act.get('crying_count', 0)}):** *Timestamps:* `{cry_stamps}`")
                st.markdown(f"💬 **Innuendos ({w_act.get('innuendo_count', 0)}):** *Timestamps:* `{inn_stamps}`")

    # 3. DISPUTES SECTION (DIRECTLY UNDER WEEKLY RESULTS)
    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene, submit a dispute below with video timestamp evidence:")
    
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 1"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Video Evidence")
            disp_correction = st.text_input("Requested Correction")
            
            sub_disp = st.form_submit_button("Submit Dispute for Democratic Review")
            if sub_disp:
                st.session_state.disputes.append({
                    "Player": disp_player,
                    "Week": disp_week,
                    "Category": disp_cat,
                    "Evidence": disp_evidence,
                    "Correction": disp_correction,
                    "Status": "Pending GroupMe Vote 🗳️"
                })
                save_league_data()
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), hide_index=True, use_container_width=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if st.session_state.get("data_erased_confirmation"):
        st.success("✅ **All competition data, predictions, broadcast actuals, disputes, and player PINs have been permanently erased!**")
        st.session_state["data_erased_confirmation"] = False

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
        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.markdown("---")
        with st.expander("🔑 Reset Player Security PINs", expanded=False):
            p_to_reset = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + ROSTER_HUMANS)
            if p_to_reset != "-- Select Player --":
                if st.button(f"Reset Security PIN for {p_to_reset}"):
                    st.session_state.player_pins[p_to_reset] = None
                    save_league_data()
                    st.success(f"Security PIN reset for {p_to_reset}!")

        st.markdown("---")
        st.write("Record official broadcast results to score prediction ballots and update the standings:")
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            list(range(1, 11)),
            index=0,
            key="admin_week_choice_sel"
        )
        
        saved_w = st.session_state.weekly_results.get(admin_selected_week) or st.session_state.weekly_results.get(str(admin_selected_week)) or {}
        is_published = bool(saved_w)
        
        if is_published:
            st.info(f"🟢 **Week {admin_selected_week} Results Recorded & Saved in System**. Form pre-populates with current recorded entries below.")
            enable_editing = st.checkbox("🔓 Enable Editing for Published Week", value=False, key=f"unlock_edit_w{admin_selected_week}")
        else:
            st.warning(f"🟡 **Week {admin_selected_week} Results Pending Input**. Fill out the broadcast results below and click Publish.")
            enable_editing = True

        active_bakers = get_active_bakers(admin_selected_week)
        baker_opts = ["-- Select Baker --"] + active_bakers

        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input Official Broadcast Results for Week {admin_selected_week}")
            actuals = {}

            cur_sb = saved_w.get("star_baker")
            cur_sb_idx = baker_opts.index(cur_sb) if cur_sb in baker_opts else 0

            cur_champ = saved_w.get("show_champion")
            cur_champ_idx = baker_opts.index(cur_champ) if cur_champ in baker_opts else 0

            cur_inline = [b for b in saved_w.get("in_line_sb", []) if b in active_bakers]
            cur_trouble = [b for b in saved_w.get("in_trouble", []) if b in active_bakers]
            cur_elim = saved_w.get("eliminated")

            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts, index=cur_champ_idx, disabled=not enable_editing)
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=cur_sb_idx, disabled=not enable_editing)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, default=cur_inline, disabled=not enable_editing)
                with col2:
                    default_elim_type_idx = 0
                    if cur_elim == "None": default_elim_type_idx = 1
                    elif isinstance(cur_elim, list): default_elim_type_idx = 2
                    
                    elim_type = st.radio(
                        "Elimination Status",
                        ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"],
                        index=default_elim_type_idx,
                        horizontal=True,
                        key=f"admin_elim_type_w{admin_selected_week}",
                        disabled=not enable_editing
                    )
                    
                    if elim_type == "Single Elimination":
                        cur_e_single = cur_elim if isinstance(cur_elim, str) and cur_elim in baker_opts else "-- Select Baker --"
                        e_idx = baker_opts.index(cur_e_single) if cur_e_single in baker_opts else 0
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=e_idx, key=f"admin_elim_single_w{admin_selected_week}", disabled=not enable_editing)
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                    else:
                        e1_saved = cur_elim[0] if isinstance(cur_elim, list) and len(cur_elim) > 0 and cur_elim[0] in baker_opts else "-- Select Baker --"
                        e2_saved = cur_elim[1] if isinstance(cur_elim, list) and len(cur_elim) > 1 and cur_elim[1] in baker_opts else "-- Select Baker --"
                        e1_idx = baker_opts.index(e1_saved) if e1_saved in baker_opts else 0
                        e2_idx = baker_opts.index(e2_saved) if e2_saved in baker_opts else 0
                        
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts, index=e1_idx, key=f"admin_elim_1_w{admin_selected_week}", disabled=not enable_editing)
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts, index=e2_idx, key=f"admin_elim_2_w{admin_selected_week}", disabled=not enable_editing)
                        actuals["eliminated"] = [e1, e2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=cur_trouble, disabled=not enable_editing)

            st.markdown("---")
            st.markdown(f"### 📊 Actual Technical Challenge Rankings (1st through {len(active_bakers)}th Place)")
            st.caption(f"Select actual technical placements for all {len(active_bakers)} active bakers in Week {admin_selected_week}:")
            
            num_bakers = len(active_bakers)
            cols_per_row = 3
            actual_tech_ranks = []
            saved_tech_list = saved_w.get("tech_rank", [])
            
            for i in range(num_bakers):
                rank_num = i + 1
                ord_str = "1st" if rank_num == 1 else ("2nd" if rank_num == 2 else ("3rd" if rank_num == 3 else f"{rank_num}th"))
                saved_t_baker = saved_tech_list[i] if (isinstance(saved_tech_list, list) and i < len(saved_tech_list) and saved_tech_list[i] in baker_opts) else "-- Select Baker --"
                t_idx = baker_opts.index(saved_t_baker) if saved_t_baker in baker_opts else 0
                
                if i % cols_per_row == 0:
                    t_cols = st.columns(min(cols_per_row, num_bakers - i))
                col = t_cols[i % cols_per_row]
                with col:
                    sel_baker = st.selectbox(
                        f"Actual Technical {ord_str} Place",
                        baker_opts,
                        index=t_idx,
                        key=f"admin_tech_rank_w{admin_selected_week}_r{rank_num}",
                        disabled=not enable_editing
                    )
                    actual_tech_ranks.append(sel_baker)

            actuals["tech_rank"] = actual_tech_ranks

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            def_hs_bakers = [b for b in saved_w.get("handshake_bakers", []) if b in active_bakers]
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshake(s) This Week", active_bakers, default=def_hs_bakers, key=f"admin_hs_bakers_w{admin_selected_week}", disabled=not enable_editing)
            act_handshake_cnt = len(act_handshake_bakers)
            st.info(f"🤝 **Calculated Handshake Counter for Week {admin_selected_week}:** `{act_handshake_cnt} Handshake(s)`")
            def_hs_stamps = saved_w.get("handshake_timestamps", "")
            act_handshake_stamps = st.text_input("Handshake Circumstances & Video Timestamps", value=def_hs_stamps, placeholder="e.g., Tom @ 14:22 Signature, Clara @ 42:10 Showstopper", key=f"admin_hs_stamps_w{admin_selected_week}", disabled=not enable_editing)

            st.markdown("### 😢 Crying Incidents")
            col_c1, col_c2 = st.columns(2)
            def_cry_cnt = int(saved_w.get("crying_count", 0))
            def_cry_stamps = saved_w.get("crying_timestamps", "")
            with col_c1:
                act_crying_cnt = st.number_input("Number of Crying Occurrences", min_value=0, value=def_cry_cnt, key=f"admin_cry_cnt_w{admin_selected_week}", disabled=not enable_editing)
            with col_c2:
                act_crying_stamps = st.text_input("Crying Circumstances & Video Timestamps", value=def_cry_stamps, placeholder="e.g., Mo after the technical @ 34:12", key=f"admin_cry_stamps_w{admin_selected_week}", disabled=not enable_editing)

            st.markdown("### 💬 Sexual Innuendos")
            col_i1, col_i2 = st.columns(2)
            def_inn_cnt = int(saved_w.get("innuendo_count", 0))
            def_inn_stamps = saved_w.get("innuendo_timestamps", "")
            with col_i1:
                act_innuendo_cnt = st.number_input("Number of Innuendo Occurrences", min_value=0, value=def_inn_cnt, key=f"admin_inn_cnt_w{admin_selected_week}", disabled=not enable_editing)
            with col_i2:
                act_innuendo_stamps = st.text_input("Innuendo Circumstances & Video Timestamps", value=def_inn_stamps, placeholder="e.g., Paul soggy bottom comment @ 18:45", key=f"admin_inn_stamps_w{admin_selected_week}", disabled=not enable_editing)

            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_count"] = act_handshake_cnt
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            actuals["innuendo_timestamps"] = act_innuendo_stamps

            submit_admin = st.form_submit_button("Publish Official Week Results & Recalculate Standings", disabled=not enable_editing)
            if submit_admin:
                st.session_state.weekly_results[admin_selected_week] = actuals
                save_league_data()

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

                for m_name, m_data in st.session_state.league_members.items():
                    m_data["total_score"] = sum(m_data["weekly_breakdown"].values())

                save_league_data()
                st.success(f"Official results published for Week {admin_selected_week}! Leaderboard updated.")
                st.rerun()

        # --- DISPUTE RESOLUTION CONSOLE FOR ADMIN ---
        st.markdown("---")
        st.subheader("⚖️ Dispute Resolution & Management Console")
        st.write("Review result contestations submitted by league members and update their resolution status after a GroupMe democratic vote:")
        
        if st.session_state.disputes:
            for idx, disp in enumerate(st.session_state.disputes):
                with st.expander(f"🚩 Dispute #{idx+1}: {disp.get('Player')} — {disp.get('Week')} ({disp.get('Category')})", expanded=False):
                    st.write(f"**Evidence:** {disp.get('Evidence')}")
                    st.write(f"**Requested Correction:** {disp.get('Correction')}")
                    
                    cur_status = disp.get("Status", "Pending GroupMe Vote 🗳️")
                    status_opts = ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"]
                    s_idx = status_opts.index(cur_status) if cur_status in status_opts else 0
                    
                    new_status = st.selectbox(f"Resolution Status for Dispute #{idx+1}", status_opts, index=s_idx, key=f"admin_disp_status_{idx}")
                    if st.button(f"Save Resolution Status for Dispute #{idx+1}", key=f"btn_disp_status_{idx}"):
                        st.session_state.disputes[idx]["Status"] = new_status
                        save_league_data()
                        st.success(f"Status updated to '{new_status}'!")
                        st.rerun()
        else:
            st.info("No active result disputes logged.")

        # --- ERASE ALL COMPETITION DATA ---
        st.markdown("---")
        with st.expander("🗑️ Reset All Competition Data", expanded=False):
            st.warning("⚠️ **Danger Zone:** Clearing competition data will permanently wipe all recorded weekly broadcast results, season results, player prediction ballots, dispute logs, and player PINs!")
            confirm_reset = st.checkbox("I understand that this will erase all competition data across all weeks.", key="confirm_reset_data_check")
            if st.button("🗑️ Erase All Competition Data", type="primary", disabled=not confirm_reset):
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                st.session_state.player_pins = {}
                
                for member_name in st.session_state.league_members:
                    st.session_state.league_members[member_name]["weekly_picks"] = {}
                    st.session_state.league_members[member_name]["season_picks"] = {}
                    st.session_state.league_members[member_name]["total_score"] = 0
                    st.session_state.league_members[member_name]["season_score"] = 0
                    st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                
                if os.path.exists(DATA_FILE):
                    try: os.remove(DATA_FILE)
                    except Exception: pass
                    
                st.session_state["data_erased_confirmation"] = True
                st.rerun()
