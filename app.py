import streamlit as st
import pandas as pd
import random
import json
import os
import base64
import io
from PIL import Image

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for a beautiful, cozy baking theme
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
    }
    .stHeader {
        color: #5D4037;
    }
    /* Dark Mode High-Contrast Overrides */
    @media (prefers-color-scheme: dark) {
        .lb-rank, .lb-name, .stMarkdown, p, span, label {
            color: #FFFFFF !important;
        }
        .lb-pts {
            color: #FF8A80 !important;
        }
    }
    [data-theme="dark"] .lb-rank,
    [data-theme="dark"] .lb-name,
    .stApp[data-theme="dark"] .lb-rank,
    .stApp[data-theme="dark"] .lb-name,
    .stApp[data-theme="dark"] p,
    .stApp[data-theme="dark"] span,
    .stApp[data-theme="dark"] label {
        color: #FFFFFF !important;
    }
    [data-theme="dark"] .lb-pts,
    .stApp[data-theme="dark"] .lb-pts {
        color: #FF8A80 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. THE 2026 OFFICIAL SCORING ENGINE (INTERNALIZED FOR PORTABILITY) ---
def calculate_weekly_score(predictions, actuals, week_num):
    if not predictions or not actuals:
        return 0
        
    score = 0
    
    # 1. Star Baker (5 points)
    if "star_baker" in predictions and "star_baker" in actuals:
        if predictions["star_baker"] == actuals["star_baker"]:
            score += 5
            
    # 2. In Line for Star Baker Consolation (2 points)
    if "in_line_sb" in predictions and "in_line_sb" in actuals:
        pred_inline = predictions["in_line_sb"]
        act_inlines = actuals.get("in_line_sb", [])
        if pred_inline in act_inlines and pred_inline != actuals.get("star_baker"):
            score += 2
            
    # 3. Eliminated Baker (5 points)
    if "eliminated" in predictions and "eliminated" in actuals:
        pred_elim = predictions["eliminated"]
        act_elim = actuals["eliminated"]
        if act_elim == "None":
            score += 0
        elif isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for pe in pred_elim:
                    if pe in act_elim:
                        score += 5
            else:
                if pred_elim in act_elim:
                    score += 5
        else:
            if pred_elim == act_elim:
                score += 5
                
    # 4. In Trouble of Elimination Consolation (2 points)
    if "in_trouble" in predictions and "in_trouble" in actuals:
        pred_trouble = predictions["in_trouble"]
        act_troubles = actuals.get("in_trouble", [])
        act_elim = actuals.get("eliminated")
        if isinstance(act_elim, list):
            saved_from_elim = pred_trouble not in act_elim
        else:
            saved_from_elim = pred_trouble != act_elim
        if pred_trouble in act_troubles and saved_from_elim:
            score += 2
            
    # 5. Technical Challenge Scoring
    if week_num in [8, 9, 10]:
        pred_tech = predictions.get("tech_rank", [])
        act_tech = actuals.get("tech_rank", [])
        if pred_tech and act_tech:
            if pred_tech == act_tech:
                if week_num == 8: score += 25
                elif week_num == 9: score += 20
                elif week_num == 10: score += 15
            else:
                for idx, baker in enumerate(pred_tech):
                    if idx < len(act_tech) and baker == act_tech[idx]:
                        if idx in [0, len(act_tech)-1]:
                            score += 3
                        else:
                            score += 2
    else:
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        
        if pred_top3 and act_top3:
            if pred_top3 == act_top3:
                score += 10
            else:
                for idx, baker in enumerate(pred_top3):
                    if idx < len(act_top3):
                        if baker == act_top3[idx]:
                            if idx == 0: score += 3
                            else: score += 2
                        elif baker in act_top3:
                            score += 1
                            
        pred_bot3 = predictions.get("tech_bottom_3", [])
        act_bot3 = actuals.get("tech_bottom_3", [])
        if pred_bot3 and act_bot3:
            if pred_bot3 == act_bot3:
                score += 10
            else:
                for idx, baker in enumerate(pred_bot3):
                    if idx < len(act_bot3):
                        if baker == act_bot3[idx]:
                            if idx == 2: score += 3
                            else: score += 2
                        elif baker in act_bot3:
                            score += 1

    return score

def calculate_season_score(predictions, actuals):
    if not predictions or not actuals:
        return 0
        
    score = 0
    if "winner" in predictions and "winner" in actuals:
        if predictions["winner"] == actuals["winner"]:
            score += 40
        elif predictions["winner"] in actuals.get("finalists", []):
            score += 15
            
    if "semifinalists" in predictions and "semifinalists" in actuals:
        act_semis = actuals["semifinalists"]
        for s in predictions["semifinalists"]:
            if s in act_semis:
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

# --- 3. CORE BAKERS LIST & DATABASE INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo",
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", 
    "Taliah", "Tressa"
]

