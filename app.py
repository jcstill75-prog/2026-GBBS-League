import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import os
import base64

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
            score += 15  # Buffed show champion prediction
    else:
        if predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
        
        # Sickness / Double Elimination Safe Scoring
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
            pass # 0 points for elimination in a grace week
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim == act_elim:
                score += 5
            
    # --- B. Technical Challenge (Dynamic Scaling) ---
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 5:
                score += 25  # Flat 25 pts for perfect sweep of 5 bakers
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 4]:
                            score += 3  # 1st and 5th
                        else:
                            score += 2  # 2nd, 3rd, 4th
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                score += 20  # Flat 20 pts for perfect sweep
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 3]:
                            score += 3  # 1st and 4th
                        else:
                            score += 2  # 2nd and 3rd
                    
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
                score += 15  # Flat 15 pts for perfect sweep
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
                score += 10  # Perfect Top 3 Combo Bonus
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
                score += 10  # Perfect Bottom 3 Combo Bonus
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
            score += 2  # Consolations
        if (predictions.get("in_trouble") in actuals.get("in_trouble", [])) and (predictions.get("in_trouble") != actuals.get("eliminated")):
            score += 2  # Consolations
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    # 1. Season Winner (40 points) or finalist consolation (15 points)
    pred_winner = predictions.get("winner")
    if pred_winner == act_winner:
        score += 40
    elif pred_winner in act_finalists:
        score += 15
        
    # 2. Other 3 Semifinalists (10 pts each)
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    # 3. Hollywood Handshakes (Spot-on = 20 pts, +/- 1 = 10 pts)
    pred_handshakes = predictions.get("handshakes")
    act_handshakes = actuals.get("handshakes")
    if pred_handshakes is not None and act_handshakes is not None:
        if pred_handshakes == act_handshakes:
            score += 20
        elif abs(pred_handshakes - act_handshakes) <= 1:
            score += 10
            
    # 4. Crying Events (Spot-on = 20 pts, +/- 5 = 10 pts)
    pred_crying = predictions.get("crying")
    act_crying = actuals.get("crying")
    if pred_crying is not None and act_crying is not None:
        if pred_crying == act_crying:
            score += 20
        elif abs(pred_crying - act_crying) <= 5:
            score += 10
            
    # 5. Sexual Innuendos (Spot-on = 20 pts, +/- 5 = 10 pts)
    pred_innuendos = predictions.get("innuendos")
    act_innuendos = actuals.get("innuendos")
    if pred_innuendos is not None and act_innuendos is not None:
        if pred_innuendos == act_innuendos:
            score += 20
        elif abs(pred_innuendos - act_innuendos) <= 5:
            score += 10
            
    return score


def load_baker_image(baker_name):
    """Smart case-insensitive and multi-extension image loader for bakers."""
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

# --- 3. ROSTER & DATABASE INITIALIZATION ---
ALL_HUMAN_PLAYERS = [
    "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ALL_LEAGUE_MEMBERS = ALL_HUMAN_PLAYERS + ["AI Brian"]

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
    st.session_state.league_members = {}

# Initialize all 15 roster members cleanly
for m_name in ALL_LEAGUE_MEMBERS:
    if m_name not in st.session_state.league_members:
        st.session_state.league_members[m_name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

# Remove any lingering legacy test keys if present
for legacy_key in ["You", "Steve", "Craig"]:
    if legacy_key in st.session_state.league_members and legacy_key not in ALL_LEAGUE_MEMBERS:
        del st.session_state.league_members[legacy_key]

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []


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
            eliminated = random.sample([b for b in active_bakers if b != star_baker], min(2, len(active_bakers)-1))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank
        }
    elif week == 8:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            eliminated = random.sample([b for b in active_bakers if b != star_baker], min(2, len(active_bakers)-1))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
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
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        remaining_for_bottom = [b for b in active_bakers if b not in tech_top_3]
        if len(remaining_for_bottom) >= 3:
            tech_bottom_3 = random.sample(remaining_for_bottom, 3)
        else:
            tech_bottom_3 = random.sample(active_bakers, min(3, len(active_bakers)))
            
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
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

# --- 5. APP INTERFACE LAYOUT ---

# Norman Beaver Header
col_header_logo, col_header_title = st.columns([1, 5])
with col_header_logo:
    beaver_path = None
    for bp in ["normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.jpg", "assets/normanbeaver.png"]:
        if os.path.exists(bp):
            beaver_path = bp
            break
    if beaver_path:
        st.image(beaver_path, width=110)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)

