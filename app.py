import os
import streamlit as st
import pandas as pd
import random
from PIL import Image
import io

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for cozy baking theme
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

# --- 2. GLOBAL CONSTANTS & ROSTER ---
ROSTER_ALPHABETICAL = [
    "AI Brian", "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", 
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ALL_HUMAN_PLAYERS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", 
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ALL_LEAGUE_MEMBERS = [
    "AI Brian", "Ana", "Becca", "Brian", "Cassie", 
    "Emma", "Gisselle", "Jasmine", "Jennifer", "Mark", 
    "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

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

def get_current_eliminated_bakers(week):
    return eliminated_bakers_by_week.get(week, [])

# --- 3. SESSION STATE INITIALIZATION ---
if "league_members" not in st.session_state:
    st.session_state.league_members = {
        member: {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "season_score": 0,
            "pin": None
        }
        for member in ROSTER_ALPHABETICAL
    }

if "player_passwords" not in st.session_state:
    st.session_state.player_passwords = {}

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "current_week" not in st.session_state:
    st.session_state.current_week = 2

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

# --- 4. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    if week == 10:
        p_c = predictions.get("show_champion")
        a_c = actuals.get("show_champion")
        if p_c and a_c and p_c == a_c and not str(p_c).startswith("-- Select"):
            score += 15
    else:
        p_sb = predictions.get("star_baker")
        a_sb = actuals.get("star_baker")
        if p_sb and a_sb and p_sb == a_sb and not str(p_sb).startswith("-- Select"):
            score += 5
        
        p_el = predictions.get("eliminated")
        a_el = actuals.get("eliminated")
        if a_el == "None":
            pass
        else:
            if isinstance(a_el, list):
                if isinstance(p_el, list):
                    for p in p_el:
                        if p in a_el and not str(p).startswith("-- Select"):
                            score += 5
                elif isinstance(p_el, str):
                    if p_el in a_el and not str(p_el).startswith("-- Select"):
                        score += 5
            else:
                if isinstance(p_el, list):
                    if a_el in p_el and not str(a_el).startswith("-- Select"):
                        score += 5
                elif p_el == a_el and p_el and not str(p_el).startswith("-- Select"):
                    score += 5
                    
    if week >= 8:
        p_rank = predictions.get("tech_rank", [])
        a_rank = actuals.get("tech_rank", [])
        clean_p = [b for b in p_rank if b and not str(b).startswith("-- Select")]
        clean_a = [b for b in a_rank if b and not str(b).startswith("-- Select")]
        
        if clean_p and clean_a and len(clean_p) == len(clean_a):
            if clean_p == clean_a:
                sweep_pts = {8: 25, 9: 20, 10: 15}
                score += sweep_pts.get(week, 15)
            else:
                for idx, b in enumerate(clean_p):
                    if clean_a[idx] == b:
                        p_val = 3 if idx in [0, len(clean_p)-1] else 2
                        score += p_val
    else:
        p_top3 = [b for b in predictions.get("tech_top_3", []) if b and not str(b).startswith("-- Select")]
        a_top3 = [b for b in actuals.get("tech_top_3", []) if b and not str(b).startswith("-- Select")]
        if len(p_top3) == 3 and len(a_top3) == 3:
            if p_top3 == a_top3:
                score += 10
            else:
                if p_top3 == a_top3: score += 3
                if p_top3 == a_top3: score += 2
                if p_top3 == a_top3: score += 2
                for idx, baker in enumerate(p_top3):
                    if baker in a_top3 and baker != a_top3[idx]:
                        score += 1
                        
        p_bot3 = [b for b in predictions.get("tech_bottom_3", []) if b and not str(b).startswith("-- Select")]
        a_bot3 = [b for b in actuals.get("tech_bottom_3", []) if b and not str(b).startswith("-- Select")]
        if len(p_bot3) == 3 and len(a_bot3) == 3:
            if p_bot3 == a_bot3:
                score += 10
            else:
                if p_bot3 == a_bot3: score += 2
                if p_bot3 == a_bot3: score += 2
                if p_bot3 == a_bot3: score += 3
                for idx, baker in enumerate(p_bot3):
                    if baker in a_bot3 and baker != a_bot3[idx]:
                        score += 1
                        
    if week < 9:
        p_in_line = predictions.get("in_line_sb")
        a_in_line = actuals.get("in_line_sb", [])
        a_sb = actuals.get("star_baker")
        if p_in_line and not str(p_in_line).startswith("-- Select"):
            if p_in_line in a_in_line and p_in_line != a_sb:
                score += 2
                
        p_in_tr = predictions.get("in_trouble")
        a_in_tr = actuals.get("in_trouble", [])
        if p_in_tr and not str(p_in_tr).startswith("-- Select"):
            if p_in_tr in a_in_tr:
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
        if p_hs == a_hs:
            score += 20
        elif abs(p_hs - a_hs) <= 1:
            score += 10
            
    p_cry = predictions.get("crying")
    a_cry = actuals.get("crying")
    if p_cry is not None and a_cry is not None:
        if p_cry == a_cry:
            score += 20
        elif abs(p_cry - a_cry) <= 5:
            score += 10
            
    p_inn = predictions.get("innuendos")
    a_inn = actuals.get("innuendos")
    if p_inn is not None and a_inn is not None:
        if p_inn == a_inn:
            score += 20
        elif abs(p_inn - a_inn) <= 5:
            score += 10
            
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
                try:
                    return Image.open(full_path)
                except Exception:
                    pass
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
        if is_double_elim:
            el_pool = [b for b in active_bakers if b != sb]
            elim = random.sample(el_pool, min(2, len(el_pool)))
        else:
            elim = random.choice([b for b in active_bakers if b != sb]) if len(active_bakers) > 1 else active_bakers
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": sb, "eliminated": elim, "tech_rank": tech_rank}
    elif week == 8:
        sb = random.choice(active_bakers)
        if is_double_elim:
            el_pool = [b for b in active_bakers if b != sb]
            elim = random.sample(el_pool, min(2, len(el_pool)))
        else:
            elim = random.choice([b for b in active_bakers if b != sb]) if len(active_bakers) > 1 else active_bakers
        in_line = random.choice([b for b in active_bakers if b != sb]) if len(active_bakers) > 1 else active_bakers
        in_tr_pool = [b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])]
        in_tr = random.choice(in_tr_pool) if in_tr_pool else active_bakers
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": sb, "eliminated": elim, "tech_rank": tech_rank, "in_line_sb": in_line, "in_trouble": in_tr}
    else:
        sb = random.choice(active_bakers)
        if is_double_elim:
            el_pool = [b for b in active_bakers if b != sb]
            elim = random.sample(el_pool, min(2, len(el_pool)))
        else:
            elim = random.choice([b for b in active_bakers if b != sb]) if len(active_bakers) > 1 else active_bakers
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bot = [b for b in active_bakers if b not in tech_top_3]
        tech_bot_3 = random.sample(rem_bot, min(3, len(rem_bot))) if rem_bot else []
        in_line = random.choice([b for b in active_bakers if b != sb]) if len(active_bakers) > 1 else active_bakers
        in_tr_pool = [b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])]
        in_tr = random.choice(in_tr_pool) if in_tr_pool else active_bakers
        return {
            "star_baker": sb, "eliminated": elim, "tech_top_3": tech_top_3, "tech_bottom_3": tech_bot_3,
            "in_line_sb": in_line, "in_trouble": in_tr
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

def get_filtered_tech_options(active_bakers, key_prefix, current_key, placeholder="-- Select Baker --"):
    options = [placeholder] + active_bakers
    curr_val = st.session_state.get(current_key)
    if curr_val in options:
        idx = options.index(curr_val)
    else:
        idx = 0
    return options, idx

# --- 5. HEADER ---
col_head1, col_head2 = st.columns()
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

# --- SIDEBAR ---
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
        * **Top 3 Technical Challenge:** Exact: 1st=3pts, 2nd/3rd=2pts; Wrong Spot=1pt; Combo Sweep=10pts flat
        * **Bottom 3 Technical Challenge:** Exact: 9th=2pts, 10th=2pts, 11th=3pts; Wrong Spot=1pt; Combo Sweep=10pts flat
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)

    with st.expander("🏁 Weeks 8, 9 & 10 (Dynamic Scaling)", expanded=False):
        st.markdown("""
        * **Week 8 (Quarterfinal episodic - 5 bakers):** Star Baker=5pts, Eliminated=5pts, Technical Exact=1st/5th(3pts), 2nd-4th(2pts), Perfect Sweep=25pts flat
        * **Week 9 (Semifinal episodic - 4 bakers):** Star Baker=5pts, Eliminated=5pts, Technical Exact=1st/4th(3pts), 2nd-3rd(2pts), Perfect Sweep=20pts flat
        * **Week 10 (Grand Finale episodic - 3 bakers):** Show Champion=15pts, Technical Exact=1st(3pts), 2nd-3rd(2pts), Perfect Sweep=15pts flat
        """)