ROSTER_ALPHABETICAL = sorted(["AI Brian"] + ROSTER_HUMANS)

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

DATA_FILE = "league_data.json"

def save_league_data():
    data = {
        "weekly_results": st.session_state.weekly_results,
        "season_results": st.session_state.season_results,
        "disputes": st.session_state.get("disputes", []),
        "league_members": {}
    }
    for m_name, m_data in st.session_state.league_members.items():
        data["league_members"][m_name] = {
            "weekly_picks": m_data.get("weekly_picks", {}),
            "season_picks": m_data.get("season_picks", {}),
            "total_score": m_data.get("total_score", 0),
            "weekly_breakdown": m_data.get("weekly_breakdown", {}),
            "pin": m_data.get("pin", None),
            "season_score": m_data.get("season_score", 0)
        }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            st.session_state.weekly_results = data.get("weekly_results", {})
            st.session_state.season_results = data.get("season_results", {})
            st.session_state.disputes = data.get("disputes", [])
            
            saved_members = data.get("league_members", {})
            for m_name in ROSTER_ALPHABETICAL:
                if m_name in saved_members:
                    st.session_state.league_members[m_name] = {
                        "weekly_picks": saved_members[m_name].get("weekly_picks", {}),
                        "season_picks": saved_members[m_name].get("season_picks", {}),
                        "total_score": saved_members[m_name].get("total_score", 0),
                        "weekly_breakdown": saved_members[m_name].get("weekly_breakdown", {}),
                        "pin": saved_members[m_name].get("pin", None),
                        "season_score": saved_members[m_name].get("season_score", 0)
                    }
        except Exception:
            pass

# Initialize session state roster
if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for m_name in ROSTER_ALPHABETICAL:
        st.session_state.league_members[m_name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None,
            "season_score": 0
        }

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

load_league_data()

# Ensure PIN key exists for all members
for m_name in st.session_state.league_members:
    if "pin" not in st.session_state.league_members[m_name]:
        st.session_state.league_members[m_name]["pin"] = None

# --- 4. DYNAMIC AUTOMATION: "AI BRIAN" PICK GENERATOR ---
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
        return {
            "show_champion": champion,
            "tech_rank": tech_rank
        }
    elif week == 9:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank
        }
    elif week == 8:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank,
            "in_line_sb": in_line_sb,
            "in_trouble": in_trouble
        }
    else:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
            
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        remaining_for_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(remaining_for_bottom, min(3, len(remaining_for_bottom)))
            
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3,
            "in_line_sb": in_line_sb,
            "in_trouble": in_trouble
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# Determine active competition week
all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
active_prediction_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_prediction_week > 10: active_prediction_week = 10
st.session_state.current_week = active_prediction_week

# --- 5. APP INTERFACE LAYOUT ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("normanbeaver.jpg"):
        st.image("normanbeaver.jpg", width=90)
    elif os.path.exists("assets/normanbeaver.jpg"):
        st.image("assets/normanbeaver.jpg", width=90)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🧁</h1>", unsafe_allow_html=True)

with col_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: COMPETITION PROGRESS & POINTS REMINDER ---
with st.sidebar:
    st.header("⚙️ Competition Progress")
    if not st.session_state.weekly_results:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nSeason-Long Predictions are open! Episode 2 ballot unlocks after Week 1 results are posted.")
    else:
        st.success(f"🟢 **Active Competition Week: Week {st.session_state.current_week}**")

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

