import streamlit as st
import pandas as pd
import random
from PIL import Image
import os
import base64
import json

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

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
    # --- A. Main Episode Results ---
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") and predictions.get("star_baker") == actuals.get("star_baker"):
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
            elif pred_elim and pred_elim == act_elim:
                score += 5
            
    # --- B. Technical Challenge ---
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
                        if idx in [0, 4]:
                            score += 3
                        else:
                            score += 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 3]:
                            score += 3
                        else:
                            score += 2
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx == 0:
                            score += 3
                        else:
                            score += 2
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

    # --- C. Consolations ---
    if week < 9:
        if (predictions.get("in_line_sb") in actuals.get("in_line_sb", [])) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2
        # In Trouble scoring rule: matches any in_trouble nominee regardless of elimination
        act_trouble = actuals.get("in_trouble", [])
        pred_trouble = predictions.get("in_trouble")
        if pred_trouble and ((isinstance(act_trouble, list) and pred_trouble in act_trouble) or pred_trouble == act_trouble):
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

# --- 3. CORE CONSTANTS & GLOBAL DATA ---
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

# Global Elimination Schedule across weeks
eliminated_bakers_by_week = {
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

DEFAULT_ROSTER_HUMANS = [
    "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

# Session State Initialization
if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for h in DEFAULT_ROSTER_HUMANS:
        st.session_state.league_members[h] = {
            "pin": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }
    st.session_state.league_members["AI Brian"] = {
        "pin": "BOT",
        "weekly_picks": {},
        "season_picks": {},
        "total_score": 0,
        "weekly_breakdown": {}
    }

# Ensure all 15 members are present
for h in DEFAULT_ROSTER_HUMANS:
    if h not in st.session_state.league_members:
        st.session_state.league_members[h] = {
            "pin": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

if "AI Brian" not in st.session_state.league_members:
    st.session_state.league_members["AI Brian"] = {
        "pin": "BOT",
        "weekly_picks": {},
        "season_picks": {},
        "total_score": 0,
        "weekly_breakdown": {}
    }

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

# --- 4. AI BRIAN AUTOMATION ---
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
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line_sb,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_rank": tech_rank
        }
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bottom, min(3, len(rem_bottom))) if len(rem_bottom) >= 3 else rem_bottom
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line_sb,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. APP INTERFACE LAYOUT ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    norman_path = None
    for p in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.png"]:
        if os.path.exists(p):
            norman_path = p
            break
    if norman_path:
        st.image(norman_path, width=100)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)

with col_title:
    st.title("Great British Baking Show Fantasy League 2026")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Game Controls")
    selected_week = st.slider("Select App Active Week", min_value=1, max_value=10, value=st.session_state.current_week)
    st.session_state.current_week = selected_week

    st.markdown("---")
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
        * **Top 3 Technical Challenge:**
            * *Exact:* 3 pts for 1st, 2 pts for 2nd/3rd
            * *Wrong Spot:* 1 pt for any correct Top 3 baker
            * *Combo Sweep:* **10 pts** *(flat)*
        * **Bottom 3 Technical Challenge:**
            * *Exact:* 2 pts for 9th/10th, 3 pts for 11th
            * *Wrong Spot:* 1 pt for any correct Bottom 3 baker
            * *Combo Sweep:* **10 pts** *(flat)*
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)
        
    with st.expander("🏁 Weeks 8, 9 & 10 (Dynamic Scaling)", expanded=False):
        st.markdown("""
        * **Week 8 (Quarterfinal episodic - 5 bakers):**
            * *Star Baker:* 5 pts
            * *Eliminated:* 5 pts
            * *Technical:* Exact positions 1st/5th (3 pts), 2nd/3rd/4th (2 pts)
            * *Perfect 5-for-5 Sweep:* **25 pts** *(flat)*
        * **Week 9 (Semifinal episodic - 4 bakers):**
            * *Star Baker:* 5 pts
            * *Eliminated:* 5 pts
            * *Technical:* Exact positions 1st/4th (3 pts), 2nd/3rd (2 pts)
            * *Perfect 4-for-4 Sweep:* **20 pts** *(flat)*
        * **Week 10 (Grand Finale episodic - 3 bakers):**
            * *Show Champion:* 15 pts
            * *Technical:* Exact positions 1st (3 pts), 2nd/3rd (2 pts)
            * *Perfect 3-for-3 Sweep:* **15 pts** *(flat)*
        """)