# --- MAIN TABS ---
tab_lead, tab_submit, tab_show_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📺 Show Results", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS (ONLY LEADERBOARD & PLAYER SCORECARDS) ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_data = []
    for name, data in st.session_state.league_members.items():
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

    # Individual Player Scorecards
    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards")
    
    selected_sc_player = st.selectbox("Select Player to View Scorecard:", ALL_LEAGUE_MEMBERS, index=0)
    if selected_sc_player:
        p_data = st.session_state.league_members[selected_sc_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### 👤 **{selected_sc_player}'s Scorecard** — Total Score: `{p_pts} pts`")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("#### **🌟 Season-Long Projections**")
            win_pick = p_season.get("winner", "Not submitted yet")
            semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
            hs_pick = p_season.get("handshakes", "N/A")
            cry_pick = p_season.get("crying", "N/A")
            inn_pick = p_season.get("innuendos", "N/A")
            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🏅 **Predicted Other Semifinalists:** {semis_pick}")
            st.write(f"🤝 **Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        with col_s2:
            st.markdown("#### **📅 Weekly Predictions Log**")
            if p_weekly:
                for w_num in sorted(p_weekly.keys()):
                    w_picks = p_weekly[w_num]
                    w_score = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                    with st.expander(f"Week {w_num} Picks ({w_score} pts earned)", expanded=False):
                        st.json(w_picks)
            else:
                st.info(f"No weekly predictions logged for {selected_sc_player} yet.")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions Ballot")
    
    # Week 1 results requirement check
    if 1 not in st.session_state.weekly_results:
        st.info("⏰ **Week 2 ballots will become available after the Week 1 results are posted by the League Administrator.**")
        st.warning("📢 Week 1 is the Scouting Phase! No predictions are submitted for Episode 1.")
    else:
        # Determine active prediction week based on published results
        latest_published = max(st.session_state.weekly_results.keys())
        active_pred_week = min(latest_published + 1, 10)
        st.session_state.current_week = active_pred_week
        
        st.subheader(f"📅 Unlocked Ballot: Week {st.session_state.current_week}")
        
        submitting_player = st.selectbox("Select Your Player Profile:", ALL_HUMAN_PLAYERS, key="submit_player_profile_select")
        saved_pwd = st.session_state.player_passwords.get(submitting_player)
        authenticated = False
        
        if saved_pwd is None:
            st.info(f"Welcome, **{submitting_player}**! Create a 4-digit PIN password to secure your prediction ballot.")
            with st.form(f"form_create_pin_{submitting_player}"):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    new_p1 = st.text_input("Create 4-Digit PIN", type="password", max_chars=4, key=f"create_p1_{submitting_player}")
                with col_p2:
                    new_p2 = st.text_input("Confirm 4-Digit PIN", type="password", max_chars=4, key=f"create_p2_{submitting_player}")
                btn_create_pin = st.form_submit_button("Set 4-Digit PIN & Unlock Ballot")
                if btn_create_pin:
                    if len(new_p1) != 4 or not new_p1.isdigit():
                        st.error("PIN must be exactly 4 numeric digits!")
                    elif new_p1 != new_p2:
                        st.error("PINs do not match! Please check and try again.")
                    else:
                        st.session_state.player_passwords[submitting_player] = new_p1
                        st.success(f"PIN created successfully for {submitting_player}! Your ballot is unlocked.")
                        st.rerun()
        else:
            with st.form(f"form_login_pin_{submitting_player}"):
                entered_pwd = st.text_input("Enter Your 4-Digit PIN Password", type="password", max_chars=4, key=f"login_pwd_{submitting_player}")
                btn_login_pin = st.form_submit_button("Submit Password / Unlock Ballot")
                if btn_login_pin:
                    if entered_pwd == saved_pwd:
                        st.session_state.authenticated_players[submitting_player] = True
                        st.success(f"🔓 Authenticated as **{submitting_player}**!")
                    else:
                        st.error("❌ Incorrect 4-digit PIN! Please try again or ask the Admin to reset your password.")
            
            if st.session_state.authenticated_players.get(submitting_player, False):
                authenticated = True

        if authenticated:
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
                            st.info(f"📸 Photograph of {baker}")
                            st.markdown(f"[🔗 View {baker}'s Show Profile]({info['url']})")
                        st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("---")
            st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
            
            current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            baker_options = ["-- Select Baker --"] + active_bakers
            
            prev_week_num = st.session_state.current_week - 1
            prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
            prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
            
            st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
            
            is_double_elim = False
            if st.session_state.current_week < 10:
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)
            
            # Season long entry if week is 2
            if st.session_state.current_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_options, key="user_win_pick")
                    user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", active_bakers, default=[], placeholder="-- Select 3 Semifinalists --", max_selections=3, key="user_semis_pick")
                    
                    user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key="user_hs_pick")
                    user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key="user_cry_pick")
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=None, placeholder="Enter predicted count...", key="user_inn_pick")
                    
                    if st.button("Lock Season-Long Predictions"):
                        if user_winner.startswith("-- Select") or len(user_semis) != 3 or user_handshakes is None or user_crying is None or user_innuendos is None:
                            st.error("⚠️ Please fill in all Season-Long prediction fields with valid values!")
                        elif user_winner in user_semis:
                            st.error("❌ Duplicate Selection Error: Your predicted Season Winner cannot also be selected as an 'Other Semifinalist'!")
                        else:
                            st.session_state.league_members[submitting_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                            st.success(f"Season-long predictions saved for {submitting_player}!")

            # Weekly Form
            st.markdown("### Weekly Ballot")
            with st.form(f"weekly_predictions_form_{submitting_player}_w{st.session_state.current_week}"):
                weekly_picks = {}
                
                if st.session_state.current_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_options, key="w10_champ")
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place", baker_options, key="w10_t1")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, key="w10_t2")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, key="w10_t3")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                elif st.session_state.current_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="w9_sb")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="w9_e1")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="w9_e2")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w9_el")
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place", baker_options, key="w9_t1")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, key="w9_t2")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, key="w9_t3")
                    t4 = st.selectbox("Technical 4th Place", baker_options, key="w9_t4")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]
                elif st.session_state.current_week == 8:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="w8_sb")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="w8_inline")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="w8_e1")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="w8_e2")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w8_el")
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="w8_trouble")
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place", baker_options, key="w8_t1")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, key="w8_t2")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, key="w8_t3")
                    t4 = st.selectbox("Technical 4th Place", baker_options, key="w8_t4")
                    t5 = st.selectbox("Technical 5th Place", baker_options, key="w8_t5")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                else:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="std_sb")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="std_inline")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="std_e1")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="std_e2")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="std_el")
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="std_trouble")
                    
                    st.write("Predict Top 3 Technical Challenge Placements:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="std_t1")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="std_t2")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="std_t3")
                    weekly_picks["tech_top_3"] = [t1, t2, t3]
                    
                    st.write("Predict Bottom 3 Technical Challenge Placements:")
                    b3 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_options, key="std_b3")
                    b2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_options, key="std_b2")
                    b1 = st.selectbox("Technical Last Place [3 pts]", baker_options, key="std_b1")
                    weekly_picks["tech_bottom_3"] = [b3, b2, b1]
                    
                submit_ballot = st.form_submit_button("Lock In Weekly Predictions Ballot")
                if submit_ballot:
                    all_selected_values = []
                    for k, v in weekly_picks.items():
                        if isinstance(v, list):
                            all_selected_values.extend(v)
                        else:
                            all_selected_values.append(v)
                            
                    if "-- Select Baker --" in all_selected_values:
                        st.error("⚠️ Please select a valid baker for all prediction fields!")
                    else:
                        episodic_picks = []
                        for k in ["star_baker", "in_line_sb", "in_trouble", "show_champion"]:
                            if k in weekly_picks: episodic_picks.append(weekly_picks[k])
                        if "eliminated" in weekly_picks:
                            if isinstance(weekly_picks["eliminated"], list):
                                episodic_picks.extend(weekly_picks["eliminated"])
                            else:
                                episodic_picks.append(weekly_picks["eliminated"])
                                
                        tech_picks = []
                        if "tech_rank" in weekly_picks: tech_picks.extend(weekly_picks["tech_rank"])
                        if "tech_top_3" in weekly_picks: tech_picks.extend(weekly_picks["tech_top_3"])
                        if "tech_bottom_3" in weekly_picks: tech_picks.extend(weekly_picks["tech_bottom_3"])
                        
                        has_episodic_dup = len(episodic_picks) != len(set(episodic_picks))
                        has_tech_dup = len(tech_picks) != len(set(tech_picks))
                        
                        if has_episodic_dup:
                            st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                        elif has_tech_dup:
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            st.session_state.league_members[submitting_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                            st.success(f"Predictions successfully submitted for {submitting_player} (Week {st.session_state.current_week})!")

# --- TAB 3: SHOW RESULTS (CHAOS TOTALS AT TOP, WEEKLY RESULTS, AUDIT & DISPUTES) ---
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # 1. CHAOS CATEGORIES RUNNING TOTALS (AT TOP OF SHOW RESULTS TAB)
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    for w_num, w_act in st.session_state.weekly_results.items():
        tot_hs += w_act.get("handshakes", 0) or 0
        tot_cry += w_act.get("crying_count", 0) or 0
        tot_inn += w_act.get("innuendo_count", 0) or 0

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Total Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Total Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Total Sexual Innuendos", f"{tot_inn}")

    st.markdown("---")
    
    # 2. WEEKLY SHOW RESULTS (DETAILED WEEK-BY-WEEK BREAKDOWN)
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
                    if isinstance(in_line_val, list):
                        in_line_str = ", ".join(in_line_val) if in_line_val else "None"
                    else:
                        in_line_str = str(in_line_val)
                    st.write(f"🎖️ **In Line for Star Baker:** {in_line_str}")
                    
                    elim_val = w_act.get("eliminated", "None")
                    if isinstance(elim_val, list):
                        elim_str = ", ".join(elim_val) if elim_val else "None (Sickness Grace Week)"
                    else:
                        elim_str = str(elim_val)
                    st.write(f"🚪 **Eliminated Baker:** {elim_str}")
                    
                    in_tr_val = w_act.get("in_trouble", [])
                    if isinstance(in_tr_val, list):
                        in_tr_str = ", ".join(in_tr_val) if in_tr_val else "None"
                    else:
                        in_tr_str = str(in_tr_val)
                    st.write(f"⚠️ **In Trouble of Elimination:** {in_tr_str}")
                    
                with col_w2:
                    st.markdown("#### **🔥 Chaos Metrics & Descriptions**")
                    hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                    hs_cnt = w_act.get("handshakes", 0)
                    st.write(f"🤝 **Handshakes ({hs_cnt}):** {hs_bakers}")
                    
                    cry_cnt = w_act.get("crying_count", 0)
                    cry_stamps = w_act.get("crying_timestamps", "None")
                    st.write(f"😢 **Crying Incidents ({cry_cnt}):** {cry_stamps}")
                    
                    inn_cnt = w_act.get("innuendo_count", 0)
                    inn_stamps = w_act.get("innuendo_timestamps", "None")
                    st.write(f"💬 **Sexual Innuendos ({inn_cnt}):** {inn_stamps}")
                
                # Technical Challenge Placement
                tech_ranks = w_act.get("tech_rank", [])
                if tech_ranks:
                    st.markdown("#### **📊 Technical Challenge Placements**")
                    tech_items = [f"**{idx+1}st**" if idx==0 else (f"**{idx+1}nd**" if idx==1 else (f"**{idx+1}rd**" if idx==2 else f"**{idx+1}th**")) + f": {baker}" for idx, baker in enumerate(tech_ranks)]
                    st.write(" | ".join(tech_items))

    # 3. BROADCAST AUDIT TABLE & VIDEO TIMESTAMPS
    st.markdown("---")
    st.subheader("📋 Broadcast Audit Summary Table")
    if st.session_state.weekly_results:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            cry_cnt = w_act.get("crying_count", 0)
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"
            
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshakes', 0)} ({hs_bakers})",
                "Crying Incidents": f"{cry_cnt} ({cry_stamps})",
                "Sexual Innuendos": f"{inn_cnt} ({inn_stamps})"
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

    # 4. BROADCAST RESULT DISPUTES & TIMESTAMP CORRECTIONS
    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")
    
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ALL_HUMAN_PLAYERS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 2"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Evidence (e.g., 'At 28:14 in Episode 3, Paul clearly shakes Tom's hand')")
            disp_correction = st.text_input("Requested Correction (e.g., 'Add +1 Handshake for Tom in Week 3')")
            sub_disp = st.form_submit_button("Submit Dispute for League Vote")
            if sub_disp:
                st.session_state.disputes.append({
                    "Player": disp_player, "Week": disp_week, "Category": disp_cat,
                    "Evidence": disp_evidence, "Correction": disp_correction, "Status": "Pending GroupMe Vote 🗳️"
                })
                st.success("Dispute submitted successfully!")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Lock Screen**")
        with st.form("admin_login_form"):
            pin_input = st.text_input("Enter Admin PIN", type="password")
            login_btn = st.form_submit_button("Unlock Admin Panel")
            if login_btn:
                if pin_input == "6284":
                    st.session_state.admin_authenticated = True
                    st.success("Admin PIN verified! Unlocking console...")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again.")
    else:
        st.success("🔓 **Authenticated as League Administrator**")
        if st.button("🔒 Lock Console Session"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.markdown("---")
        with st.expander("🔑 Player Security PIN Management & Reset", expanded=False):
            p_to_reset = st.selectbox("Select Player Profile to Reset Password PIN:", ["-- Select Player --"] + ALL_HUMAN_PLAYERS)
            if p_to_reset != "-- Select Player --":
                cur_p_pwd = st.session_state.player_passwords.get(p_to_reset)
                cur_status = "Locked 🔒" if cur_p_pwd else "Unset 🔓"
                st.write(f"Current PIN Status for **{p_to_reset}**: `{cur_status}`")
                if st.button(f"Reset Password PIN for {p_to_reset}"):
                    st.session_state.player_passwords[p_to_reset] = None
                    if p_to_reset in st.session_state.authenticated_players:
                        st.session_state.authenticated_players[p_to_reset] = False
                    st.success(f"Security PIN reset for {p_to_reset}!")
                    st.rerun()

        st.markdown("---")
        with st.expander("🗑️ Reset All Competition Data", expanded=False):
            st.warning("⚠️ **Danger Zone:** Clearing competition data will permanently wipe all recorded weekly broadcast results, season results, player prediction ballots, and dispute logs!")
            confirm_reset = st.checkbox("I understand that this will erase all competition data across all weeks.", key="confirm_reset_data_check")
            if st.button("🗑️ Erase All Competition Data", type="primary", disabled=not confirm_reset):
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                st.session_state.current_week = 2
                
                for member_name in st.session_state.league_members:
                    st.session_state.league_members[member_name]["weekly_picks"] = {}
                    st.session_state.league_members[member_name]["season_picks"] = {}
                    st.session_state.league_members[member_name]["total_score"] = 0
                    st.session_state.league_members[member_name]["season_score"] = 0
                    st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                    st.session_state.league_members[member_name]["pin"] = None
                
                st.success("All competition data has been completely reset!")
                st.rerun()

        st.markdown("---")
        st.subheader("📅 Select Broadcast Episode Week")
        st.write("Select week to input new results or review/edit previously saved results:")
        
        admin_selected_week = st.selectbox(
            "Select Week to Record or Review Broadcast Results:",
            [f"Week {w}" for w in range(1, 11)],
            index=min(st.session_state.current_week - 1, 9),
            key="admin_selected_week_dropdown"
        )
        cur_w = int(admin_selected_week.replace("Week ", ""))
        
        current_eliminated = get_current_eliminated_bakers(cur_w)
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]

        saved_actuals = st.session_state.weekly_results.get(cur_w, {})
        is_already_published = cur_w in st.session_state.weekly_results

        if is_already_published:
            st.info(f"🟢 **Week {cur_w} Results Recorded & Saved in System**\n\nReviewing saved entries below. To prevent accidental edits that alter player scores, fields are locked by default.")
            enable_edit = st.checkbox(f"🔓 Enable Editing for Week {cur_w} (Requires Verification before Overwriting Saved Results)", key=f"unlock_edit_w{cur_w}")
        else:
            enable_edit = True

        with st.form(f"admin_actuals_form_w{cur_w}"):
            st.subheader(f"Input / Review Broadcast Results for Week {cur_w}")
            if is_already_published and not enable_edit:
                st.warning("🔒 **Saved Entry Protection Active:** Check the 'Enable Editing' box above to modify published results.")

            actuals = {}
            
            if cur_w == 10:
                opts_sc = ["-- Select Show Champion --"] + active_bakers
                saved_sc = saved_actuals.get("show_champion", "-- Select Show Champion --")
                sc_idx = opts_sc.index(saved_sc) if saved_sc in opts_sc else 0
                act_sc_sel = st.selectbox("Actual Show Champion", opts_sc, index=sc_idx, key=f"admin_act_sc_w10_{cur_w}", disabled=(is_already_published and not enable_edit))
                actuals["show_champion"] = act_sc_sel if not act_sc_sel.startswith("-- Select") else "None"
                
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                saved_season = st.session_state.season_results
                opts_win = ["-- Select Season Winner --"] + active_bakers
                saved_win = saved_season.get("winner", "-- Select Season Winner --")
                win_idx = opts_win.index(saved_win) if saved_win in opts_win else 0
                act_winner_sel = st.selectbox("Actual Season Winner (Show Champion)", opts_win, index=win_idx, key=f"act_w10_winner_{cur_w}", disabled=(is_already_published and not enable_edit))
                act_winner = act_winner_sel if not act_winner_sel.startswith("-- Select") else "None"
                
                saved_semis = [b for b in saved_season.get("semifinalists", []) if b in ALL_BAKERS]
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, default=saved_semis, placeholder="-- Select 4 Semifinalists --", key=f"act_w10_semis_{cur_w}", disabled=(is_already_published and not enable_edit))
                
                saved_finalists = [b for b in saved_season.get("finalists", []) if b in ALL_BAKERS]
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, default=saved_finalists, placeholder="-- Select 3 Finalists --", key=f"act_w10_finalists_{cur_w}", disabled=(is_already_published and not enable_edit))
                
                saved_hs_tot = saved_season.get("handshakes")
                act_handshakes = st.number_input("Actual Total Handshakes across Season", min_value=0, value=saved_hs_tot, placeholder="Enter total count...", key=f"act_w10_hs_{cur_w}", disabled=(is_already_published and not enable_edit))
                
                saved_cry_tot = saved_season.get("crying")
                act_crying = st.number_input("Actual Total Crying Scenes across Season", min_value=0, value=saved_cry_tot, placeholder="Enter total count...", key=f"act_w10_cry_{cur_w}", disabled=(is_already_published and not enable_edit))
                
                saved_inn_tot = saved_season.get("innuendos")
                act_innuendos = st.number_input("Actual Total Sexual Innuendos across Season", min_value=0, value=saved_inn_tot, placeholder="Enter total count...", key=f"act_w10_inn_{cur_w}", disabled=(is_already_published and not enable_edit))
                actuals_season = {
                    "winner": act_winner, "semifinalists": act_semis, "finalists": act_finalists,
                    "handshakes": act_handshakes, "crying": act_crying, "innuendos": act_innuendos
                }
            elif cur_w == 9:
                opts_sb9 = ["-- Select Star Baker --"] + active_bakers
                saved_sb9 = saved_actuals.get("star_baker", "-- Select Star Baker --")
                sb9_idx = opts_sb9.index(saved_sb9) if saved_sb9 in opts_sb9 else 0
                act_sb9_sel = st.selectbox("Actual Star Baker", opts_sb9, index=sb9_idx, key=f"admin_act_sb_w9_{cur_w}", disabled=(is_already_published and not enable_edit))
                actuals["star_baker"] = act_sb9_sel if not act_sb9_sel.startswith("-- Select") else "None"
                
                saved_elim = saved_actuals.get("eliminated", "None")
                default_elim_type = "Single Elimination"
                if saved_elim == "None":
                    default_elim_type = "No Elimination (Sickness/Grace Week)"
                elif isinstance(saved_elim, list):
                    default_elim_type = "Double Elimination"
                
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], index=["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"].index(default_elim_type), horizontal=True, key=f"admin_elim_type_w9_{cur_w}", disabled=(is_already_published and not enable_edit))
                if elim_type == "Single Elimination":
                    opts_el9 = ["-- Select Eliminated Baker --"] + active_bakers
                    s_el9 = saved_elim if isinstance(saved_elim, str) else "-- Select Eliminated Baker --"
                    el9_idx = opts_el9.index(s_el9) if s_el9 in opts_el9 else 0
                    act_el9_sel = st.selectbox("Actual Eliminated Baker", opts_el9, index=el9_idx, key=f"admin_act_elim_w9_{cur_w}", disabled=(is_already_published and not enable_edit))
                    actuals["eliminated"] = act_el9_sel if not act_el9_sel.startswith("-- Select") else "None"
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    opts_el9_1 = ["-- Select Eliminated Baker #1 --"] + active_bakers
                    opts_el9_2 = ["-- Select Eliminated Baker #2 --"] + active_bakers
                    s_el1 = saved_elim if isinstance(saved_elim, list) and len(saved_elim) > 0 else "-- Select Eliminated Baker #1 --"
                    s_el2 = saved_elim if isinstance(saved_elim, list) and len(saved_elim) > 1 else "-- Select Eliminated Baker #2 --"
                    el1_idx = opts_el9_1.index(s_el1) if s_el1 in opts_el9_1 else 0
                    el2_idx = opts_el9_2.index(s_el2) if s_el2 in opts_el9_2 else 0
                    act_el9_1 = st.selectbox("Actual Eliminated Baker #1", opts_el9_1, index=el1_idx, key=f"admin_act_elim_1_w9_{cur_w}", disabled=(is_already_published and not enable_edit))
                    act_el9_2 = st.selectbox("Actual Eliminated Baker #2", opts_el9_2, index=el2_idx, key=f"admin_act_elim_2_w9_{cur_w}", disabled=(is_already_published and not enable_edit))
                    actuals["eliminated"] = [b for b in [act_el9_1, act_el9_2] if not b.startswith("-- Select")]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    opts_sb = ["-- Select Star Baker --", "None (No Star Baker)"] + active_bakers
                    saved_sb = saved_actuals.get("star_baker", "-- Select Star Baker --")
                    sb_idx = opts_sb.index(saved_sb) if saved_sb in opts_sb else 0
                    act_sb_sel = st.selectbox("Actual Star Baker", opts_sb, index=sb_idx, key=f"admin_act_sb_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    actuals["star_baker"] = act_sb_sel if act_sb_sel not in ["-- Select Star Baker --", "None (No Star Baker)"] else "None"
                    
                    saved_inline = [b for b in saved_actuals.get("in_line_sb", []) if b in active_bakers]
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, default=saved_inline, placeholder="-- Select Baker(s) --", key=f"admin_in_line_w{cur_w}", disabled=(is_already_published and not enable_edit))
                with col2:
                    saved_elim = saved_actuals.get("eliminated", "None")
                    default_elim_type = "Single Elimination"
                    if saved_elim == "None":
                        default_elim_type = "No Elimination (Sickness/Grace Week)"
                    elif isinstance(saved_elim, list):
                        default_elim_type = "Double Elimination"
                        
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], index=["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"].index(default_elim_type), horizontal=True, key=f"admin_elim_type_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    saved_trouble = [b for b in saved_actuals.get("in_trouble", []) if b in active_bakers]
                    if elim_type == "Single Elimination":
                        opts_el = ["-- Select Eliminated Baker --"] + active_bakers
                        s_el = saved_elim if isinstance(saved_elim, str) else "-- Select Eliminated Baker --"
                        el_idx = opts_el.index(s_el) if s_el in opts_el else 0
                        act_el_sel = st.selectbox("Actual Eliminated Baker", opts_el, index=el_idx, key=f"admin_act_elim_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        actuals["eliminated"] = act_el_sel if not act_el_sel.startswith("-- Select") else "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=saved_trouble, placeholder="-- Select Baker(s) --", key=f"admin_in_trouble_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, default=saved_trouble, placeholder="-- Select Baker(s) --", key=f"admin_in_trouble_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    else:
                        opts_el1 = ["-- Select Eliminated Baker #1 --"] + active_bakers
                        opts_el2 = ["-- Select Eliminated Baker #2 --"] + active_bakers
                        s_el1 = saved_elim if isinstance(saved_elim, list) and len(saved_elim) > 0 else "-- Select Eliminated Baker #1 --"
                        s_el2 = saved_elim if isinstance(saved_elim, list) and len(saved_elim) > 1 else "-- Select Eliminated Baker #2 --"
                        el1_idx = opts_el1.index(s_el1) if s_el1 in opts_el1 else 0
                        el2_idx = opts_el2.index(s_el2) if s_el2 in opts_el2 else 0
                        act_el1_sel = st.selectbox("Actual Eliminated Baker #1", opts_el1, index=el1_idx, key=f"admin_act_elim_1_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        act_el2_sel = st.selectbox("Actual Eliminated Baker #2", opts_el2, index=el2_idx, key=f"admin_act_elim_2_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        actuals["eliminated"] = [b for b in [act_el1_sel, act_el2_sel] if not b.startswith("-- Select")]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=saved_trouble, placeholder="-- Select Baker(s) --", key=f"admin_in_trouble_w{cur_w}", disabled=(is_already_published and not enable_edit))

            st.markdown("---")
            st.markdown(f"### 📊 Actual Technical Challenge Rankings (1st through {len(active_bakers)}th Place)")
            num_bakers = len(active_bakers)
            cols_per_row = 3
            admin_keys = [f"admin_full_tech_w{cur_w}_r{r}" for r in range(1, num_bakers + 1)]
            full_tech_ranks = []
            saved_tech_ranks = saved_actuals.get("tech_rank", [])
            
            for i in range(num_bakers):
                rank_num = i + 1
                ord_str = "1st" if rank_num == 1 else ("2nd" if rank_num == 2 else ("3rd" if rank_num == 3 else f"{rank_num}th"))
                if i % cols_per_row == 0:
                    t_cols = st.columns(min(cols_per_row, num_bakers - i))
                col = t_cols[i % cols_per_row]
                with col:
                    key_r = f"admin_full_tech_w{cur_w}_r{rank_num}"
                    placeholder = f"-- Select {ord_str} Place --"
                    saved_baker_for_pos = saved_tech_ranks[i] if i < len(saved_tech_ranks) else None
                    opts = [placeholder] + active_bakers
                    idx = opts.index(saved_baker_for_pos) if saved_baker_for_pos in opts else 0
                    sel_baker = st.selectbox(f"Actual Technical {ord_str} Place", opts, index=idx, key=key_r, disabled=(is_already_published and not enable_edit))
                    if sel_baker and not str(sel_baker).startswith("-- Select"):
                        full_tech_ranks.append(sel_baker)
                    else:
                        full_tech_ranks.append(None)

            cleaned_tech_ranks = [b for b in full_tech_ranks if b is not None]
            actuals["tech_rank"] = cleaned_tech_ranks
            if len(cleaned_tech_ranks) >= 3:
                actuals["tech_top_3"] = cleaned_tech_ranks[:3]
                actuals["tech_bottom_3"] = cleaned_tech_ranks[-3:]
            else:
                actuals["tech_top_3"] = cleaned_tech_ranks
                actuals["tech_bottom_3"] = cleaned_tech_ranks

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            saved_hs_bakers = [b for b in saved_actuals.get("handshake_bakers", []) if b in active_bakers]
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, default=saved_hs_bakers, placeholder="-- Select Baker(s) --", key=f"adm_hs_bakers_w{cur_w}", disabled=(is_already_published and not enable_edit))
            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshakes"] = len(act_handshake_bakers)

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            saved_cry_cnt = saved_actuals.get("crying_count")
            saved_cry_stamps = saved_actuals.get("crying_timestamps", "")
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Incidents in Episode", min_value=0, value=saved_cry_cnt, placeholder="Enter count...", key=f"crying_cnt_w{cur_w}", disabled=(is_already_published and not enable_edit))
            with col_cry2:
                act_crying_stamps = st.text_input("Descriptions & Video Timestamps", value=saved_cry_stamps, placeholder="e.g. 'Mo after technical @ 34:12'", key=f"crying_stamps_w{cur_w}", disabled=(is_already_published and not enable_edit))

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            saved_inn_cnt = saved_actuals.get("innuendo_count")
            saved_inn_stamps = saved_actuals.get("innuendo_timestamps", "")
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Sexual Innuendos in Episode", min_value=0, value=saved_inn_cnt, placeholder="Enter count...", key=f"innuendo_cnt_w{cur_w}", disabled=(is_already_published and not enable_edit))
            with col_inn2:
                act_innuendo_stamps = st.text_input("Descriptions & Video Timestamps", value=saved_inn_stamps, placeholder="e.g. 'Paul soggy bottom comment @ 18:05'", key=f"innuendo_stamps_w{cur_w}", disabled=(is_already_published and not enable_edit))

            actuals["crying_count"] = act_crying_cnt or 0
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt or 0
            actuals["innuendo_timestamps"] = act_innuendo_stamps

            btn_label = "Update & Recalculate Saved Results" if is_already_published else "Publish Actual Results & Recalculate Standings"
            submit_actuals = st.form_submit_button(btn_label, disabled=(is_already_published and not enable_edit))
            if submit_actuals:
                if is_already_published and not enable_edit:
                    st.error("🔒 Overwrite Blocked: You must check the 'Enable Editing' verification box above before saving changes to a published week!")
                elif len(actuals.get("tech_rank", [])) < len(active_bakers):
                    st.error(f"⚠️ Please select a baker for all {len(active_bakers)} Technical Challenge ranks before publishing!")
                else:
                    st.session_state.weekly_results[cur_w] = actuals
                    if cur_w == 10:
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

                    st.success(f"Week {cur_w} results saved and verified! All player scores and leaderboard standings updated.")
                    st.rerun()
