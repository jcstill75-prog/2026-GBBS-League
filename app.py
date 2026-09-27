import streamlit as st
import pandas as pd
import random
import json
import os

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

# --- 2. PERSISTENCE ENGINE ---
DATA_FILE = "league_data.json"

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
            clean_members[m] = {
                "weekly_picks": mdata.get("weekly_picks", {}),
                "season_picks": mdata.get("season_picks", {}),
                "total_score": mdata.get("total_score", 0),
                "weekly_breakdown": mdata.get("weekly_breakdown", {})
            }
        data["league_members"] = clean_members
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data
        except Exception:
            return None
    return None

saved_data = load_league_data()

# --- 3. ROSTER & BAKER CONSTANTS ---
# Official 12 Bakers competing in Series 17 (Class of 2026)
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

# 14 Human Fantasy League Players
ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", 
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ALL_HUMANS_AND_AI = sorted(ROSTER_HUMANS) + ["AI Brian"]

# --- INITIALIZE SESSION STATE ---
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

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_data.get("season_results", {}) if saved_data else {}

if "disputes" not in st.session_state:
    st.session_state.disputes = saved_data.get("disputes", []) if saved_data else []

if "player_pins" not in st.session_state:
    st.session_state.player_pins = saved_data.get("player_pins", {}) if saved_data else {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# Ensure all 15 members exist in league_members
for name in ALL_HUMANS_AND_AI:
    if name not in st.session_state.league_members:
        st.session_state.league_members[name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

# Automatic Week Determination based on published results
def get_sorted_weekly_result_weeks():
    weeks = []
    for k in st.session_state.weekly_results.keys():
        try:
            weeks.append(int(k))
        except (ValueError, TypeError):
            pass
    return sorted(list(set(weeks)))

def get_weekly_result(week):
    try:
        w_int = int(week)
    except (ValueError, TypeError):
        w_int = week
    return st.session_state.weekly_results.get(w_int) or st.session_state.weekly_results.get(str(w_int)) or {}

all_scored_weeks = get_sorted_weekly_result_weeks()
active_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_week > 10: active_week = 10
st.session_state.current_week = active_week

def get_current_eliminated_bakers(week_num):
    elim = []
    try:
        target_week = int(week_num)
    except (ValueError, TypeError):
        target_week = 10
    for w_int in get_sorted_weekly_result_weeks():
        if w_int <= target_week:
            res = get_weekly_result(w_int)
            act_el = res.get("eliminated")
            if isinstance(act_el, list):
                for b in act_el:
                    if b and b != "None" and b not in elim:
                        elim.append(b)
            elif isinstance(act_el, str) and act_el and act_el != "None":
                if act_el not in elim:
                    elim.append(act_el)
    return elim

# --- 4. OFFICIAL SCORING ENGINE ---
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

    # Technical Challenge Scoring
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
        # Standard Weeks 1-7
        p_top = predictions.get("tech_top_3", [])
        p_bot = predictions.get("tech_bottom_3", [])
        a_top = actuals.get("tech_top_3", [])
        a_bot = actuals.get("tech_bottom_3", [])
        
        # Check perfect 3-for-3 sweep
        if p_top and a_top and p_top == a_top:
            score += 10
        elif p_top and a_top:
            for idx, b in enumerate(p_top):
                if idx < len(a_top) and a_top[idx] == b:
                    if idx == 0: score += 3
                    else: score += 2
                elif b in a_top:
                    score += 1

        if p_bot and a_bot and p_bot == a_bot:
            score += 10
        elif p_bot and a_bot:
            for idx, b in enumerate(p_bot):
                if idx < len(a_bot) and a_bot[idx] == b:
                    if idx == 2: score += 3
                    else: score += 2
                elif b in a_bot:
                    score += 1

    return score

def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return 0
        
    act_winner = actuals.get("winner")
    pred_winner = predictions.get("winner")
    act_finalists = actuals.get("finalists", [])
    
    if pred_winner and act_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and act_finalists and pred_winner in act_finalists:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    act_semis = actuals.get("semifinalists", [])
    if pred_semis and act_semis:
        for b in pred_semis:
            if b in act_semis:
                score += 10

    # Chaos Category Season Totals
    p_hs = predictions.get("handshakes")
    a_hs = actuals.get("handshakes")
    if p_hs is not None and a_hs is not None:
        if p_hs == a_hs: score += 20
        elif abs(p_hs - a_hs) == 1: score += 10

    p_cry = predictions.get("crying")
    a_cry = actuals.get("crying")
    if p_cry is not None and a_cry is not None:
        if p_cry == a_cry: score += 20
        elif abs(p_cry - a_cry) <= 5: score += 10

    p_inn = predictions.get("innuendos")
    a_inn = actuals.get("innuendos")
    if p_inn is not None and a_inn is not None:
        if p_inn == a_inn: score += 20
        elif abs(p_inn - a_inn) <= 5: score += 10

    return score

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    if week == 10:
        champion = random.choice(active_bakers)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"show_champion": champion, "tech_rank": tech_rank}
    elif week == 9:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim and len(elim_pool) >= 2:
            eliminated = random.sample(elim_pool, 2)
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim and len(elim_pool) >= 2:
            eliminated = random.sample(elim_pool, 2)
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim and len(elim_pool) >= 2:
            eliminated = random.sample(elim_pool, 2)
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bot = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bot, min(3, len(rem_bot))) if rem_bot else random.sample(active_bakers, min(3, len(active_bakers)))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_top_3": tech_top_3, "tech_bottom_3": tech_bottom_3, "in_line_sb": in_line_sb, "in_trouble": in_trouble}