# --- MAIN TABS (4 TABS WITH ADMIN ON FAR RIGHT) ---
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
    for name, data in st.session_state.league_members.items():
        tot_pts = data.get("total_score", 0)
        lb_data.append({
            "League Member": name,
            "Total Points": f"{tot_pts} pts",
            "_score": tot_pts
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="_score", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        ranks = []
        for idx in range(1, len(df_lb) + 1):
            if idx == 1: ranks.append("🥇 #1")
            elif idx == 2: ranks.append("🥈 #2")
            elif idx == 3: ranks.append("🥉 #3")
            else: ranks.append(f"#{idx}")
        df_lb.insert(0, "Rank", ranks)
        
        df_display = df_lb[["Rank", "League Member", "Total Points"]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    scorecard_player = st.selectbox("Select Player to View Scorecard:", DEFAULT_ROSTER_HUMANS + ["AI Brian"])
    if scorecard_player:
        p_data = st.session_state.league_members.get(scorecard_player, {})
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{scorecard_player}'s Scorecard — Total Points: {p_pts}**")
        col_sec1, col_sec2 = st.columns(2)
        with col_sec1:
            st.markdown("#### **🌟 Season Projections**")
            st.write(f"🏆 **Winner:** {p_season.get('winner', 'Not submitted')}")
            semis_str = ", ".join(p_season.get('semifinalists', [])) if p_season.get('semifinalists') else 'Not submitted'
            st.write(f"🏅 **Semifinalists:** {semis_str}")
            st.write(f"🤝 **Handshakes:** {p_season.get('handshakes', 'N/A')} | 😢 **Crying:** {p_season.get('crying', 'N/A')} | 💬 **Innuendos:** {p_season.get('innuendos', 'N/A')}")
        
        with col_sec2:
            st.markdown("#### **📅 Weekly Predictions Log**")
            if not p_weekly:
                st.info("No weekly ballots submitted yet.")
            else:
                for w_num in sorted(p_weekly.keys()):
                    with st.expander(f"Week {w_num} Ballot"):
                        st.json(p_weekly[w_num])

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0

    if st.session_state.weekly_results:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            
            tot_hs += len(w_act.get("handshake_bakers", []))
            if w_act.get("crying_timestamps") and w_act.get("crying_timestamps") != "N/A":
                tot_cry += len([s for s in w_act.get("crying_timestamps").split(",") if s.strip()])
            tot_inn += inn_cnt
            
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": str(w_act.get("star_baker", "N/A")),
                "Eliminated": str(w_act.get("eliminated", "N/A")),
                "Handshake Bakers": hs_bakers,
                "Handshake Timestamps": hs_stamps,
                "Crying Timestamps": cry_stamps,
                "Innuendos Count": inn_cnt
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

    st.markdown("### 🔥 Chaos Categories Running Totals Across Logged Weeks")
    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("🤝 Total Hollywood Handshakes", tot_hs)
    col_c2.metric("😢 Total Crying Incidents", tot_cry)
    col_c3.metric("💬 Total Sexual Innuendos", tot_inn)

    st.markdown("---")
    st.subheader("⚖️ Result Dispute / Timestamp Correction Log")
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", DEFAULT_ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 1", "Week 2"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Video Evidence (e.g., 'At 28:14 in Episode 3, Paul clearly shakes Tom's hand')")
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
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions Ballot")
    
    sel_player = st.selectbox("Select Your Player Profile:", ["-- Select Your Name --"] + DEFAULT_ROSTER_HUMANS)
    if sel_player != "-- Select Your Name --":
        player_data = st.session_state.league_members[sel_player]
        existing_pin = player_data.get("pin")
        
        pin_authenticated = False
        
        if existing_pin is None:
            st.info(f"Welcome {sel_player}! Please set a 4-digit PIN password for your profile.")
            col_p1, col_p2 = st.columns(2)
            new_pin = col_p1.text_input("Create 4-Digit PIN", type="password", key="create_pin_input")
            confirm_pin = col_p2.text_input("Confirm 4-Digit PIN", type="password", key="confirm_pin_input")
            if st.button("Set My Password PIN"):
                if len(new_pin) == 4 and new_pin.isdigit():
                    if new_pin == confirm_pin:
                        player_data["pin"] = new_pin
                        st.success("PIN set successfully! You are now logged in.")
                        st.rerun()
                    else:
                        st.error("PINs do not match! Please verify both fields.")
                else:
                    st.error("PIN must be exactly 4 numeric digits!")
        else:
            entered_pin = st.text_input(f"Enter 4-Digit PIN Password for {sel_player}:", type="password", key="login_pin_input")
            if entered_pin == existing_pin:
                pin_authenticated = True
                st.success(f"Unlocked ballot for {sel_player}!")
            elif entered_pin:
                st.error("Incorrect PIN! Please try again or ask the administrator to reset your PIN.")
                
        if pin_authenticated:
            st.markdown("---")
            current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            baker_options = ["--Select Baker--"] + active_bakers
            
            st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
            
            prev_week_num = st.session_state.current_week - 1
            prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
            prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
            
            is_double_elim = False
            if st.session_state.current_week < 10:
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)

            if st.session_state.current_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", baker_options, key="user_win_pick")
                    rem_for_semis = [b for b in active_bakers if b != user_winner]
                    user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", rem_for_semis, max_selections=3)
                    
                    user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                    user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                    user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)
                    
                    if st.button("Lock Season-Long Predictions"):
                        if user_winner == "--Select Baker--":
                            st.error("Please select a valid Season Winner!")
                        elif len(user_semis) != 3:
                            st.error("Please select exactly 3 other semifinalists.")
                        else:
                            player_data["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                            st.success("Season long predictions saved successfully!")

            st.markdown(f"### 📅 Weekly Ballot: Week {st.session_state.current_week}")
            with st.form("weekly_predictions_form"):
                weekly_picks = {}
                
                if st.session_state.current_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_options)
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="w10_t1")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="w10_t2")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="w10_t3")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                    
                elif st.session_state.current_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options)
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="w9_e1")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="w9_e2")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options)
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="w9_t1")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="w9_t2")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="w9_t3")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", baker_options, key="w9_t4")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]

                elif st.session_state.current_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options)
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options)
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="w8_e1")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="w8_e2")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="w8_tr")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options)
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="w8_tr")
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="w8_t1")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="w8_t2")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="w8_t3")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", baker_options, key="w8_t4")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", baker_options, key="w8_t5")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options)
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options)
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="std_e1")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="std_e2")
                            weekly_picks["eliminated"] = [e1, e2]
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="std_tr")
                        else:
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options)
                            weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="std_tr")
                        
                    st.markdown("---")
                    st.write("Predict Technical Challenge Top 3 Placements:")
                    top1 = st.selectbox("1st Place", baker_options, key="top1")
                    top2 = st.selectbox("2nd Place", baker_options, key="top2")
                    top3 = st.selectbox("3rd Place", baker_options, key="top3")
                    weekly_picks["tech_top_3"] = [top1, top2, top3]
                    
                    st.write("Predict Technical Challenge Bottom 3 Placements:")
                    bot1 = st.selectbox("3rd-to-Last Place", baker_options, key="bot1")
                    bot2 = st.selectbox("2nd-to-Last Place", baker_options, key="bot2")
                    bot3 = st.selectbox("Last Place", baker_options, key="bot3")
                    weekly_picks["tech_bottom_3"] = [bot1, bot2, bot3]

                submitted = st.form_submit_button("Submit Predictions")
                if submitted:
                    all_selected_picks = []
                    unselected = False
                    
                    for k, val in weekly_picks.items():
                        if isinstance(val, list):
                            for sub_val in val:
                                if sub_val == "--Select Baker--":
                                    unselected = True
                                else:
                                    all_selected_picks.append((k, sub_val))
                        else:
                            if val == "--Select Baker--":
                                unselected = True
                            else:
                                all_selected_picks.append((k, val))
                                
                    if unselected:
                        st.error("⚠️ Please select a valid baker for all prediction fields!")
                    else:
                        episodic_keys = ["star_baker", "in_line_sb", "eliminated", "in_trouble", "show_champion"]
                        episodic_picks = [val for k, val in all_selected_picks if k in episodic_keys]
                        
                        has_episodic_dups = len(episodic_picks) != len(set(episodic_picks))
                        
                        tech_keys = ["tech_rank", "tech_top_3", "tech_bottom_3"]
                        tech_picks = [val for k, val in all_selected_picks if k in tech_keys]
                        has_tech_dups = len(tech_picks) != len(set(tech_picks))
                        
                        if has_episodic_dups:
                            st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                        elif has_tech_dups:
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            player_data["weekly_picks"][st.session_state.current_week] = weekly_picks
                            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                            st.success(f"Predictions submitted for Week {st.session_state.current_week}! AI Brian has also submitted his randomized picks.")


# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Gallery")
    st.write("Detailed profiles and images for the Series 17 Bakers:")
    
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS)
    if selected_baker:
        col_img, col_details = st.columns([1, 2])
        with col_img:
            b_img = load_baker_image(selected_baker)
            if b_img is not None:
                st.image(b_img, caption=selected_baker, use_container_width=True)
            else:
                st.info(f"No image file found for {selected_baker} in assets/.")
        with col_details:
            st.subheader(f"Baker Profile: {selected_baker}")
            b_info = BAKER_INFO.get(selected_baker, {})
            st.markdown(f"[🔗 Official Show Profile Page]({b_info.get('url', '#')})")


# --- TAB 4: ADMIN PANEL (FAR RIGHT TAB) ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Use this tab to input broadcast results and manage player security PINs.")
    
    st.markdown("### 🔑 Player Password Management")
    reset_player = st.selectbox("Select Player Profile to Reset Password:", ["-- Select Player --"] + DEFAULT_ROSTER_HUMANS)
    if reset_player != "-- Select Player --":
        if st.button(f"Reset {reset_player}'s Password PIN"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"Password PIN for {reset_player} has been cleared! They can now set a new PIN on the Submit Predictions tab.")

    st.markdown("---")
    st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
    
    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    
    with st.form("admin_actuals_form"):
        actuals = {}
        
        if st.session_state.current_week == 10:
            actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers)
            st.write("Actual Technical Challenge Rankings:")
            act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0)
            act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0)
            act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0)
            actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            
        elif st.session_state.current_week == 9:
            actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers)
            elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
            if elim_type == "Single Elimination":
                actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")])
            elif elim_type == "No Elimination (Sickness/Grace Week)":
                actuals["eliminated"] = "None"
            else:
                act_elim_1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], key="admin_act_elim_1_w9")
                act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), act_elim_1]], key="admin_act_elim_2_w9")
                actuals["eliminated"] = [act_elim_1, act_elim_2]
            
            st.write("Actual Technical Challenge Rankings:")
            act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0)
            act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0)
            act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0)
            act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0)
            actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

        elif st.session_state.current_week == 8:
            col1, col2 = st.columns(2)
            with col1:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers)
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
            with col2:
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers)
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers)
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_w8")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_w8")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                
            st.write("Actual Technical Challenge Rankings:")
            act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0, key="act_t1_w8")
            act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0, key="act_t2_w8")
            act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="act_t3_w8")
            act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="act_t4_w8")
            act_t5 = st.selectbox("Actual Technical 5th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], index=0, key="act_t5_w8")
            actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]

        else:
            col1, col2 = st.columns(2)
            with col1:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers)
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
            with col2:
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_std")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers)
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers)
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_std")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_std")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                
            st.markdown("---")
            act_top_3 = st.multiselect("Actual Top 3 Technical (Order: 1st, 2nd, 3rd)", active_bakers, max_selections=3)
            act_bottom_3 = st.multiselect("Actual Bottom 3 Technical (Order: 3rd-to-last, 2nd-to-last, Last)", [b for b in active_bakers if b not in act_top_3], max_selections=3)
            actuals["tech_top_3"] = act_top_3
            actuals["tech_bottom_3"] = act_bottom_3

        st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
        act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers)
        act_handshake_stamps = st.text_input("Handshake Video Timestamps & Context")
        
        st.markdown("### 😢 Crying Incidents & Video Timestamps")
        act_crying_stamps = st.text_input("Crying Scene Video Timestamps & Context")
        
        st.markdown("### 💬 Weekly Sexual Innuendos Count")
        act_innuendo_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0)
        
        actuals["handshake_bakers"] = act_handshake_bakers
        actuals["handshake_timestamps"] = act_handshake_stamps
        actuals["crying_timestamps"] = act_crying_stamps
        actuals["innuendo_count"] = act_innuendo_cnt

        if st.session_state.current_week == 10:
            st.markdown("---")
            st.subheader("🏆 Actual Season-Long Totals (Finale Week 10 Entry)")
            act_winner = st.selectbox("Actual Season Winner (Show Champion)", active_bakers)
            act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
            act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
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
            st.session_state.weekly_results[st.session_state.current_week] = actuals
            if st.session_state.current_week == 10:
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
                
            st.success("Leaderboard updated! All predictions scored and verified against the 2026 rule constraints.")
