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

# Custom Styling for clean contrast and theme support
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

# --- AUTOMATIC WEEK DETERMINATION ---
all_scored_weeks = sorted([int(k) for k in st.session_state.weekly_results.keys()])
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
            if exact_count == 15:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx == 0: score += 3
                        else: score += 2
    else:
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        if len(pred_top3) == 3 and len(act_top3) == 3:
            if pred_top3 == act_top3:
                score += 10
            else:
                for idx, b in enumerate(pred_top3):
                    if idx < len(act_top3) and act_top3[idx] == b:
                        score += 3 if idx == 0 else 2
                    elif b in act_top3:
                        score += 1
                        
        pred_bot3 = predictions.get("tech_bottom_3", [])
        act_bot3 = actuals.get("tech_bottom_3", [])
        if len(pred_bot3) == 3 and len(act_bot3) == 3:
            if pred_bot3 == act_bot3:
                score += 10
            else:
                for idx, b in enumerate(pred_bot3):
                    if idx < len(act_bot3) and act_bot3[idx] == b:
                        score += 3 if idx == 2 else 2
                    elif b in act_bot3:
                        score += 1
                        
    if week < 9:
        if predictions.get("in_line_sb") and predictions.get("in_line_sb") in actuals.get("in_line_sb", []):
            if predictions.get("in_line_sb") != actuals.get("star_baker"):
                score += 2
        if predictions.get("in_trouble") and predictions.get("in_trouble") in actuals.get("in_trouble", []):
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
    if pred_winner and pred_winner != "--Select Baker--":
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
            
    pred_semis = predictions.get("semifinalists", [])
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
                return Image.open(os.path.join("assets", filename))
    except Exception:
        pass
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
        elim = random.sample([b for b in active_bakers if b != sb], min(2, len(active_bakers)-1)) if is_double_elim else random.choice([b for b in active_bakers if b != sb])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": sb, "eliminated": elim, "tech_rank": tech_rank}
    elif week == 8:
        sb = random.choice(active_bakers)
        elim = random.sample([b for b in active_bakers if b != sb], min(2, len(active_bakers)-1)) if is_double_elim else random.choice([b for b in active_bakers if b != sb])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line = random.choice([b for b in active_bakers if b != sb])
        in_tr = random.choice([b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])])
        return {"star_baker": sb, "eliminated": elim, "tech_rank": tech_rank, "in_line_sb": in_line, "in_trouble": in_tr}
    else:
        sb = random.choice(active_bakers)
        elim = random.sample([b for b in active_bakers if b != sb], min(2, len(active_bakers)-1)) if is_double_elim else random.choice([b for b in active_bakers if b != sb])
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem = [b for b in active_bakers if b not in tech_top_3]
        tech_bot_3 = random.sample(rem, min(3, len(rem))) if rem else []
        in_line = random.choice([b for b in active_bakers if b != sb])
        in_tr = random.choice([b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])])
        return {
            "star_baker": sb, "eliminated": elim, "tech_top_3": tech_top_3, "tech_bottom_3": tech_bot_3,
            "in_line_sb": in_line, "in_trouble": in_tr
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. APP INTERFACE LAYOUT ---
col_head1, col_head2 = st.columns([1, 5])
with col_head1:
    norman_img = None
    for p in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.png"]:
        if os.path.exists(p):
            norman_img = p
            break
    if norman_img is not None:
        st.image(norman_img, width=90)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_head2:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📌 Competition Progress")
    if active_week == 1:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nSubmit your Season-Long Predictions! Week 2 predictions unlock after Week 1 results are posted.")
    else:
        st.success(f"🟢 **Active Status: Week {active_week} Open**\n\nWeekly predictions are open up through Week {active_week}.")

    st.markdown("---")
    st.header("🎯 Points Reference Guide")
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
        * **Technical Challenge:** Exact positions (3 pts 1st/Last, 2 pts others); Sweep Bonus
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)

