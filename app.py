import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import os
import json
import base64

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
</style>
""", unsafe_allow_html=True)

# --- 2. OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
    # Main Episode Results
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim: score += 5
            elif isinstance(pred_elim, str):
                if pred_elim in act_elim: score += 5
        elif act_elim == "None":
            pass
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: score += 5
            elif pred_elim == act_elim:
                score += 5
            
    # Technical Challenge
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
        if len(pred_top3) == 3 and len(act_top3) == 3:
            if pred_top3 == act_top3:
                score += 10
            else:
                for idx, baker in enumerate(pred_top3):
                    if baker == act_top3[idx]:
                        score += 3 if idx == 0 else 2
                    elif baker in act_top3:
                        score += 1
                        
        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        if len(pred_bottom3) == 3 and len(act_bottom3) == 3:
            if pred_bottom3 == act_bottom3:
                score += 10
            else:
                for idx, baker in enumerate(pred_bottom3):
                    if baker == act_bottom3[idx]:
                        score += 3 if idx == 2 else 2
                    elif baker in act_bottom3:
                        score += 1

    # Consolations
    if week < 9:
        if (predictions.get("in_line_sb") in actuals.get("in_line_sb", [])) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2
        if (predictions.get("in_trouble") in actuals.get("in_trouble", [])) and (predictions.get("in_trouble") != actuals.get("eliminated")):
            score += 2
            
    return score

def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner == act_winner:
        score += 40
    elif pred_winner in act_finalists:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    pred_handshakes = predictions.get("handshakes")
    act_handshakes = actuals.get("handshakes")
    if pred_handshakes is not None and act_handshakes is not None:
        if pred_handshakes == act_handshakes: score += 20
        elif abs(pred_handshakes - act_handshakes) <= 1: score += 10
            
    pred_crying = predictions.get("crying")
    act_crying = actuals.get("crying")
    if pred_crying is not None and act_crying is not None:
        if pred_crying == act_crying: score += 20
        elif abs(pred_crying - act_crying) <= 5: score += 10
            
    pred_innuendos = predictions.get("innuendos")
    act_innuendos = actuals.get("innuendos")
    if pred_innuendos is not None and act_innuendos is not None:
        if pred_innuendos == act_innuendos: score += 20
        elif abs(pred_innuendos - act_innuendos) <= 5: score += 10
            
    return score

def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    try:
        for filename in os.listdir("assets"):
            stem, ext = os.path.splitext(filename)
            if stem.lower().strip() == target and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                return Image.open(os.path.join("assets", filename))
    except Exception:
        pass
    return None

# --- 3. CORE BAKERS LIST & ROSTER --- 
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

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", "Jasmine", 
    "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]
ROSTER_ALL = sorted(ROSTER_HUMANS + ["AI Brian"])

DATA_FILE = "league_data.json"

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_league_data():
    try:
        data_to_save = {
            "league_members": st.session_state.league_members,
            "weekly_results": st.session_state.weekly_results,
            "season_results": st.session_state.season_results,
            "current_week": st.session_state.current_week,
            "disputes": st.session_state.disputes
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data_to_save, f, indent=2)
    except Exception:
        pass

saved_data = load_league_data()

if "league_members" not in st.session_state:
    if saved_data and "league_members" in saved_data:
        st.session_state.league_members = saved_data["league_members"]
    else:
        st.session_state.league_members = {}
        for member_name in ROSTER_ALL:
            st.session_state.league_members[member_name] = {
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": "1234"
            }

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_data.get("weekly_results", {}) if saved_data else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_data.get("season_results", {}) if saved_data else {}

if "current_week" not in st.session_state:
    st.session_state.current_week = saved_data.get("current_week", 1) if saved_data else 1

if "disputes" not in st.session_state:
    st.session_state.disputes = saved_data.get("disputes", []) if saved_data else []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

def generate_ai_brian_season_picks():
    w = random.choice(ALL_BAKERS)
    rem = [b for b in ALL_BAKERS if b != w]
    s = random.sample(rem, 3)
    return {
        "winner": w,
        "semifinalists": s,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    picks = {}
    if week == 10:
        w = random.choice(active_bakers)
        picks["show_champion"] = w
        picks["tech_rank"] = random.sample(active_bakers, len(active_bakers))
    elif week == 9:
        sb = random.choice(active_bakers)
        picks["star_baker"] = sb
        rem = [b for b in active_bakers if b != sb]
        if is_double_elim and len(rem) >= 2:
            picks["eliminated"] = random.sample(rem, 2)
        elif rem:
            picks["eliminated"] = random.choice(rem)
        picks["tech_rank"] = random.sample(active_bakers, len(active_bakers))
    elif week == 8:
        sb = random.choice(active_bakers)
        picks["star_baker"] = sb
        rem = [b for b in active_bakers if b != sb]
        picks["in_line_sb"] = random.choice(rem) if rem else sb
        if is_double_elim and len(rem) >= 2:
            picks["eliminated"] = random.sample(rem, 2)
            rem_trouble = [b for b in active_bakers if b not in picks["eliminated"]]
            picks["in_trouble"] = random.choice(rem_trouble) if rem_trouble else sb
        elif rem:
            el = random.choice(rem)
            picks["eliminated"] = el
            rem_trouble = [b for b in active_bakers if b != el]
            picks["in_trouble"] = random.choice(rem_trouble) if rem_trouble else sb
        picks["tech_rank"] = random.sample(active_bakers, len(active_bakers))
    else:
        sb = random.choice(active_bakers)
        picks["star_baker"] = sb
        rem = [b for b in active_bakers if b != sb]
        picks["in_line_sb"] = random.choice(rem) if rem else sb
        if is_double_elim and len(rem) >= 2:
            picks["eliminated"] = random.sample(rem, 2)
            rem_trouble = [b for b in active_bakers if b not in picks["eliminated"]]
            picks["in_trouble"] = random.choice(rem_trouble) if rem_trouble else sb
        elif rem:
            el = random.choice(rem)
            picks["eliminated"] = el
            rem_trouble = [b for b in active_bakers if b != el]
            picks["in_trouble"] = random.choice(rem_trouble) if rem_trouble else sb
        
        t_sample = random.sample(active_bakers, min(6, len(active_bakers)))
        picks["tech_top_3"] = t_sample[:3]
        picks["tech_bottom_3"] = t_sample[3:6]
    return picks

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 4. APP TITLE & SIDEBAR --- 
st.title("🧁 Great British Baking Show Fantasy League 2026")

with st.sidebar:
    st.markdown("### 📌 Competition Progress")
    active_week = st.session_state.get("current_week", 1)
    
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

# --- 5. MAIN NAVIGATION TABS --- 
tab_lead, tab_submit, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "👑 Admin Panel"])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
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
                color: #2C1810;
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
            [data-theme="dark"] .lb-table th, .stApp[data-theme="dark"] .lb-table th, [data-testid="stAppViewContainer"][data-theme="dark"] .lb-table th {
                background-color: #3E2723 !important;
                color: #FFFFFF !important;
            }
            [data-theme="dark"] .lb-table td, [data-theme="dark"] .lb-rank, [data-theme="dark"] .lb-name,
            .stApp[data-theme="dark"] .lb-table td, .stApp[data-theme="dark"] .lb-rank, .stApp[data-theme="dark"] .lb-name,
            [data-testid="stAppViewContainer"][data-theme="dark"] .lb-table td,
            [data-testid="stAppViewContainer"][data-theme="dark"] .lb-rank,
            [data-testid="stAppViewContainer"][data-theme="dark"] .lb-name {
                color: #FFFFFF !important;
            }
            [data-theme="dark"] .lb-pts, .stApp[data-theme="dark"] .lb-pts, [data-testid="stAppViewContainer"][data-theme="dark"] .lb-pts {
                color: #FF8A80 !important;
            }
            [data-theme="light"] .lb-table td, [data-theme="light"] .lb-rank, [data-theme="light"] .lb-name,
            .stApp[data-theme="light"] .lb-table td, .stApp[data-theme="light"] .lb-rank, .stApp[data-theme="light"] .lb-name,
            [data-testid="stAppViewContainer"][data-theme="light"] .lb-table td,
            [data-testid="stAppViewContainer"][data-theme="light"] .lb-rank,
            [data-testid="stAppViewContainer"][data-theme="light"] .lb-name {
                color: #2C1810 !important;
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
            
            html_rows.append(
                f'<tr><td class="lb-rank">{rank_badge}</td>'
                f'<td class="lb-name">{m_name}</td>'
                f'<td class="lb-pts">{m_pts} pts</td></tr>'
            )
            
        table_html = (
            '<table class="lb-table">'
            '<thead><tr>'
            '<th style="width: 100px;">Rank</th>'
            '<th>League Member</th>'
            '<th style="text-align: right; width: 140px;">Total Points</th>'
            '</tr></thead>'
            f'<tbody>{"".join(html_rows)}</tbody>'
            '</table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🌀 Chaos Categories Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    if st.session_state.weekly_results:
        for w_num, w_act in st.session_state.weekly_results.items():
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
    st.subheader("📋 Individual Player Scorecards & Projections")
    st.write("Select a player profile below to view their weekly predictions and season projections.")
    
    selected_sc_player = st.selectbox("Select Player Scorecard to View:", ROSTER_ALL, key="sc_player_select")
    
    if selected_sc_player:
        p_data = st.session_state.league_members.get(selected_sc_player, {})
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### 👤 Scorecard for **{selected_sc_player}** (Total Score: **{p_pts} pts**)")
        
        # 1. Season-Wide Predictions (Unprotected & Public)
        st.markdown("#### **🌟 Season-Long Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
        
        # 2. Weekly Predictions Log
        st.markdown("#### **📅 Weekly Predictions Log**")
        if not p_weekly:
            st.info(f"No weekly predictions recorded yet for {selected_sc_player}.")
        else:
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                t3 = ", ".join(w_picks.get("tech_top_3", [])) if w_picks.get("tech_top_3") else "N/A"
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Top 3": t3
                })
            st.dataframe(pd.DataFrame(w_rows), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.header("📺 Crying and Innuendo Occurrences")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Crying incidents and Sexual Innuendos, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            cry_cnt = w_act.get("crying_count", 0)
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Crying Occurrences": cry_cnt,
                "Crying Notes & Video Timestamps": cry_stamps,
                "Innuendo Occurrences": inn_cnt,
                "Innuendo Notes & Video Timestamps": inn_stamps
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

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
            disp_evidence = st.text_area("Video Timestamp & Video Evidence (e.g., 'At 28:14 in Episode 3, Paul clearly shakes Tom's hand during Showstopper judging')")
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
        user_pin = st.text_input("Enter Your 4-Digit Security PIN:", type="password", key="submit_player_pin", max_chars=4)
        
        stored_pin = st.session_state.league_members[user_submitting_player].get("pin", "1234")
        
        if user_pin != stored_pin:
            st.warning(f"🔒 Please enter the correct PIN for {user_submitting_player} to unlock the prediction forms below.")
        else:
            st.success(f"🔓 Profile Unlocked for {user_submitting_player}")
            
            if st.session_state.current_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_dropdown_options, key="user_win_pick")
                    user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", active_bakers, max_selections=3)
                    user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                    user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)
                    
                    if st.button("Lock Season-Long Predictions"):
                        if user_winner == "--Select Baker--":
                            st.error("Please select a valid baker for Season Winner.")
                        elif len(user_semis) != 3:
                            st.error("Please select exactly 3 other semifinalists.")
                        elif user_winner in user_semis:
                            st.error("Season Winner cannot also be listed as one of the other 3 semifinalists.")
                        else:
                            st.session_state.league_members[user_submitting_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
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
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_dropdown_options, key="pred_elim_1_w9")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_dropdown_options, key="pred_elim_2_w9")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_dropdown_options)
                    
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
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_dropdown_options)
                    with col2:
                        if is_double_elim:
                            elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_dropdown_options, key="pred_elim_1_w8")
                            elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_dropdown_options, key="pred_elim_2_w8")
                            weekly_picks["eliminated"] = [elim_1, elim_2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_dropdown_options, key="pred_trb_w8")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_dropdown_options)
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_dropdown_options, key="pred_trb_w8")
                    
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
                            elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_dropdown_options, key="pred_elim_1_std")
                            elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_dropdown_options, key="pred_elim_2_std")
                            weekly_picks["eliminated"] = [elim_1, elim_2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_dropdown_options, key="pred_trb_std")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_dropdown_options)
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_dropdown_options, key="pred_trb_std")
                        
                    st.markdown("---")
                    st.markdown("**Predict Technical Challenge Placements:**")
                    tt1 = st.selectbox("Technical 1st Place [3 pts]", baker_dropdown_options, key="tt1_std")
                    tt2 = st.selectbox("Technical 2nd Place [2 pts]", baker_dropdown_options, key="tt2_std")
                    tt3 = st.selectbox("Technical 3rd Place [2 pts]", baker_dropdown_options, key="tt3_std")
                    tb1 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_dropdown_options, key="tb1_std")
                    tb2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_dropdown_options, key="tb2_std")
                    tb3 = st.selectbox("Technical Last Place [3 pts]", baker_dropdown_options, key="tb3_std")
                    
                    weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                    weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]
                    
                submitted = st.form_submit_button("Submit Predictions")
                if submitted:
                    all_selected = []
                    if st.session_state.current_week < 8:
                        main_picks = [weekly_picks.get("star_baker"), weekly_picks.get("in_line_sb"), weekly_picks.get("in_trouble")]
                        if isinstance(weekly_picks.get("eliminated"), list):
                            main_picks.extend(weekly_picks.get("eliminated"))
                        else:
                            main_picks.append(weekly_picks.get("eliminated"))
                        tech_picks = weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])
                    elif st.session_state.current_week == 10:
                        main_picks = [weekly_picks.get("show_champion")]
                        tech_picks = weekly_picks.get("tech_rank", [])
                    else:
                        main_picks = [weekly_picks.get("star_baker")]
                        if "in_line_sb" in weekly_picks: main_picks.append(weekly_picks.get("in_line_sb"))
                        if "in_trouble" in weekly_picks: main_picks.append(weekly_picks.get("in_trouble"))
                        if isinstance(weekly_picks.get("eliminated"), list):
                            main_picks.extend(weekly_picks.get("eliminated"))
                        else:
                            main_picks.append(weekly_picks.get("eliminated"))
                        tech_picks = weekly_picks.get("tech_rank", [])
                        
                    if "--Select Baker--" in main_picks or "--Select Baker--" in tech_picks:
                        st.error("⚠️ Missing Selection Error: Please select a valid baker for all prediction fields before submitting!")
                    else:
                        clean_main = [b for b in main_picks if b != "--Select Baker--"]
                        clean_tech = [b for b in tech_picks if b != "--Select Baker--"]
                        
                        if len(clean_main) != len(set(clean_main)):
                            st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                        elif len(clean_tech) != len(set(clean_tech)):
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            st.session_state.league_members[user_submitting_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                            save_league_data()
                            st.success(f"Predictions submitted successfully for {user_submitting_player} (Week {st.session_state.current_week})! AI Brian has also submitted his picks.")

# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Input actual broadcast results here to calculate player scores and update the leaderboard.")
    
    admin_pin = st.text_input("Enter Administrator Security PIN:", type="password", key="admin_pin_input")
    if admin_pin == "6284":
        st.session_state.admin_authenticated = True
        st.success("🔓 Administrator Console Unlocked!")
    
    if not st.session_state.admin_authenticated:
        st.warning("🔒 Admin panel is locked. Please enter PIN 6284 above to gain administrative access.")
    else:
        admin_selected_week = st.selectbox("Select Week to Record or Review Broadcast Results:", list(range(1, 11)), index=min(st.session_state.current_week - 1, 9))
        
        saved_w = st.session_state.weekly_results.get(admin_selected_week, {})
        is_published = admin_selected_week in st.session_state.weekly_results
        
        if is_published:
            st.info(f"ℹ️ Results for Week {admin_selected_week} are saved in memory. You can review or edit them below.")
            
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
        admin_baker_options = ["--Select Baker--"] + active_bakers
        
        def get_opt_idx(val, options):
            if isinstance(val, str) and val in options:
                return options.index(val)
            return 0
            
        def get_multi_default(val_list, options):
            if isinstance(val_list, list):
                return [b for b in val_list if b in options]
            return []
            
        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_baker_options, index=get_opt_idx(saved_w.get("show_champion"), admin_baker_options))
                st.markdown("**Actual Technical Challenge Rankings:**")
                saved_tr = saved_w.get("tech_rank", ["--Select Baker--"]*3)
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_baker_options, index=get_opt_idx(saved_tr[0] if len(saved_tr)>0 else None, admin_baker_options), key=f"act_t1_w10_{admin_selected_week}")
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_baker_options, index=get_opt_idx(saved_tr[1] if len(saved_tr)>1 else None, admin_baker_options), key=f"act_t2_w10_{admin_selected_week}")
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_baker_options, index=get_opt_idx(saved_tr[2] if len(saved_tr)>2 else None, admin_baker_options), key=f"act_t3_w10_{admin_selected_week}")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
                
            elif admin_selected_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, index=get_opt_idx(saved_w.get("star_baker"), admin_baker_options))
                saved_elim = saved_w.get("eliminated", "Single Elimination")
                elim_init_idx = 0
                if saved_elim == "None": elim_init_idx = 1
                elif isinstance(saved_elim, list): elim_init_idx = 2
                
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], index=elim_init_idx, horizontal=True, key=f"admin_elim_type_w9_{admin_selected_week}")
                if elim_type == "Single Elimination":
                    s_el = saved_elim if isinstance(saved_elim, str) else "--Select Baker--"
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, index=get_opt_idx(s_el, admin_baker_options), key=f"act_elim_single_w9_{admin_selected_week}")
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    e1 = saved_elim[0] if isinstance(saved_elim, list) and len(saved_elim)>0 else "--Select Baker--"
                    e2 = saved_elim[1] if isinstance(saved_elim, list) and len(saved_elim)>1 else "--Select Baker--"
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, index=get_opt_idx(e1, admin_baker_options), key=f"admin_act_elim_1_w9_{admin_selected_week}")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_baker_options, index=get_opt_idx(e2, admin_baker_options), key=f"admin_act_elim_2_w9_{admin_selected_week}")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                
                st.markdown("**Actual Technical Challenge Rankings:**")
                saved_tr = saved_w.get("tech_rank", ["--Select Baker--"]*4)
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_baker_options, index=get_opt_idx(saved_tr[0] if len(saved_tr)>0 else None, admin_baker_options), key=f"act_t1_w9_{admin_selected_week}")
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_baker_options, index=get_opt_idx(saved_tr[1] if len(saved_tr)>1 else None, admin_baker_options), key=f"act_t2_w9_{admin_selected_week}")
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_baker_options, index=get_opt_idx(saved_tr[2] if len(saved_tr)>2 else None, admin_baker_options), key=f"act_t3_w9_{admin_selected_week}")
                act_t4 = st.selectbox("Actual Technical 4th Place", admin_baker_options, index=get_opt_idx(saved_tr[3] if len(saved_tr)>3 else None, admin_baker_options), key=f"act_t4_w9_{admin_selected_week}")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

            elif admin_selected_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, index=get_opt_idx(saved_w.get("star_baker"), admin_baker_options))
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, default=get_multi_default(saved_w.get("in_line_sb"), active_bakers))
                with col2:
                    saved_elim = saved_w.get("eliminated", "Single Elimination")
                    elim_init_idx = 0
                    if saved_elim == "None": elim_init_idx = 1
                    elif isinstance(saved_elim, list): elim_init_idx = 2
                    
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], index=elim_init_idx, horizontal=True, key=f"admin_elim_type_w8_{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        s_el = saved_elim if isinstance(saved_elim, str) else "--Select Baker--"
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, index=get_opt_idx(s_el, admin_baker_options), key=f"act_elim_single_w8_{admin_selected_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=get_multi_default(saved_w.get("in_trouble"), active_bakers), key=f"admin_trb_w8_{admin_selected_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, default=get_multi_default(saved_w.get("in_trouble"), active_bakers), key=f"admin_trb_w8_{admin_selected_week}")
                    else:
                        e1 = saved_elim[0] if isinstance(saved_elim, list) and len(saved_elim)>0 else "--Select Baker--"
                        e2 = saved_elim[1] if isinstance(saved_elim, list) and len(saved_elim)>1 else "--Select Baker--"
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, index=get_opt_idx(e1, admin_baker_options), key=f"admin_act_elim_1_w8_{admin_selected_week}")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_baker_options, index=get_opt_idx(e2, admin_baker_options), key=f"admin_act_elim_2_w8_{admin_selected_week}")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=get_multi_default(saved_w.get("in_trouble"), active_bakers), key=f"admin_trb_w8_{admin_selected_week}")
                    
                st.markdown("**Actual Technical Challenge Rankings:**")
                saved_tr = saved_w.get("tech_rank", ["--Select Baker--"]*5)
                act_t1 = st.selectbox("Actual Technical 1st Place", admin_baker_options, index=get_opt_idx(saved_tr[0] if len(saved_tr)>0 else None, admin_baker_options), key=f"act_t1_w8_{admin_selected_week}")
                act_t2 = st.selectbox("Actual Technical 2nd Place", admin_baker_options, index=get_opt_idx(saved_tr[1] if len(saved_tr)>1 else None, admin_baker_options), key=f"act_t2_w8_{admin_selected_week}")
                act_t3 = st.selectbox("Actual Technical 3rd Place", admin_baker_options, index=get_opt_idx(saved_tr[2] if len(saved_tr)>2 else None, admin_baker_options), key=f"act_t3_w8_{admin_selected_week}")
                act_t4 = st.selectbox("Actual Technical 4th Place", admin_baker_options, index=get_opt_idx(saved_tr[3] if len(saved_tr)>3 else None, admin_baker_options), key=f"act_t4_w8_{admin_selected_week}")
                act_t5 = st.selectbox("Actual Technical 5th Place", admin_baker_options, index=get_opt_idx(saved_tr[4] if len(saved_tr)>4 else None, admin_baker_options), key=f"act_t5_w8_{admin_selected_week}")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
                
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, index=get_opt_idx(saved_w.get("star_baker"), admin_baker_options))
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, default=get_multi_default(saved_w.get("in_line_sb"), active_bakers))
                with col2:
                    saved_elim = saved_w.get("eliminated", "Single Elimination")
                    elim_init_idx = 0
                    if saved_elim == "None": elim_init_idx = 1
                    elif isinstance(saved_elim, list): elim_init_idx = 2
                    
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], index=elim_init_idx, horizontal=True, key=f"admin_elim_type_std_{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        s_el = saved_elim if isinstance(saved_elim, str) else "--Select Baker--"
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, index=get_opt_idx(s_el, admin_baker_options), key=f"act_elim_single_std_{admin_selected_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=get_multi_default(saved_w.get("in_trouble"), active_bakers), key=f"admin_trb_std_{admin_selected_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, default=get_multi_default(saved_w.get("in_trouble"), active_bakers), key=f"admin_trb_std_{admin_selected_week}")
                    else:
                        e1 = saved_elim[0] if isinstance(saved_elim, list) and len(saved_elim)>0 else "--Select Baker--"
                        e2 = saved_elim[1] if isinstance(saved_elim, list) and len(saved_elim)>1 else "--Select Baker--"
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", admin_baker_options, index=get_opt_idx(e1, admin_baker_options), key=f"admin_act_elim_1_std_{admin_selected_week}")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", admin_baker_options, index=get_opt_idx(e2, admin_baker_options), key=f"admin_act_elim_2_std_{admin_selected_week}")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=get_multi_default(saved_w.get("in_trouble"), active_bakers), key=f"admin_trb_std_{admin_selected_week}")
                    
                st.markdown("---")
                st.markdown("**Actual Technical Challenge Rankings:**")
                saved_tt = saved_w.get("tech_top_3", ["--Select Baker--"]*3)
                saved_tb = saved_w.get("tech_bottom_3", ["--Select Baker--"]*3)
                act_tt1 = st.selectbox("Actual Technical 1st Place", admin_baker_options, index=get_opt_idx(saved_tt[0] if len(saved_tt)>0 else None, admin_baker_options), key=f"act_tt1_std_{admin_selected_week}")
                act_tt2 = st.selectbox("Actual Technical 2nd Place", admin_baker_options, index=get_opt_idx(saved_tt[1] if len(saved_tt)>1 else None, admin_baker_options), key=f"act_tt2_std_{admin_selected_week}")
                act_tt3 = st.selectbox("Actual Technical 3rd Place", admin_baker_options, index=get_opt_idx(saved_tt[2] if len(saved_tt)>2 else None, admin_baker_options), key=f"act_tt3_std_{admin_selected_week}")
                act_tb1 = st.selectbox("Actual Technical 3rd-to-Last Place", admin_baker_options, index=get_opt_idx(saved_tb[0] if len(saved_tb)>0 else None, admin_baker_options), key=f"act_tb1_std_{admin_selected_week}")
                act_tb2 = st.selectbox("Actual Technical 2nd-to-Last Place", admin_baker_options, index=get_opt_idx(saved_tb[1] if len(saved_tb)>1 else None, admin_baker_options), key=f"act_tb2_std_{admin_selected_week}")
                act_tb3 = st.selectbox("Actual Technical Last Place", admin_baker_options, index=get_opt_idx(saved_tb[2] if len(saved_tb)>2 else None, admin_baker_options), key=f"act_tb3_std_{admin_selected_week}")
                
                actuals["tech_top_3"] = [act_tt1, act_tt2, act_tt3]
                actuals["tech_bottom_3"] = [act_tb1, act_tb2, act_tb3]
                
            # --- WEEKLY CHAOS CATEGORIES LOGGING (COUNT + DETAILS/TIMESTAMPS) ---
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            with col_hs1:
                act_handshake_cnt = st.number_input("Number of Handshake Occurrences", min_value=0, value=saved_w.get("handshake_count", 0), key=f"admin_hs_cnt_w{admin_selected_week}")
            with col_hs2:
                act_handshake_stamps = st.text_input("Handshake Circumstances & Video Timestamps", value=saved_w.get("handshake_timestamps", ""), placeholder="e.g., Clara @ 14:22 Signature, Tom @ 42:10 Showstopper", key=f"admin_hs_stamps_w{admin_selected_week}")
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", active_bakers, default=get_multi_default(saved_w.get("handshake_bakers"), active_bakers), key=f"admin_hs_bakers_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Occurrences", min_value=0, value=saved_w.get("crying_count", 0), key=f"admin_cry_cnt_w{admin_selected_week}")
            with col_cry2:
                act_crying_stamps = st.text_input("Crying Circumstances & Video Timestamps", value=saved_w.get("crying_timestamps", ""), placeholder="e.g., Gabe @ 24:15 Technical, Molly @ 54:02 Elimination", key=f"admin_cry_stamps_w{admin_selected_week}")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Innuendo Occurrences", min_value=0, value=saved_w.get("innuendo_count", 0), key=f"admin_inn_cnt_w{admin_selected_week}")
            with col_inn2:
                act_innuendo_stamps = st.text_input("Innuendo Circumstances & Video Timestamps", value=saved_w.get("innuendo_timestamps", ""), placeholder="e.g., Prue soggy bottom @ 12:10, Paul big nuts comment @ 33:45", key=f"admin_inn_stamps_w{admin_selected_week}")

            actuals["handshake_count"] = act_handshake_cnt
            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            actuals["innuendo_timestamps"] = act_innuendo_stamps
            
            submit_admin = st.form_submit_button("Publish Official Week Results & Recalculate Scores")
            if submit_admin:
                st.session_state.weekly_results[admin_selected_week] = actuals
                next_week = min(admin_selected_week + 1, 10)
                st.session_state.current_week = next_week
                
                # Recalculate all scores
                for member_name in st.session_state.league_members:
                    st.session_state.league_members[member_name]["total_score"] = 0
                    st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                    
                for w, act in st.session_state.weekly_results.items():
                    w_scores = {}
                    for m_name, m_data in st.session_state.league_members.items():
                        p_picks = m_data["weekly_picks"].get(w, {})
                        w_pts = calculate_weekly_score(p_picks, act, week=w)
                        m_data["weekly_breakdown"][w] = w_pts
                        w_scores[m_name] = w_pts
                        
                    if w_scores:
                        max_pts = max(w_scores.values())
                        if max_pts > 0:
                            for m_name, pts in w_scores.items():
                                if pts == max_pts:
                                    m_data["weekly_breakdown"][w] += 5
                                    
                for m_name, m_data in st.session_state.league_members.items():
                    m_data["total_score"] = sum(m_data["weekly_breakdown"].values())
                    if st.session_state.season_results:
                        m_data["total_score"] += calculate_season_score(m_data["season_picks"], st.session_state.season_results)
                        
                save_league_data()
                st.success(f"Official results published for Week {admin_selected_week}! All player scores have been recalculated.")

        st.markdown("---")
        st.subheader("🚩 Dispute Management & Resolution")
        st.write("Review active player contestations and update their status following GroupMe league votes.")
        if not st.session_state.disputes:
            st.info("No disputes currently logged.")
        else:
            for idx, d in enumerate(st.session_state.disputes):
                p_name = d.get("Player", "Unknown")
                wk = d.get("Week", "N/A")
                cat = d.get("Category", "N/A")
                curr_status = d.get("Status", "Active 🗳️")
                
                with st.expander(f"Dispute #{idx+1}: {wk} - {cat} ({p_name}) — Status: {curr_status}"):
                    st.write(f"**Submitted By:** {p_name}")
                    st.write(f"**Week Contested:** {wk}")
                    st.write(f"**Category:** {cat}")
                    st.write(f"**Video Evidence:** {d.get('Evidence', 'N/A')}")
                    st.write(f"**Requested Correction:** {d.get('Correction', 'N/A')}")
                    
                    status_options = ["Active 🗳️", "Resolved ✅", "Rejected ❌"]
                    current_idx = 0
                    if "Resolved" in curr_status:
                        current_idx = 1
                    elif "Rejected" in curr_status:
                        current_idx = 2
                        
                    new_status = st.selectbox(
                        f"Update Status for Dispute #{idx+1}:",
                        status_options,
                        index=current_idx,
                        key=f"disp_status_select_{idx}"
                    )
                    if st.button(f"Update Dispute #{idx+1} Status", key=f"btn_update_disp_{idx}"):
                        st.session_state.disputes[idx]["Status"] = new_status
                        save_league_data()
                        st.success(f"Status updated to '{new_status}' for Dispute #{idx+1}!")
                        st.rerun()

        st.markdown("---")
        st.subheader("🔑 Player Security PIN Management")
        reset_player = st.selectbox("Select Player Profile to Reset PIN:", ROSTER_HUMANS)
        new_pin = st.text_input("Set New 4-Digit Security PIN:", max_chars=4, key="admin_new_pin")
        if st.button("Update Player PIN"):
            if len(new_pin) == 4 and new_pin.isdigit():
                st.session_state.league_members[reset_player]["pin"] = new_pin
                save_league_data()
                st.success(f"Security PIN updated successfully for {reset_player}!")
            else:
                st.error("PIN must be exactly 4 numeric digits.")

        st.markdown("---")
        st.subheader("🚨 Emergency Data Wipe & League Reset")
        confirm_wipe = st.checkbox("I understand this will erase all player predictions and broadcast results.")
        if st.button("Wipe All League Data & Reset to Clean State"):
            if confirm_wipe:
                if os.path.exists(DATA_FILE):
                    os.remove(DATA_FILE)
                st.session_state.clear()
                st.success("All league data erased. Refreshing application...")
                st.rerun()
            else:
                st.error("Please check the confirmation box above before resetting.")
