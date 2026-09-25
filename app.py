import streamlit as st
import pandas as pd
import random
from PIL import Image
import os

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

# --- HEADER WITH NORMAN BEAVER IMAGE ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    for norman_path in ["normanbeaver.jpg", "Normanbeaver.jpg", "assets/normanbeaver.jpg", "assets/Normanbeaver.jpg"]:
        if os.path.exists(norman_path):
            try:
                st.image(Image.open(norman_path), width=110)
                break
            except Exception:
                pass
with col_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- 2. OFFICIAL 15-MEMBER ALPHABETICAL ROSTER & BAKERS ---
ROSTER_ALPHABETICAL = [
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

# --- 3. SESSION STATE INITIALIZATION ---
if "league_members" not in st.session_state:
    st.session_state.league_members = {
        name: {
            "pin": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }
        for name in ROSTER_ALPHABETICAL
    }

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# Calculate Current Active Week and Maximum Unlocked Week dynamically
published_weeks = sorted(list(st.session_state.weekly_results.keys()))
max_published_week = max(published_weeks) if published_weeks else 0
current_active_week = max_published_week + 1 if max_published_week < 10 else 10

# --- 4. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
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

    if week < 9:
        if (predictions.get("in_line_sb") in actuals.get("in_line_sb", [])) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2
        if (predictions.get("in_trouble") in actuals.get("in_trouble", [])):
            score += 2
            
    return score

def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner == act_winner:
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
            if stem.lower().strip() == target and ext.lower() in [".jpg", ".jpeg", ".png"]:
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
        eliminated = random.sample(elim_pool, 2) if is_double_elim else random.choice(elim_pool)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if is_double_elim else random.choice(elim_pool)
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_rank": tech_rank
        }
    else:
        star_baker = random.choice(active_bakers)
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if is_double_elim else random.choice(elim_pool)
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        tech_top_3 = random.sample(active_bakers, 3)
        bottom_pool = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(bottom_pool, 3) if len(bottom_pool) >= 3 else bottom_pool
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("📌 Competition Progress")
    if max_published_week == 0:
        st.info("🏆 **Current Status: Week 1 (Scouting Phase)**")
        st.caption("🔒 **Week 2 predictions will unlock** once the Administrator posts official broadcast results for Week 1!")
    else:
        st.success(f"🏆 **Current Active Week: Week {current_active_week}**")
        st.caption(f"Results published through Week {max_published_week}. Week {current_active_week} predictions are open!")
        
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