with col_header_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: GAME CONTROLS & POINTS REFERENCE GUIDE ---
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
        *   **Season Winner:** 40 pts
        *   **Finalist Consolation:** 15 pts *(if picked winner makes Top 3 but loses)*
        *   **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        *   **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        *   **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        *   **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Standard Weeks (Weeks 2–7)", expanded=False):
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

# --- MAIN TABS (4 TOTAL) ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Contestant Analytics", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    # Compile scoring for all 15 members
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
        
        # Prepare display dataframe for native Streamlit rendering
        display_rows = []
        for idx, row in df_lb.iterrows():
            rank_num = idx + 1
            if rank_num == 1:
                rank_str = "🥇 #1"
            elif rank_num == 2:
                rank_str = "🥈 #2"
            elif rank_num == 3:
                rank_str = "🥉 #3"
            else:
                rank_str = f"#{rank_num}"
                
            display_rows.append({
                "Rank": rank_str,
                "League Member": row["member"],
                "Total Points": f"{row['points']} pts"
            })
            
        df_display = pd.DataFrame(display_rows)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Player Scorecards & Season Projections")
    
    selected_sc_player = st.selectbox("Select Player to View Scorecard:", ALL_LEAGUE_MEMBERS, index=0)
    
    sc_data = st.session_state.league_members.get(selected_sc_player, {})
    sc_pts = sc_data.get("total_score", 0)
    sc_season = sc_data.get("season_picks", {})
    sc_weekly = sc_data.get("weekly_picks", {})
    
    st.markdown(f"### **{selected_sc_player}'s Scorecard (Total Score: {sc_pts} pts)**")
    
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        st.markdown("#### **🌟 Season Projections**")
        win_pick = sc_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(sc_season.get("semifinalists", [])) if sc_season.get("semifinalists") else "Not submitted yet"
        hs_pick = sc_season.get("handshakes", "N/A")
        cry_pick = sc_season.get("crying", "N/A")
        inn_pick = sc_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick}")
        st.write(f"😢 **Predicted Crying Scenes:** {cry_pick}")
        st.write(f"💬 **Predicted Innuendos:** {inn_pick}")
        
    with col_sc2:
        st.markdown("#### **📅 Weekly Predictions Log**")
        if sc_weekly:
            for w_num in sorted(sc_weekly.keys()):
                w_picks = sc_weekly[w_num]
                w_pts = sc_data.get("weekly_breakdown", {}).get(w_num, 0)
                with st.expander(f"Week {w_num} Ballot — Earned: {w_pts} pts"):
                    st.json(w_picks)
        else:
            st.info(f"{selected_sc_player} has not submitted any weekly predictions yet.")

    st.markdown("---")
    st.subheader("🍪 AI Brian's Automated Simulator Log")
    col_brian1, col_brian2 = st.columns(2)
    with col_brian1:
        st.markdown("**AI Brian's Locked Season Projections:**")
        st.json(st.session_state.league_members["AI Brian"]["season_picks"])
    with col_brian2:
        st.markdown("**AI Brian's Weekly Predictions Log:**")
        st.write(st.session_state.league_members["AI Brian"]["weekly_picks"])

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Contestants can review episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_bakers = ", ".join(w_act.get("crying_bakers", [])) if w_act.get("crying_bakers") else "None"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", "N/A"),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshakes', 0)} ({hs_bakers} @ {hs_stamps})",
                "Crying Events": f"{w_act.get('crying', 0)} ({cry_bakers} @ {cry_stamps})",
                "Innuendos": w_act.get("innuendos", 0)
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    user_player = st.selectbox("Select Your Player Profile:", ALL_HUMAN_PLAYERS, index=0)
    
    # 1. Visual Baker Cheat Sheet
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
        st.write("Series 17 Bakers competing in the tent:")
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
                    st.markdown(f"[🔗 View {baker}'s Profile]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"📅 Submit Predictions for {user_player}: Week {st.session_state.current_week}")
    st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")

    # Dynamic active bakers list
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

    prev_week_num = st.session_state.current_week - 1
    prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
    prev_week_was_grace = (prev_week_results.get("eliminated") == "None")

    st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))

    is_double_elim = False
    if st.session_state.current_week < 10:
        is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)

    # Post-Week 1 Season long entry (Locks on Week 2)
    if st.session_state.current_week == 2:
        with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
            user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", active_bakers, key="user_win_pick")
            remaining_for_semis = [b for b in active_bakers if b != user_winner]
            user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", remaining_for_semis, max_selections=3)

            user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
            user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
            user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)

            if st.button("Lock Season-Long Predictions"):
                if len(user_semis) != 3:
                    st.error("Please select exactly 3 other semifinalists.")
                else:
                    st.session_state.league_members[user_player]["season_picks"] = {
                        "winner": user_winner,
                        "semifinalists": user_semis,
                        "handshakes": user_handshakes,
                        "crying": user_crying,
                        "innuendos": user_innuendos
                    }
                    st.success(f"Season long predictions for {user_player} saved successfully!")

    # Weekly Form based on active week
    st.markdown("### Weekly Ballot")
    with st.form("weekly_predictions_form"):
        weekly_picks = {}

        if st.session_state.current_week == 10:
            weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", active_bakers)
            st.write("Predict Technical Challenge Final Rank:")
            tech_1st = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0)
            tech_2nd = st.selectbox("Technical 2nd Place [2 pts]", [b for b in active_bakers if b != tech_1st], index=0)
            tech_3rd = st.selectbox("Technical 3rd Place [2 pts]", [b for b in active_bakers if b not in [tech_1st, tech_2nd]], index=0)
            weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]

        elif st.session_state.current_week == 9:
            weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers)
            if is_double_elim:
                elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", [b for b in active_bakers if b != weekly_picks.get("star_baker")], key="pred_elim_1_w9")
                elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", [b for b in active_bakers if b not in [weekly_picks.get("star_baker"), elim_1]], key="pred_elim_2_w9")
                weekly_picks["eliminated"] = [elim_1, elim_2]
            else:
                weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])

            st.write("Predict Technical Challenge Final Rank:")
            t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0)
            t2 = st.selectbox("Technical 2nd Place [2 pts]", [b for b in active_bakers if b != t1], index=0)
            t3 = st.selectbox("Technical 3rd Place [2 pts]", [b for b in active_bakers if b not in [t1, t2]], index=0)
            t4 = st.selectbox("Technical 4th Place [3 pts]", [b for b in active_bakers if b not in [t1, t2, t3]], index=0)
            weekly_picks["tech_rank"] = [t1, t2, t3, t4]

        elif st.session_state.current_week == 8:
            col1, col2 = st.columns(2)
            with col1:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers)
                weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
            with col2:
                if is_double_elim:
                    elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, key="pred_elim_1_w8")
                    elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", [b for b in active_bakers if b != elim_1], key="pred_elim_2_w8")
                    weekly_picks["eliminated"] = [elim_1, elim_2]
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", [b for b in active_bakers if b not in weekly_picks["eliminated"]])
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers)
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", [b for b in active_bakers if b != weekly_picks.get("eliminated")])

            st.write("Predict Technical Challenge Final Rank:")
            t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0, key="t1_w8")
            t2 = st.selectbox("Technical 2nd Place [2 pts]", [b for b in active_bakers if b != t1], index=0, key="t2_w8")
            t3 = st.selectbox("Technical 3rd Place [2 pts]", [b for b in active_bakers if b not in [t1, t2]], index=0, key="t3_w8")
            t4 = st.selectbox("Technical 4th Place [2 pts]", [b for b in active_bakers if b not in [t1, t2, t3]], index=0, key="t4_w8")
            t5 = st.selectbox("Technical 5th Place [3 pts]", [b for b in active_bakers if b not in [t1, t2, t3, t4]], index=0, key="t5_w8")
            weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]

        else:
            col1, col2 = st.columns(2)
            with col1:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers)
                weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
            with col2:
                if is_double_elim:
                    elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, key="pred_elim_1_std")
                    elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", [b for b in active_bakers if b != elim_1], key="pred_elim_2_std")
                    weekly_picks["eliminated"] = [elim_1, elim_2]
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", [b for b in active_bakers if b not in weekly_picks["eliminated"]])
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers)
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", [b for b in active_bakers if b != weekly_picks.get("eliminated")])

            st.markdown("---")
            st.write("Predict Technical Challenge Placements:")
            tech_top_3 = st.multiselect("Top 3 Technical (Order: 1st, 2nd, 3rd - Max 3)", active_bakers, max_selections=3)
            tech_bottom_3 = st.multiselect("Bottom 3 Technical (Order: 3rd-to-last, 2nd-to-last, Last - Max 3)", [b for b in active_bakers if b not in tech_top_3], max_selections=3)

            weekly_picks["tech_top_3"] = tech_top_3
            weekly_picks["tech_bottom_3"] = tech_bottom_3

        submitted = st.form_submit_button("Submit Predictions")
        if submitted:
            st.session_state.league_members[user_player]["weekly_picks"][st.session_state.current_week] = weekly_picks

            # Automatically trigger AI Brian
            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks

            st.success(f"Predictions submitted for {user_player} for Week {st.session_state.current_week}! AI Brian has also submitted his randomized picks.")

    st.markdown("---")
    st.subheader("📝 Submit a Result Dispute / Timestamp Correction")
    with st.form("dispute_form"):
        disp_player = st.selectbox("Your Name / Player Profile", ALL_HUMAN_PLAYERS)
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
            st.success("Dispute submitted successfully! Logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True)


# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles and performance trajectories for the Series 17 Bakers:")
    
    selected_analytics_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS)
    
    col_b_img, col_b_details = st.columns([1, 2])
    with col_b_img:
        b_img = load_baker_image(selected_analytics_baker)
        if b_img is not None:
            st.image(b_img, caption=selected_analytics_baker, use_container_width=True)
        else:
            st.info(f"No image file found for {selected_analytics_baker} in assets/.")
    with col_b_details:
        st.subheader(f"Baker Profile: {selected_analytics_baker}")
        b_info = BAKER_INFO.get(selected_analytics_baker, {})
        st.markdown(f"[🔗 View Official Show Profile Page]({b_info.get('url', '#')})")
        st.write(f"Class of 2026 Contestant competing in Series 17.")


# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Input official broadcast results to calculate scores and update the Live Leaderboard!")

    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]

    with st.form("admin_actuals_form"):
        st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
        actuals = {}

        if st.session_state.current_week == 10:
            actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers)
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
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")])
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers)
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_w8")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_w8")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])

            st.write("Actual Technical Challenge Rankings (1st through 5th):")
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
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")])
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers)
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_std")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_std")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])

            st.write("Actual Technical Challenge Results:")
            act_tech_top3 = st.multiselect("Actual Top 3 Technical (1st, 2nd, 3rd)", active_bakers, max_selections=3)
            act_tech_bottom3 = st.multiselect("Actual Bottom 3 Technical", [b for b in active_bakers if b not in act_tech_top3], max_selections=3)
            actuals["tech_top_3"] = act_tech_top3
            actuals["tech_bottom_3"] = act_tech_bottom3

        st.markdown("### Broadcast Episode Chaos Counts")
        act_handshakes = st.number_input("Actual Hollywood Handshakes in Episode", min_value=0, value=0)
        act_handshake_bakers = st.multiselect("Handshake Recipients", active_bakers)
        act_handshake_stamps = st.text_input("Handshake Timestamps (e.g., '14:20, 38:45')")

        act_crying = st.number_input("Actual Crying Incidents in Episode", min_value=0, value=0)
        act_crying_bakers = st.multiselect("Crying Bakers", active_bakers)
        act_crying_stamps = st.text_input("Crying Timestamps (e.g., '22:15')")

        act_innuendo_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0)

        actuals["handshakes"] = act_handshakes
        actuals["handshake_bakers"] = act_handshake_bakers
        actuals["handshake_timestamps"] = act_handshake_stamps
        actuals["crying"] = act_crying
        actuals["crying_bakers"] = act_crying_bakers
        actuals["crying_timestamps"] = act_crying_stamps
        actuals["innuendos"] = act_innuendo_cnt

        if st.session_state.current_week == 10:
            st.subheader("Actual Season-Long Totals (Entered at Season Finale)")
            act_winner = st.selectbox("Actual Season Champion", ALL_BAKERS)
            act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
            act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
            act_tot_hs = st.number_input("Actual Total Seasonal Handshakes", min_value=0, value=6)
            act_tot_cry = st.number_input("Actual Total Seasonal Crying Events", min_value=0, value=12)
            act_tot_inn = st.number_input("Actual Total Seasonal Innuendos", min_value=0, value=48)

            actuals_season = {
                "winner": act_winner,
                "semifinalists": act_semis,
                "finalists": act_finalists,
                "handshakes": act_tot_hs,
                "crying": act_tot_cry,
                "innuendos": act_tot_inn
            }

        submit_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
        if submit_actuals:
            st.session_state.weekly_results[st.session_state.current_week] = actuals
            if st.session_state.current_week == 10:
                st.session_state.season_results = actuals_season

            # Reset scores and re-evaluate
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

            st.success("Leaderboard updated! All predictions scored successfully.")
