import streamlit as st
import pandas as pd
import random
from PIL import Image
import os
import io

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for baking theme
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

# --- 2. CORE BAKERS LIST & ROSTER INITIALIZATION ---
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

ROSTER_MEMBERS = [
    "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", 
    "Taliah", "Tressa", "AI Brian"
]

ELIMINATED_BY_WEEK = {
    1: [], # Week 1 Scouting phase (all 12 active)
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

def get_active_bakers(week):
    elim = ELIMINATED_BY_WEEK.get(week, [])
    return [b for b in ALL_BAKERS if b not in elim]

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

# Streamlit Session State Initialization
if "league_members" not in st.session_state:
    st.session_state.league_members = {}

for m in ROSTER_MEMBERS:
    if m not in st.session_state.league_members:
        st.session_state.league_members[m] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None
        }

# Purge legacy keys if present
for legacy_k in ["You", "Steve", "Craig"]:
    if legacy_k in st.session_state.league_members:
        del st.session_state.league_members[legacy_k]

if "current_week" not in st.session_state:
    st.session_state.current_week = 2

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False


# --- 3. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    # Main Episode Results
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion != "-- Select Baker --" and pred_champion == act_champion:
            score += 15
    else:
        pred_sb = predictions.get("star_baker")
        act_sb = actuals.get("star_baker")
        if pred_sb and act_sb and pred_sb != "-- Select Baker --" and pred_sb == act_sb:
            score += 5
            
        pred_el = predictions.get("eliminated")
        act_el = actuals.get("eliminated")
        if act_el == "None":
            pass # Grace week
        elif isinstance(act_el, list):
            if isinstance(pred_el, list):
                for p in pred_el:
                    if p in act_el and p != "-- Select Baker --":
                        score += 5
            elif isinstance(pred_el, str) and pred_el != "-- Select Baker --":
                if pred_el in act_el:
                    score += 5
        else:
            if isinstance(pred_el, list):
                if act_el in pred_el:
                    score += 5
            elif pred_el and pred_el != "-- Select Baker --" and pred_el == act_el:
                score += 5

    # Technical Challenge Scoring
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        pred_clean = [b for b in pred_rank if b and not str(b).startswith("-- Select")]
        act_clean = [b for b in act_rank if b and not str(b).startswith("-- Select")]
        
        if len(pred_clean) == len(act_clean) and len(pred_clean) > 0:
            if pred_clean == act_clean:
                sweep_pts = {8: 25, 9: 20, 10: 15}
                score += sweep_pts.get(week, 15)
            else:
                for idx, b in enumerate(pred_clean):
                    if idx < len(act_clean) and act_clean[idx] == b:
                        if idx in [0, len(act_clean)-1]:
                            score += 3
                        else:
                            score += 2
    else:
        # Standard Weeks 2-7
        p_t1 = predictions.get("tech_1st")
        p_t2 = predictions.get("tech_2nd")
        p_t3 = predictions.get("tech_3rd")
        
        pred_top3 = []
        if p_t1 and not str(p_t1).startswith("-- Select"): pred_top3.append(p_t1)
        if p_t2 and not str(p_t2).startswith("-- Select"): pred_top3.append(p_t2)
        if p_t3 and not str(p_t3).startswith("-- Select"): pred_top3.append(p_t3)
        if not pred_top3:
            pred_top3 = [b for b in predictions.get("tech_top_3", []) if not str(b).startswith("-- Select")]
            
        act_top3 = [b for b in actuals.get("tech_top_3", []) if not str(b).startswith("-- Select")]
        if not act_top3 and actuals.get("tech_rank"):
            act_top3 = actuals.get("tech_rank")[:3]

        if len(pred_top3) == 3 and len(act_top3) >= 3:
            if pred_top3 == act_top3[:3]:
                score += 10
            else:
                if pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] == act_top3[2]: score += 2
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3[:3] and baker != act_top3[idx]:
                        score += 1
                        
        p_tb1 = predictions.get("tech_3rd_last")
        p_tb2 = predictions.get("tech_2nd_last")
        p_tb3 = predictions.get("tech_last")
        
        pred_bottom3 = []
        if p_tb1 and not str(p_tb1).startswith("-- Select"): pred_bottom3.append(p_tb1)
        if p_tb2 and not str(p_tb2).startswith("-- Select"): pred_bottom3.append(p_tb2)
        if p_tb3 and not str(p_tb3).startswith("-- Select"): pred_bottom3.append(p_tb3)
        if not pred_bottom3:
            pred_bottom3 = [b for b in predictions.get("tech_bottom_3", []) if not str(b).startswith("-- Select")]

        act_bottom3 = [b for b in actuals.get("tech_bottom_3", []) if not str(b).startswith("-- Select")]
        if not act_bottom3 and actuals.get("tech_rank"):
            act_bottom3 = actuals.get("tech_rank")[-3:]

        if len(pred_bottom3) == 3 and len(act_bottom3) >= 3:
            if pred_bottom3 == act_bottom3[-3:]:
                score += 10
            else:
                if pred_bottom3[0] == act_bottom3[0]: score += 2
                if pred_bottom3[1] == act_bottom3[1]: score += 2
                if pred_bottom3[2] == act_bottom3[2]: score += 3
                for idx, baker in enumerate(pred_bottom3):
                    if baker in act_bottom3[-3:] and baker != act_bottom3[idx]:
                        score += 1

    # Consolations
    if week < 9:
        p_inline = predictions.get("in_line_sb")
        a_sb = actuals.get("star_baker")
        a_inline = actuals.get("in_line_sb", [])
        if p_inline and p_inline != "-- Select Baker --" and p_inline in a_inline and p_inline != a_sb:
            score += 2
            
        p_trouble = predictions.get("in_trouble")
        a_trouble = actuals.get("in_trouble", [])
        if p_trouble and p_trouble != "-- Select Baker --" and p_trouble in a_trouble:
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
    if pred_winner and pred_winner != "-- Select Baker --":
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
            
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker and baker != "-- Select Baker --" and baker in act_semis and baker != pred_winner:
            score += 10
            
    pred_handshakes = predictions.get("handshakes")
    act_handshakes = actuals.get("handshakes")
    if isinstance(pred_handshakes, int) and isinstance(act_handshakes, int):
        if pred_handshakes == act_handshakes:
            score += 20
        elif abs(pred_handshakes - act_handshakes) <= 1:
            score += 10
            
    pred_crying = predictions.get("crying")
    act_crying = actuals.get("crying")
    if isinstance(pred_crying, int) and isinstance(act_crying, int):
        if pred_crying == act_crying:
            score += 20
        elif abs(pred_crying - act_crying) <= 5:
            score += 10
            
    pred_innuendos = predictions.get("innuendos")
    act_innuendos = actuals.get("innuendos")
    if isinstance(pred_innuendos, int) and isinstance(act_innuendos, int):
        if pred_innuendos == act_innuendos:
            score += 20
        elif abs(pred_innuendos - act_innuendos) <= 5:
            score += 10
            
    return score


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
        return {"show_champion": champion, "tech_rank": tech_rank}
    elif week == 9:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2, len(elim_pool))) if is_double_elim else (random.choice(elim_pool) if elim_pool else active_bakers[0])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2, len(elim_pool))) if is_double_elim else (random.choice(elim_pool) if elim_pool else active_bakers[0])
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank,
            "in_line_sb": in_line_sb,
            "in_trouble": in_trouble
        }
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2, len(elim_pool))) if is_double_elim else (random.choice(elim_pool) if elim_pool else active_bakers[0])
        
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        remaining_for_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(remaining_for_bottom, min(3, len(remaining_for_bottom))) if remaining_for_bottom else []
            
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_1st": tech_top_3[0] if len(tech_top_3) > 0 else "-- Select Baker --",
            "tech_2nd": tech_top_3[1] if len(tech_top_3) > 1 else "-- Select Baker --",
            "tech_3rd": tech_top_3[2] if len(tech_top_3) > 2 else "-- Select Baker --",
            "tech_3rd_last": tech_bottom_3[0] if len(tech_bottom_3) > 0 else "-- Select Baker --",
            "tech_2nd_last": tech_bottom_3[1] if len(tech_bottom_3) > 1 else "-- Select Baker --",
            "tech_last": tech_bottom_3[2] if len(tech_bottom_3) > 2 else "-- Select Baker --",
            "in_line_sb": in_line_sb,
            "in_trouble": in_trouble
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. HEADER LAYOUT ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    norman_path = None
    for path in ["normanbeaver.jpg", "assets/normanbeaver.jpg"]:
        if os.path.exists(path):
            norman_path = path
            break
    if norman_path:
        st.image(norman_path, width=110)
    else:
        st.markdown("<h1 style='font-size: 60px; margin:0;'>🧁</h1>", unsafe_allow_html=True)

