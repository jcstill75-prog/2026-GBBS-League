import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import json
import os
import base64

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for high contrast in both dark and light modes
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
    @media (prefers-color-scheme: dark) {
        h1, h2, h3 { color: #FFCC80 !important; }
    }
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3,
    .stApp[data-theme="dark"] h1, .stApp[data-theme="dark"] h2, .stApp[data-theme="dark"] h3 {
        color: #FFCC80 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- DATA PERSISTENCE ENGINE WITH KEY NORMALIZATION ---
DATA_FILE = "league_data.json"

def normalize_dict_keys(d):
    """Normalize dictionary keys to integers where possible to prevent duplicate str/int keys."""
    if not isinstance(d, dict):
        return d
    normalized = {}
    for k, v in d.items():
        try:
            norm_k = int(k)
        except (ValueError, TypeError):
            norm_k = k
        
        if isinstance(v, dict):
            normalized[norm_k] = normalize_dict_keys(v)
        else:
            normalized[norm_k] = v
    return normalized

def save_league_data():
    data = {
        "league_members": st.session_state.get("league_members", {}),
        "weekly_results": st.session_state.get("weekly_results", {}),
        "season_results": st.session_state.get("season_results", {}),
        "disputes": st.session_state.get("disputes", []),
        "player_pins": st.session_state.get("player_pins", {})
    }
    try:
        clean_members = {}
        for m, mdata in data["league_members"].items():
            clean_picks = {}
            for wk, wval in mdata.get("weekly_picks", {}).items():
                clean_picks[str(wk)] = wval
            clean_members[m] = {
                "weekly_picks": clean_picks,
                "season_picks": mdata.get("season_picks", {}),
                "total_score": mdata.get("total_score", 0),
                "weekly_breakdown": {str(bk): bv for bk, bv in mdata.get("weekly_breakdown", {}).items()}
            }
        
        clean_weekly_results = {}
        for rk, rval in data["weekly_results"].items():
            clean_weekly_results[str(rk)] = rval
            
        data_to_save = {
            "league_members": clean_members,
            "weekly_results": clean_weekly_results,
            "season_results": data["season_results"],
            "disputes": data["disputes"],
            "player_pins": data["player_pins"]
        }
        
        with open(DATA_FILE, "w") as f:
            json.dump(data_to_save, f, indent=4)
    except Exception as e:
        pass

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return normalize_dict_keys(data)
        except Exception:
            return None
    return None

saved_data = load_league_data()

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", 
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ALL_HUMANS_AND_AI = sorted(ROSTER_HUMANS) + ["AI Brian"]

ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Molly",
    "Moyin", "Nikki", "Sam", "Shannon", "Tom", "Yannis"
]

BAKER_INFO = {b: {"url": "https://www.thegreatbritishbakeoff.co.uk"} for b in ALL_BAKERS}

def load_baker_image(baker_name):
    filename = f"assets/{baker_name.lower().replace(' ', '')}.jpg"
    if os.path.exists(filename):
        try:
            return Image.open(filename)
        except Exception:
            return None
    return None

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
    st.session_state.weekly_results = saved_data.get("weekly_results", {}) if saved_data else {}
else:
    st.session_state.weekly_results = normalize_dict_keys(st.session_state.weekly_results)

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

# Ensure integer key normalization across weekly results
norm_weekly_results = {}
for wk, wv in st.session_state.weekly_results.items():
    norm_weekly_results[int(wk)] = wv
st.session_state.weekly_results = norm_weekly_results

# Automatic active week calculation
all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
active_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_week > 10: active_week = 10
st.session_state.current_week = active_week

# --- 2. OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") == actuals.get("star_baker") and predictions.get("star_baker") is not None:
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
            elif pred_elim == act_elim and pred_elim is not None:
                score += 5
                
        pred_in_line = predictions.get("in_line_sb")
        act_in_line = actuals.get("in_line_sb", [])
        if pred_in_line and act_in_line and pred_in_line in act_in_line and pred_in_line != actuals.get("star_baker"):
            score += 2
            
        pred_trouble = predictions.get("in_trouble")
        act_trouble = actuals.get("in_trouble", [])
        if pred_trouble and act_trouble and pred_trouble in act_trouble:
            if isinstance(act_elim, list) and pred_trouble not in act_elim:
                score += 2
            elif isinstance(act_elim, str) and pred_trouble != act_elim:
                score += 2

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
                        if idx in [0, 4]: score += 3
                        else: score += 2
                        
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 3]: score += 3
                        else: score += 2
                    
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx == 0: score += 3
                        else: score += 2
    else:
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        pred_bot3 = predictions.get("tech_bottom_3", [])
        act_bot3 = actuals.get("tech_bottom_3", [])
        
        if len(pred_top3) == 3 and len(act_top3) == 3 and pred_top3 == act_top3:
            score += 10
        else:
            for idx, b in enumerate(pred_top3):
                if idx < len(act_top3):
                    if b == act_top3[idx]:
                        if idx == 0: score += 3
                        else: score += 2
                    elif b in act_top3:
                        score += 1
                        
        if len(pred_bot3) == 3 and len(act_bot3) == 3 and pred_bot3 == act_bot3:
            score += 10
        else:
            for idx, b in enumerate(pred_bot3):
                if idx < len(act_bot3):
                    if b == act_bot3[idx]:
                        if idx == 2: score += 3
                        else: score += 2
                    elif b in act_bot3:
                        score += 1

    return score

