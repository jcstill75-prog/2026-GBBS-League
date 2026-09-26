import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import json
import os

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
        # Sanitize any non-serializable objects
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
    except Exception as e:
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

# Initialize saved data or default state
saved_data = load_league_data()

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", 
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ALL_HUMANS_AND_AI = sorted(ROSTER_HUMANS) + ["AI Brian"]

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
        # Standard Weeks 2-7
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        
        if len(pred_top3) == 3 and len(act_top3) == 3:
            if pred_top3 == act_top3:
                score += 10
            else:
                if pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] == act_top3[2]: score += 2
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3 and baker != act_top3[idx]:
                        score += 1
                        
        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        
        if len(pred_bottom3) == 3 and len(act_bottom3) == 3:
            if pred_bottom3 == act_bottom3:
                score += 10
            else:
                if pred_bottom3[0] == act_bottom3[0]: score += 2
                if pred_bottom3[1] == act_bottom3[1]: score += 2
                if pred_bottom3[2] == act_bottom3[2]: score += 3
                for idx, baker in enumerate(pred_bottom3):
                    if baker in act_bottom3 and baker != act_bottom3[idx]:
                        score += 1

    # Consolations
    if week < 9:
        in_line = predictions.get("in_line_sb")
        act_in_line = actuals.get("in_line_sb", [])
        if in_line and in_line in act_in_line and in_line != actuals.get("star_baker"):
            score += 2
            
        in_trouble = predictions.get("in_trouble")
        act_in_trouble = actuals.get("in_trouble", [])
        if in_trouble and in_trouble in act_in_trouble and in_trouble != actuals.get("eliminated"):
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
    if pred_winner and act_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and pred_winner in act_finalists:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
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

def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    try:
        for filename in os.listdir("assets"):
            stem, ext = os.path.splitext(filename)
            if stem.lower().strip() == target and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                full_path = os.path.join("assets", filename)
                try:
                    return Image.open(full_path)
                except Exception:
                    pass
    except Exception:
        pass
    return None

# CORE BAKERS LIST
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

BAKER_INFO = {b: {"url": f"https://thegreatbritishbakeoff.co.uk/bakers/series-17-{b.lower()}/"} for b in ALL_BAKERS}