with col_title:
    st.title("Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: POINTS REFERENCE GUIDE ONLY (CLEAN NAVIGATION) ---
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
tab_lead, tab_submit, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "👑 Admin Panel"])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    # Compile scoring for all 15 members
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
        for rank_idx, row in df_lb.iterrows():
            rank = rank_idx + 1
            m_name = row["member"]
            m_pts = row["points"]
            rank_badge = f"#{rank}"
            if rank == 1: rank_badge = "🥇 #1"
            elif rank == 2: rank_badge = "🥈 #2"
            elif rank == 3: rank_badge = "🥉 #3"
            
            lb_table_data.append({
                "Rank": rank_badge,
                "League Member": m_name,
                "Total Points": f"{m_pts} pts"
            })
            
        df_lb_show = pd.DataFrame(lb_table_data)
        st.dataframe(df_lb_show, hide_index=True, use_container_width=True)

    # --- REQUIREMENT 1: RUNNING COUNTER OF CHAOS CATEGORIES UNDERNEATH LIVE LEADERBOARD ---
    st.markdown("---")
    st.markdown("### 📊 Season Running Chaos Totals")
    st.write("Current broadcast totals across all published episodes this season:")
    
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    
    for w_num, w_act in st.session_state.weekly_results.items():
        hs_list = w_act.get("handshake_bakers", [])
        hs_cnt = w_act.get("handshake_count", len(hs_list) if isinstance(hs_list, list) else 0)
        tot_hs += hs_cnt if isinstance(hs_cnt, int) else (len(hs_list) if isinstance(hs_list, list) else 0)
        
        cry_cnt = w_act.get("crying_count", 0)
        tot_cry += cry_cnt if isinstance(cry_cnt, int) else 0
        
        inn_cnt = w_act.get("innuendo_count", w_act.get("innuendos", 0))
        tot_inn += inn_cnt if isinstance(inn_cnt, int) else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("🤝 Hollywood Handshakes", f"{tot_hs} Total")
    with col_m2:
        st.metric("😢 Crying Incidents", f"{tot_cry} Total")
    with col_m3:
        st.metric("💬 Sexual Innuendos", f"{tot_inn} Total")

    st.markdown("---")
    st.subheader("📋 View Individual Player Scorecards")
    
    sc_members = sorted(list(st.session_state.league_members.keys()))
    selected_sc_player = st.selectbox("Select Player to View Scorecard:", sc_members, index=0)
    
    if selected_sc_player:
        p_data = st.session_state.league_members[selected_sc_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### 👤 **{selected_sc_player}'s Scorecard** — Total Score: `{p_pts} pts`")
        
        st.markdown("#### **🌟 Season-Long Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🏅 **Predicted Other Semifinalists:** {semis_pick}")
        with col_s2:
            st.write(f"🤝 **Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        st.markdown("#### **📅 Weekly Predictions Log**")
        if p_weekly:
            for w_num in range(2, 11):
                if w_num in p_weekly:
                    w_picks = p_weekly[w_num]
                    w_score = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                    with st.expander(f"Week {w_num} Predictions Log ({w_score} pts earned)", expanded=False):
                        pred_rows = []
                        for k, v in w_picks.items():
                            val_str = ", ".join(v) if isinstance(v, list) else str(v)
                            label_k = k.replace("_", " ").title()
                            pred_rows.append({"Category": label_k, "Your Prediction": val_str})
                        st.dataframe(pd.DataFrame(pred_rows), hide_index=True, use_container_width=True)
        else:
            st.info(f"No weekly predictions logged for {selected_sc_player} yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Contestants can review episode logging, including video timestamps for Hollywood Handshakes and Crying incidents.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 2!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", w_act.get("innuendos", 0))

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", "N/A"),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshake Recipients": hs_bakers,
                "Handshake Timestamps": hs_stamps,
                "Crying Timestamps": cry_stamps,
                "Innuendos Count": inn_cnt
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("⚖️ Result Disputes & Video Timestamp Evidence Log")
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ["-- Select Profile --"] + human_players)
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
                if disp_player.startswith("-- Select"):
                    st.error("Please select your player profile name!")
                else:
                    st.session_state.disputes.append({
                        "Player": disp_player,
                        "Week": disp_week,
                        "Category": disp_cat,
                        "Evidence": disp_evidence,
                        "Correction": disp_correction,
                        "Status": "Pending GroupMe Vote 🗳️"
                    })
                    st.success("Dispute submitted successfully!")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        df_disp = pd.DataFrame(st.session_state.disputes)
        st.dataframe(df_disp, hide_index=True, use_container_width=True)


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Player Predictions")
    human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
    active_user = st.selectbox("Select Your Player Profile:", ["-- Select Profile --"] + human_players, key="submit_player_profile_sel")
    
    if active_user and not active_user.startswith("-- Select"):
        p_data = st.session_state.league_members[active_user]
        p_pin = p_data.get("pin")
        is_authed = st.session_state.authenticated_players.get(active_user, False)

        # --- REQUIREMENT 2: PASSWORD PROTECTION FOR PLAYER SUBMISSIONS ---
        if p_pin is None:
            st.info(f"🔑 **First Visit for {active_user}?** Please create a 4-digit Security PIN to lock and protect your prediction ballot.")
            with st.form(f"pin_setup_form_{active_user}"):
                new_pin = st.text_input("Create 4-Digit Security PIN", type="password", max_chars=4)
                confirm_pin = st.text_input("Confirm 4-Digit Security PIN", type="password", max_chars=4)
                set_pin_btn = st.form_submit_button("Set My Security PIN")
                if set_pin_btn:
                    if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                        st.session_state.league_members[active_user]["pin"] = new_pin
                        st.session_state.authenticated_players[active_user] = True
                        st.success(f"Security PIN set successfully for {active_user}! Your ballot is unlocked.")
                        st.rerun()
                    else:
                        st.error("PINs must be exactly 4 digits and match!")
        elif not is_authed:
            st.warning(f"🔒 Profile **{active_user}** is protected by a Security PIN.")
            with st.form(f"pin_verify_form_{active_user}"):
                entered_pin = st.text_input(f"Enter 4-Digit Security PIN for {active_user}", type="password", max_chars=4)
                verify_btn = st.form_submit_button("Unlock Ballot")
                if verify_btn:
                    if entered_pin == p_pin:
                        st.session_state.authenticated_players[active_user] = True
                        st.success(f"PIN verified! Welcome back, {active_user}.")
                        st.rerun()
                    else:
                        st.error("Incorrect Security PIN. Please try again!")
        else:
            st.success(f"🔓 **Unlocked Ballot for {active_user}**")
            
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
                            st.markdown(f"[🔗 View {baker}'s Photo Page]({info['url']})")
                        st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("---")
            # --- REQUIREMENT 3: ELIMINATE WEEK 1 SUBMISSIONS (START AT WEEK 2) ---
            st.info("💡 **Notice:** Week 1 is the Scouting Phase (no weekly predictions are submitted for Week 1). Weekly prediction ballots start in **Week 2**!")
            
            sub_week = st.selectbox("Select Week for Prediction Ballot:", list(range(2, 11)), index=0, key=f"sub_week_sel_{active_user}")
            
            active_bakers = get_active_bakers(sub_week)
            baker_opts = ["-- Select Baker --"] + active_bakers
            
            st.write(f"**Active Bakers in the Tent for Week {sub_week}:** " + ", ".join(active_bakers))
            st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to broadcast on **Tuesdays right before the episode airs in the UK**.")

            is_double_elim = False
            if sub_week < 10:
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=False)

            # Season Long Entry when submitting Week 2
            if sub_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up]", baker_opts, key=f"user_win_{active_user}")
                    remaining_for_semis = [b for b in active_bakers if b != user_winner]
                    user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", remaining_for_semis, max_selections=3, key=f"user_semis_{active_user}")

                    user_handshakes = st.number_input("Predict Seasonal Handshakes [20 pts spot-on]", min_value=0, value=5, key=f"user_hs_{active_user}")
                    user_crying = st.number_input("Predict Seasonal Crying [20 pts spot-on]", min_value=0, value=10, key=f"user_cry_{active_user}")
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [20 pts spot-on]", min_value=0, value=40, key=f"user_inn_{active_user}")

                    if st.button("Lock Season-Long Predictions", key=f"btn_lock_season_{active_user}"):
                        if user_winner.startswith("-- Select"):
                            st.error("Please select a predicted Season Winner!")
                        elif len(user_semis) != 3:
                            st.error("Please select exactly 3 other semifinalists!")
                        else:
                            st.session_state.league_members[active_user]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                            st.success(f"Season long predictions saved successfully for {active_user}!")

            st.markdown(f"### Weekly Ballot for Week {sub_week}")
            with st.form(f"weekly_form_w{sub_week}_{active_user}"):
                weekly_picks = {}

                # --- REQUIREMENT 4 & 5: INDIVIDUAL TECHNICAL FIELDS + "-- Select Baker --" PLACEHOLDERS ---
                if sub_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_opts, index=0)
                    st.markdown("#### **Predict Technical Challenge Final Rank:**")
                    col_t1, col_t2, col_t3 = st.columns(3)
                    with col_t1: t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, index=0, key=f"w10_t1_{active_user}")
                    with col_t2: t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, index=0, key=f"w10_t2_{active_user}")
                    with col_t3: t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, index=0, key=f"w10_t3_{active_user}")
                    weekly_picks["tech_rank"] = [t1, t2, t3]

                elif sub_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts, index=0)
                    if is_double_elim:
                        col_e1, col_e2 = st.columns(2)
                        with col_e1: e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, index=0, key=f"w9_e1_{active_user}")
                        with col_e2: e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, index=0, key=f"w9_e2_{active_user}")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, index=0)

                    st.markdown("#### **Predict Technical Challenge Final Rank:**")
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, index=0, key=f"w9_t1_{active_user}")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, index=0, key=f"w9_t2_{active_user}")
                    with col_t2:
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, index=0, key=f"w9_t3_{active_user}")
                        t4 = st.selectbox("Technical 4th Place [3 pts]", baker_opts, index=0, key=f"w9_t4_{active_user}")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]

                elif sub_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts, index=0)
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts, index=0)
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, index=0, key=f"w8_e1_{active_user}")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, index=0, key=f"w8_e2_{active_user}")
                            weekly_picks["eliminated"] = [e1, e2]
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, index=0)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_opts, index=0)

                    st.markdown("#### **Predict Technical Challenge Final Rank (1st through 5th):**")
                    cols_tr = st.columns(5)
                    with cols_tr[0]: t1 = st.selectbox("Technical 1st Place", baker_opts, index=0, key=f"w8_t1_{active_user}")
                    with cols_tr[1]: t2 = st.selectbox("Technical 2nd Place", baker_opts, index=0, key=f"w8_t2_{active_user}")
                    with cols_tr[2]: t3 = st.selectbox("Technical 3rd Place", baker_opts, index=0, key=f"w8_t3_{active_user}")
                    with cols_tr[3]: t4 = st.selectbox("Technical 4th Place", baker_opts, index=0, key=f"w8_t4_{active_user}")
                    with cols_tr[4]: t5 = st.selectbox("Technical 5th Place", baker_opts, index=0, key=f"w8_t5_{active_user}")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]

                else:
                    # Standard Weeks 2-7
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts, index=0, key=f"std_sb_w{sub_week}_{active_user}")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts, index=0, key=f"std_inline_w{sub_week}_{active_user}")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, index=0, key=f"std_e1_w{sub_week}_{active_user}")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, index=0, key=f"std_e2_w{sub_week}_{active_user}")
                            weekly_picks["eliminated"] = [e1, e2]
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, index=0, key=f"std_elim_w{sub_week}_{active_user}")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_opts, index=0, key=f"std_trouble_w{sub_week}_{active_user}")

                    st.markdown("#### **Predict Technical Challenge Placements:**")
                    st.caption("Individual prediction fields for Top 3 and Bottom 3 technical placements:")
                    col_top, col_bot = st.columns(2)
                    with col_top:
                        st.markdown("**Top Technical Placements:**")
                        t1 = st.selectbox("1st Place Technical", baker_opts, index=0, key=f"t1_std_w{sub_week}_{active_user}")
                        t2 = st.selectbox("2nd Place Technical", baker_opts, index=0, key=f"t2_std_w{sub_week}_{active_user}")
                        t3 = st.selectbox("3rd Place Technical", baker_opts, index=0, key=f"t3_std_w{sub_week}_{active_user}")
                    with col_bot:
                        st.markdown("**Bottom Technical Placements:**")
                        tb1 = st.selectbox("3rd-to-Last Technical", baker_opts, index=0, key=f"tb1_std_w{sub_week}_{active_user}")
                        tb2 = st.selectbox("2nd-to-Last Technical", baker_opts, index=0, key=f"tb2_std_w{sub_week}_{active_user}")
                        tb3 = st.selectbox("Last Place Technical", baker_opts, index=0, key=f"tb3_std_w{sub_week}_{active_user}")

                    weekly_picks["tech_1st"] = t1
                    weekly_picks["tech_2nd"] = t2
                    weekly_picks["tech_3rd"] = t3
                    weekly_picks["tech_3rd_last"] = tb1
                    weekly_picks["tech_2nd_last"] = tb2
                    weekly_picks["tech_last"] = tb3

                submitted = st.form_submit_button("Submit Prediction Ballot")
                if submitted:
                    st.session_state.league_members[active_user]["weekly_picks"][sub_week] = weekly_picks
                    
                    # Generate AI Brian's picks automatically
                    ai_picks = generate_ai_brian_weekly_picks(sub_week, active_bakers, is_double_elim=is_double_elim)
                    st.session_state.league_members["AI Brian"]["weekly_picks"][sub_week] = ai_picks
                    
                    st.success(f"Prediction ballot submitted successfully for {active_user} (Week {sub_week})!")


# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    # --- REQUIREMENT 2: ADMIN PASSWORD PROTECTION (PIN 6284) ---
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
            human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
            p_to_reset = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + human_players)
            if p_to_reset != "-- Select Player --":
                cur_status = "Set 🔒" if st.session_state.league_members[p_to_reset].get("pin") else "Unset 🔓"
                st.write(f"Current PIN status for **{p_to_reset}**: `{cur_status}`")
                if st.button(f"Reset PIN for {p_to_reset}"):
                    st.session_state.league_members[p_to_reset]["pin"] = None
                    if p_to_reset in st.session_state.authenticated_players:
                        st.session_state.authenticated_players[p_to_reset] = False
                    st.success(f"Security PIN reset for {p_to_reset}!")
                    st.rerun()

        st.markdown("---")
        st.write("Record official broadcast results to score prediction ballots and update the standings:")
        
        admin_selected_week = st.selectbox(
            "Select Week to Record or Review Broadcast Results:",
            list(range(1, 11)),
            index=0,
            key="admin_week_selector_dropdown"
        )
        
        active_bakers = get_active_bakers(admin_selected_week)
        baker_opts = ["-- Select Baker --"] + active_bakers
        saved_w = st.session_state.weekly_results.get(admin_selected_week, {})

        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input Official Broadcast Results for Week {admin_selected_week}")
            actuals = {}

            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts, index=0)
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers)
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=0, key=f"admin_elim_single_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts, index=0, key=f"admin_elim_1_w{admin_selected_week}")
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts, index=0, key=f"admin_elim_2_w{admin_selected_week}")
                        actuals["eliminated"] = [e1, e2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)

            # --- REQUIREMENT 6: FIELDS FOR EVERY TECHNICAL PLACEMENT AVAILABLE IN EACH WEEK ---
            st.markdown("---")
            st.markdown(f"### 📊 Actual Technical Challenge Rankings (1st through {len(active_bakers)}th Place)")
            st.caption(f"Select actual technical placements for all {len(active_bakers)} active bakers in Week {admin_selected_week}:")
            
            num_bakers = len(active_bakers)
            cols_per_row = 3
            actual_tech_ranks = []
            
            for i in range(num_bakers):
                rank_num = i + 1
                ord_str = "1st" if rank_num == 1 else ("2nd" if rank_num == 2 else ("3rd" if rank_num == 3 else f"{rank_num}th"))
                if i % col