# --- 5. APP INTERFACE LAYOUT ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
st.markdown("### Powered by the Balanced 2026 Competition Rules Engine")

# SIDEBAR: POINTS REFERENCE GUIDE ONLY (NO SLIDERS, NO AVATARS)
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
        *   **Week 8 (Quarterfinal - 5 bakers):** Star Baker (5 pts), Eliminated (5 pts), Perfect Tech Sweep (25 pts)
        *   **Week 9 (Semifinal - 4 bakers):** Star Baker (5 pts), Eliminated (5 pts), Perfect Tech Sweep (20 pts)
        *   **Week 10 (Grand Finale - 3 bakers):** Champion (15 pts), Perfect Tech Sweep (15 pts)
        """)

# --- MAIN NAVIGATION TABS ---
tab_lead, tab_submit, tab_show_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings",
    "📝 Submit Predictions",
    "📺 Show Results",
    "👑 Admin Panel"
])

# ==========================================
# --- TAB 1: LEADERBOARD & STANDINGS ---
# ==========================================
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_data = []
    for name in ALL_HUMANS_AND_AI:
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
        df_lb.index = df_lb.index + 1
        
        df_lb_show = pd.DataFrame({
            "Rank": [f"🥇 #1" if i == 1 else f"🥈 #2" if i == 2 else f"🥉 #3" if i == 3 else f"#{i}" for i in range(1, len(df_lb) + 1)],
            "League Member": df_lb["member"],
            "Total Points": [f"{p} pts" for p in df_lb["points"]]
        })
        
        st.dataframe(df_lb_show, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    st.write("Inspect season-long projections and weekly prediction logs for any participant:")
    
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ALL_HUMANS_AND_AI, key="lb_player_card_sel")
    
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Scorecard (Total Score: {p_pts} pts)**")
        
        st.markdown("#### **🌟 Season-Long Projections:**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        st.markdown("#### **📅 Weekly Predictions Log:**")
        if p_weekly:
            w_rows = []
            for w_num in sorted([int(k) for k in p_weekly.keys()]):
                w_picks = p_weekly.get(w_num) or p_weekly.get(str(w_num), {})
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

# ==========================================
# --- TAB 2: SUBMIT PREDICTIONS ---
# ==========================================
with tab_submit:
    st.header("📝 Submit Predictions Ballot")
    
    # 1. VISUAL BAKER GALLERY (STRICTLY 12 SERIES 17 BAKERS - NO PLAYERS!)
    current_elim_gallery = get_current_eliminated_bakers(active_week)
    active_gallery_bakers = [b for b in ALL_BAKERS if b not in current_elim_gallery]
    
    with st.expander("📸 Visual Baker Gallery (Class of 2026 - Official Contestants)", expanded=True):
        st.write("Browse the official Series 17 amateur bakers competing in the tent:")
        cols = st.columns(4)
        for idx, baker in enumerate(active_gallery_bakers):
            info = BAKER_INFO.get(baker, {"url": "#"})
            with cols[idx % 4]:
                st.markdown(f"**{baker}**")
                st.markdown(f"[🔗 Official Show Profile]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    
    # 2. PLAYER PROFILE SELECTION & 4-DIGIT PIN AUTHENTICATION
    sel_player = st.selectbox("Select Your Player Profile Name:", ROSTER_HUMANS, key="pred_player_select")
    player_data = st.session_state.league_members[sel_player]
    player_pin = st.session_state.player_pins.get(sel_player)
    
    authenticated = False
    
    if player_pin is None:
        st.warning(f"🔒 First-time setup for **{sel_player}**: Create a 4-digit security PIN to protect your predictions ballot!")
        col1, col2 = st.columns(2)
        with col1:
            new_pin = st.text_input("Create 4-Digit PIN:", type="password", key="create_pin_1", max_chars=4)
        with col2:
            confirm_pin = st.text_input("Confirm 4-Digit PIN:", type="password", key="create_pin_2", max_chars=4)
            
        if st.button("Set PIN & Unlock Ballot"):
            if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                st.session_state.player_pins[sel_player] = new_pin
                save_league_data()
                st.success("4-digit PIN saved successfully!")
                st.rerun()
            else:
                st.error("PINs must be exactly 4 digits and match!")
    else:
        entered_pin = st.text_input(f"Enter 4-Digit PIN for **{sel_player}**:", type="password", key="login_pin_input", max_chars=4)
        if entered_pin == player_pin:
            authenticated = True
            st.success(f"🔓 Authenticated as **{sel_player}**!")
        elif entered_pin != "":
            st.error("Incorrect 4-digit PIN!")

    if authenticated:
        st.markdown("---")
        
        # WEEK 1 SCOUTING PHASE LOCK
        if active_week == 1:
            st.info("🔍 **Week 1 Scouting Phase Active!** Browse the baker gallery above to scout the Class of 2026. Weekly prediction ballots unlock in Week 2 after Episode 1 results are published!")
        else:
            # SEASON-LONG PREDICTIONS FORM (UNLOCKED IN WEEK 2)
            if active_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total)", expanded=True):
                    baker_options_s = ["--Select Baker--"] + ALL_BAKERS
                    s_win = st.selectbox("Predict Season Winner [40 pts]", baker_options_s, key="s_win_sel")
                    s_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", [b for b in ALL_BAKERS if b != s_win], max_selections=3, key="s_semis_sel")
                    s_hs = st.number_input("Predict Seasonal Handshakes [20 pts spot-on]", min_value=0, value=None, placeholder="Enter total handshakes", key="s_hs_num")
                    s_cry = st.number_input("Predict Seasonal Crying Incidents [20 pts spot-on]", min_value=0, value=None, placeholder="Enter total crying incidents", key="s_cry_num")
                    s_inn = st.number_input("Predict Seasonal Innuendos [20 pts spot-on]", min_value=0, value=None, placeholder="Enter total innuendos", key="s_inn_num")
                    
                    if st.button("Lock Season-Long Predictions"):
                        if s_win == "--Select Baker--" or len(s_semis) != 3 or s_hs is None or s_cry is None or s_inn is None:
                            st.error("Please fill out all season projection fields!")
                        else:
                            player_data["season_picks"] = {
                                "winner": s_win,
                                "semifinalists": s_semis,
                                "handshakes": s_hs,
                                "crying": s_cry,
                                "innuendos": s_inn
                            }
                            save_league_data()
                            st.success("Season-long projections saved successfully!")

            st.markdown(f"### 📅 Submit Episodic Predictions: Week {active_week}")
            st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
            
            current_eliminated = get_current_eliminated_bakers(active_week)
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            baker_options = ["--Select Baker--"] + active_bakers
            
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=False, key=f"dbl_elim_chk_w{active_week}")
            
            with st.form("weekly_ballot_form"):
                st.subheader(f"Week {active_week} Prediction Ballot")
                p_picks = {}
                
                if active_week == 10:
                    p_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_options, key="p_champ_s")
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w10")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w10")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w10")
                    p_picks["tech_rank"] = [t1, t2, t3]
                    
                elif active_week == 9:
                    p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="p_sb_w9")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="p_e1_w9")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="p_e2_w9")
                        p_picks["eliminated"] = [e1, e2]
                    else:
                        p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="p_e1_w9_s")
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w9")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w9")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w9")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", baker_options, key="p_t4_w9")
                    p_picks["tech_rank"] = [t1, t2, t3, t4]
                    
                elif active_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="p_sb_w8")
                        p_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="p_inline_w8")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="p_e1_w8")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="p_e2_w8")
                            p_picks["eliminated"] = [e1, e2]
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_w8")
                        else:
                            p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="p_e1_w8_s")
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_w8_s")
                            
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w8")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w8")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w8")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", baker_options, key="p_t4_w8")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", baker_options, key="p_t5_w8")
                    p_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="p_sb_std")
                        p_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="p_inline_std")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="p_e1_std")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="p_e2_std")
                            p_picks["eliminated"] = [e1, e2]
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_std")
                        else:
                            p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="p_e1_std_s")
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_std_s")
                            
                    st.markdown("---")
                    st.write("Predict Technical Challenge Placements:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_std")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_std")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_std")
                    t_bot3 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_options, key="p_tbot3_std")
                    t_bot2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_options, key="p_tbot2_std")
                    t_last = st.selectbox("Technical Last Place [3 pts]", baker_options, key="p_tlast_std")
                    p_picks["tech_rank"] = [t1, t2, t3, t_bot3, t_bot2, t_last]

                sub_ballot = st.form_submit_button("Submit Weekly Prediction Ballot")
                if sub_ballot:
                    main_selections = []
                    for k in ["star_baker", "in_line_sb", "in_trouble", "show_champion"]:
                        if k in p_picks and p_picks[k] != "--Select Baker--":
                            main_selections.append(p_picks[k])
                    if "eliminated" in p_picks:
                        el_val = p_picks["eliminated"]
                        if isinstance(el_val, list):
                            for ev in el_val:
                                if ev != "--Select Baker--": main_selections.append(ev)
                        elif el_val != "--Select Baker--":
                            main_selections.append(el_val)
                            
                    tech_selections = [t for t in p_picks.get("tech_rank", []) if t != "--Select Baker--"]
                    
                    has_placeholder = False
                    for k, v in p_picks.items():
                        if v == "--Select Baker--": has_placeholder = True
                        if isinstance(v, list):
                            for item in v:
                                if item == "--Select Baker--": has_placeholder = True
                                
                    if has_placeholder:
                        st.error("⚠️ Missing Selection Error: Please select a valid baker for all prediction fields before submitting!")
                    elif len(main_selections) != len(set(main_selections)):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    elif len(tech_selections) != len(set(tech_selections)):
                        st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                    else:
                        player_data["weekly_picks"][active_week] = p_picks
                        
                        # AI Brian Automatic Picks Submission
                        ai_picks = generate_ai_brian_weekly_picks(active_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][active_week] = ai_picks
                        
                        save_league_data()
                        st.success(f"Predictions submitted for Week {active_week}! AI Brian has also logged his picks.")

# ==========================================
# --- TAB 3: SHOW RESULTS ---
# ==========================================
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # 1. CHAOS CATEGORIES RUNNING TOTALS
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    
    for w_num in get_sorted_weekly_result_weeks():
        w_act = get_weekly_result(w_num)
        tot_hs += w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
        tot_cry += w_act.get("crying_count", 0)
        tot_inn += w_act.get("innuendo_count", 0)
        
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
    
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        for w_num in get_sorted_weekly_result_weeks():
            w_act = get_weekly_result(w_num)
            with st.expander(f"📺 Week {w_num} Official Broadcast Results", expanded=(w_num == active_week - 1 or w_num == active_week)):
                if w_num == 10:
                    st.write(f"🏆 **Show Champion:** `{w_act.get('show_champion', 'N/A')}`")
                else:
                    st.write(f"🌟 **Star Baker:** `{w_act.get('star_baker', 'N/A')}`")
                    st.write(f"📈 **In Line for Star Baker:** `{', '.join(w_act.get('in_line_sb', [])) if w_act.get('in_line_sb') else 'None'}`")
                    el_display = ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A")
                    st.write(f"🚪 **Eliminated Baker:** `{el_display}`")
                    st.write(f"⚠️ **In Trouble of Elimination:** `{', '.join(w_act.get('in_trouble', [])) if w_act.get('in_trouble') else 'None'}`")
                
                st.markdown("**📊 Technical Challenge Placement:**")
                t_ranks = w_act.get("tech_rank", [])
                if t_ranks:
                    t_str_list = []
                    for pos_idx, baker in enumerate(t_ranks):
                        if pos_idx == 0:
                            t_str_list.append(f"🥇 **1st Place:** {baker}")
                        elif pos_idx == 1:
                            t_str_list.append(f"🥈 **2nd Place:** {baker}")
                        elif pos_idx == 2:
                            t_str_list.append(f"🥉 **3rd Place:** {baker}")
                        else:
                            t_str_list.append(f"**#{pos_idx + 1}:** {baker}")
                    st.write(" | ".join(t_str_list))
                else:
                    st.write("N/A")
                    
                st.markdown("**🌀 Weekly Chaos Counts & Timestamps:**")
                st.write(f"🤝 **Handshakes:** {w_act.get('handshake_count', 0)} ({', '.join(w_act.get('handshake_bakers', [])) if w_act.get('handshake_bakers') else 'None'}) — *{w_act.get('handshake_timestamps', 'N/A')}*")
                st.write(f"😢 **Crying:** {w_act.get('crying_count', 0)} — *{w_act.get('crying_timestamps', 'N/A')}*")
                st.write(f"💬 **Innuendos:** {w_act.get('innuendo_count', 0)} — *{w_act.get('innuendo_timestamps', 'N/A')}*")

    st.markdown("---")
    # 3. BROADCAST RESULT DISPUTES & TIMESTAMP CORRECTIONS
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in get_sorted_weekly_result_weeks()] if get_sorted_weekly_result_weeks() else ["Week 1"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Evidence (e.g., 'At 28:14 in Episode 3, Paul clearly shakes Tom\\'s hand during Showstopper judging')")
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
                save_league_data()
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        df_disp = pd.DataFrame(st.session_state.disputes)
        st.dataframe(df_disp, hide_index=True, use_container_width=True)

# ==========================================
# --- TAB 4: ADMIN PANEL ---
# ==========================================
with tab_admin:
    st.header("👑 League Administrator Console")
    
    # Notification Banner on Data Reset
    if st.session_state.get("data_erased_confirmation"):
        st.success("✅ **All competition data, predictions, broadcast actuals, disputes, and player PINs have been permanently erased!**")
        st.session_state["data_erased_confirmation"] = False
    
    if not st.session_state.admin_authenticated:
        st.info("🔒 Admin Panel Locked. Enter Administrator PIN to access controls.")
        admin_pin_in = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_gate", max_chars=4)
        if st.button("Unlock Admin Panel"):
            if admin_pin_in == "6284":
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
        st.markdown("### 📅 Select Episode Results to Input / Update")
        
        default_admin_week = active_week
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=default_admin_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in get_sorted_weekly_result_weeks() else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        current_eliminated_admin = get_current_eliminated_bakers(admin_selected_week)
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated_admin]
        baker_opts_admin = ["--Select Baker--"] + admin_active_bakers
        
        saved_w = get_weekly_result(admin_selected_week)
        is_published = admin_selected_week in get_sorted_weekly_result_weeks()
        
        edit_unlocked = True
        if is_published:
            st.info(f"🟢 **Week {admin_selected_week} Results Recorded & Saved in System.** Reviewing saved entries below. Fields are locked by default.")
            edit_unlocked = st.checkbox(f"🔓 Enable Editing for Week {admin_selected_week} (Requires Verification before Overwriting)", value=False, key=f"unlock_edit_w{admin_selected_week}")
            
        # INTERACTIVE ELIMINATION RADIO OUTSIDE FORM
        st.markdown("#### 📣 Episode Elimination Status")
        elim_type_choice = st.radio(
            "Select Elimination Type:",
            ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"],
            index=0,
            horizontal=True,
            key=f"adm_elim_radio_w{admin_selected_week}"
        )
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts_admin, disabled=not edit_unlocked, key="adm_champ")
                st.write("Actual Technical Challenge Rankings:")
                t1 = st.selectbox("Technical 1st Place", baker_opts_admin, disabled=not edit_unlocked, key="adm_t1_w10")
                t2 = st.selectbox("Technical 2nd Place", baker_opts_admin, disabled=not edit_unlocked, key="adm_t2_w10")
                t3 = st.selectbox("Technical 3rd Place", baker_opts_admin, disabled=not edit_unlocked, key="adm_t3_w10")
                actuals["tech_rank"] = [t1, t2, t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts_admin, disabled=not edit_unlocked, key=f"adm_sb_w{admin_selected_week}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, disabled=not edit_unlocked, key=f"adm_inline_w{admin_selected_week}")
                with col2:
                    if elim_type_choice == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts_admin, disabled=not edit_unlocked, key=f"adm_elim_s_w{admin_selected_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, disabled=not edit_unlocked, key=f"adm_tr_s_w{admin_selected_week}")
                    elif elim_type_choice == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("ℹ️ No baker eliminated this week. Predicting elimination scores 0 points.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, disabled=not edit_unlocked, key=f"adm_tr_g_w{admin_selected_week}")
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts_admin, disabled=not edit_unlocked, key=f"adm_e1_d_w{admin_selected_week}")
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts_admin, disabled=not edit_unlocked, key=f"adm_e2_d_w{admin_selected_week}")
                        actuals["eliminated"] = [e1, e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, disabled=not edit_unlocked, key=f"adm_tr_d_w{admin_selected_week}")
                
                st.write(f"Actual Technical Challenge Rankings (All {len(admin_active_bakers)} Bakers):")
                tech_rank_inputs = []
                for i_pos in range(len(admin_active_bakers)):
                    pos_label = f"Technical Position #{i_pos + 1}"
                    if i_pos == 0: pos_label += " (1st Place)"
                    elif i_pos == len(admin_active_bakers) - 1: pos_label += f" ({i_pos+1}th / Last Place)"
                    t_val = st.selectbox(pos_label, baker_opts_admin, disabled=not edit_unlocked, key=f"adm_tech_pos_{i_pos}_w{admin_selected_week}")
                    tech_rank_inputs.append(t_val)
                actuals["tech_rank"] = tech_rank_inputs

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            act_hs_cnt = st.number_input("Handshakes Count", min_value=0, value=0, disabled=not edit_unlocked, key=f"adm_hs_cnt_w{admin_selected_week}")
            act_hs_stamps = st.text_input("Handshake Descriptions & Timestamps", value="", disabled=not edit_unlocked, key=f"adm_hs_stamps_w{admin_selected_week}")
            
            st.markdown("### 😢 Crying Incidents")
            act_cry_cnt = st.number_input("Crying Incidents Count", min_value=0, value=0, disabled=not edit_unlocked, key=f"adm_cry_cnt_w{admin_selected_week}")
            act_cry_stamps = st.text_input("Crying Descriptions & Timestamps", value="", disabled=not edit_unlocked, key=f"adm_cry_stamps_w{admin_selected_week}")
            
            st.markdown("### 💬 Sexual Innuendos")
            act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=0, disabled=not edit_unlocked, key=f"adm_inn_cnt_w{admin_selected_week}")
            act_inn_stamps = st.text_input("Innuendos Descriptions & Timestamps", value="", disabled=not edit_unlocked, key=f"adm_inn_stamps_w{admin_selected_week}")
            
            actuals["handshake_count"] = act_hs_cnt or 0
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt or 0
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt or 0
            actuals["innuendo_timestamps"] = act_inn_stamps
            
            if admin_selected_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                s_winner = st.selectbox("Actual Season Winner", baker_opts_admin, disabled=not edit_unlocked, key="adm_s_winner")
                s_semis = st.multiselect("Actual Semifinalists (4 Bakers)", ALL_BAKERS, disabled=not edit_unlocked, key="adm_s_semis")
                s_finalists = st.multiselect("Actual Finalists (3 Bakers)", ALL_BAKERS, disabled=not edit_unlocked, key="adm_s_finalists")
                
                s_hs_tot = st.number_input("Actual Total Season Handshakes", min_value=0, value=5, disabled=not edit_unlocked, key="adm_s_hs")
                s_cry_tot = st.number_input("Actual Total Season Crying", min_value=0, value=12, disabled=not edit_unlocked, key="adm_s_cry")
                s_inn_tot = st.number_input("Actual Total Season Innuendos", min_value=0, value=48, disabled=not edit_unlocked, key="adm_s_inn")
                
                actuals_season = {
                    "winner": s_winner,
                    "semifinalists": s_semis,
                    "finalists": s_finalists,
                    "handshakes": s_hs_tot,
                    "crying": s_cry_tot,
                    "innuendos": s_inn_tot
                }

            sub_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings", disabled=not edit_unlocked)
            if sub_actuals:
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # Recalculate Scores across all weeks
                for m_name in ALL_HUMANS_AND_AI:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    
                all_weeks_scored = get_sorted_weekly_result_weeks()
                for w in all_weeks_scored:
                    act_w = get_weekly_result(w)
                    weekly_raw = {}
                    for m_name in ALL_HUMANS_AND_AI:
                        m_data = st.session_state.league_members[m_name]
                        pred_w = m_data["weekly_picks"].get(w) or m_data["weekly_picks"].get(str(w), {})
                        raw_s = calculate_weekly_score(pred_w, act_w, w)
                        weekly_raw[m_name] = raw_s
                        m_data["weekly_breakdown"][w] = raw_s
                        
                    if weekly_raw:
                        max_r = max(weekly_raw.values())
                        if max_r > 0:
                            for m_name, raw_s in weekly_raw.items():
                                if raw_s == max_r:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                
                if st.session_state.season_results:
                    for m_name in ALL_HUMANS_AND_AI:
                        m_data = st.session_state.league_members[m_name]
                        s_pred = m_data["season_picks"]
                        s_score = calculate_season_score(s_pred, st.session_state.season_results)
                        m_data["season_score"] = s_score
                        
                for m_name in ALL_HUMANS_AND_AI:
                    m_data = st.session_state.league_members[m_name]
                    w_tot = sum(m_data["weekly_breakdown"].values())
                    s_tot = m_data.get("season_score", 0)
                    m_data["total_score"] = w_tot + s_tot
                    
                save_league_data()
                st.success(f"Results published for Week {admin_selected_week}! Leaderboard updated.")
                st.rerun()

        # --- DISPUTE RESOLUTION & MANAGEMENT CONSOLE ---
        st.markdown("---")
        st.markdown("### ⚖️ Dispute Resolution & Management Console")
        if not st.session_state.disputes:
            st.info("No active or pending disputes logged by contestants.")
        else:
            for idx, disp in enumerate(st.session_state.disputes):
                with st.expander(f"🚩 Dispute #{idx+1}: {disp.get('Player', 'Player')} contesting {disp.get('Week', 'Week')} ({disp.get('Status', 'Pending')})"):
                    st.write(f"**Contestant:** {disp.get('Player')}")
                    st.write(f"**Week:** {disp.get('Week')}")
                    st.write(f"**Category:** {disp.get('Category')}")
                    st.write(f"**Submitted Evidence:** {disp.get('Evidence')}")
                    st.write(f"**Requested Correction:** {disp.get('Correction')}")
                    
                    cur_status = disp.get("Status", "Pending GroupMe Vote 🗳️")
                    status_opts = ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"]
                    status_idx = status_opts.index(cur_status) if cur_status in status_opts else 0
                    
                    new_status = st.selectbox(f"Update Dispute Status for #{idx+1}:", status_opts, index=status_idx, key=f"disp_status_sel_{idx}")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        if st.button(f"Save Status for #{idx+1}", key=f"save_disp_btn_{idx}"):
                            disp["Status"] = new_status
                            save_league_data()
                            st.success(f"Dispute #{idx+1} status updated to '{new_status}'!")
                            st.rerun()
                    with col_d2:
                        if st.button(f"Delete Dispute #{idx+1}", key=f"del_disp_btn_{idx}"):
                            st.session_state.disputes.pop(idx)
                            save_league_data()
                            st.success(f"Dispute #{idx+1} removed!")
                            st.rerun()

        # --- PLAYER PIN RESET CONSOLE ---
        st.markdown("---")
        st.markdown("### 🔑 Player PIN Reset Console")
        pin_reset_player = st.selectbox("Select Player to Reset PIN:", ROSTER_HUMANS, key="pin_reset_sel")
        if st.button("Reset Player PIN"):
            if pin_reset_player in st.session_state.player_pins:
                del st.session_state.player_pins[pin_reset_player]
                save_league_data()
                st.success(f"✅ PIN reset for {pin_reset_player}. They can now set a new PIN on the prediction tab.")
            else:
                st.info(f"{pin_reset_player} does not have an active PIN set.")

        # --- ERASE ALL SAVED COMPETITION DATA ---
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