# --- 6. MAIN TABS ---
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
    for name in ROSTER_ALPHABETICAL:
        data = st.session_state.league_members[name]
        lb_data.append({
            "member": name,
            "points": data.get("total_score", 0),
            "data": data
        })
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        display_rows = []
        for rank, row in df_lb.iterrows():
            rank_str = f"🥇 #{rank}" if rank == 1 else (f"🥈 #{rank}" if rank == 2 else (f"🥉 #{rank}" if rank == 3 else f"#{rank}"))
            display_rows.append({
                "Rank": rank_str,
                "League Member": row["member"],
                "Total Points": f"{row['points']} pts"
            })
            
        st.dataframe(pd.DataFrame(display_rows), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecard Inspector")
    
    scorecard_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="scorecard_player_sel")
    if scorecard_player:
        p_data = st.session_state.league_members[scorecard_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        col_sec1, col_sec2 = st.columns(2)
        with col_sec1:
            st.markdown(f"### **🌟 {scorecard_player}'s Season Projections**")
            win_pick = p_season.get("winner", "Not submitted yet")
            semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
            hs_pick = p_season.get("handshakes", "N/A")
            cry_pick = p_season.get("crying", "N/A")
            inn_pick = p_season.get("innuendos", "N/A")
            
            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
            st.write(f"🤝 **Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        with col_sec2:
            st.markdown(f"### **📅 {scorecard_player}'s Weekly Predictions Log**")
            if p_weekly:
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
                        "Technical Placements": t3
                    })
                st.dataframe(pd.DataFrame(w_rows), hide_index=True, use_container_width=True)
            else:
                st.info(f"No weekly predictions logged yet for {scorecard_player}.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Contestants can review official episode broadcast logging, including video timestamps for Hollywood Handshakes, Crying scenes, and Sexual Innuendos.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_cnt = w_act.get("handshake_count", 0)
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_cnt = w_act.get("crying_count", 0)
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"

            tot_hs += hs_cnt
            tot_cry += cry_cnt
            tot_inn += inn_cnt

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{hs_cnt} ({hs_stamps})",
                "Crying Scenes": f"{cry_cnt} ({cry_stamps})",
                "Innuendos": f"{inn_cnt} ({inn_stamps})"
            })

        st.dataframe(pd.DataFrame(audit_rows), hide_index=True, use_container_width=True)
        st.markdown(f"**Cumulative Broadcast Totals:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_ALPHABETICAL, key="disp_player_sel")
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
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), hide_index=True, use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions Ballot")
    
    # 1. Player Selection & PIN Verification
    st.subheader("👤 Select Player Profile & Unlock Ballot")
    selected_player = st.selectbox("Select Your Name / Player Profile:", ["-- Select Your Name --"] + ROSTER_ALPHABETICAL, key="submit_player_sel")
    
    player_authenticated = False
    if selected_player != "-- Select Your Name --":
        p_info = st.session_state.league_members[selected_player]
        
        if p_info["pin"] is None:
            st.info(f"Welcome, **{selected_player}**! Create a 4-digit PIN to protect your prediction ballot.")
            pin_create = st.text_input("Create 4-Digit Password PIN:", type="password", key=f"pin_create_{selected_player}")
            pin_confirm = st.text_input("Confirm 4-Digit Password PIN:", type="password", key=f"pin_confirm_{selected_player}")
            if st.button("Save Password PIN & Unlock Ballot"):
                if len(pin_create) == 4 and pin_create.isdigit():
                    if pin_create == pin_confirm:
                        st.session_state.league_members[selected_player]["pin"] = pin_create
                        st.success(f"PIN created successfully for {selected_player}! Ballot unlocked.")
                        st.rerun()
                    else:
                        st.error("PINs do not match. Please re-enter.")
                else:
                    st.error("PIN must be exactly 4 numeric digits!")
        else:
            pin_input = st.text_input(f"Enter 4-Digit Password PIN for {selected_player}:", type="password", key=f"pin_login_{selected_player}")
            if pin_input == p_info["pin"]:
                player_authenticated = True
                st.success(f"Unlocked! Logged in as **{selected_player}**.")
            elif pin_input != "":
                st.error("Incorrect PIN. Please try again.")

    st.markdown("---")

    # 2. Week Selection (Dynamic Lock / Unlock based on Admin Results Posting)
    unlocked_weeks = [1] + [w + 1 for w in published_weeks if w < 10]
    unlocked_weeks = sorted(list(set(unlocked_weeks)))
    max_unlocked_week = max(unlocked_weeks)
    
    st.subheader("📅 Select Prediction Week")
    
    # Let user pick any week from 2 to 10
    sel_pred_week = st.selectbox(
        "Select Week to Submit Predictions:", 
        [f"Week {w}" for w in range(2, 11)],
        index=min(max_unlocked_week - 2, 8) if max_unlocked_week >= 2 else 0,
        key="sel_pred_week_dropdown"
    )
    
    chosen_week_num = int(sel_pred_week.replace("Week ", ""))
    
    if chosen_week_num > max_unlocked_week:
        st.warning(f"🔒 **Week {chosen_week_num} Predictions Are Currently Locked!**")
        st.info(f"Predictions for Week {chosen_week_num} will unlock automatically once the Administrator posts the official broadcast results for **Week {chosen_week_num - 1}**.")
    else:
        st.success(f"🔓 **Week {chosen_week_num} Predictions Are Unlocked & Open!**")

    # Visual Baker Gallery
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
                    st.markdown(f"[🔗 Profile Page]({info['url']})")

    # Post-Week 1 Season Long Predictions (Available in Week 1 / Week 2 before locks)
    if player_authenticated and chosen_week_num <= max_unlocked_week:
        if chosen_week_num == 2 and max_published_week <= 1:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Before Week 2 Broadcast! | 130 pts total at stake)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", ["--Select Baker--"] + ALL_BAKERS, key="user_win_pick")
                remaining_for_semis = [b for b in ALL_BAKERS if b != user_winner and b != "--Select Baker--"]
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", remaining_for_semis, max_selections=3, key="user_semis_pick")
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5, key="user_hs_pick")
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10, key="user_cry_pick")
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40, key="user_inn_pick")
                
                if st.button("Lock Season-Long Predictions"):
                    if user_winner == "--Select Baker--":
                        st.error("Please select a valid Season Winner.")
                    elif len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members[selected_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        st.success(f"Season-long predictions saved successfully for {selected_player}!")

        # Weekly Ballot Form
        st.markdown(f"### 📅 Weekly Prediction Ballot: Week {chosen_week_num}")
        
        current_eliminated = eliminated_bakers_by_week.get(chosen_week_num, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_options = ["--Select Baker--"] + active_bakers
        
        prev_week_num = chosen_week_num - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        is_double_elim = False
        if chosen_week_num < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, key=f"dbl_elim_chk_w{chosen_week_num}")

        with st.form(f"weekly_form_w{chosen_week_num}"):
            weekly_picks = {}
            valid_submission = True
            
            if chosen_week_num == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_options, key="p_champ_w10")
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", baker_options, key="pt1_w10")
                t2 = st.selectbox("Technical 2nd Place", baker_options, key="pt2_w10")
                t3 = st.selectbox("Technical 3rd Place", baker_options, key="pt3_w10")
                weekly_picks["tech_rank"] = [t1, t2, t3]
                
            elif chosen_week_num == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, key="psb_w9")
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="pe1_w9")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="pe2_w9")
                    weekly_picks["eliminated"] = [e1, e2]
                else:
                    e = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options, key="pe_w9")
                    weekly_picks["eliminated"] = e
                    
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", baker_options, key="pt1_w9")
                t2 = st.selectbox("Technical 2nd Place", baker_options, key="pt2_w9")
                t3 = st.selectbox("Technical 3rd Place", baker_options, key="pt3_w9")
                t4 = st.selectbox("Technical 4th Place", baker_options, key="pt4_w9")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif chosen_week_num == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, key="psb_w8")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated]", baker_options, key="pinline_w8")
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key="pe1_w8")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key="pe2_w8")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        e = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options, key="pe_w8")
                        weekly_picks["eliminated"] = e
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if nominated]", baker_options, key="ptrouble_w8")

                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", baker_options, key="pt1_w8")
                t2 = st.selectbox("Technical 2nd Place", baker_options, key="pt2_w8")
                t3 = st.selectbox("Technical 3rd Place", baker_options, key="pt3_w8")
                t4 = st.selectbox("Technical 4th Place", baker_options, key="pt4_w8")
                t5 = st.selectbox("Technical 5th Place", baker_options, key="pt5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]

            else:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_options, key=f"psb_w{chosen_week_num}")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated]", baker_options, key=f"pinline_w{chosen_week_num}")
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_options, key=f"pe1_w{chosen_week_num}")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_options, key=f"pe2_w{chosen_week_num}")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        e = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_options, key=f"pe_w{chosen_week_num}")
                        weekly_picks["eliminated"] = e
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if nominated]", baker_options, key=f"ptrouble_w{chosen_week_num}")

                st.markdown("---")
                st.write("Predict Top 3 Technical Challenge Placements:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key=f"pt1_w{chosen_week_num}")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key=f"pt2_w{chosen_week_num}")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key=f"pt3_w{chosen_week_num}")
                weekly_picks["tech_top_3"] = [t1, t2, t3]

                st.write("Predict Bottom 3 Technical Challenge Placements:")
                b3 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_options, key=f"pb3_w{chosen_week_num}")
                b2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_options, key=f"pb2_w{chosen_week_num}")
                b1 = st.selectbox("Technical Last Place [3 pts]", baker_options, key=f"pb1_w{chosen_week_num}")
                weekly_picks["tech_bottom_3"] = [b3, b2, b1]

            sub_ballot = st.form_submit_button(f"Submit Week {chosen_week_num} Predictions")
            if sub_ballot:
                all_selections = []
                for k, v in weekly_picks.items():
                    if isinstance(v, list):
                        all_selections.extend(v)
                    elif isinstance(v, str):
                        all_selections.append(v)

                if "--Select Baker--" in all_selections:
                    st.error("⚠️ Please select a valid baker for all prediction fields!")
                else:
                    episodic_picks = []
                    if "star_baker" in weekly_picks: episodic_picks.append(weekly_picks["star_baker"])
                    if "show_champion" in weekly_picks: episodic_picks.append(weekly_picks["show_champion"])
                    if "in_line_sb" in weekly_picks: episodic_picks.append(weekly_picks["in_line_sb"])
                    if "in_trouble" in weekly_picks: episodic_picks.append(weekly_picks["in_trouble"])
                    if "eliminated" in weekly_picks:
                        if isinstance(weekly_picks["eliminated"], list):
                            episodic_picks.extend(weekly_picks["eliminated"])
                        else:
                            episodic_picks.append(weekly_picks["eliminated"])

                    if len(episodic_picks) != len(set(episodic_picks)):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    else:
                        tech_picks = weekly_picks.get("tech_rank", []) + weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])
                        if len(tech_picks) != len(set(tech_picks)):
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            st.session_state.league_members[selected_player]["weekly_picks"][chosen_week_num] = weekly_picks
                            ai_picks = generate_ai_brian_weekly_picks(chosen_week_num, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][chosen_week_num] = ai_picks
                            st.success(f"Predictions submitted for Week {chosen_week_num}! AI Brian has also logged his randomized picks.")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles and official photograph links for the Series 17 Bakers:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS, key="analytics_baker_sel")
    
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

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        st.info("🔒 **Admin Panel Locked.** Please enter the Administrator PIN to access controls.")
        admin_pass = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_input")
        if st.button("Unlock Admin Panel"):
            if admin_pass == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN!")
    else:
        st.success("🔓 **Authenticated as League Administrator**")
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.markdown("---")
        st.subheader("📢 Publish Broadcast Results & Update Standings")
        
        admin_week_num = st.selectbox("Select Broadcast Episode Week to Input Results:", [f"Week {w}" for w in range(1, 11)], key="admin_week_sel")
        adm_w = int(admin_week_num.replace("Week ", ""))
        
        current_eliminated = eliminated_bakers_by_week.get(adm_w, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        with st.form(f"admin_actuals_form_w{adm_w}"):
            st.subheader(f"Input Broadcast Results for Week {adm_w}")
            actuals = {}
            
            if adm_w == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers, index=0)
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0, key="adm_t1_w10")
                act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0, key="adm_t2_w10")
                act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="adm_t3_w10")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
                
            elif adm_w == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")], index=0)
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week.")
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], index=0, key="admin_act_elim_1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), act_elim_1]], index=0, key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0, key="adm_t1_w9")
                act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0, key="adm_t2_w9")
                act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="adm_t3_w9")
                act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="adm_t4_w9")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

            elif adm_w == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0)
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key="admin_act_elim_1_w8")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], index=0, key="admin_act_elim_2_w8")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0, key="adm_t1_w8")
                act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0, key="adm_t2_w8")
                act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="adm_t3_w8")
                act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="adm_t4_w8")
                act_t5 = st.selectbox("Actual Technical 5th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], index=0, key="adm_t5_w8")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
                
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0, key=f"adm_sb_w{adm_w}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")], key=f"adm_inline_w{adm_w}")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{adm_w}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0, key=f"adm_el_w{adm_w}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"adm_tr_w{adm_w}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"adm_tr_w{adm_w}")
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key=f"adm_el1_w{adm_w}")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], index=0, key=f"adm_el2_w{adm_w}")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"adm_tr_w{adm_w}")
                    
                st.write("Actual Technical Challenge Placements:")
                act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0, key=f"adm_t1_w{adm_w}")
                act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0, key=f"adm_t2_w{adm_w}")
                act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key=f"adm_t3_w{adm_w}")
                actuals["tech_top_3"] = [act_t1, act_t2, act_t3]

                rem_for_bot = [b for b in active_bakers if b not in actuals["tech_top_3"]]
                act_b3 = st.selectbox("Actual Technical 3rd-to-Last Place", rem_for_bot, index=0, key=f"adm_b3_w{adm_w}")
                act_b2 = st.selectbox("Actual Technical 2nd-to-Last Place", [b for b in rem_for_bot if b != act_b3], index=0, key=f"adm_b2_w{adm_w}")
                act_b1 = st.selectbox("Actual Technical Last Place", [b for b in rem_for_bot if b not in [act_b3, act_b2]], index=0, key=f"adm_b1_w{adm_w}")
                actuals["tech_bottom_3"] = [act_b3, act_b2, act_b1]

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes (Count & Video Timestamps)")
            hs_cnt = st.number_input("Hollywood Handshakes Count in Episode", min_value=0, value=0, key=f"hs_cnt_w{adm_w}")
            hs_stamps = st.text_input("Handshake Video Timestamps & Descriptions (e.g. 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper')", value="", key=f"hs_stamps_w{adm_w}")

            st.markdown("### 😢 Crying Incidents (Count & Video Timestamps)")
            cry_cnt = st.number_input("Crying Incidents Count in Episode", min_value=0, value=0, key=f"cry_cnt_w{adm_w}")
            cry_stamps = st.text_input("Crying Video Timestamps & Descriptions (e.g. 'Gabe @ 24:15 Technical')", value="", key=f"cry_stamps_w{adm_w}")

            st.markdown("### 💬 Sexual Innuendos (Count & Video Timestamps)")
            inn_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0, key=f"inn_cnt_w{adm_w}")
            inn_stamps = st.text_input("Innuendos Video Timestamps & Descriptions (e.g. 'Paul @ 18:05 Soggy Bottom')", value="", key=f"inn_stamps_w{adm_w}")

            actuals["handshake_count"] = hs_cnt
            actuals["handshake_timestamps"] = hs_stamps
            actuals["crying_count"] = cry_cnt
            actuals["crying_timestamps"] = cry_stamps
            actuals["innuendo_count"] = inn_cnt
            actuals["innuendo_timestamps"] = inn_stamps

            if adm_w == 10:
                st.markdown("---")
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", ALL_BAKERS, index=0)
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
                
                act_handshakes = st.number_input("Actual Total Handshakes across Season", min_value=0, value=5)
                act_crying = st.number_input("Actual Total Crying Scenes across Season", min_value=0, value=12)
                act_innuendos = st.number_input("Actual Total Sexual Innuendos across Season", min_value=0, value=48)
                
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }

            submit_actuals = st.form_submit_button(f"Publish Broadcast Results for Week {adm_w} & Recalculate Standings")
            if submit_actuals:
                st.session_state.weekly_results[adm_w] = actuals
                if adm_w == 10:
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

                st.success(f"Broadcast results published for Week {adm_w}! Standings recalculated and next week unlocked automatically.")
                st.rerun()

        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_ALPHABETICAL, key="admin_pwd_reset_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"Password PIN for {reset_player} has been cleared! They can now set a new 4-digit PIN on the Submit Predictions tab.")

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
                st.success("All saved data, test predictions, actuals, disputes, and player PINs have been permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed with erasing all data.")