def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return 0
        
    act_winner = actuals.get("winner")
    act_finalists = actuals.get("finalists", [])
    act_semis = actuals.get("semifinalists", [])
    
    pred_winner = predictions.get("winner")
    if pred_winner and act_winner:
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
            
    pred_semis = predictions.get("semifinalists", [])
    for ps in pred_semis:
        if ps in act_semis:
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

# AI Brian Helper
def generate_ai_brian_season_picks():
    shuffled = list(ALL_BAKERS)
    random.shuffle(shuffled)
    winner = shuffled[0]
    semis = shuffled[1:4]
    return {
        "winner": winner,
        "semifinalists": semis,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    shuffled = list(active_bakers)
    random.shuffle(shuffled)
    if week == 10:
        return {"show_champion": shuffled[0], "tech_rank": shuffled[:3]}
    elif week == 9:
        sb = shuffled[0]
        el = shuffled[1:3] if is_double_elim else shuffled[1]
        return {"star_baker": sb, "eliminated": el, "tech_rank": shuffled[:4]}
    elif week == 8:
        sb = shuffled[0]
        el = shuffled[1:3] if is_double_elim else shuffled[1]
        inline = shuffled[3] if len(shuffled) > 3 else shuffled[0]
        trouble = shuffled[4] if len(shuffled) > 4 else shuffled[0]
        return {"star_baker": sb, "eliminated": el, "in_line_sb": inline, "in_trouble": trouble, "tech_rank": shuffled[:5]}
    else:
        sb = shuffled[0]
        inline = shuffled[1] if len(shuffled) > 1 else shuffled[0]
        el = shuffled[2:4] if is_double_elim else (shuffled[2] if len(shuffled) > 2 else shuffled[0])
        trouble = shuffled[4] if len(shuffled) > 4 else shuffled[0]
        t_top = shuffled[:3]
        t_bot = shuffled[-3:]
        return {"star_baker": sb, "in_line_sb": inline, "eliminated": el, "in_trouble": trouble, "tech_top_3": t_top, "tech_bottom_3": t_bot}

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 3. HEADER & TITLE ---
col_head1, col_head2 = st.columns([1, 5])
with col_head1:
    st.markdown("<h1 style='font-size: 60px; margin: 0;'>🧁</h1>", unsafe_allow_html=True)
with col_head2:
    st.title("Great British Baking Show Fantasy League 2026")

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("📌 Competition Status")
    if active_week == 1:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nBrowse contestant bios and prepare for post-Week 1 predictions!")
    else:
        st.success(f"🟢 **Active Status: Week {active_week} Open**\n\nWeekly predictions unlock through Week {active_week}.")

    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of what points are at stake!")
    st.warning("⏰ **Voting window ends Tuesdays right before the UK broadcast.**")
    
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(if runner-up)*
        * **Other 3 Semifinalists:** 10 pts each *(30 max)*
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
        * **Top 3 Technical:** Exact 1st (3 pts), 2nd/3rd (2 pts) | Perfect Sweep = 10 pts
        * **Bottom 3 Technical:** Exact Last (3 pts), 9th/10th (2 pts) | Perfect Sweep = 10 pts
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)