# --- MAIN TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "📈 Contestant Analytics", "👑 Admin Panel"])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    # Calculate running total across chaos categories
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    for w_num, w_act in st.session_state.weekly_results.items():
        if "handshake_count" in w_act:
            tot_hs += w_act["handshake_count"]
        elif "handshake_bakers" in w_act and isinstance(w_act["handshake_bakers"], list):
            tot_hs += len(w_act["handshake_bakers"])
        elif "handshakes" in w_act:
            tot_hs += w_act["handshakes"]
            
        if "crying_count" in w_act:
            tot_cry += w_act["crying_count"]
        elif w_act.get("crying_timestamps"):
            tot_cry += len([s for s in str(w_act["crying_timestamps"]).split(",") if s.strip()])
        elif "crying" in w_act:
            tot_cry += w_act["crying"]
            
        if "innuendo_count" in w_act:
            tot_inn += w_act["innuendo_count"]
        elif "innuendos" in w_act:
            tot_inn += w_act["innuendos"]
            
    # DISPLAY RUNNING CHAOS CATEGORIES TOTALS
    st.markdown("### 🌀 Running Chaos Categories Broadcast Totals")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Hollywood Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Sexual Innuendos", f"{tot_inn}")
        
    st.markdown("---")
    
    # Compile scoring
    lb_data = []
    for name, data in st.session_state.league_members.items():
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
        
        # Render clean HTML leaderboard table with high dark mode contrast
        st.markdown("""
<style>
    .lb-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        margin-bottom: 25px;
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
        border-bottom: 1px solid rgba(128, 128, 128, 0.3);
        vertical-align: middle;
    }
    .lb-rank {
        font-weight: 800;
        font-size: 1.15rem;
        color: #2C1810;
    }
    .lb-name {
        font-weight: 800;
        font-size: 1.2rem;
        color: #2C1810;
    }
    .lb-pts {
        font-weight: 800;
        font-size: 1.25rem;
        color: #D36B5F;
        text-align: right;
    }
    @media (prefers-color-scheme: dark) {
        .lb-rank, .lb-name {
            color: #FFFFFF !important;
        }
        .lb-pts {
            color: #FF8A80 !important;
        }
    }
    [data-theme="dark"] .lb-rank,
    [data-theme="dark"] .lb-name,
    .stApp[data-theme="dark"] .lb-rank,
    .stApp[data-theme="dark"] .lb-name {
        color: #FFFFFF !important;
    }
    [data-theme="dark"] .lb-pts,
    .stApp[data-theme="dark"] .lb-pts {
        color: #FF8A80 !important;
    }
</style>
""", unsafe_allow_html=True)
        
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

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    # Dropdown to inspect a player's individual scorecard
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="lb_player_card_sel")
    
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Scorecard — Total Score: {p_pts} pts**")
        
        # PASSWORD PROTECT SEASON PROJECTIONS ON SCORECARD
        with st.expander(f"🌟 {selected_card_player}'s Season Projections (Password Protected)", expanded=False):
            sc_pin_input = st.text_input(f"Enter {selected_card_player}'s 4-Digit PIN to View Season Projections:", type="password", key=f"sc_pin_{selected_card_player}")
            if st.button(f"Unlock Season Projections for {selected_card_player}"):
                stored_pin = p_data.get("pin")
                if stored_pin is not None and sc_pin_input == stored_pin:
                    st.session_state[f"unlocked_season_{selected_card_player}"] = True
                    st.success("Season Projections Unlocked!")
                else:
                    st.error("Incorrect PIN!")
                    
            if st.session_state.get(f"unlocked_season_{selected_card_player}", False):
                win_pick = p_season.get("winner", "Not submitted yet")
                semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
                hs_pick = p_season.get("handshakes", "N/A")
                cry_pick = p_season.get("crying", "N/A")
                inn_pick = p_season.get("innuendos", "N/A")
                
                st.write(f"🏆 **Predicted Winner:** {win_pick}")
                st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
                st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            else:
                st.info("🔒 Season Projections are locked. Enter player PIN above to view.")
            
        # WEEKLY PREDICTIONS ARE UNLOCKED FOR ALL
        if p_weekly:
            st.markdown("#### **Weekly Predictions Log:**")
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                
                t_str = "N/A"
                if "tech_rank" in w_picks:
                    t_str = ", ".join(w_picks["tech_rank"])
                elif "tech_top_3" in w_picks:
                    t_str = "Top 3: " + ", ".join(w_picks.get("tech_top_3", [])) + " | Bot 3: " + ", ".join(w_picks.get("tech_bottom_3", []))
                    
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Placements": t_str
                })
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True)
        else:
            st.info(f"No weekly predictions logged yet for {selected_card_player}.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps (Verify Counts)")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshake Bakers": hs_bakers,
                "Handshake Timestamps": hs_stamps,
                "Crying Timestamps": cry_stamps,
                "Innuendos": inn_cnt
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True)

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in range(1, 11)])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Video Evidence (e.g., 'At 28:14 in Episode 3, Paul clearly shakes Tom\'s hand during Showstopper judging')")
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
        st.dataframe(df_disp, use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    # Visual Baker Cheat Sheet
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
        cols = st.columns(4)
        for idx, baker in enumerate(ALL_BAKERS):
            info = BAKER_INFO.get(baker, {"url": "#"})
            with cols[idx % 4]:
                st.markdown(f"**{baker}**")
                st.markdown(f"[🔗 View {baker}'s Photo Page]({info['url']})")

    st.markdown("---")
    st.subheader("👤 Player Login & Authentication")
    current_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="pred_login_player")
    player_data = st.session_state.league_members[current_player]
    
    # 4-Digit Password Authentication
    if player_data.get("pin") is None:
        st.info(f"Welcome, {current_player}! Set a 4-digit PIN password to secure your predictions:")
        new_pin = st.text_input("Create 4-Digit PIN Password:", type="password", max_chars=4, key="create_pin_input")
        confirm_pin = st.text_input("Confirm 4-Digit PIN Password:", type="password", max_chars=4, key="confirm_pin_input")
        if st.button("Set PIN Password & Authenticate"):
            if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                st.session_state.league_members[current_player]["pin"] = new_pin
                save_league_data()
                st.success("PIN set successfully! You are now authenticated.")
                st.rerun()
            else:
                st.error("PINs must match and be exactly 4 digits.")
        st.stop()
    else:
        entered_pin = st.text_input(f"Enter 4-Digit PIN for {current_player}:", type="password", max_chars=4, key="login_pin_input")
        if entered_pin != player_data.get("pin"):
            st.warning("Please enter your correct 4-digit PIN above to unlock ballot fields.")
            st.stop()
        else:
            st.success(f"Authenticated as {current_player}!")

    st.markdown("---")
    st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
    st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
    
    # Dynamic active bakers list
    eliminated_bakers_by_week = {
        1: [],  # Week 1: All 12 bakers active in the tent!
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
    
    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    
    st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
    
    # 1. Season-Long Entry (Available in Week 1 / Scouting phase)
    if st.session_state.current_week == 1 or not st.session_state.weekly_results:
        with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Post-Week 1! | 130 pts total at stake)", expanded=True):
            user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", ["--Select Baker--"] + active_bakers, key="user_win_pick")
            user_s1 = st.selectbox("Predict Semifinalist #1 [10 pts]", ["--Select Baker--"] + active_bakers, key="user_s1_pick")
            user_s2 = st.selectbox("Predict Semifinalist #2 [10 pts]", ["--Select Baker--"] + active_bakers, key="user_s2_pick")
            user_s3 = st.selectbox("Predict Semifinalist #3 [10 pts]", ["--Select Baker--"] + active_bakers, key="user_s3_pick")
            
            user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
            user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
            user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)
            
            if st.button("Lock Season-Long Predictions"):
                semis_list = [user_s1, user_s2, user_s3]
                if "--Select Baker--" in [user_winner] + semis_list:
                    st.error("⚠️ Missing Selection: Please select a valid baker for all season-long prediction fields.")
                elif len(set([user_winner] + semis_list)) != 4:
                    st.error("❌ Duplicate Selection: You may not select the same baker more than once across Season Winner and Semifinalists.")
                else:
                    st.session_state.league_members[current_player]["season_picks"] = {
                        "winner": user_winner,
                        "semifinalists": semis_list,
                        "handshakes": user_handshakes,
                        "crying": user_crying,
                        "innuendos": user_innuendos
                    }
                    save_league_data()
                    st.success(f"Season long predictions saved successfully for {current_player}!")

    # 2. Weekly Form based on active week
    st.markdown("### Weekly Ballot")
    
    if st.session_state.current_week == 1 and not st.session_state.weekly_results:
        st.info("🔒 Week 2 Predictions Are Currently Locked! Predictions for Week 2 will unlock automatically once the Administrator posts the official broadcast results for Week 1.")
    else:
        # Sickness / Grace Week Auto-Detection
        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, help="Automatically checked if the previous week was a sickness grace week with no elimination!")

        dropdown_options = ["--Select Baker--"] + active_bakers

        with st.form("weekly_predictions_form"):
            weekly_picks = {}
            
            if st.session_state.current_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", dropdown_options, key="p_champ")
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="p_t1_w10")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="p_t2_w10")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="p_t3_w10")
                tech_list = [t1, t2, t3]
                weekly_picks["tech_rank"] = tech_list
                main_picks_check = [weekly_picks["show_champion"]]
                
            elif st.session_state.current_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", dropdown_options, key="p_sb_w9")
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="p_e1_w9")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="p_e2_w9")
                    weekly_picks["eliminated"] = [e1, e2]
                    main_picks_check = [weekly_picks["star_baker"], e1, e2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options, key="p_el_w9")
                    main_picks_check = [weekly_picks["star_baker"], weekly_picks["eliminated"]]
                    
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="p_t1_w9")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="p_t2_w9")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="p_t3_w9")
                t4 = st.selectbox("Technical 4th Place [3 pts]", dropdown_options, key="p_t4_w9")
                tech_list = [t1, t2, t3, t4]
                weekly_picks["tech_rank"] = tech_list

            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options, key="p_sb_w8")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", dropdown_options, key="p_inline_w8")
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="p_e1_w8")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="p_e2_w8")
                        weekly_picks["eliminated"] = [e1, e2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="p_tr_w8")
                        main_picks_check = [weekly_picks["star_baker"], weekly_picks["in_line_sb"], e1, e2, weekly_picks["in_trouble"]]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options, key="p_el_w8")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="p_tr_w8")
                        main_picks_check = [weekly_picks["star_baker"], weekly_picks["in_line_sb"], weekly_picks["eliminated"], weekly_picks["in_trouble"]]
                
                st.write("Predict Technical Challenge Final Rank (1st through 5th):")
                t1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="p_t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="p_t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="p_t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", dropdown_options, key="p_t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", dropdown_options, key="p_t5_w8")
                tech_list = [t1, t2, t3, t4, t5]
                weekly_picks["tech_rank"] = tech_list

            else:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", dropdown_options, key="p_sb_std")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", dropdown_options, key="p_inline_std")
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", dropdown_options, key="p_e1_std")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", dropdown_options, key="p_e2_std")
                        weekly_picks["eliminated"] = [e1, e2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="p_tr_std")
                        main_picks_check = [weekly_picks["star_baker"], weekly_picks["in_line_sb"], e1, e2, weekly_picks["in_trouble"]]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options, key="p_el_std")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", dropdown_options, key="p_tr_std")
                        main_picks_check = [weekly_picks["star_baker"], weekly_picks["in_line_sb"], weekly_picks["eliminated"], weekly_picks["in_trouble"]]
                    
                st.markdown("---")
                st.write("Predict Technical Challenge Top 3:")
                tt1 = st.selectbox("Technical 1st Place [3 pts]", dropdown_options, key="p_tt1_std")
                tt2 = st.selectbox("Technical 2nd Place [2 pts]", dropdown_options, key="p_tt2_std")
                tt3 = st.selectbox("Technical 3rd Place [2 pts]", dropdown_options, key="p_tt3_std")
                weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                
                st.write("Predict Technical Challenge Bottom 3:")
                tb1 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", dropdown_options, key="p_tb1_std")
                tb2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", dropdown_options, key="p_tb2_std")
                tb3 = st.selectbox("Technical Last Place [3 pts]", dropdown_options, key="p_tb3_std")
                weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]
                
                tech_list = [tt1, tt2, tt3, tb1, tb2, tb3]
                
            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                # Validation checks
                has_missing_main = any(x == "--Select Baker--" for x in main_picks_check)
                has_missing_tech = any(x == "--Select Baker--" for x in tech_list)
                
                clean_main = [x for x in main_picks_check if x != "--Select Baker--"]
                clean_tech = [x for x in tech_list if x != "--Select Baker--"]
                
                has_dup_main = len(clean_main) != len(set(clean_main))
                has_dup_tech = len(clean_tech) != len(set(clean_tech))
                
                if has_missing_main or has_missing_tech:
                    st.error("⚠️ Missing Selection Error: Please select a valid baker for all prediction fields before submitting!")
                elif has_dup_main:
                    st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                elif has_dup_tech:
                    st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                else:
                    st.session_state.league_members[current_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                    
                    # Auto-trigger AI Brian picks
                    ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                    st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                    
                    save_league_data()
                    st.success(f"Predictions successfully submitted for {current_player} for Week {st.session_state.current_week}! AI Brian has also logged his picks.")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Performance & Momentum Trajectories")
    st.write("Examine technical challenge trends, star baker honors, and placement trajectories across the season.")
    
    if not st.session_state.weekly_results:
        st.info("No broadcast results logged yet. Analytics will activate after Episode 1 results are published!")
    else:
        st.subheader("📊 Cumulative Contestant Placement Matrix")
        baker_stats = []
        for b in ALL_BAKERS:
            b_stats = {"Baker": b, "Star Baker Count": 0, "Handshakes": 0, "Status": "Active in Tent ⛺"}
            for w in sorted(st.session_state.weekly_results.keys()):
                w_act = st.session_state.weekly_results[w]
                if w_act.get("star_baker") == b:
                    b_stats["Star Baker Count"] += 1
                if b in w_act.get("handshake_bakers", []):
                    b_stats["Handshakes"] += 1
                el = w_act.get("eliminated")
                if (isinstance(el, list) and b in el) or (el == b):
                    b_stats["Status"] = f"Eliminated (Week {w}) ❌"
            baker_stats.append(b_stats)
            
        st.dataframe(pd.DataFrame(baker_stats), use_container_width=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Use this tab to input the actual results from the broadcast. Submitting actual results will score the predictions and update the leaderboard!")
    
    # ADMIN PASSWORD PROTECTION
    if not st.session_state.admin_authenticated:
        st.markdown("### 🔒 Admin Security Gate")
        admin_pin_input = st.text_input("Enter Administrator PIN to Access Console:", type="password", key="admin_pin_gate")
        if st.button("Unlock Admin Console"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Console Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN!")
        st.info("🔒 Admin Panel is locked. Please enter PIN 6284 to continue.")
    else:
        col_adm_title, col_adm_lock = st.columns([4, 1])
        with col_adm_lock:
            if st.button("🔒 Lock Console"):
                st.session_state.admin_authenticated = False
                st.rerun()

        st.markdown("### 📅 Select Episode Results to Input")
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=st.session_state.current_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
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
        
        current_eliminated = eliminated_bakers_by_week.get(admin_selected_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        admin_dropdown_opts = ["--Select Baker--"] + active_bakers
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_dropdown_opts, key="act_champ")
                st.write("Actual Technical Challenge Rankings (1st through 3rd):")
                t1 = st.selectbox("Technical 1st Place", admin_dropdown_opts, key="act_t1_w10")
                t2 = st.selectbox("Technical 2nd Place", admin_dropdown_opts, key="act_t2_w10")
                t3 = st.selectbox("Technical 3rd Place", admin_dropdown_opts, key="act_t3_w10")
                actuals["tech_rank"] = [t1, t2, t3]
                
            elif admin_selected_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_opts, key="act_sb_w9")
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_opts, key="act_el_w9")
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week. Consolation and other categories are scored normally.")
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_opts, key="admin_act_elim_1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_opts, key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                
                st.write("Actual Technical Challenge Rankings (1st through 4th):")
                t1 = st.selectbox("Technical 1st Place", admin_dropdown_opts, key="act_t1_w9")
                t2 = st.selectbox("Technical 2nd Place", admin_dropdown_opts, key="act_t2_w9")
                t3 = st.selectbox("Technical 3rd Place", admin_dropdown_opts, key="act_t3_w9")
                t4 = st.selectbox("Technical 4th Place", admin_dropdown_opts, key="act_t4_w9")
                actuals["tech_rank"] = [t1, t2, t3, t4]

            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_opts, key=f"act_sb_w{admin_selected_week}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, key=f"act_inline_w{admin_selected_week}")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_opts, key=f"act_el_w{admin_selected_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"act_tr_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("No baker was eliminated this week. Predicting elimination scores 0.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, key=f"act_tr_sick_w{admin_selected_week}")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_opts, key=f"admin_act_elim_1_w{admin_selected_week}")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_opts, key=f"admin_act_elim_2_w{admin_selected_week}")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"act_tr_dbl_w{admin_selected_week}")
                    
                st.write(f"Actual Technical Challenge Rankings for Week {admin_selected_week} (1st through {len(active_bakers)}th Place):")
                tech_actuals_list = []
                num_tech_positions = len(active_bakers)
                for pos in range(1, num_tech_positions + 1):
                    suffix = "st" if pos == 1 else "nd" if pos == 2 else "rd" if pos == 3 else "th"
                    t_baker = st.selectbox(f"Actual Technical {pos}{suffix} Place", admin_dropdown_opts, key=f"act_tech_pos_{pos}_w{admin_selected_week}")
                    tech_actuals_list.append(t_baker)
                    
                actuals["tech_rank"] = tech_actuals_list
                if len(tech_actuals_list) >= 3:
                    actuals["tech_top_3"] = tech_actuals_list[:3]
                if len(tech_actuals_list) >= 3:
                    actuals["tech_bottom_3"] = tech_actuals_list[-3:]

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"handshake_bakers_w{admin_selected_week}")
            act_handshake_stamps = st.text_input("Handshake Video Timestamps & Context (e.g. 'Clara @ 14:22 Signature')", value="", key=f"handshake_stamps_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            act_crying_stamps = st.text_input("Crying Scene Video Timestamps & Context (e.g. 'Gabe @ 24:15 Technical')", value="", key=f"crying_stamps_w{admin_selected_week}")

            st.markdown("### 💬 Weekly Sexual Innuendos Count")
            act_innuendo_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0, key=f"innuendo_cnt_w{admin_selected_week}")

            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            
            if admin_selected_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", admin_dropdown_opts, key="act_season_winner_w10")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4, key="act_season_semis_w10")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3, key="act_season_finals_w10")
                
                act_handshakes = st.number_input("Actual Total Handshakes", min_value=0, value=5)
                act_crying = st.number_input("Actual Total Crying Scenes", min_value=0, value=12)
                act_innuendos = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48)
                
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
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # TRIGGER RECALCULATION
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
                    
                save_league_data()
                st.success(f"Week {admin_selected_week} broadcast results published! Leaderboard recalculated.")
                st.rerun()

        # --- PLAYER PASSWORD MANAGEMENT ---
        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_HUMANS, key="admin_pwd_reset_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            save_league_data()
            st.success(f"Password PIN for {reset_player} has been cleared!")

        # --- ERASE ALL SAVED DATA (VERY BOTTOM) ---
        st.markdown("---")
        st.markdown("### 🚨 Erase All Saved Data (Reset App State)")
        st.write("Use this feature after testing to wipe all test predictions, weekly broadcast actuals, disputes, and player passwords back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords", key="confirm_erase_chk")
        if st.button("Erase All Saved Data & Reset Application", type="primary"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["weekly_picks"] = {}
                    st.session_state.league_members[m_name]["season_picks"] = {}
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    st.session_state.league_members[m_name]["pin"] = None
                    st.session_state.league_members[m_name]["season_score"] = 0
                if os.path.exists(DATA_FILE):
                    os.remove(DATA_FILE)
                st.success("All saved data permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed.")