# AI Brian Automated Generators
def generate_ai_brian_season_picks():
    w = random.choice(ALL_BAKERS)
    rem = [b for b in ALL_BAKERS if b != w]
    semis = random.sample(rem, 3)
    return {
        "winner": w,
        "semifinalists": semis,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    picks = {}
    if week == 10:
        picks["show_champion"] = random.choice(active_bakers)
        picks["tech_rank"] = random.sample(active_bakers, min(3, len(active_bakers)))
    elif week == 9:
        sb = random.choice(active_bakers)
        picks["star_baker"] = sb
        rem = [b for b in active_bakers if b != sb]
        if is_double_elim and len(rem) >= 2:
            picks["eliminated"] = random.sample(rem, 2)
        else:
            picks["eliminated"] = random.choice(rem) if rem else "None"
        picks["tech_rank"] = random.sample(active_bakers, min(4, len(active_bakers)))
    elif week == 8:
        sb = random.choice(active_bakers)
        picks["star_baker"] = sb
        rem = [b for b in active_bakers if b != sb]
        picks["in_line_sb"] = random.choice(rem) if rem else None
        if is_double_elim and len(rem) >= 2:
            el = random.sample(rem, 2)
            picks["eliminated"] = el
            rem_tr = [b for b in rem if b not in el]
            picks["in_trouble"] = random.choice(rem_tr) if rem_tr else None
        else:
            el = random.choice(rem) if rem else None
            picks["eliminated"] = el
            rem_tr = [b for b in rem if b != el]
            picks["in_trouble"] = random.choice(rem_tr) if rem_tr else None
        picks["tech_rank"] = random.sample(active_bakers, min(5, len(active_bakers)))
    else:
        sb = random.choice(active_bakers)
        picks["star_baker"] = sb
        rem = [b for b in active_bakers if b != sb]
        picks["in_line_sb"] = random.choice(rem) if rem else None
        if is_double_elim and len(rem) >= 2:
            el = random.sample(rem, 2)
            picks["eliminated"] = el
            rem_tr = [b for b in rem if b not in el]
            picks["in_trouble"] = random.choice(rem_tr) if rem_tr else None
        else:
            el = random.choice(rem) if rem else None
            picks["eliminated"] = el
            rem_tr = [b for b in rem if b != el]
            picks["in_trouble"] = random.choice(rem_tr) if rem_tr else None
            
        t_top = random.sample(active_bakers, min(3, len(active_bakers)))
        t_rem = [b for b in active_bakers if b not in t_top]
        t_bot = random.sample(t_rem, min(3, len(t_rem))) if len(t_rem) >= 3 else t_rem
        picks["tech_top_3"] = t_top
        picks["tech_bottom_3"] = t_bot
    return picks

if not st.session_state.league_members["AI Brian"].get("season_picks"):
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- APP TITLE ---
st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: COMPETITION PROGRESS & 3-PART POINTS GUIDE ---
with st.sidebar:
    st.markdown("### 📌 Competition Progress")
    if active_week == 1:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nAll 12 bakers are active in the tent! Browse the gallery and scout contestants. Episodic ballots unlock in Week 2.")
    else:
        st.success(f"🟢 **Active Competition Week: Week {active_week}**")
        
    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of what points are at stake for each prediction!")
    st.warning("⏰ **Weekly voting window ends on Tuesdays right before the show airs in the UK.**")
    
    with st.expander("🌟 Season-Long Predictions", expanded=False):
        st.markdown("""
        *   **Season Winner:** 40 pts
        *   **Finalist Consolation:** 15 pts *(if picked winner makes Top 3 but loses)*
        *   **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        *   **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        *   **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        *   **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Weekly Predictions (Weeks 2-7)", expanded=False):
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
        
    with st.expander("🏁 Weekly Predictions (Weeks 8-10)", expanded=False):
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
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Contestant Analytics", 
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
        df_lb.index = df_lb.index + 1
        
        # Custom Table CSS for dark mode and light mode contrast
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
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
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
                .lb-table th { background-color: #3E2723 !important; color: #FFFFFF !important; }
                .lb-table td, .lb-rank, .lb-name { color: #FFFFFF !important; }
                .lb-pts { color: #FF8A80 !important; }
            }
            [data-theme="dark"] .lb-table th, .stApp[data-theme="dark"] .lb-table th {
                background-color: #3E2723 !important;
                color: #FFFFFF !important;
            }
            [data-theme="dark"] .lb-table td, [data-theme="dark"] .lb-rank, [data-theme="dark"] .lb-name,
            .stApp[data-theme="dark"] .lb-table td, .stApp[data-theme="dark"] .lb-rank, .stApp[data-theme="dark"] .lb-name {
                color: #FFFFFF !important;
            }
            [data-theme="dark"] .lb-pts, .stApp[data-theme="dark"] .lb-pts {
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

    # --- RUNNING CHAOS CATEGORIES BROADCAST TOTALS ---
    st.markdown("---")
    st.subheader("🌀 Running Chaos Categories Broadcast Totals")
    
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
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ALL_HUMANS_AND_AI, key="lb_player_card_sel")
    
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Scorecard (Total Points: {p_pts} pts)**")
        
        # Password protect season predictions for human players
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
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True)
        else:
            st.info("No weekly predictions logged yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps (Verify Counts)")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes, Crying incidents, and Innuendos.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_cnt = w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_cnt = w_act.get("crying_count", 0)
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes (Count & Details)": f"{hs_cnt} | {hs_stamps}",
                "Crying (Count & Details)": f"{cry_cnt} | {cry_stamps}",
                "Innuendos (Count & Details)": f"{inn_cnt} | {inn_stamps}"
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("Browse the Series 17 Bakers:")
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
                    st.markdown(f"[🔗 Profile Page]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    
    if active_week == 1:
        st.info("🔍 **Week 1 Scouting Phase Active!** Weekly prediction ballots unlock in Week 2 after Episode 1 results are published by the Admin.")
    else:
        st.subheader(f"📅 Submit Predictions: Week {active_week}")
        st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
        
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
        
        st.info(f"Active Bakers in the Tent for Week {active_week}: " + ", ".join(active_bakers))
        
        is_double_elim = False
        if active_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=False)
            
        user_submitting_player = st.selectbox("Select Your Player Name:", ROSTER_HUMANS, key="submit_player_sel")
        
        # PIN Authentication for submitting player
        player_authenticated = False
        existing_pin = st.session_state.player_pins.get(user_submitting_player)
        
        if not existing_pin:
            st.warning(f"🔑 Welcome {user_submitting_player}! Please create a 4-digit PIN to secure your ballots.")
            new_pin = st.text_input("Create 4-Digit Security PIN:", type="password", key="create_pin_input")
            confirm_pin = st.text_input("Confirm 4-Digit Security PIN:", type="password", key="confirm_pin_input")
            if st.button("Set My Security PIN"):
                if len(new_pin) == 4 and new_pin.isdigit():
                    if new_pin == confirm_pin:
                        st.session_state.player_pins[user_submitting_player] = new_pin
                        save_league_data()
                        st.success("✅ PIN created successfully!")
                        st.rerun()
                    else:
                        st.error("❌ PINs do not match.")
                else:
                    st.error("❌ PIN must be exactly 4 digits.")
        else:
            enter_pin = st.text_input(f"Enter 4-Digit Security PIN for {user_submitting_player}:", type="password", key="enter_pin_input")
            if enter_pin == existing_pin:
                player_authenticated = True
                st.success(f"🔓 Authenticated as {user_submitting_player}")
            elif enter_pin != "":
                st.error("❌ Incorrect PIN")
                
        if player_authenticated:
            # COMBINED WEEK 2 BALLOT (SEASON-LONG + WEEK 2)
            if active_week == 2:
                st.markdown("---")
                st.subheader("🌟 Season-Long Projections (Locks in Week 2!)")
                user_winner = st.selectbox("Predict Season Winner [40 pts]", dropdown_options, key="user_win_pick")
                user_semi1 = st.selectbox("Predict Semifinalist #1 [10 pts]", dropdown_options, key="user_semi1_pick")
                user_semi2 = st.selectbox("Predict Semifinalist #2 [10 pts]", dropdown_options, key="user_semi2_pick")
                user_semi3 = st.selectbox("Predict Semifinalist #3 [10 pts]", dropdown_options, key="user_semi3_pick")
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)

            st.markdown("---")
            st.subheader(f"📅 Week {active_week} Predictions Ballot")
            
            with st.form("weekly_predictions_form"):
                weekly_picks = {}
                if active_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", dropdown_options)
                    st.write("Technical Challenge Placement Predictions:")
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
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", dropdown_options)
                    
                    st.write("Technical Challenge Placement Predictions:")
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
                    
                    # 1. Validate Combined Season Picks in Week 2
                    if active_week == 2:
                        s_choices = [user_winner, user_semi1, user_semi2, user_semi3]
                        if "--Select Baker--" in s_choices:
                            errors.append("⚠️ Please select a valid baker for all Season-Long Prediction fields.")
                        else:
                            if len(set(s_choices)) < len(s_choices):
                                errors.append("❌ Duplicate Selection Error: Season Winner and Semifinalists must all be distinct bakers.")
                                
                    # 2. Validate Main Weekly Picks
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
                        
                    # Unselected check for main picks
                    all_req_main = []
                    for k in ["star_baker", "in_line_sb", "show_champion", "in_trouble"]:
                        if k in weekly_picks: all_req_main.append(weekly_picks[k])
                    if isinstance(el_v, list): all_req_main.extend(el_v)
                    elif isinstance(el_v, str): all_req_main.append(el_v)
                    
                    if "--Select Baker--" in all_req_main:
                        errors.append("⚠️ Missing Selection Error: Please make a selection for all required main prediction fields.")
                    elif len(set(main_picks)) < len(main_picks):
                        errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated.")
                        
                    # 3. Validate Technical Picks
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
                        # SAVE BALLOT
                        if active_week == 2:
                            st.session_state.league_members[user_submitting_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": [user_semi1, user_semi2, user_semi3],
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                        st.session_state.league_members[user_submitting_player]["weekly_picks"][active_week] = weekly_picks
                        
                        # AI Brian automatic submission
                        ai_picks = generate_ai_brian_weekly_picks(active_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][active_week] = ai_picks
                        
                        save_league_data()
                        st.success(f"🎉 Predictions successfully saved for {user_submitting_player} (Week {active_week})! AI Brian has also logged his picks.")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Inspect details and track individual baker performance across Series 17:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS)
    
    col_img, col_details = st.columns([1, 2])
    with col_img:
        b_img = load_baker_image(selected_baker)
        if b_img is not None:
            st.image(b_img, caption=selected_baker, use_container_width=True)
        else:
            st.info(f"📸 Photograph of {selected_baker}")
    with col_details:
        st.subheader(f"Baker Profile: {selected_baker}")
        b_info = BAKER_INFO.get(selected_baker, {})
        st.markdown(f"[🔗 Official Show Profile Page]({b_info.get('url', '#')})")

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
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        
        admin_selected_week = st.selectbox(
            "Select Week to Input Official Broadcast Results:",
            list(range(1, 11)),
            index=active_week - 1
        )
        
        eliminated_bakers_by_week_admin = {
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
        
        admin_curr_elim = eliminated_bakers_by_week_admin.get(admin_selected_week, [])
        admin_active_bakers = [b for b in ALL_BAKERS if b not in admin_curr_elim]
        admin_dropdown_options = ["--Select Baker--"] + admin_active_bakers
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Official Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_dropdown_options)
                st.write("Actual Technical Challenge Placement (1st to 3rd):")
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_dropdown_options, key="act_t1_w10")
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_dropdown_options, key="act_t2_w10")
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_dropdown_options, key="act_t3_w10")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
                
            elif admin_selected_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_options)
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_options, key="act_elim_w9")
                elif elim_type == "No Elimination (Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_options, key="act_elim1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_options, key="act_elim2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                
                st.write("Actual Technical Challenge Placement (1st to 4th):")
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_dropdown_options, key="act_t1_w9")
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_dropdown_options, key="act_t2_w9")
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_dropdown_options, key="act_t3_w9")
                act_t4 = st.selectbox("Actual Technical 4th Place", admin_dropdown_options, key="act_t4_w9")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

            elif admin_selected_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_options)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers)
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_options, key="act_elim_w8")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key="act_tr_w8")
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key="act_tr_w8")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_options, key="act_elim1_w8")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_options, key="act_elim2_w8")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key="act_tr_w8")
                    
                st.write("Actual Technical Challenge Placement (1st to 5th):")
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_dropdown_options, key="act_t1_w8")
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_dropdown_options, key="act_t2_w8")
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_dropdown_options, key="act_t3_w8")
                act_t4 = st.selectbox("Actual Technical 4th Place", admin_dropdown_options, key="act_t4_w8")
                act_t5 = st.selectbox("Actual Technical 5th Place", admin_dropdown_options, key="act_t5_w8")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
                
            else: # Weeks 1-7
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_dropdown_options)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers)
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_std")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_dropdown_options, key="act_elim_std")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key="act_tr_std")
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key="act_tr_std")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_dropdown_options, key="act_elim1_std")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_dropdown_options, key="act_elim2_std")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key="act_tr_std")
                    
                st.write("Actual Technical Challenge Placement (Position-by-Position for All Active Bakers):")
                tech_positions = []
                for idx, _ in enumerate(admin_active_bakers):
                    pos_name = f"Technical Position #{idx+1}"
                    if idx == 0: pos_name += " (1st Place)"
                    elif idx == len(admin_active_bakers) - 1: pos_name += " (Last Place)"
                    t_val = st.selectbox(pos_name, admin_dropdown_options, key=f"admin_pos_{idx}_w{admin_selected_week}")
                    tech_positions.append(t_val)
                    
                if len(tech_positions) >= 3:
                    actuals["tech_top_3"] = tech_positions[:3]
                if len(tech_positions) >= 6:
                    actuals["tech_bottom_3"] = tech_positions[-3:]
                else:
                    actuals["tech_bottom_3"] = tech_positions[3:] if len(tech_positions) > 3 else []
                    
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            with col_hs1:
                act_handshake_cnt = st.number_input("Number of Handshake Occurrences", min_value=0, value=0, key=f"adm_hs_cnt_w{admin_selected_week}")
            with col_hs2:
                act_handshake_stamps = st.text_input("Handshake Circumstances & Video Timestamps", value="", placeholder="e.g., Clara @ 14:22 Signature, Tom @ 42:10 Showstopper", key=f"adm_hs_stamps_w{admin_selected_week}")
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", admin_active_bakers, key=f"adm_hs_bakers_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Occurrences", min_value=0, value=0, key=f"adm_cry_cnt_w{admin_selected_week}")
            with col_cry2:
                act_crying_stamps = st.text_input("Crying Circumstances & Video Timestamps", value="", placeholder="e.g., Gabe @ 24:15 Technical, Molly @ 54:02 Elimination", key=f"adm_cry_stamps_w{admin_selected_week}")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Innuendo Occurrences", min_value=0, value=0, key=f"adm_inn_cnt_w{admin_selected_week}")
            with col_inn2:
                act_innuendo_stamps = st.text_input("Innuendo Circumstances & Video Timestamps", value="", placeholder="e.g., Prue soggy bottom @ 12:10, Paul big nuts comment @ 33:45", key=f"adm_inn_stamps_w{admin_selected_week}")

            actuals["handshake_count"] = act_handshake_cnt
            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            actuals["innuendo_timestamps"] = act_innuendo_stamps

            submit_admin = st.form_submit_button("Publish Official Week Results & Recalculate Standings")
            
            if submit_admin:
                st.session_state.weekly_results[admin_selected_week] = actuals
                
                # Recalculate scores for all members
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
                                    
                for m_name in ALL_HUMAN