# --- 5. MAIN NAVIGATION TABS (4 TABS) ---
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
            "League Member": name,
            "Total Points": tot_pts
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="Total Points", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        ranks = []
        for r in range(1, len(df_lb) + 1):
            if r == 1: ranks.append("🥇 #1")
            elif r == 2: ranks.append("🥈 #2")
            elif r == 3: ranks.append("🥉 #3")
            else: ranks.append(f"#{r}")
            
        df_lb_show = pd.DataFrame({
            "Rank": ranks,
            "League Member": df_lb["League Member"],
            "Total Points": [f"{pts} pts" for pts in df_lb["Total Points"]]
        })
        
        st.dataframe(df_lb_show, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    st.write("Select a player profile below to view their predictions and projections.")
    
    selected_card_player = st.selectbox("Select Player Scorecard to View:", ALL_HUMANS_AND_AI, key="lb_player_card_sel")
    
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Scorecard (Total Points: {p_pts} pts)**")
        
        show_season = False
        if selected_card_player == "AI Brian":
            show_season = True
        else:
            p_pin = st.session_state.player_pins.get(selected_card_player)
            if not p_pin:
                st.info(f"🔒 {selected_card_player} has not set a PIN yet. Season predictions are hidden.")
            else:
                card_pin_input = st.text_input(f"Enter {selected_card_player}'s 4-Digit PIN to unlock Season Projections:", type="password", key=f"card_pin_{selected_card_player}")
                if card_pin_input == p_pin:
                    show_season = True
                    st.success("🔓 PIN Verified! Unlocking season projections below.")
                elif card_pin_input != "":
                    st.error("❌ Incorrect PIN")
                    
        if show_season:
            st.markdown(f"#### **{selected_card_player}'s Season Projections:**")
            win_pick = p_season.get("winner", "Not submitted yet")
            semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
            hs_pick = p_season.get("handshakes", "N/A")
            cry_pick = p_season.get("crying", "N/A")
            inn_pick = p_season.get("innuendos", "N/A")
            
            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
            st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        st.markdown("#### **Weekly Predictions Log (Public):**")
        if p_weekly:
            w_rows = []
            for w_num in sorted([int(k) for k in p_weekly.keys()]):
                w_picks = p_weekly.get(w_num, p_weekly.get(str(w_num), {}))
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                t_rank = w_picks.get("tech_rank", [])
                if t_rank:
                    t_str = ", ".join(t_rank)
                else:
                    t_top = ", ".join(w_picks.get("tech_top_3", [])) if w_picks.get("tech_top_3") else "N/A"
                    t_bot = ", ".join(w_picks.get("tech_bottom_3", [])) if w_picks.get("tech_bottom_3") else "N/A"
                    t_str = f"Top 3: [{t_top}] | Bottom 3: [{t_bot}]"
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Pick": t_str
                })
            st.dataframe(pd.DataFrame(w_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No weekly predictions logged yet.")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
        st.write("Browse the official Series 17 contestants:")
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
    
    current_eliminated = eliminated_bakers_by_week.get(active_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    dropdown_options = ["--Select Baker--"] + active_bakers
    
    user_submitting_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="submit_player_sel")
    
    user_pin_in = st.text_input("Enter 4-Digit Security PIN:", type="password", key=f"pin_in_{user_submitting_player}")
    stored_pin = st.session_state.player_pins.get(user_submitting_player)
    
    if not stored_pin:
        st.info(f"🔒 First-time setup for **{user_submitting_player}**: Please set a 4-digit PIN below.")
        new_pin_1 = st.text_input("Create 4-Digit PIN:", type="password", key=f"np1_{user_submitting_player}")
        new_pin_2 = st.text_input("Confirm 4-Digit PIN:", type="password", key=f"np2_{user_submitting_player}")
        if st.button("Set PIN & Unlock Ballot"):
            if len(new_pin_1) == 4 and new_pin_1.isdigit() and new_pin_1 == new_pin_2:
                st.session_state.player_pins[user_submitting_player] = new_pin_1
                save_league_data()
                st.success("4-digit PIN saved successfully!")
                st.rerun()
            else:
                st.error("PINs must be exactly 4 digits and match!")
    else:
        if user_pin_in == stored_pin:
            st.success(f"🔓 Profile Authenticated as **{user_submitting_player}**")
            
            if active_week == 1 and not st.session_state.weekly_results.get(1):
                st.info("🔒 **Week 1 Scouting Phase Active!** Weekly prediction ballots unlock in Week 2 after Episode 1 results are published.")
            else:
                if active_week == 2:
                    with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total)", expanded=True):
                        user_winner = st.selectbox("Predict Season Winner [40 pts]", dropdown_options, key="user_win_pick")
                        user_semi1 = st.selectbox("Predict Semifinalist #1 [10 pts]", dropdown_options, key="user_s1")
                        user_semi2 = st.selectbox("Predict Semifinalist #2 [10 pts]", dropdown_options, key="user_s2")
                        user_semi3 = st.selectbox("Predict Semifinalist #3 [10 pts]", dropdown_options, key="user_s3")
                        user_handshakes = st.number_input("Predict Seasonal Handshakes [20 pts]", min_value=0, value=5)
                        user_crying = st.number_input("Predict Seasonal Crying [20 pts]", min_value=0, value=10)
                        user_innuendos = st.number_input("Predict Seasonal Innuendos [20 pts]", min_value=0, value=40)

                is_double_elim = False
                if active_week < 10:
                    is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=False, key=f"is_dbl_chk_w{active_week}")

                st.markdown(f"### 📅 Weekly Ballot: Week {active_week}")
                with st.form("weekly_predictions_form"):
                    weekly_picks = {}
                    if active_week == 10:
                        weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", dropdown_options, key="p_champ")
                        st.markdown("**Predict Technical Challenge Rankings:**")
                        t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w10")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w10")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w10")
                        weekly_picks["tech_rank"] = [t1, t2, t3]
                    elif active_week == 9:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options, key="p_sb_w9")
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_w9")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_w9")
                            weekly_picks["eliminated"] = [e1, e2]
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options, key="e1_w9_s")
                        st.markdown("**Predict Technical Challenge Rankings:**")
                        t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w9")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w9")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w9")
                        t4 = st.selectbox("Technical 4th Place [3 pts]", dropdown_options, key="t4_w9")
                        weekly_picks["tech_rank"] = [t1, t2, t3, t4]
                    elif active_week == 8:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options, key="p_sb_w8")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", dropdown_options, key="p_inline_w8")
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_w8")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_w8")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="tr_w8")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options, key="e1_w8_s")
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="tr_w8_s")
                        st.markdown("**Predict Technical Challenge Rankings:**")
                        t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w8")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w8")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w8")
                        t4 = st.selectbox("Technical 4th Place [2 pts]", dropdown_options, key="t4_w8")
                        t5 = st.selectbox("Technical 5th Place [3 pts]", dropdown_options, key="t5_w8")
                        weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    else:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options, key="p_sb_std")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", dropdown_options, key="p_inline_std")
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_std")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_std")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="tr_std")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options, key="e1_std_s")
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="tr_std_s")
                        st.markdown("**Predict Technical Challenge Positions:**")
                        tt1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="tt1_std")
                        tt2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="tt2_std")
                        tt3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="tt3_std")
                        tb1 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", dropdown_options, key="tb1_std")
                        tb2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", dropdown_options, key="tb2_std")
                        tb3 = st.selectbox("Technical Last Place [3 pts]", dropdown_options, key="tb3_std")
                        weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                        weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]

                    sub_ballot = st.form_submit_button("Submit Prediction Ballot")
                    if sub_ballot:
                        errors = []
                        if active_week == 2:
                            s_choices = [user_winner, user_semi1, user_semi2, user_semi3]
                            if "--Select Baker--" in s_choices:
                                errors.append("⚠️ Please select a valid baker for all Season-Long Prediction fields.")
                            elif len(set(s_choices)) < len(s_choices):
                                errors.append("❌ Duplicate Selection Error: Season Winner and Semifinalists must all be distinct bakers.")

                        main_picks = []
                        for k in ["star_baker", "in_line_sb", "show_champion", "in_trouble"]:
                            v = weekly_picks.get(k)
                            if v and v != "--Select Baker--": main_picks.append(v)
                        el_v = weekly_picks.get("eliminated")
                        if isinstance(el_v, list):
                            for x in el_v:
                                if x and x != "--Select Baker--": main_picks.append(x)
                        elif isinstance(el_v, str) and el_v != "--Select Baker--":
                            main_picks.append(el_v)

                        all_req_main = []
                        for k in ["star_baker", "in_line_sb", "show_champion", "in_trouble"]:
                            if k in weekly_picks: all_req_main.append(weekly_picks[k])
                        if isinstance(el_v, list): all_req_main.extend(el_v)
                        elif isinstance(el_v, str): all_req_main.append(el_v)

                        if "--Select Baker--" in all_req_main:
                            errors.append("⚠️ Missing Selection Error: Please select a valid baker for all prediction fields.")
                        elif len(set(main_picks)) < len(main_picks):
                            errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated.")

                        tech_picks = []
                        if "tech_rank" in weekly_picks:
                            tech_picks = weekly_picks["tech_rank"]
                        else:
                            tech_picks = weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])

                        if "--Select Baker--" in tech_picks:
                            errors.append("⚠️ Missing Selection Error: Please select a valid baker for all Technical Challenge position fields.")
                        elif len(set(tech_picks)) < len(tech_picks):
                            errors.append("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions.")

                        if errors:
                            for err in errors: st.error(err)
                        else:
                            if active_week == 2:
                                st.session_state.league_members[user_submitting_player]["season_picks"] = {
                                    "winner": user_winner,
                                    "semifinalists": [user_semi1, user_semi2, user_semi3],
                                    "handshakes": user_handshakes,
                                    "crying": user_crying,
                                    "innuendos": user_innuendos
                                }
                            st.session_state.league_members[user_submitting_player]["weekly_picks"][active_week] = weekly_picks

                            ai_picks = generate_ai_brian_weekly_picks(active_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][active_week] = ai_picks

                            save_league_data()
                            st.success(f"🎉 Predictions successfully saved for {user_submitting_player} (Week {active_week})!")
                            st.rerun()
        elif user_pin_in != "":
            st.error("❌ Incorrect 4-Digit PIN")

