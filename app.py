import os
import json
import base64
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
                data = json.load(f)
                return data
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
            if sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b) == 5:
                score += 25
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += (3 if idx in [0, 4] else 2)
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            if sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b) == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += (3 if idx in [0, 3] else 2)
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            if sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b) == 3:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += (3 if idx == 0 else 2)
    else:
        p_top3 = predictions.get("tech_top_3", [])
        p_bot3 = predictions.get("tech_bottom_3", [])
        a_rank = actuals.get("tech_rank", [])
        a_top3 = actuals.get("tech_top_3", a_rank[:3] if len(a_rank)>=3 else [])
        a_bot3 = actuals.get("tech_bottom_3", a_rank[-3:] if len(a_rank)>=3 else [])
        
        if len(p_top3) == 3 and len(a_top3) == 3:
            if p_top3 == a_top3:
                score += 10
            else:
                if p_top3[0] == a_top3[0]: score += 3
                if p_top3[1] == a_top3[1]: score += 2
                if p_top3[2] == a_top3[2]: score += 2
                for idx, baker in enumerate(p_top3):
                    if baker in a_top3 and baker != a_top3[idx]:
                        score += 1
                        
        if len(p_bot3) == 3 and len(a_bot3) == 3:
            if p_bot3 == a_bot3:
                score += 10
            else:
                if p_bot3[0] == a_bot3[0]: score += 2
                if p_bot3[1] == a_bot3[1]: score += 2
                if p_bot3[2] == a_bot3[2]: score += 3
                for idx, baker in enumerate(p_bot3):
                    if baker in a_bot3 and baker != a_bot3[idx]:
                        score += 1

    if week < 9:
        p_inline = predictions.get("in_line_sb")
        a_inline = actuals.get("in_line_sb", [])
        if p_inline and p_inline in a_inline and p_inline != actuals.get("star_baker"):
            score += 2
            
        p_trouble = predictions.get("in_trouble")
        a_trouble = actuals.get("in_trouble", [])
        if p_trouble and p_trouble in a_trouble:
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
    if pred_winner:
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
    semis = random.sample([b for b in ALL_BAKERS if b != winner], 3)
    return {
        "winner": winner,
        "semifinalists": semis,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    if week == 10:
        return {"show_champion": random.choice(active_bakers), "tech_rank": random.sample(active_bakers, len(active_bakers))}
    elif week in [8, 9]:
        sb = random.choice(active_bakers)
        el_pool = [b for b in active_bakers if b != sb]
        elim = random.sample(el_pool, min(2, len(el_pool))) if is_double_elim else (random.choice(el_pool) if el_pool else active_bakers[0])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line = random.choice([b for b in active_bakers if b != sb]) if len(active_bakers) > 1 else active_bakers[0]
        in_tr = random.choice([b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])]) if active_bakers else active_bakers[0]
        return {"star_baker": sb, "eliminated": elim, "tech_rank": tech_rank, "in_line_sb": in_line, "in_trouble": in_tr}
    else:
        sb = random.choice(active_bakers)
        el_pool = [b for b in active_bakers if b != sb]
        elim = random.sample(el_pool, min(2, len(el_pool))) if is_double_elim else (random.choice(el_pool) if el_pool else active_bakers[0])
        top3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bot = [b for b in active_bakers if b not in top3]
        bot3 = random.sample(rem_bot, min(3, len(rem_bot))) if rem_bot else top3
        in_line = random.choice([b for b in active_bakers if b != sb]) if len(active_bakers) > 1 else active_bakers[0]
        in_tr = random.choice([b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])]) if active_bakers else active_bakers[0]
        return {"star_baker": sb, "eliminated": elim, "tech_top_3": top3, "tech_bottom_3": bot3, "in_line_sb": in_line, "in_trouble": in_tr}

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 3. HEADER & SIDEBAR ---
col_head1, col_head2 = st.columns([1, 5])
with col_head1:
    norman_img = None
    for p in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.png"]:
        if os.path.exists(p):
            norman_img = p
            break
    if norman_img is not None:
        st.image(norman_img, width=100)
    else:
        st.markdown("<h1 style='font-size: 65px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_head2:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

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

# --- 4. MAIN NAVIGATION TABS --- 
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
            "points": tot_pts,
            "data": data
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
    st.subheader("📋 Individual Player Scorecards")
    
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ALL_HUMANS_AND_AI, key="lb_player_card_sel")
    
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Scorecard (Total Score: {p_pts} pts)**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        if p_weekly:
            st.markdown("#### **Weekly Predictions Log:**")
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

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions Ballot")
    
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
                    st.markdown(f"[🔗 View {baker}'s Profile Page]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    
    if st.session_state.current_week == 1 and not st.session_state.weekly_results.get(1):
        st.info("🔍 **Week 1 Scouting Phase Active!** Browse the baker gallery above to scout the Class of 2026. Weekly prediction ballots unlock in Week 2 after Episode 1 results are published!")
    else:
        st.subheader(f"📅 Active Ballot: Week {st.session_state.current_week}")
        st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
        
        eliminated_bakers_by_week = {
            1: [], 2: ["Yannis"], 3: ["Yannis", "Nikki"], 4: ["Yannis", "Nikki", "Connie"],
            5: ["Yannis", "Nikki", "Connie", "Gary"], 6: ["Yannis", "Nikki", "Connie", "Gary", "Moyin"],
            7: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara"],
            8: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon"],
            9: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly"],
            10: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly", "Danni"]
        }
        
        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_dropdown_options = ["--Select Baker--"] + active_bakers
        
        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
        
        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)
            
        user_submitting_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="submit_player_sel")
        
        stored_pin = st.session_state.player_pins.get(user_submitting_player)
        authenticated = False
        
        if stored_pin is None:
            st.warning(f"🔒 First-time setup for **{user_submitting_player}**: Please create a 4-digit security PIN to protect your predictions ballot!")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                new_p1 = st.text_input("Create 4-Digit PIN:", type="password", max_chars=4, key="create_p1")
            with col_p2:
                new_p2 = st.text_input("Confirm 4-Digit PIN:", type="password", max_chars=4, key="create_p2")
            if st.button("Set PIN & Unlock Ballot"):
                if len(new_p1) == 4 and new_p1.isdigit() and new_p1 == new_p2:
                    st.session_state.player_pins[user_submitting_player] = new_p1
                    save_league_data()
                    st.success(f"4-digit PIN saved for {user_submitting_player}!")
                    st.rerun()
                else:
                    st.error("PINs must be exactly 4 digits and match!")
        else:
            user_pin_in = st.text_input(f"Enter 4-Digit Security PIN for **{user_submitting_player}**:", type="password", key="login_pin_input", max_chars=4)
            if user_pin_in == stored_pin:
                authenticated = True
                st.success(f"🔓 Authenticated as **{user_submitting_player}**!")
            elif user_pin_in != "":
                st.error("❌ Incorrect PIN!")

        if authenticated:
            if st.session_state.current_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_dropdown_options, key="user_win_pick")
                    user_semi1 = st.selectbox("Predict Other Semifinalist #1 [10 pts]", baker_dropdown_options, key="s1")
                    user_semi2 = st.selectbox("Predict Other Semifinalist #2 [10 pts]", baker_dropdown_options, key="s2")
                    user_semi3 = st.selectbox("Predict Other Semifinalist #3 [10 pts]", baker_dropdown_options, key="s3")
                    
                    user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                    user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)
                    
                    if st.button("Lock Season-Long Predictions"):
                        s_picks = [user_winner, user_semi1, user_semi2, user_semi3]
                        if "--Select Baker--" in s_picks:
                            st.error("Please select a valid baker for all Season prediction fields.")
                        elif len(set(s_picks)) < len(s_picks):
                            st.error("❌ Duplicate Selection Error: Season Winner and Semifinalists must all be distinct bakers.")
                        else:
                            st.session_state.league_members[user_submitting_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": [user_semi1, user_semi2, user_semi3],
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                            save_league_data()
                            st.success(f"Season-long predictions saved for {user_submitting_player}!")

            st.markdown("### Weekly Ballot")
            with st.form("weekly_predictions_form"):
                weekly_picks = {}
                if st.session_state.current_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_dropdown_options)
                    st.markdown("**Predict Technical Challenge Rankings:**")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="t1_w10")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="t2_w10")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="t3_w10")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                    
                elif st.session_state.current_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_dropdown_options)
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_dropdown_options, key="e1_w9")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_dropdown_options, key="e2_w9")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_dropdown_options)
                    st.markdown("**Predict Technical Challenge Rankings:**")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="t1_w9")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="t2_w9")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="t3_w9")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", baker_dropdown_options, key="t4_w9")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]
                    
                elif st.session_state.current_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_dropdown_options)
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_dropdown_options, key="inline_w8")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_dropdown_options, key="e1_w8")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_dropdown_options, key="e2_w8")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_dropdown_options, key="tr_w8")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_dropdown_options)
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_dropdown_options, key="tr_w8")
                            
                    st.markdown("**Predict Technical Challenge Rankings:**")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="t1_w8")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="t2_w8")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="t3_w8")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", baker_dropdown_options, key="t4_w8")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", baker_dropdown_options, key="t5_w8")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_dropdown_options)
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_dropdown_options)
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_dropdown_options, key="e1_std")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_dropdown_options, key="e2_std")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_dropdown_options, key="tr_std")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_dropdown_options)
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_dropdown_options, key="tr_std")
                            
                    st.markdown("**Predict Technical Challenge Placements:**")
                    tt1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="tt1_std")
                    tt2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="tt2_std")
                    tt3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="tt3_std")
                    tb1 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_dropdown_options, key="tb1_std")
                    tb2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_dropdown_options, key="tb2_std")
                    tb3 = st.selectbox("Technical Last Place [3 pts]", baker_dropdown_options, key="tb3_std")
                    weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                    weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]

                sub_ballot = st.form_submit_button("Lock In & Submit Predictions")
                if sub_ballot:
                    errors = []
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
                        st.session_state.league_members[user_submitting_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                        ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                        save_league_data()
                        st.success(f"🎉 Predictions successfully saved for {user_submitting_player} (Week {st.session_state.current_week})!")

# --- TAB 3: SHOW RESULTS ---
with tab_show_results:
    st.header("📺 Broadcast Results & Episode Archive")
    
    # Running Chaos Metrics
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = sum([w.get("handshake_count", len(w.get("handshake_bakers", []))) for w in st.session_state.weekly_results.values()])
    tot_cry = sum([w.get("crying_count", 0) for w in st.session_state.weekly_results.values()])
    tot_inn = sum([w.get("innuendo_count", 0) for w in st.session_state.weekly_results.values()])
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Hollywood Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Sexual Innuendos", f"{tot_inn}")
        
    st.markdown("---")
    st.subheader("📅 Weekly Episode Results Breakdown")
    
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        for w_num in sorted([int(k) for k in st.session_state.weekly_results.keys()]):
            w_act = st.session_state.weekly_results.get(w_num, st.session_state.weekly_results.get(str(w_num), {}))
            with st.expander(f"📺 Week {w_num} Official Broadcast Results", expanded=(w_num == max([int(k) for k in st.session_state.weekly_results.keys()]))):
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.markdown("#### **🏆 Main Episode Awards**")
                    sb_val = w_act.get("star_baker", w_act.get("show_champion", "None"))
                    st.write(f"🌟 **Star Baker / Champion:** {sb_val}")
                    
                    in_line_val = w_act.get("in_line_sb", [])
                    in_line_str = ", ".join(in_line_val) if isinstance(in_line_val, list) and in_line_val else (str(in_line_val) if in_line_val else "None")
                    st.write(f"🎖️ **In Line for Star Baker:** {in_line_str}")
                    
                    elim_val = w_act.get("eliminated", "None")
                    elim_str = ", ".join(elim_val) if isinstance(elim_val, list) and elim_val else (str(elim_val) if elim_val != "None" else "None (Sickness Grace Week)")
                    st.write(f"🚪 **Eliminated Baker:** {elim_str}")
                    
                    in_tr_val = w_act.get("in_trouble", [])
                    in_tr_str = ", ".join(in_tr_val) if isinstance(in_tr_val, list) and in_tr_val else (str(in_tr_val) if in_tr_val else "None")
                    st.write(f"⚠️ **In Trouble of Elimination:** {in_tr_str}")
                    
                with col_w2:
                    st.markdown("#### **🔥 Chaos Metrics & Video Timestamps**")
                    hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                    hs_cnt = w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
                    hs_stamps = w_act.get("handshake_timestamps", "")
                    st.write(f"🤝 **Hollywood Handshakes ({hs_cnt}):** {hs_bakers}")
                    if hs_stamps: st.caption(f"📍 Timestamps: {hs_stamps}")
                    
                    cry_cnt = w_act.get("crying_count", 0)
                    cry_stamps = w_act.get("crying_timestamps", "")
                    st.write(f"😢 **Crying Incidents ({cry_cnt}):** {cry_stamps if cry_stamps else 'None recorded'}")
                    
                    inn_cnt = w_act.get("innuendo_count", 0)
                    inn_stamps = w_act.get("innuendo_timestamps", "")
                    st.write(f"💬 **Sexual Innuendos ({inn_cnt}):** {inn_stamps if inn_stamps else 'None recorded'}")

                # Technical Challenge Placement
                tech_ranks = w_act.get("tech_rank", [])
                if not tech_ranks:
                    tech_top = w_act.get("tech_top_3", [])
                    tech_bot = w_act.get("tech_bottom_3", [])
                    if tech_top or tech_bot:
                        tech_ranks = tech_top + ["..."] + tech_bot
                        
                if tech_ranks:
                    st.markdown("#### **📊 Technical Challenge Placements**")
                    formatted_tech = []
                    for idx, baker in enumerate(tech_ranks):
                        if idx == 0: formatted_tech.append(f"🥇 **1st Place:** {baker}")
                        elif idx == 1: formatted_tech.append(f"🥈 **2nd Place:** {baker}")
                        elif idx == 2: formatted_tech.append(f"🥉 **3rd Place:** {baker}")
                        else: formatted_tech.append(f"**{idx+1}th Place:** {baker}")
                    st.write(" | ".join(formatted_tech))

    # Broadcast Audit Table
    st.markdown("---")
    st.subheader("📋 Broadcast Audit Summary Table")
    if st.session_state.weekly_results:
        audit_rows = []
        for w_num in sorted([int(k) for k in st.session_state.weekly_results.keys()]):
            w_act = st.session_state.weekly_results.get(w_num, st.session_state.weekly_results.get(str(w_num), {}))
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            cry_cnt = w_act.get("crying_count", 0)
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"
            
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshake_count', 0)} ({hs_bakers})",
                "Crying Occurrences": f"{cry_cnt} ({cry_stamps})",
                "Innuendos Occurrences": f"{inn_cnt} ({inn_stamps})"
            })
        st.dataframe(pd.DataFrame(audit_rows), hide_index=True, use_container_width=True)

    # Disputes Form & Log
    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence for democratic review.")
    
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
        st.dataframe(pd.DataFrame(st.session_state.disputes), hide_index=True, use_container_width=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if st.session_state.get("data_erased_confirmation"):
        st.success("✅ All competition data, predictions, broadcast actuals, disputes, and player PINs have been permanently erased!")
        st.session_state.data_erased_confirmation = False
    
    if not st.session_state.admin_authenticated:
        st.warning("🔒 Restricted Console Access")
        admin_pin_input = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_field")
        if st.button("Unlock Admin Panel"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("🔓 Authenticated as Administrator!")
                st.rerun()
            else:
                st.error("❌ Incorrect Admin PIN")
    else:
        st.success("🔓 Administrator Console Unlocked")
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        st.subheader("📅 Record or Review Broadcast Results")
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Review Broadcast Results:",
            options=list(range(1, 11)),
            index=active_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in [int(k) for k in st.session_state.weekly_results.keys()] else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        cur_w = admin_selected_week
        saved_actuals = st.session_state.weekly_results.get(cur_w, st.session_state.weekly_results.get(str(cur_w), {}))
        is_already_published = cur_w in [int(k) for k in st.session_state.weekly_results.keys()]
        
        eliminated_bakers_by_week = {
            1: [], 2: ["Yannis"], 3: ["Yannis", "Nikki"], 4: ["Yannis", "Nikki", "Connie"],
            5: ["Yannis", "Nikki", "Connie", "Gary"], 6: ["Yannis", "Nikki", "Connie", "Gary", "Moyin"],
            7: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara"],
            8: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon"],
            9: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly"],
            10: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly", "Danni"]
        }
        current_eliminated = eliminated_bakers_by_week.get(cur_w, [])
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        admin_dropdown_options = ["--Select Baker--"] + admin_active_bakers
        
        if is_already_published:
            st.info(f"🟢 **Week {cur_w} Results Recorded & Saved in System** — Reviewing saved entries below. Fields are locked to prevent accidental edits.")
            enable_edit = st.checkbox(f"🔓 Enable Editing for Week {cur_w} (Requires Verification before Overwriting Saved Results)", key=f"unlock_edit_w{cur_w}")
        else:
            enable_edit = True

        st.markdown("### Elimination Status Selection")
        saved_elim = saved_actuals.get("eliminated", "None")
        default_elim_idx = 0
        if saved_elim == "None": default_elim_idx = 1
        elif isinstance(saved_elim, list): default_elim_idx = 2
        
        elim_type = st.radio(
            "Select Episode Elimination Type:", 
            ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], 
            index=default_elim_idx, 
            horizontal=True, 
            key=f"adm_elim_type_radio_w{cur_w}",
            disabled=(is_already_published and not enable_edit)
        )

        with st.form(f"admin_actuals_form_w{cur_w}"):
            st.subheader(f"Input / Edit Results for Week {cur_w}")
            actuals = {}
            
            if cur_w == 10:
                s_sc = saved_actuals.get("show_champion", "--Select Baker--")
                sc_idx = admin_dropdown_options.index(s_sc) if s_sc in admin_dropdown_options else 0
                act_sc = st.selectbox("Actual Show Champion", admin_dropdown_options, index=sc_idx, disabled=(is_already_published and not enable_edit))
                actuals["show_champion"] = act_sc
                
                st.markdown("### Technical Challenge Rankings (3 Bakers):")
                saved_tech = saved_actuals.get("tech_rank", [])
                s_t1 = saved_tech[0] if len(saved_tech)>0 else "--Select Baker--"
                s_t2 = saved_tech[1] if len(saved_tech)>1 else "--Select Baker--"
                s_t3 = saved_tech[2] if len(saved_tech)>2 else "--Select Baker--"
                act_t1 = st.selectbox("1st Place Technical", admin_dropdown_options, index=admin_dropdown_options.index(s_t1) if s_t1 in admin_dropdown_options else 0, disabled=(is_already_published and not enable_edit))
                act_t2 = st.selectbox("2nd Place Technical", admin_dropdown_options, index=admin_dropdown_options.index(s_t2) if s_t2 in admin_dropdown_options else 0, disabled=(is_already_published and not enable_edit))
                act_t3 = st.selectbox("3rd Place Technical", admin_dropdown_options, index=admin_dropdown_options.index(s_t3) if s_t3 in admin_dropdown_options else 0, disabled=(is_already_published and not enable_edit))
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    s_sb = saved_actuals.get("star_baker", "--Select Baker--")
                    sb_idx = admin_dropdown_options.index(s_sb) if s_sb in admin_dropdown_options else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_options, index=sb_idx, disabled=(is_already_published and not enable_edit))
                    
                    s_inline = [b for b in saved_actuals.get("in_line_sb", []) if b in admin_active_bakers]
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, default=s_inline, disabled=(is_already_published and not enable_edit))
                with col2:
                    s_trouble = [b for b in saved_actuals.get("in_trouble", []) if b in admin_active_bakers]
                    if elim_type == "Single Elimination":
                        s_el = saved_elim if isinstance(saved_elim, str) else "--Select Baker--"
                        el_idx = admin_dropdown_options.index(s_el) if s_el in admin_dropdown_options else 0
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_options, index=el_idx, key=f"adm_elim_single_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=s_trouble, key=f"adm_tr_single_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=s_trouble, key=f"adm_tr_grace_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    else:
                        s_el1 = saved_elim[0] if isinstance(saved_elim, list) and len(saved_elim)>0 else "--Select Baker--"
                        s_el2 = saved_elim[1] if isinstance(saved_elim, list) and len(saved_elim)>1 else "--Select Baker--"
                        e1_idx = admin_dropdown_options.index(s_el1) if s_el1 in admin_dropdown_options else 0
                        e2_idx = admin_dropdown_options.index(s_el2) if s_el2 in admin_dropdown_options else 0
                        act_e1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_options, index=e1_idx, key=f"adm_e1_d_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        act_e2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_options, index=e2_idx, key=f"adm_e2_d_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        actuals["eliminated"] = [act_e1, act_e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=s_trouble, key=f"adm_tr_d_w{cur_w}", disabled=(is_already_published and not enable_edit))

                st.markdown(f"**Technical Challenge Rankings ({len(admin_active_bakers)} Bakers):**")
                saved_tech = saved_actuals.get("tech_rank", [])
                tech_inputs = []
                for idx_pos in range(len(admin_active_bakers)):
                    s_pos_baker = saved_tech[idx_pos] if idx_pos < len(saved_tech) else "--Select Baker--"
                    pos_idx = admin_dropdown_options.index(s_pos_baker) if s_pos_baker in admin_dropdown_options else 0
                    pos_label = f"Technical Position #{idx_pos + 1}"
                    if idx_pos == 0: pos_label += " (1st Place)"
                    elif idx_pos == len(admin_active_bakers) - 1: pos_label += f" ({idx_pos + 1}th / Last Place)"
                    t_val = st.selectbox(pos_label, admin_dropdown_options, index=pos_idx, key=f"adm_tech_pos_{idx_pos}_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    tech_inputs.append(t_val)
                actuals["tech_rank"] = tech_inputs

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            saved_hs_cnt = saved_actuals.get("handshake_count", len(saved_actuals.get("handshake_bakers", [])))
            saved_hs_stamps = saved_actuals.get("handshake_timestamps", "")
            saved_hs_bakers = [b for b in saved_actuals.get("handshake_bakers", []) if b in admin_active_bakers]
            act_hs_cnt = st.number_input("Handshake Occurrences Count", min_value=0, value=saved_hs_cnt, disabled=(is_already_published and not enable_edit))
            act_hs_stamps = st.text_input("Handshake Descriptions & Timestamps", value=saved_hs_stamps, disabled=(is_already_published and not enable_edit))
            act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", admin_active_bakers, default=saved_hs_bakers, disabled=(is_already_published and not enable_edit))

            st.markdown("### 😢 Crying Incidents")
            saved_cry_cnt = saved_actuals.get("crying_count", 0)
            saved_cry_stamps = saved_actuals.get("crying_timestamps", "")
            act_cry_cnt = st.number_input("Crying Occurrences Count", min_value=0, value=saved_cry_cnt, disabled=(is_already_published and not enable_edit))
            act_cry_stamps = st.text_input("Crying Descriptions & Timestamps", value=saved_cry_stamps, disabled=(is_already_published and not enable_edit))

            st.markdown("### 💬 Sexual Innuendos")
            saved_inn_cnt = saved_actuals.get("innuendo_count", 0)
            saved_inn_stamps = saved_actuals.get("innuendo_timestamps", "")
            act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=saved_inn_cnt, disabled=(is_already_published and not enable_edit))
            act_inn_stamps = st.text_input("Innuendos Descriptions & Timestamps", value=saved_inn_stamps, disabled=(is_already_published and not enable_edit))

            actuals["handshake_count"] = act_hs_cnt or 0
            actuals["handshake_bakers"] = act_hs_bakers
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt or 0
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt or 0
            actuals["innuendo_timestamps"] = act_inn_stamps

            btn_label = "Update & Recalculate Saved Results" if is_already_published else "Publish Official Week Results & Recalculate Standings"
            submit_admin = st.form_submit_button(btn_label, disabled=(is_already_published and not enable_edit))
            
            if submit_admin:
                if is_already_published and not enable_edit:
                    st.error("🔒 Overwrite Blocked: You must check the 'Enable Editing' box above before saving edits.")
                else:
                    st.session_state.weekly_results[cur_w] = actuals
                    
                    # Recalculate
                    for m_name in ALL_HUMANS_AND_AI:
                        st.session_state.league_members[m_name]["total_score"] = 0
                        st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                        
                    for w_num in sorted([int(k) for k in st.session_state.weekly_results.keys()]):
                        act_w = st.session_state.weekly_results.get(w_num, st.session_state.weekly_results.get(str(w_num), {}))
                        w_scores = {}
                        for m_name in ALL_HUMANS_AND_AI:
                            m_data = st.session_state.league_members[m_name]
                            p_picks = m_data["weekly_picks"].get(w_num, m_data["weekly_picks"].get(str(w_num), {}))
                            w_pts = calculate_weekly_score(p_picks, act_w, week=w_num)
                            m_data["weekly_breakdown"][w_num] = w_pts
                            w_scores[m_name] = w_pts
                            
                        if w_scores:
                            max_pts = max(w_scores.values())
                            if max_pts > 0:
                                for m_name, pts in w_scores.items():
                                    if pts == max_pts:
                                        st.session_state.league_members[m_name]["weekly_breakdown"][w_num] += 5
                                        
                    for m_name in ALL_HUMANS_AND_AI:
                        m_data = st.session_state.league_members[m_name]
                        m_data["total_score"] = sum(m_data["weekly_breakdown"].values())
                        if st.session_state.season_results:
                            m_data["total_score"] += calculate_season_score(m_data["season_picks"], st.session_state.season_results)
                            
                    save_league_data()
                    st.success(f"🎉 Official Week {cur_w} results published! All standings recalculated.")
                    st.rerun()

        # Dispute Resolution Console
        st.markdown("---")
        st.subheader("⚖️ Dispute Resolution & Management Console")
        if not st.session_state.disputes:
            st.info("No active player disputes submitted yet.")
        else:
            st.write("Review active player disputes and update their vote status after GroupMe resolution:")
            for idx_d, disp in enumerate(st.session_state.disputes):
                with st.expander(f"Dispute #{idx_d+1}: {disp.get('Player')} - {disp.get('Week')} ({disp.get('Category')})", expanded=False):
                    st.write(f"**Player:** {disp.get('Player')}")
                    st.write(f"**Contested Week:** {disp.get('Week')}")
                    st.write(f"**Category:** {disp.get('Category')}")
                    st.write(f"**Evidence:** {disp.get('Evidence')}")
                    st.write(f"**Requested Correction:** {disp.get('Correction')}")
                    
                    cur_status = disp.get("Status", "Pending GroupMe Vote 🗳️")
                    status_opts = ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"]
                    status_idx = status_opts.index(cur_status) if cur_status in status_opts else 0
                    
                    new_status = st.selectbox(f"Update Dispute #{idx_d+1} Resolution Status:", status_opts, index=status_idx, key=f"disp_status_sel_{idx_d}")
                    if st.button(f"Save Resolution Status for Dispute #{idx_d+1}", key=f"btn_save_disp_{idx_d}"):
                        disp["Status"] = new_status
                        save_league_data()
                        st.success(f"Dispute #{idx_d+1} status updated to '{new_status}'!")
                        st.rerun()

        # Player PIN Reset Console
        st.markdown("---")
        st.subheader("🔑 Player Security PIN Reset Console")
        pin_reset_player = st.selectbox("Select Player Profile to Reset PIN:", ROSTER_HUMANS, key="pin_reset_sel")
        if st.button(f"Reset PIN for {pin_reset_player}"):
            if pin_reset_player in st.session_state.player_pins:
                del st.session_state.player_pins[pin_reset_player]
                save_league_data()
                st.success(f"✅ PIN reset for {pin_reset_player}. They can now set a new 4-digit PIN on the prediction tab.")
            else:
                st.info(f"{pin_reset_player} does not have an active PIN set.")

        # Master Data Reset Button
        st.markdown("---")
        st.subheader("🚨 Erase All Saved Competition Data")
        st.warning("⚠️ **Danger Zone:** Clearing competition data will permanently wipe all recorded weekly broadcast results, season results, player prediction ballots, dispute logs, and player PINs!")
        confirm_erase = st.checkbox("I understand this will permanently erase all player picks, PINs, and published broadcast actuals.", key="confirm_erase_chk_final")
        if st.button("Erase All Saved Competition Data", type="primary", disabled=not confirm_erase):
            st.session_state.weekly_results = {}
            st.session_state.season_results = {}
            st.session_state.disputes = []
            st.session_state.player_pins = {}
            
            for m_name in ALL_HUMANS_AND_AI:
                st.session_state.league_members[m_name] = {
                    "weekly_picks": {},
                    "season_picks": {},
                    "total_score": 0,
                    "weekly_breakdown": {}
                }
                
            if os.path.exists(DATA_FILE):
                try: os.remove(DATA_FILE)
                except Exception: pass
                
            st.session_state.data_erased_confirmation = True
            st.rerun()