# --- MAIN TABS ---
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
        
        lb_display = []
        for rank, row in df_lb.iterrows():
            r_num = rank + 1
            m_name = row["member"]
            m_pts = row["points"]
            badge = f"#{r_num}"
            if r_num == 1: badge = "🥇 #1"
            elif r_num == 2: badge = "🥈 #2"
            elif r_num == 3: badge = "🥉 #3"
            
            lb_display.append({
                "Rank": badge,
                "League Member": m_name,
                "Total Points": f"{m_pts} pts"
            })
            
        df_lb_show = pd.DataFrame(lb_display)
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
                st.info(f"🔒 {selected_card_player} has not set a PIN yet.")
            else:
                card_pin_input = st.text_input(f"Enter {selected_card_player}'s 4-Digit PIN to unlock Season Projections:", type="password", key=f"card_pin_{selected_card_player}")
                if card_pin_input == p_pin:
                    show_season = True
                    st.success("🔓 PIN Verified!")
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
            
        st.markdown("#### **Weekly Predictions Log:**")
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
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True)
        else:
            st.info("No weekly predictions logged yet.")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions Ballot")
    
    current_eliminated = eliminated_bakers_by_week.get(active_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    dropdown_options = ["--Select Baker--"] + active_bakers
    
    user_submitting_player = st.selectbox("Select Your Name / Profile:", ROSTER_HUMANS, key="pred_user_sel")
    user_pin = st.session_state.player_pins.get(user_submitting_player)
    
    user_authed = False
    
    if user_pin is None:
        st.info(f"Welcome, **{user_submitting_player}**! Create a 4-digit PIN password to secure your ballot.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p1 = st.text_input("Create 4-Digit PIN", type="password", max_chars=4, key=f"create_p1_{user_submitting_player}")
        with col_p2:
            p2 = st.text_input("Confirm 4-Digit PIN", type="password", max_chars=4, key=f"create_p2_{user_submitting_player}")
        if st.button("Set PIN & Unlock Ballot"):
            if len(p1) != 4 or not p1.isdigit():
                st.error("PIN must be exactly 4 numeric digits!")
            elif p1 != p2:
                st.error("PINs do not match!")
            else:
                st.session_state.player_pins[user_submitting_player] = p1
                save_league_data()
                st.success("PIN created successfully!")
                st.rerun()
    else:
        entered_pin = st.text_input(f"Enter 4-Digit PIN for {user_submitting_player}:", type="password", max_chars=4, key=f"login_pin_{user_submitting_player}")
        if entered_pin == user_pin:
            user_authed = True
            st.success(f"🔓 Authenticated as **{user_submitting_player}**!")
        elif entered_pin != "":
            st.error("❌ Incorrect 4-digit PIN")

    if user_authed:
        st.markdown("---")
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

        st.markdown("---")
        
        # Post-Week 1 Season-Long Predictions Entry in Week 2
        user_winner, user_semi1, user_semi2, user_semi3 = "--Select Baker--", "--Select Baker--", "--Select Baker--", "--Select Baker--"
        user_handshakes, user_crying, user_innuendos = None, None, None
        
        if active_week == 2:
            st.subheader("🌟 Season-Long Projections (Post-Week 1 / Scouting Phase)")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                user_winner = st.selectbox("Predict Season Winner [40 pts]", dropdown_options, key="u_win_s")
                user_semi1 = st.selectbox("Predict Semifinalist #1 [10 pts]", dropdown_options, key="u_semi1_s")
                user_semi2 = st.selectbox("Predict Semifinalist #2 [10 pts]", dropdown_options, key="u_semi2_s")
                user_semi3 = st.selectbox("Predict Semifinalist #3 [10 pts]", dropdown_options, key="u_semi3_s")
            with col_s2:
                user_handshakes = st.number_input("Predict Total Handshakes", min_value=0, value=None, placeholder="Enter count...", key="u_hs_s")
                user_crying = st.number_input("Predict Total Crying Incidents", min_value=0, value=None, placeholder="Enter count...", key="u_cry_s")
                user_innuendos = st.number_input("Predict Total Innuendos", min_value=0, value=None, placeholder="Enter count...", key="u_inn_s")

        st.subheader(f"📅 Submit Predictions Ballot: Week {active_week}")
        is_double_elim = False
        if active_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=False, key=f"is_dbl_elim_chk_w{active_week}")

        with st.form("weekly_predictions_ballot_form"):
            weekly_picks = {}
            if active_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", dropdown_options, key="champ_w10")
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w10")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w10")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w10")
                weekly_picks["tech_rank"] = [t1, t2, t3]
            elif active_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options)
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_w9")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_w9")
                    weekly_picks["eliminated"] = [e1, e2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options, key="e1_w9_s")
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w9")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w9")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w9")
                t4 = st.selectbox("Technical 4th Place [3 pts]", dropdown_options, key="t4_w9")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]
            elif active_week == 8:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options)
                weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", dropdown_options)
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="e1_w8")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="e2_w8")
                    weekly_picks["eliminated"] = [e1, e2]
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", dropdown_options, key="tr_w8")
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options)
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", dropdown_options, key="tr_w8")
                
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", dropdown_options, key="t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", dropdown_options, key="t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
            else:
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
                    
                st.write("Predict Technical Challenge Positions:")
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
                    errors.append("⚠️ Missing Selection Error: Please make a selection for all required main prediction fields.")
                elif len(set(main_picks)) < len(main_picks):
                    errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated.")
                    
                tech_picks = weekly_picks.get("tech_rank", []) if "tech_rank" in weekly_picks else weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])
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