# --- TAB 3: SHOW RESULTS ---
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # Clean deduplicated weekly results keys
    dedup_results = {}
    for wk, wv in st.session_state.weekly_results.items():
        dedup_results[int(wk)] = wv

    # 1. CHAOS CATEGORIES RUNNING TOTALS
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = sum([w.get("handshake_count", len(w.get("handshake_bakers", []))) for w in dedup_results.values()])
    tot_cry = sum([w.get("crying_count", 0) for w in dedup_results.values()])
    tot_inn = sum([w.get("innuendo_count", 0) for w in dedup_results.values()])

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Hollywood Handshakes", f"{tot_hs} total")
    with col_c2:
        st.metric("😢 Crying Incidents", f"{tot_cry} total")
    with col_c3:
        st.metric("💬 Sexual Innuendos", f"{tot_inn} total")

    st.markdown("---")

    # 2. WEEKLY BROADCAST RESULTS BREAKDOWN
    st.subheader("📅 Weekly Broadcast Results Breakdown")
    if not dedup_results:
        st.info("No episode broadcast results recorded yet. Results will populate here as published by the Administrator!")
    else:
        for w_num in sorted(dedup_results.keys()):
            w_act = dedup_results[w_num]
            with st.expander(f"📺 Episode Breakdown: Week {w_num}", expanded=(w_num == max(dedup_results.keys()))):
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    sb_val = w_act.get("star_baker", w_act.get("show_champion", "None"))
                    st.write(f"🌟 **Star Baker / Champion:** {sb_val}")
                    in_line_val = ", ".join(w_act.get("in_line_sb", [])) if w_act.get("in_line_sb") else "None"
                    st.write(f"🎖️ **In Line for Star Baker:** {in_line_val}")
                with col_w2:
                    el_val = w_act.get("eliminated", "None")
                    if isinstance(el_val, list): el_val = ", ".join(el_val)
                    st.write(f"🚪 **Eliminated Baker(s):** {el_val}")
                    tr_val = ", ".join(w_act.get("in_trouble", [])) if w_act.get("in_trouble") else "None"
                    st.write(f"⚠️ **In Trouble of Elimination:** {tr_val}")

                st.markdown("---")
                st.markdown("**📊 Technical Challenge Placements:**")
                t_rank = w_act.get("tech_rank", [])
                if t_rank:
                    formatted_tech_list = []
                    for idx, b in enumerate(t_rank):
                        pos_str = f"🥇 1st Place: {b}" if idx == 0 else (f"🥈 2nd Place: {b}" if idx == 1 else (f"🥉 3rd Place: {b}" if idx == 2 else f"{idx+1}th Place: {b}"))
                        formatted_tech_list.append(pos_str)
                    st.write(" | ".join(formatted_tech_list))
                else:
                    top_3_str = ", ".join(w_act.get("tech_top_3", [])) if w_act.get("tech_top_3") else "None"
                    bot_3_str = ", ".join(w_act.get("tech_bottom_3", [])) if w_act.get("tech_bottom_3") else "None"
                    st.write(f"🥇 **Top 3:** {top_3_str}")
                    st.write(f"⚠️ **Bottom 3:** {bot_3_str}")

                st.markdown("---")
                st.markdown("**🤝 Hollywood Handshakes:**")
                hs_cnt = w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
                hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
                st.write(f"Count: `{hs_cnt}` | Recipients: `{hs_bakers}` | Context & Video Timestamps: `{hs_stamps}`")

                st.markdown("**😢 Crying Incidents:**")
                cry_cnt = w_act.get("crying_count", 0)
                cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
                st.write(f"Count: `{cry_cnt}` | Context & Video Timestamps: `{cry_stamps}`")

                st.markdown("**💬 Sexual Innuendos:**")
                inn_cnt = w_act.get("innuendo_count", 0)
                inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"
                st.write(f"Count: `{inn_cnt}` | Context & Video Timestamps: `{inn_stamps}`")

    st.markdown("---")

    # 3. BROADCAST RESULT DISPUTES & TIMESTAMP CORRECTIONS
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS, key="disp_player_sel")
            available_weeks = [f"Week {w}" for w in sorted(dedup_results.keys())] if dedup_results else ["Week 1"]
            disp_week = st.selectbox("Week to Contest", available_weeks, key="disp_week_sel")
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ], key="disp_cat_sel")
            disp_evidence = st.text_area("Video Timestamp & Video Evidence (e.g., 'At 28:14 in Episode 1, Paul clearly shakes Tom\'s hand during Showstopper judging')")
            disp_correction = st.text_input("Requested Correction (e.g., 'Add +1 Crying Incident for Week 1')")

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
                save_league_data()
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")
                st.rerun()

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), hide_index=True, use_container_width=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if st.session_state.get("data_erased_confirmation"):
        st.success("✅ All competition data, predictions, broadcast actuals, disputes, and player PINs have been permanently erased!")
        st.session_state.data_erased_confirmation = False

    if not st.session_state.admin_authenticated:
        st.warning("🔒 This panel is restricted to the League Administrator.")
        admin_pin_input = st.text_input("Enter Admin Security PIN:", type="password", key="admin_pin_field")
        if st.button("Unlock Admin Panel"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("🔓 Administrator Authenticated!")
                st.rerun()
            else:
                st.error("❌ Incorrect Admin PIN")
    else:
        st.success("🔓 Administrator Console Unlocked")
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        st.markdown("### 📅 Select Episode Results to Input / Update")
        
        default_admin_week = active_week
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=default_admin_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        current_eliminated = eliminated_bakers_by_week.get(admin_selected_week, [])
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        admin_dropdown_options = ["--Select Baker--"] + admin_active_bakers
        
        saved_w = st.session_state.weekly_results.get(admin_selected_week, {})
        is_published = admin_selected_week in st.session_state.weekly_results

        if is_published:
            st.info(f"🟢 **Week {admin_selected_week} Results Recorded & Saved in System**\n\nFields are locked to protect player scores. Check the box below to unlock editing.")
            enable_edit = st.checkbox(f"🔓 Enable Editing for Week {admin_selected_week} (Requires Verification)", key=f"unlock_edit_w{admin_selected_week}")
        else:
            enable_edit = True

        elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], index=0, horizontal=True, key=f"admin_elim_type_w{admin_selected_week}")

        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input / Update Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                s_champ = saved_w.get("show_champion", "--Select Baker--")
                idx_sc = admin_dropdown_options.index(s_champ) if s_champ in admin_dropdown_options else 0
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_dropdown_options, index=idx_sc, key="adm_sc_w10", disabled=(is_published and not enable_edit))
                
                st.markdown("**Actual Technical Challenge Rankings:**")
                saved_tr = saved_w.get("tech_rank", [])
                t1_val = saved_tr[0] if len(saved_tr) > 0 else "--Select Baker--"
                t2_val = saved_tr[1] if len(saved_tr) > 1 else "--Select Baker--"
                t3_val = saved_tr[2] if len(saved_tr) > 2 else "--Select Baker--"
                idx_t1 = admin_dropdown_options.index(t1_val) if t1_val in admin_dropdown_options else 0
                idx_t2 = admin_dropdown_options.index(t2_val) if t2_val in admin_dropdown_options else 0
                idx_t3 = admin_dropdown_options.index(t3_val) if t3_val in admin_dropdown_options else 0
                act_t1 = st.selectbox("Technical 1st Place", admin_dropdown_options, index=idx_t1, key="adm_t1_w10", disabled=(is_published and not enable_edit))
                act_t2 = st.selectbox("Technical 2nd Place", admin_dropdown_options, index=idx_t2, key="adm_t2_w10", disabled=(is_published and not enable_edit))
                act_t3 = st.selectbox("Technical 3rd Place", admin_dropdown_options, index=idx_t3, key="adm_t3_w10", disabled=(is_published and not enable_edit))
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    s_sb = saved_w.get("star_baker", "--Select Baker--")
                    idx_sb = admin_dropdown_options.index(s_sb) if s_sb in admin_dropdown_options else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_options, index=idx_sb, key=f"adm_sb_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, default=[b for b in saved_w.get("in_line_sb", []) if b in admin_active_bakers], key=f"adm_inline_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                with col2:
                    saved_el = saved_w.get("eliminated", "--Select Baker--")
                    if elim_type == "Single Elimination":
                        s_el_single = saved_el if isinstance(saved_el, str) else "--Select Baker--"
                        idx_el_s = admin_dropdown_options.index(s_el_single) if s_el_single in admin_dropdown_options else 0
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_options, index=idx_el_s, key=f"adm_elim_s_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=[b for b in saved_w.get("in_trouble", []) if b in admin_active_bakers], key=f"adm_tr_s_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=[b for b in saved_w.get("in_trouble", []) if b in admin_active_bakers], key=f"adm_tr_g_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                    else:
                        s_el1 = saved_el[0] if isinstance(saved_el, list) and len(saved_el) > 0 else "--Select Baker--"
                        s_el2 = saved_el[1] if isinstance(saved_el, list) and len(saved_el) > 1 else "--Select Baker--"
                        idx_e1 = admin_dropdown_options.index(s_el1) if s_el1 in admin_dropdown_options else 0
                        idx_e2 = admin_dropdown_options.index(s_el2) if s_el2 in admin_dropdown_options else 0
                        e1_val = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_options, index=idx_e1, key=f"adm_e1_d_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                        e2_val = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_options, index=idx_e2, key=f"adm_e2_d_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                        actuals["eliminated"] = [e1_val, e2_val]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=[b for b in saved_w.get("in_trouble", []) if b in admin_active_bakers], key=f"adm_tr_d_w{admin_selected_week}", disabled=(is_published and not enable_edit))

                st.markdown(f"**Actual Technical Challenge Placement (All {len(admin_active_bakers)} Active Bakers):**")
                saved_tech = saved_w.get("tech_rank", [])
                tech_positions = []
                for idx, _ in enumerate(admin_active_bakers):
                    pos_name = f"Technical Position #{idx+1}"
                    if idx == 0: pos_name += " (🥇 1st Place)"
                    elif idx == len(admin_active_bakers) - 1: pos_name += " (Last Place)"
                    cur_b = saved_tech[idx] if idx < len(saved_tech) else "--Select Baker--"
                    idx_b = admin_dropdown_options.index(cur_b) if cur_b in admin_dropdown_options else 0
                    t_val = st.selectbox(pos_name, admin_dropdown_options, index=idx_b, key=f"admin_pos_{idx}_w{admin_selected_week}", disabled=(is_published and not enable_edit))
                    tech_positions.append(t_val)
                    
                actuals["tech_rank"] = tech_positions
                if len(tech_positions) >= 3: actuals["tech_top_3"] = tech_positions[:3]
                if len(tech_positions) >= 6: actuals["tech_bottom_3"] = tech_positions[-3:]

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            with col_hs1:
                act_handshake_cnt = st.number_input("Number of Handshake Occurrences", min_value=0, value=saved_w.get("handshake_count", 0), key=f"adm_hs_cnt_w{admin_selected_week}", disabled=(is_published and not enable_edit))
            with col_hs2:
                act_handshake_stamps = st.text_input("Handshake Video Timestamps", value=saved_w.get("handshake_timestamps", ""), key=f"adm_hs_stamps_w{admin_selected_week}", disabled=(is_published and not enable_edit))
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", admin_active_bakers, default=[b for b in saved_w.get("handshake_bakers", []) if b in admin_active_bakers], key=f"adm_hs_bakers_w{admin_selected_week}", disabled=(is_published and not enable_edit))

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Occurrences", min_value=0, value=saved_w.get("crying_count", 0), key=f"adm_cry_cnt_w{admin_selected_week}", disabled=(is_published and not enable_edit))
            with col_cry2:
                act_crying_stamps = st.text_input("Crying Video Timestamps", value=saved_w.get("crying_timestamps", ""), key=f"adm_cry_stamps_w{admin_selected_week}", disabled=(is_published and not enable_edit))

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Innuendo Occurrences", min_value=0, value=saved_w.get("innuendo_count", 0), key=f"adm_inn_cnt_w{admin_selected_week}", disabled=(is_published and not enable_edit))
            with col_inn2:
                act_innuendo_stamps = st.text_input("Innuendo Video Timestamps", value=saved_w.get("innuendo_timestamps", ""), key=f"adm_inn_stamps_w{admin_selected_week}", disabled=(is_published and not enable_edit))

            actuals["handshake_count"] = act_handshake_cnt or 0
            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt or 0
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt or 0
            actuals["innuendo_timestamps"] = act_innuendo_stamps

            submit_admin = st.form_submit_button("Publish Broadcast Results & Recalculate Standings", disabled=(is_published and not enable_edit))
            
            if submit_admin:
                cur_w = int(admin_selected_week)
                st.session_state.weekly_results.pop(str(cur_w), None)
                st.session_state.weekly_results.pop(cur_w, None)
                st.session_state.weekly_results[cur_w] = actuals
                
                # Recalculate standings across all members
                for m_name in ALL_HUMANS_AND_AI:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    
                scored_weeks = sorted([int(wk) for wk in st.session_state.weekly_results.keys()])
                for w_num_int in scored_weeks:
                    w_act = st.session_state.weekly_results[w_num_int]
                    w_scores = {}
                    for m_name in ALL_HUMANS_AND_AI:
                        m_data = st.session_state.league_members[m_name]
                        p_picks = m_data["weekly_picks"].get(w_num_int, m_data["weekly_picks"].get(str(w_num_int), {}))
                        w_pts = calculate_weekly_score(p_picks, w_act, week=w_num_int)
                        m_data["weekly_breakdown"][w_num_int] = w_pts
                        w_scores[m_name] = w_pts
                        
                    if w_scores:
                        max_pts = max(w_scores.values())
                        if max_pts > 0:
                            for m_name, pts in w_scores.items():
                                if pts == max_pts:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w_num_int] += 5
                                    
                for m_name in ALL_HUMANS_AND_AI:
                    m_data = st.session_state.league_members[m_name]
                    m_data["total_score"] = sum(m_data["weekly_breakdown"].values())
                    if st.session_state.season_results:
                        m_data["total_score"] += calculate_season_score(m_data["season_picks"], st.session_state.season_results)
                        
                save_league_data()
                st.success(f"🎉 Official Week {admin_selected_week} results published! All league standings updated.")
                st.rerun()

        # --- DISPUTE RESOLUTION & MANAGEMENT CONSOLE ---
        st.markdown("---")
        st.markdown("### ⚖️ Dispute Resolution & Management Console")
        if not st.session_state.disputes:
            st.info("No active result disputes submitted by league members.")
        else:
            st.write("Review submitted result disputes below. Change the status after your GroupMe democratic vote:")
            for d_idx, dispute in enumerate(st.session_state.disputes):
                with st.expander(f"Dispute #{d_idx+1}: {dispute.get('Player')} - {dispute.get('Week')} ({dispute.get('Category')})", expanded=True):
                    st.write(f"**Contested Category:** {dispute.get('Category')}")
                    st.write(f"**Submitted Evidence:** {dispute.get('Evidence')}")
                    st.write(f"**Requested Correction:** {dispute.get('Correction')}")
                    
                    cur_status = dispute.get("Status", "Pending GroupMe Vote 🗳️")
                    status_opts = ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"]
                    idx_st = status_opts.index(cur_status) if cur_status in status_opts else 0
                    
                    new_st = st.selectbox("Resolution Status:", status_opts, index=idx_st, key=f"disp_st_sel_{d_idx}")
                    if st.button("Save Resolution Status", key=f"btn_save_disp_{d_idx}"):
                        st.session_state.disputes[d_idx]["Status"] = new_st
                        save_league_data()
                        st.success(f"Updated status for Dispute #{d_idx+1} to '{new_st}'!")
                        st.rerun()

        # --- PLAYER PIN RESET CONSOLE ---
        st.markdown("---")
        st.subheader("🔑 Player PIN Reset Console")
        pin_reset_player = st.selectbox("Select Player to Reset PIN:", ROSTER_HUMANS, key="pin_reset_sel")
        if st.button("Reset Player PIN"):
            if pin_reset_player in st.session_state.player_pins:
                del st.session_state.player_pins[pin_reset_player]
                save_league_data()
                st.success(f"✅ PIN reset for {pin_reset_player}. They can now set a new PIN on the prediction tab.")
            else:
                st.info(f"{pin_reset_player} does not have an active PIN set.")

        # --- ERASE ALL SAVED DATA ---
        st.markdown("---")
        st.subheader("🚨 Emergency Reset Data")
        confirm_erase = st.checkbox("I understand this will erase all player picks, PINs, and published broadcast actuals.")
        if st.button("Erase All Saved League Data", type="primary"):
            if confirm_erase:
                if os.path.exists(DATA_FILE):
                    try: os.remove(DATA_FILE)
                    except: pass
                    
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                st.session_state.player_pins = {}
                
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["weekly_picks"] = {}
                    st.session_state.league_members[m_name]["season_picks"] = {}
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    
                st.session_state.data_erased_confirmation = True
                st.rerun()
            else:
                st.error("Please check the confirmation box above first.")
