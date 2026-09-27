import os
import json
import random
import pandas as pd
import streamlit as st
from PIL import Image

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for High Contrast in both Dark and Light modes
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

# --- DATA PERSISTENCE ENGINE ---
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
                return json.load(f)
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

for name in ALL_HUMANS_AND_AI:
    if name not in st.session_state.league_members:
        st.session_state.league_members[name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

all_scored_weeks = sorted([int(k) for k in st.session_state.weekly_results.keys()])
active_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_week > 10: active_week = 10
st.session_state.current_week = active_week

# --- 2. SCORING ENGINE ---
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
            
        pred_in_line = predictions.get("in_line_sb")
        act_in_line = actuals.get("in_line_sb", [])
        if pred_in_line and act_in_line and pred_in_line in act_in_line and pred_in_line != actuals.get("star_baker"):
            score += 2
        
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

        pred_trouble = predictions.get("in_trouble")
        act_trouble = actuals.get("in_trouble", [])
        if pred_trouble and act_trouble and pred_trouble in act_trouble:
            score += 2
            
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
        pred_top_3 = predictions.get("tech_top_3", [])
        act_top_3 = actuals.get("tech_top_3", [])
        if len(pred_top_3) == 3 and len(act_top_3) == 3:
            if pred_top_3 == act_top_3:
                score += 10
            else:
                for idx, baker in enumerate(pred_top_3):
                    if act_top_3[idx] == baker:
                        score += 3 if idx == 0 else 2
                    elif baker in act_top_3:
                        score += 1
                        
        pred_bot_3 = predictions.get("tech_bottom_3", [])
        act_bot_3 = actuals.get("tech_bottom_3", [])
        if len(pred_bot_3) == 3 and len(act_bot_3) == 3:
            if pred_bot_3 == act_bot_3:
                score += 10
            else:
                for idx, baker in enumerate(pred_bot_3):
                    if act_bot_3[idx] == baker:
                        score += 3 if idx == 2 else 2
                    elif baker in act_bot_3:
                        score += 1
                        
    return score

def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return 0
        
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and not str(pred_winner).startswith("-- Select"):
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
            
    pred_semis = [b for b in predictions.get("semifinalists", []) if b and not str(b).startswith("-- Select")]
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    p_hs = predictions.get("handshakes")
    a_hs = actuals.get("handshakes")
    if p_hs is not None and a_hs is not None:
        if p_hs == a_hs: score += 20
        elif abs(p_hs - a_hs) <= 1: score += 10
            
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

def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    try:
        for filename in os.listdir("assets"):
            stem, ext = os.path.splitext(filename)
            if stem.lower().strip() == target and ext.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                full_path = os.path.join("assets", filename)
                try: return Image.open(full_path)
                except Exception: pass
    except Exception: pass
    return None

def generate_ai_brian_season_picks():
    winner = random.choice(ALL_BAKERS)
    remaining = [b for b in ALL_BAKERS if b != winner]
    semis = random.sample(remaining, 3)
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
        sb = random.choice(active_bakers)
        elim = random.sample([b for b in active_bakers if b != sb], 2) if is_double_elim else random.choice([b for b in active_bakers if b != sb])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": sb, "eliminated": elim, "tech_rank": tech_rank}
    elif week == 8:
        sb = random.choice(active_bakers)
        elim = random.sample([b for b in active_bakers if b != sb], 2) if is_double_elim else random.choice([b for b in active_bakers if b != sb])
        in_line = random.choice([b for b in active_bakers if b != sb])
        in_tr = random.choice([b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": sb, "eliminated": elim, "tech_rank": tech_rank, "in_line_sb": in_line, "in_trouble": in_tr}
    else:
        sb = random.choice(active_bakers)
        elim = random.sample([b for b in active_bakers if b != sb], 2) if is_double_elim else random.choice([b for b in active_bakers if b != sb])
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bot = [b for b in active_bakers if b not in tech_top_3]
        tech_bot_3 = random.sample(rem_bot, min(3, len(rem_bot))) if rem_bot else []
        in_line = random.choice([b for b in active_bakers if b != sb])
        in_tr = random.choice([b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])])
        return {
            "star_baker": sb, "eliminated": elim, "tech_top_3": tech_top_3, "tech_bottom_3": tech_bot_3,
            "in_line_sb": in_line, "in_trouble": in_tr
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 3. HEADER LAYOUT ---
col_head1, col_head2 = st.columns([1, 5])
with col_head1:
    norman_img = None
    for p in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.png"]:
        if os.path.exists(p):
            norman_img = p
            break
    if norman_img is not None:
        st.image(norman_img, width=110)
    else:
        st.markdown("<h1 style='font-size: 70px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_head2:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- 4. SIDEBAR ---
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
        * **Technical Challenge:** Exact Spot: 1st/Last(3pts), 2nd/3rd(2pts); Wrong Spot(1pt); Perfect Sweep(10pts)
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)

    with st.expander("🏁 Weekly Predictions (Weeks 8-10)", expanded=False):
        st.markdown("""
        * **Week 8 (Quarterfinal episodic - 5 bakers):** Star Baker(5pts), Eliminated(5pts), Perfect Tech Sweep(25pts)
        * **Week 9 (Semifinal episodic - 4 bakers):** Star Baker(5pts), Eliminated(5pts), Perfect Tech Sweep(20pts)
        * **Week 10 (Grand Finale episodic - 3 bakers):** Show Champion(15pts), Perfect Tech Sweep(15pts)
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
            "member": name,
            "points": tot_pts
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        
        lb_table_data = []
        for rank, row in df_lb.iterrows():
            r_num = rank + 1
            m_name = row["member"]
            m_pts = row["points"]
            rank_badge = f"#{r_num}"
            if r_num == 1: rank_badge = "🥇 #1"
            elif r_num == 2: rank_badge = "🥈 #2"
            elif r_num == 3: rank_badge = "🥉 #3"
            
            lb_table_data.append({
                "Rank": rank_badge,
                "League Member": m_name,
                "Total Points": f"{m_pts} pts"
            })
            
        df_lb_show = pd.DataFrame(lb_table_data)
        st.dataframe(df_lb_show, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ALL_HUMANS_AND_AI, key="lb_player_card_sel")
    
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
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
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
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
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
    
    if st.session_state.current_week == 1:
        st.info("🔍 **Week 1 Scouting Phase Active!** Browse the baker gallery above to scout the Class of 2026. Weekly prediction ballots unlock in Week 2 after Episode 1 results are published!")
    else:
        st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
        st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
        
        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        dropdown_options = ["--Select Baker--"] + active_bakers
        
        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
        
        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)
            
        user_submitting_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="submit_player_sel")
        
        # Player PIN Authentication
        user_pin = st.text_input("Enter Your 4-Digit Security PIN:", type="password", key="submit_player_pin", max_chars=4)
        stored_pin = st.session_state.player_pins.get(user_submitting_player)
        
        authenticated = False
        if stored_pin is None:
            st.info(f"Welcome **{user_submitting_player}**! Please set your 4-digit PIN password below to lock your profile.")
            if len(user_pin) == 4 and user_pin.isdigit():
                if st.button("Set PIN & Unlock Ballot"):
                    st.session_state.player_pins[user_submitting_player] = user_pin
                    save_league_data()
                    st.success(f"PIN set successfully for {user_submitting_player}!")
                    st.rerun()
        else:
            if user_pin == stored_pin:
                authenticated = True
                st.success(f"🔓 Profile Unlocked for {user_submitting_player}")
            elif user_pin != "":
                st.error("❌ Incorrect 4-Digit PIN!")

        if authenticated:
            if st.session_state.current_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", dropdown_options, key="user_win_pick")
                    user_semi1 = st.selectbox("Predict Semifinalist #1 [10 pts]", dropdown_options, key="user_semi1_pick")
                    user_semi2 = st.selectbox("Predict Semifinalist #2 [10 pts]", dropdown_options, key="user_semi2_pick")
                    user_semi3 = st.selectbox("Predict Semifinalist #3 [10 pts]", dropdown_options, key="user_semi3_pick")
                    user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                    user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)

            st.markdown("### Weekly Ballot")
            with st.form("weekly_predictions_form"):
                weekly_picks = {}
                if st.session_state.current_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", dropdown_options)
                    st.markdown("**Predict Technical Challenge Rankings:**")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w10")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w10")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w10")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                    
                elif st.session_state.current_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", dropdown_options)
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_w9")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_w9")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options)
                    
                    st.markdown("**Predict Technical Challenge Rankings:**")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w9")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w9")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w9")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", dropdown_options, key="t4_w9")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]
                    
                elif st.session_state.current_week == 8:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", dropdown_options)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", dropdown_options)
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_w8")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_w8")
                        weekly_picks["eliminated"] = [e1, e2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", dropdown_options, key="tr_w8")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", dropdown_options, key="tr_w8")
                    
                    st.write("Technical Challenge Placement Predictions:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w8")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w8")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w8")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", dropdown_options, key="t4_w8")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", dropdown_options, key="t5_w8")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    
                else: # Weeks 2-7
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", dropdown_options)
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_std")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_std")
                        weekly_picks["eliminated"] = [e1, e2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", dropdown_options, key="tr_std")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", dropdown_options, key="tr_std")
                        
                    st.write("Technical Challenge Placement Predictions:")
                    tt1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="tt1_std")
                    tt2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="tt2_std")
                    tt3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="tt3_std")
                    tb1 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", dropdown_options, key="tb1_std")
                    tb2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", dropdown_options, key="tb2_std")
                    tb3 = st.selectbox("Technical Last Place [3 pts]", dropdown_options, key="tb3_std")
                    
                    weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                    weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]
                    
                sub_ballot = st.form_submit_button("Lock In & Submit Predictions")
                
                if sub_ballot:
                    errors = []
                    
                    if st.session_state.current_week == 2:
                        s_choices = [user_winner, user_semi1, user_semi2, user_semi3]
                        if "--Select Baker--" in s_choices:
                            errors.append("⚠️ Please select a valid baker for all Season-Long Prediction fields.")
                        else:
                            if len(set(s_choices)) < len(s_choices):
                                errors.append("❌ Duplicate Selection Error: Season Winner and Semifinalists must all be distinct bakers.")
                                
                    main_picks = []
                    for k in ["star_baker", "in_line_sb", "show_champion", "in_trouble"]:
                        v = weekly_picks.get(k)
                        if v and v != "--Select Baker--":
                            main_picks.append(v)
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
                        errors.append("⚠️ Missing Selection Error: Please make a selection for all required main prediction fields.")
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
                        for err in errors:
                            st.error(err)
                    else:
                        if st.session_state.current_week == 2:
                            st.session_state.league_members[user_submitting_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": [user_semi1, user_semi2, user_semi3],
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                        st.session_state.league_members[user_submitting_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                        
                        ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                        
                        save_league_data()
                        st.success(f"🎉 Predictions successfully saved for {user_submitting_player} (Week {st.session_state.current_week})! AI Brian has also logged his picks.")

# --- TAB 3: SHOW RESULTS ---
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # 1. Chaos Categories Running Totals
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    for w_num, w_act in st.session_state.weekly_results.items():
        tot_hs += w_act.get("handshake_count", len(w_act.get("handshake_bakers", []))) or 0
        tot_cry += w_act.get("crying_count", 0) or 0
        tot_inn += w_act.get("innuendo_count", 0) or 0

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Hollywood Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Sexual Innuendos", f"{tot_inn}")

    st.markdown("---")
    
    # 2. Weekly Show Results Breakdown
    st.subheader("📅 Weekly Broadcast Results Breakdown")
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        sorted_weeks = sorted([int(k) for k in st.session_state.weekly_results.keys()])
        for w_num in sorted_weeks:
            w_act = st.session_state.weekly_results.get(w_num, st.session_state.weekly_results.get(str(w_num), {}))
            with st.expander(f"📺 Week {w_num} Broadcast Results", expanded=(w_num == max(sorted_weeks))):
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.markdown("#### **🏆 Main Episode Awards**")
                    sb_val = w_act.get("star_baker", w_act.get("show_champion", "None"))
                    st.write(f"🌟 **Star Baker / Champion:** {sb_val}")
                    
                    in_line_val = w_act.get("in_line_sb", [])
                    in_line_str = ", ".join(in_line_val) if isinstance(in_line_val, list) and in_line_val else (str(in_line_val) if in_line_val else "None")
                    st.write(f"🎖️ **In Line for Star Baker:** {in_line_str}")
                    
                    elim_val = w_act.get("eliminated", "None")
                    elim_str = ", ".join(elim_val) if isinstance(elim_val, list) and elim_val else (str(elim_val) if elim_val else "None")
                    st.write(f"🚪 **Eliminated Baker:** {elim_str}")
                    
                    in_tr_val = w_act.get("in_trouble", [])
                    in_tr_str = ", ".join(in_tr_val) if isinstance(in_tr_val, list) and in_tr_val else (str(in_tr_val) if in_tr_val else "None")
                    st.write(f"⚠️ **In Trouble of Elimination:** {in_tr_str}")
                    
                with col_w2:
                    st.markdown("#### **🔥 Chaos Metrics & Video Timestamps**")
                    hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                    hs_cnt = w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
                    hs_stamps = w_act.get("handshake_timestamps", "None") or "None"
                    st.write(f"🤝 **Handshakes ({hs_cnt}):** {hs_bakers} | Notes: `{hs_stamps}`")
                    
                    cry_cnt = w_act.get("crying_count", 0)
                    cry_stamps = w_act.get("crying_timestamps", "None") or "None"
                    st.write(f"😢 **Crying Incidents ({cry_cnt}):** `{cry_stamps}`")
                    
                    inn_cnt = w_act.get("innuendo_count", 0)
                    inn_stamps = w_act.get("innuendo_timestamps", "None") or "None"
                    st.write(f"💬 **Sexual Innuendos ({inn_cnt}):** `{inn_stamps}`")
                
                # Technical Challenge Placement with 1st Place Highlight
                tech_ranks = w_act.get("tech_rank", [])
                if tech_ranks:
                    st.markdown("#### **📊 Technical Challenge Placements**")
                    tech_items = []
                    for idx, baker in enumerate(tech_ranks):
                        rank_str = f"🥇 1st Place: **{baker}**" if idx == 0 else (f"🥈 2nd Place: **{baker}**" if idx == 1 else (f"🥉 3rd Place: **{baker}**" if idx == 2 else f"{idx+1}th Place: **{baker}**"))
                        tech_items.append(rank_str)
                    st.write(" | ".join(tech_items))

    # 3. Broadcast Result Disputes
    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")
    
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted([int(k) for k in st.session_state.weekly_results.keys()])] if st.session_state.weekly_results else ["Week 1"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Evidence")
            disp_correction = st.text_input("Requested Correction")
            sub_disp = st.form_submit_button("Submit Dispute for League Vote")
            if sub_disp:
                st.session_state.disputes.append({
                    "Player": disp_player, "Week": disp_week, "Category": disp_cat,
                    "Evidence": disp_evidence, "Correction": disp_correction, "Status": "Pending GroupMe Vote 🗳️"
                })
                save_league_data()
                st.success("Dispute submitted successfully!")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if st.session_state.get("data_erased_confirmation"):
        st.success("✅ All competition data, predictions, broadcast actuals, disputes, and player PINs have been permanently erased!")
        del st.session_state["data_erased_confirmation"]
    
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
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=st.session_state.current_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results or str(w) in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        cur_w = admin_selected_week
        current_eliminated = eliminated_bakers_by_week.get(cur_w, [])
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        admin_dropdown_options = ["--Select Baker--"] + admin_active_bakers
        
        saved_actuals = st.session_state.weekly_results.get(cur_w, st.session_state.weekly_results.get(str(cur_w), {}))
        is_already_published = (cur_w in st.session_state.weekly_results or str(cur_w) in st.session_state.weekly_results)
        
        if is_already_published:
            st.info(f"🟢 **Week {cur_w} Results Recorded & Saved in System**\n\nReviewing saved entries below. To prevent accidental edits that alter player scores, fields are locked by default.")
            enable_edit = st.checkbox(f"🔓 Enable Editing for Week {cur_w} (Requires Verification before Overwriting Saved Results)", key=f"unlock_edit_w{cur_w}")
        else:
            enable_edit = True

        st.markdown("### 📢 Elimination Status")
        saved_elim = saved_actuals.get("eliminated", "None")
        default_elim_idx = 0
        if saved_elim == "None": default_elim_idx = 1
        elif isinstance(saved_elim, list): default_elim_idx = 2
        
        elim_type = st.radio(
            "Select Elimination Status for Week:", 
            ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], 
            index=default_elim_idx, 
            horizontal=True, 
            key=f"admin_elim_type_w{cur_w}",
            disabled=(is_already_published and not enable_edit)
        )

        with st.form(f"admin_actuals_form_w{cur_w}"):
            st.subheader(f"Input Broadcast Results for Week {cur_w}")
            actuals = {}
            
            if cur_w == 10:
                s_sc = saved_actuals.get("show_champion", "--Select Baker--")
                sc_idx = admin_dropdown_options.index(s_sc) if s_sc in admin_dropdown_options else 0
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_dropdown_options, index=sc_idx, disabled=(is_already_published and not enable_edit))
            else:
                col1, col2 = st.columns(2)
                with col1:
                    s_sb = saved_actuals.get("star_baker", "--Select Baker--")
                    sb_idx = admin_dropdown_options.index(s_sb) if s_sb in admin_dropdown_options else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_options, index=sb_idx, disabled=(is_already_published and not enable_edit))
                    
                    saved_inline = [b for b in saved_actuals.get("in_line_sb", []) if b in admin_active_bakers]
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, default=saved_inline, disabled=(is_already_published and not enable_edit))
                
                with col2:
                    saved_trouble = [b for b in saved_actuals.get("in_trouble", []) if b in admin_active_bakers]
                    if elim_type == "Single Elimination":
                        s_el = saved_elim if isinstance(saved_elim, str) else "--Select Baker--"
                        el_idx = admin_dropdown_options.index(s_el) if s_el in admin_dropdown_options else 0
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_options, index=el_idx, disabled=(is_already_published and not enable_edit))
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=saved_trouble, disabled=(is_already_published and not enable_edit))
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("ℹ️ No baker was eliminated this week.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=saved_trouble, disabled=(is_already_published and not enable_edit))
                    else:
                        s_el1 = saved_elim[0] if isinstance(saved_elim, list) and len(saved_elim) > 0 else "--Select Baker--"
                        s_el2 = saved_elim[1] if isinstance(saved_elim, list) and len(saved_elim) > 1 else "--Select Baker--"
                        el1_idx = admin_dropdown_options.index(s_el1) if s_el1 in admin_dropdown_options else 0
                        el2_idx = admin_dropdown_options.index(s_el2) if s_el2 in admin_dropdown_options else 0
                        e1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_options, index=el1_idx, disabled=(is_already_published and not enable_edit))
                        e2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_options, index=el2_idx, disabled=(is_already_published and not enable_edit))
                        actuals["eliminated"] = [e1, e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=saved_trouble, disabled=(is_already_published and not enable_edit))

                st.write(f"Actual Technical Challenge Placement (Position-by-Position for All {len(admin_active_bakers)} Active Bakers):")
                tech_positions = []
                saved_tech = saved_actuals.get("tech_rank", [])
                for idx_pos in range(len(admin_active_bakers)):
                    pos_name = f"Technical Position #{idx_pos+1}"
                    if idx_pos == 0: pos_name += " (1st Place)"
                    elif idx_pos == len(admin_active_bakers) - 1: pos_name += " (Last Place)"
                    s_pos_baker = saved_tech[idx_pos] if idx_pos < len(saved_tech) else "--Select Baker--"
                    pos_idx = admin_dropdown_options.index(s_pos_baker) if s_pos_baker in admin_dropdown_options else 0
                    t_val = st.selectbox(pos_name, admin_dropdown_options, index=pos_idx, key=f"admin_pos_{idx_pos}_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    tech_positions.append(t_val)
                actuals["tech_rank"] = tech_positions

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            saved_hs_cnt = saved_actuals.get("handshake_count", len(saved_actuals.get("handshake_bakers", [])))
            saved_hs_stamps = saved_actuals.get("handshake_timestamps", "")
            with col_hs1:
                act_handshake_cnt = st.number_input("Number of Handshake Occurrences", min_value=0, value=saved_hs_cnt, disabled=(is_already_published and not enable_edit))
            with col_hs2:
                act_handshake_stamps = st.text_input("Handshake Video Timestamps", value=saved_hs_stamps, disabled=(is_already_published and not enable_edit))
            saved_hs_bakers = [b for b in saved_actuals.get("handshake_bakers", []) if b in admin_active_bakers]
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", admin_active_bakers, default=saved_hs_bakers, disabled=(is_already_published and not enable_edit))

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            saved_cry_cnt = saved_actuals.get("crying_count", 0)
            saved_cry_stamps = saved_actuals.get("crying_timestamps", "")
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Occurrences", min_value=0, value=saved_cry_cnt, disabled=(is_already_published and not enable_edit))
            with col_cry2:
                act_crying_stamps = st.text_input("Crying Video Timestamps", value=saved_cry_stamps, disabled=(is_already_published and not enable_edit))

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            saved_inn_cnt = saved_actuals.get("innuendo_count", 0)
            saved_inn_stamps = saved_actuals.get("innuendo_timestamps", "")
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Innuendo Occurrences", min_value=0, value=saved_inn_cnt, disabled=(is_already_published and not enable_edit))
            with col_inn2:
                act_innuendo_stamps = st.text_input("Innuendo Video Timestamps", value=saved_inn_stamps, disabled=(is_already_published and not enable_edit))

            actuals["handshake_count"] = act_handshake_cnt
            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            actuals["innuendo_timestamps"] = act_innuendo_stamps

            btn_text = "Update & Recalculate Standings" if is_already_published else "Publish Official Week Results & Recalculate Standings"
            submit_admin = st.form_submit_button(btn_text, disabled=(is_already_published and not enable_edit))
            
            if submit_admin:
                st.session_state.weekly_results[cur_w] = actuals
                st.session_state.weekly_results[str(cur_w)] = actuals
                
                for m_name in ALL_HUMANS_AND_AI:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    
                for w_num, w_act in st.session_state.weekly_results.items():
                    try: w_num_int = int(w_num)
                    except: continue
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
                st.success(f"🎉 Official Week {cur_w} results published! All league standings updated.")
                st.rerun()

        # --- DISPUTE RESOLUTION CONSOLE ---
        if st.session_state.disputes:
            st.markdown("---")
            st.subheader("⚖️ Dispute Resolution & Management Console")
            st.write("Review and resolve result contestations submitted by league members:")
            
            for idx, disp in enumerate(st.session_state.disputes):
                with st.expander(f"Dispute #{idx+1} ({disp.get('Player')} - {disp.get('Week')}) | Current Status: {disp.get('Status')}", expanded=False):
                    st.write(f"**Category:** {disp.get('Category')}")
                    st.write(f"**Evidence:** {disp.get('Evidence')}")
                    st.write(f"**Requested Correction:** {disp.get('Correction')}")
                    
                    new_status = st.selectbox(f"Update Status for Dispute #{idx+1}", ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"], key=f"disp_status_sel_{idx}")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        if st.button(f"Save Resolution Status #{idx+1}"):
                            st.session_state.disputes[idx]["Status"] = new_status
                            save_league_data()
                            st.success("Dispute status updated!")
                            st.rerun()
                    with col_d2:
                        if st.button(f"Delete Dispute #{idx+1}"):
                            st.session_state.disputes.pop(idx)
                            save_league_data()
                            st.success("Dispute removed!")
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

        # --- ERASE ALL SAVED LEAGUE DATA ---
        st.markdown("---")
        st.subheader("🚨 Emergency Reset Data")
        st.write("Use this feature to clear all predictions, broadcast actuals, disputes, and player PINs back to a clean state.")
        confirm_erase = st.checkbox("I understand this will erase all player picks, PINs, and published broadcast actuals.", key="confirm_erase_chk")
        if st.button("Erase All Saved League Data", type="primary"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                st.session_state.player_pins = {}
                for m in ALL_HUMANS_AND_AI:
                    st.session_state.league_members[m] = {
                        "weekly_picks": {},
                        "season_picks": {},
                        "total_score": 0,
                        "weekly_breakdown": {}
                    }
                if os.path.exists(DATA_FILE):
                    try: os.remove(DATA_FILE)
                    except: pass
                st.session_state["data_erased_confirmation"] = True
                st.rerun()
            else:
                st.error("Please check the confirmation box above first.")