# --- TAB 3: SHOW RESULTS ---
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # 1. CHAOS CATEGORIES RUNNING TOTALS
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = sum([w.get("handshake_count", len(w.get("handshake_bakers", []))) for w in st.session_state.weekly_results.values()])
    tot_cry = sum([w.get("crying_count", 0) for w in st.session_state.weekly_results.values()])
    tot_inn = sum([w.get("innuendo_count", 0) for w in st.session_state.weekly_results.values()])
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1: st.metric("🤝 Hollywood Handshakes", f"{tot_hs}")
    with col_c2: st.metric("😢 Crying Incidents", f"{tot_cry}")
    with col_c3: st.metric("💬 Sexual Innuendos", f"{tot_inn}")
    
    st.markdown("---")
    st.subheader("📅 Weekly Broadcast Results Breakdown")
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            with st.expander(f"📺 Week {w_num} Broadcast Results", expanded=(w_num == max(st.session_state.weekly_results.keys()))):
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.markdown("#### **🏆 Main Episode Awards**")
                    sb_val = w_act.get("star_baker", w_act.get("show_champion", "None"))
                    st.write(f"🌟 **Star Baker / Champion:** {sb_val}")
                    
                    in_line_val = w_act.get("in_line_sb", [])
                    in_line_str = ", ".join(in_line_val) if isinstance(in_line_val, list) and in_line_val else str(in_line_val)
                    st.write(f"🎖️ **In Line for Star Baker:** {in_line_str}")
                    
                    elim_val = w_act.get("eliminated", "None")
                    elim_str = ", ".join(elim_val) if isinstance(elim_val, list) and elim_val else str(elim_val)
                    st.write(f"🚪 **Eliminated Baker:** {elim_str}")
                    
                    in_tr_val = w_act.get("in_trouble", [])
                    in_tr_str = ", ".join(in_tr_val) if isinstance(in_tr_val, list) and in_tr_val else str(in_tr_val)
                    st.write(f"⚠️ **In Trouble of Elimination:** {in_tr_str}")
                    
                with col_w2:
                    st.markdown("#### **🔥 Chaos Metrics & Video Descriptions**")
                    hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                    st.write(f"🤝 **Handshakes ({w_act.get('handshake_count', 0)}):** {hs_bakers}")
                    st.write(f"😢 **Crying ({w_act.get('crying_count', 0)}):** {w_act.get('crying_timestamps', 'N/A')}")
                    st.write(f"💬 **Innuendos ({w_act.get('innuendo_count', 0)}):** {w_act.get('innuendo_timestamps', 'N/A')}")
                
                tech_ranks = w_act.get("tech_rank", [])
                if tech_ranks:
                    st.markdown("#### **📊 Technical Challenge Placements**")
                    tech_items = []
                    for idx, baker in enumerate(tech_ranks):
                        pos_str = f"🥇 **1st Place**" if idx == 0 else (f"🥈 **2nd Place**" if idx == 1 else (f"🥉 **3rd Place**" if idx == 2 else f"**{idx+1}th Place**"))
                        tech_items.append(f"{pos_str}: {baker}")
                    st.write(" | ".join(tech_items))

    st.markdown("---")
    st.subheader("📋 Broadcast Audit Summary Table")
    if st.session_state.weekly_results:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshake_count', 0)}",
                "Crying Scenes": f"{w_act.get('crying_count', 0)} ({w_act.get('crying_timestamps', 'N/A')})",
                "Innuendos": f"{w_act.get('innuendo_count', 0)} ({w_act.get('innuendo_timestamps', 'N/A')})"
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_submission_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in range(1, 11)])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Evidence")
            disp_correction = st.text_input("Requested Correction")
            if st.form_submit_button("Submit Dispute for League Vote"):
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
        if st.session_state.get("data_erased_confirmation"):
            st.success(st.session_state.data_erased_confirmation)
            del st.session_state["data_erased_confirmation"]

        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        st.subheader("📅 Select Episode Results to Record or Review")
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=min(active_week - 1, 9),
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        saved_act = st.session_state.weekly_results.get(admin_selected_week, {})
        is_pub = admin_selected_week in st.session_state.weekly_results
        
        if is_pub:
            st.info(f"🟢 **Week {admin_selected_week} Results Recorded & Saved in System**\n\nReviewing saved entries below. Fields are locked to protect player scores.")
            enable_edit = st.checkbox(f"🔓 Enable Editing for Week {admin_selected_week} (Requires Verification before Overwriting Saved Results)", key=f"unlock_edit_w{admin_selected_week}")
        else:
            enable_edit = True

        current_eliminated = eliminated_bakers_by_week.get(admin_selected_week, [])
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        admin_dropdown_options = ["--Select Baker--"] + admin_active_bakers

        elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{admin_selected_week}", disabled=(is_pub and not enable_edit))

        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input / Review Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                s_sc = saved_act.get("show_champion", "--Select Baker--")
                sc_idx = admin_dropdown_options.index(s_sc) if s_sc in admin_dropdown_options else 0
                act_sc = st.selectbox("Actual Show Champion", admin_dropdown_options, index=sc_idx, disabled=(is_pub and not enable_edit))
                actuals["show_champion"] = act_sc if not act_sc.startswith("--Select") else "None"
                
                st.write("Actual Technical Challenge Rankings:")
                s_tr = saved_act.get("tech_rank", [])
                t1_idx = admin_dropdown_options.index(s_tr[0]) if len(s_tr) > 0 and s_tr[0] in admin_dropdown_options else 0
                t2_idx = admin_dropdown_options.index(s_tr[1]) if len(s_tr) > 1 and s_tr[1] in admin_dropdown_options else 0
                t3_idx = admin_dropdown_options.index(s_tr[2]) if len(s_tr) > 2 and s_tr[2] in admin_dropdown_options else 0
                
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_dropdown_options, index=t1_idx, disabled=(is_pub and not enable_edit))
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_dropdown_options, index=t2_idx, disabled=(is_pub and not enable_edit))
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_dropdown_options, index=t3_idx, disabled=(is_pub and not enable_edit))
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    s_sb = saved_act.get("star_baker", "--Select Baker--")
                    sb_idx = admin_dropdown_options.index(s_sb) if s_sb in admin_dropdown_options else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_options, index=sb_idx, disabled=(is_pub and not enable_edit))
                    
                    s_in_line = [b for b in saved_act.get("in_line_sb", []) if b in admin_active_bakers]
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, default=s_in_line, disabled=(is_pub and not enable_edit))
                with col2:
                    s_elim = saved_act.get("eliminated", "None")
                    s_trouble = [b for b in saved_act.get("in_trouble", []) if b in admin_active_bakers]
                    
                    if elim_type == "Single Elimination":
                        s_el_str = s_elim if isinstance(s_elim, str) else "--Select Baker--"
                        el_idx = admin_dropdown_options.index(s_el_str) if s_el_str in admin_dropdown_options else 0
                        act_el = st.selectbox("Actual Eliminated Baker", admin_dropdown_options, index=el_idx, disabled=(is_pub and not enable_edit), key=f"act_elim_single_w{admin_selected_week}")
                        actuals["eliminated"] = act_el if not act_el.startswith("--Select") else "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=s_trouble, disabled=(is_pub and not enable_edit))
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("ℹ️ No baker was eliminated this week (Grace Week).")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=s_trouble, disabled=(is_pub and not enable_edit))
                    else:
                        s_e1 = s_elim[0] if isinstance(s_elim, list) and len(s_elim) > 0 else "--Select Baker--"
                        s_e2 = s_elim[1] if isinstance(s_elim, list) and len(s_elim) > 1 else "--Select Baker--"
                        e1_idx = admin_dropdown_options.index(s_e1) if s_e1 in admin_dropdown_options else 0
                        e2_idx = admin_dropdown_options.index(s_e2) if s_e2 in admin_dropdown_options else 0
                        
                        act_e1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_options, index=e1_idx, disabled=(is_pub and not enable_edit), key=f"act_e1_dbl_w{admin_selected_week}")
                        act_e2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_options, index=e2_idx, disabled=(is_pub and not enable_edit), key=f"act_e2_dbl_w{admin_selected_week}")
                        actuals["eliminated"] = [b for b in [act_e1, act_e2] if not b.startswith("--Select")]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=s_trouble, disabled=(is_pub and not enable_edit))
                    
                st.write(f"Actual Technical Challenge Placement (All {len(admin_active_bakers)} Bakers):")
                tech_positions = []
                s_tr_list = saved_act.get("tech_rank", [])
                for idx, _ in enumerate(admin_active_bakers):
                    pos_name = f"Technical Position #{idx+1}"
                    if idx == 0: pos_name += " (1st Place)"
                    elif idx == len(admin_active_bakers) - 1: pos_name += f" ({idx+1}th / Last Place)"
                    
                    s_pos_baker = s_tr_list[idx] if idx < len(s_tr_list) else "--Select Baker--"
                    p_idx = admin_dropdown_options.index(s_pos_baker) if s_pos_baker in admin_dropdown_options else 0
                    t_val = st.selectbox(pos_name, admin_dropdown_options, index=p_idx, disabled=(is_pub and not enable_edit), key=f"admin_pos_{idx}_w{admin_selected_week}")
                    tech_positions.append(t_val)
                    
                actuals["tech_rank"] = [b for b in tech_positions if not b.startswith("--Select")]

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            s_hs_cnt = saved_act.get("handshake_count", 0)
            s_hs_stamps = saved_act.get("handshake_timestamps", "")
            s_hs_bakers = [b for b in saved_act.get("handshake_bakers", []) if b in admin_active_bakers]
            
            with col_hs1:
                act_handshake_cnt = st.number_input("Number of Handshakes", min_value=0, value=s_hs_cnt, disabled=(is_pub and not enable_edit), key=f"adm_hs_cnt_w{admin_selected_week}")
            with col_hs2:
                act_handshake_stamps = st.text_input("Handshake Timestamps & Context", value=s_hs_stamps, disabled=(is_pub and not enable_edit), key=f"adm_hs_stamps_w{admin_selected_week}")
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", admin_active_bakers, default=s_hs_bakers, disabled=(is_pub and not enable_edit), key=f"adm_hs_bakers_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            s_cry_cnt = saved_act.get("crying_count", 0)
            s_cry_stamps = saved_act.get("crying_timestamps", "")
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Incidents", min_value=0, value=s_cry_cnt, disabled=(is_pub and not enable_edit), key=f"adm_cry_cnt_w{admin_selected_week}")
            with col_cry2:
                act_crying_stamps = st.text_input("Crying Timestamps & Context", value=s_cry_stamps, disabled=(is_pub and not enable_edit), key=f"adm_cry_stamps_w{admin_selected_week}")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            s_inn_cnt = saved_act.get("innuendo_count", 0)
            s_inn_stamps = saved_act.get("innuendo_timestamps", "")
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Innuendos", min_value=0, value=s_inn_cnt, disabled=(is_pub and not enable_edit), key=f"adm_inn_cnt_w{admin_selected_week}")
            with col_inn2:
                act_innuendo_stamps = st.text_input("Innuendo Timestamps & Context", value=s_inn_stamps, disabled=(is_pub and not enable_edit), key=f"adm_inn_stamps_w{admin_selected_week}")

            actuals["handshake_count"] = act_handshake_cnt
            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            actuals["innuendo_timestamps"] = act_innuendo_stamps

            btn_label = "Update & Recalculate Saved Results" if is_pub else "Publish Official Week Results & Recalculate Standings"
            submit_admin = st.form_submit_button(btn_label, disabled=(is_pub and not enable_edit))
            
            if submit_admin:
                if is_pub and not enable_edit:
                    st.error("🔒 Overwrite Blocked: Please check 'Enable Editing' above before saving changes!")
                else:
                    st.session_state.weekly_results[admin_selected_week] = actuals
                    
                    for m_name in ALL_HUMANS_AND_AI:
                        st.session_state.league_members[m_name]["total_score"] = 0
                        st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                        
                    for w_num, w_act in st.session_state.weekly_results.items():
                        w_num_int = int(w_num)
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
                    st.success(f"🎉 Official Week {admin_selected_week} results saved! Standings recalculated.")

        # --- DISPUTE RESOLUTION CONSOLE ---
        st.markdown("---")
        st.subheader("⚖️ Dispute Resolution & Management Console")
        if not st.session_state.disputes:
            st.info("No active result disputes logged by league members.")
        else:
            disp_options = [f"#{idx+1}: {d['Player']} - {d['Week']} ({d['Category']})" for idx, d in enumerate(st.session_state.disputes)]
            sel_disp_idx = st.selectbox("Select Dispute to Resolve:", range(len(disp_options)), format_func=lambda i: disp_options[i], key="admin_disp_sel")
            
            target_disp = st.session_state.disputes[sel_disp_idx]
            st.write(f"**Submitted By:** {target_disp['Player']} | **Week:** {target_disp['Week']} | **Category:** {target_disp['Category']}")
            st.write(f"**Evidence:** {target_disp['Evidence']}")
            st.write(f"**Requested Correction:** {target_disp['Correction']}")
            
            col_res1, col_col2 = st.columns(2)
            with col_res1:
                new_status = st.selectbox("Update GroupMe Vote Resolution:", ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"], key=f"disp_status_{sel_disp_idx}")
                if st.button("Save Dispute Resolution"):
                    st.session_state.disputes[sel_disp_idx]["Status"] = new_status
                    save_league_data()
                    st.success(f"Dispute status updated to '{new_status}'!")
                    st.rerun()
            with col_col2:
                if st.button("Delete Dispute Entry"):
                    st.session_state.disputes.pop(sel_disp_idx)
                    save_league_data()
                    st.success("Dispute deleted from active log.")
                    st.rerun()

        # --- PLAYER PIN RESET CONSOLE ---
        st.markdown("---")
        st.subheader("🔑 Player Security PIN Management & Reset")
        pin_reset_player = st.selectbox("Select Player Profile to Reset Password PIN:", ROSTER_HUMANS, key="pin_reset_sel")
        if st.button("Reset Player PIN"):
            if pin_reset_player in st.session_state.player_pins:
                del st.session_state.player_pins[pin_reset_player]
                save_league_data()
                st.success(f"✅ Security PIN reset for {pin_reset_player}. They can now create a new PIN.")
            else:
                st.info(f"{pin_reset_player} does not have an active PIN set.")

        # --- ERASE ALL COMPETITION DATA ---
        st.markdown("---")
        st.subheader("🚨 Erase All Competition Data")
        st.write("Wipe all test predictions, weekly broadcast actuals, disputes, and player PINs back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player PINs", key="confirm_erase_data_chk")
        if st.button("Erase All Saved League Data", type="primary"):
            if confirm_erase:
                if os.path.exists(DATA_FILE):
                    try:
                        os.remove(DATA_FILE)
                    except Exception:
                        pass
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                st.session_state.player_pins = {}
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["weekly_picks"] = {}
                    st.session_state.league_members[m_name]["season_picks"] = {}
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                
                save_league_data()
                st.session_state.data_erased_confirmation = "✅ All competition data, predictions, broadcast actuals, disputes, and player PINs have been permanently erased!"
                st.rerun()
            else:
                st.error("Please check the confirmation box above first.")
