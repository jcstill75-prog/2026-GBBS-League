import streamlit as st
import pandas as pd
import random
from PIL import Image
import os
import json

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for a cozy baking theme
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

# --- 2. CORE BAKERS LIST & DATABASE INITIALIZATION ---
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

ALL_HUMAN_PLAYERS = [
    "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", 
    "Taliah", "Tressa"
]

ALL_LEAGUE_MEMBERS = ALL_HUMAN_PLAYERS + ["AI Brian"]

# Data Persistence Functions
DATA_FILE = "league_data.json"

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data.get("members", {}), data.get("weekly_results", {}), data.get("season_results", {})
        except Exception:
            pass
    return {}, {}, {}

def save_league_data(members, weekly_results, season_results):
    try:
        clean_weekly = {}
        for w_k, w_v in weekly_results.items():
            clean_weekly[int(w_k)] = w_v
            
        data = {
            "members": members,
            "weekly_results": clean_weekly,
            "season_results": season_results
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving data: {e}")

saved_members, saved_weekly, saved_season = load_league_data()

# Initialize session state cleanly
if "league_members" not in st.session_state:
    st.session_state.league_members = {}

for m in ALL_LEAGUE_MEMBERS:
    if m not in st.session_state.league_members:
        s_m = saved_members.get(m, {})
        st.session_state.league_members[m] = {
            "weekly_picks": s_m.get("weekly_picks", {}),
            "season_picks": s_m.get("season_picks", {}),
            "total_score": s_m.get("total_score", 0),
            "weekly_breakdown": s_m.get("weekly_breakdown", {}),
            "pin": s_m.get("pin", None)
        }

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}
    for w_k, w_v in saved_weekly.items():
        st.session_state.weekly_results[int(w_k)] = w_v

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_season

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

# --- AUTOMATIC WEEK CALCULATION BASED ON PUBLISHED ADMIN RESULTS ---
if st.session_state.weekly_results:
    latest_published = max([int(k) for k in st.session_state.weekly_results.keys()])
    active_pred_week = min(latest_published + 1, 10)
else:
    active_pred_week = 2

st.session_state.current_week = active_pred_week

# --- 3. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion != "None" and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") and predictions.get("star_baker") != "None" and predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if act_elim and act_elim != "None":
            if isinstance(act_elim, list):
                if isinstance(pred_elim, list):
                    for p in pred_elim:
                        if p in act_elim: score += 5
                elif isinstance(pred_elim, str) and pred_elim in act_elim:
                    score += 5
            else:
                if isinstance(pred_elim, list):
                    if act_elim in pred_elim: score += 5
                elif pred_elim == act_elim:
                    score += 5

    # Technical Challenge Scoring
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        if pred_rank and act_rank and len(pred_rank) == len(act_rank) and len(pred_rank) > 0:
            if pred_rank == act_rank:
                sweep_pts = {8: 25, 9: 20, 10: 15}
                score += sweep_pts.get(week, 15)
            else:
                for idx, b in enumerate(pred_rank):
                    if b and b != "None" and idx < len(act_rank) and act_rank[idx] == b:
                        if idx in [0, len(pred_rank) - 1]:
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
                if pred_top3[0] and pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] and pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] and pred_top3[2] == act_top3[2]: score += 2
                for idx, b in enumerate(pred_top3):
                    if b and b in act_top3 and b != act_top3[idx]: score += 1

        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        if len(pred_bottom3) == 3 and len(act_bottom3) == 3:
            if pred_bottom3 == act_bottom3:
                score += 10
            else:
                if pred_bottom3[0] and pred_bottom3[0] == act_bottom3[0]: score += 2
                if pred_bottom3[1] and pred_bottom3[1] == act_bottom3[1]: score += 2
                if pred_bottom3[2] and pred_bottom3[2] == act_bottom3[2]: score += 3
                for idx, b in enumerate(pred_bottom3):
                    if b and b in act_bottom3 and b != act_bottom3[idx]: score += 1

    # Consolations
    if week < 9:
        p_in_line = predictions.get("in_line_sb")
        a_in_line = actuals.get("in_line_sb", [])
        a_sb = actuals.get("star_baker")
        if p_in_line and p_in_line != "None" and p_in_line in a_in_line and p_in_line != a_sb:
            score += 2
            
        p_trouble = predictions.get("in_trouble")
        a_trouble = actuals.get("in_trouble", [])
        if p_trouble and p_trouble != "None" and p_trouble in a_trouble:
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
    if pred_winner and pred_winner != "None":
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
            
    pred_semis = predictions.get("semifinalists", [])
    for b in pred_semis:
        if b and b != "None" and b in act_semis and b != pred_winner:
            score += 10
            
    pred_hs = predictions.get("handshakes")
    act_hs = actuals.get("handshakes")
    if pred_hs is not None and act_hs is not None:
        if pred_hs == act_hs: score += 20
        elif abs(pred_hs - act_hs) <= 1: score += 10
        
    pred_cry = predictions.get("crying")
    act_cry = actuals.get("crying")
    if pred_cry is not None and act_cry is not None:
        if pred_cry == act_cry: score += 20
        elif abs(pred_cry - act_cry) <= 5: score += 10

    pred_inn = predictions.get("innuendos")
    act_inn = actuals.get("innuendos")
    if pred_inn is not None and act_inn is not None:
        if pred_inn == act_inn: score += 20
        elif abs(pred_inn - act_inn) <= 5: score += 10

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
                try: return Image.open(full_path)
                except Exception: pass
    except Exception: pass
    return None

# --- AI BRIAN AUTOMATION ---
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
        eliminated = random.sample(elim_pool, min(2, len(elim_pool))) if is_double_elim else random.choice(elim_pool)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2, len(elim_pool))) if is_double_elim else random.choice(elim_pool)
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        in_trb_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trb_pool) if in_trb_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank,
            "in_line_sb": in_line,
            "in_trouble": in_trouble
        }
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2, len(elim_pool))) if is_double_elim else random.choice(elim_pool)
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bottom, min(3, len(rem_bottom))) if rem_bottom else []
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        in_trb_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trb_pool) if in_trb_pool else active_bakers[0]
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3,
            "in_line_sb": in_line,
            "in_trouble": in_trouble
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 4. APP INTERFACE LAYOUT ---
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

# --- SIDEBAR: POINTS REFERENCE GUIDE ---
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

# --- MAIN TABS ---
tab_lead, tab_submit, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "👑 Admin Panel"])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_data = []
    for name in ALL_LEAGUE_MEMBERS:
        data = st.session_state.league_members.get(name, {})
        tot_pts = data.get("total_score", 0)
        lb_data.append({"member": name, "points": tot_pts})
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        lb_table_data = []
        for rank, row in df_lb.iterrows():
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

    # REQ 1: Cumulative Season Chaos Totals underneath Live Leaderboard
    st.markdown("---")
    st.subheader("🔥 Cumulative Season Chaos Totals")
    
    cum_hs = 0
    cum_cry = 0
    cum_inn = 0
    
    for w_num, w_act in st.session_state.weekly_results.items():
        cum_hs += w_act.get("handshake_count", 0)
        cum_cry += w_act.get("crying_count", 0)
        cum_inn += w_act.get("innuendo_count", 0)
        
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Hollywood Handshakes", f"{cum_hs}")
    with col_c2:
        st.metric("😢 Crying Incidents", f"{cum_cry}")
    with col_c3:
        st.metric("💬 Sexual Innuendos", f"{cum_inn}")

    st.markdown("---")
    st.subheader("📋 View Individual Player Scorecards")
    
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
            st.markdown("#### **📅 Weekly Predictions Log (Weeks 2–10)**")
            if p_weekly:
                for w_num in range(2, 11):
                    if w_num in p_weekly:
                        w_picks = p_weekly[w_num]
                        w_score = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                        with st.expander(f"Week {w_num} Picks ({w_score} pts earned)", expanded=False):
                            st.json(w_picks)
            else:
                st.info(f"No weekly predictions logged for {selected_sc_player} yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Contestants can review episode logging, including video timestamps for Hollywood Handshakes and Crying incidents.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_stamps = w_act.get("innuendo_timestamps", "N/A") or "N/A"

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", "N/A"),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshake_count', 0)} ({hs_bakers} @ {hs_stamps})",
                "Crying Events": f"{w_act.get('crying_count', 0)} ({cry_stamps})",
                "Innuendos": f"{w_act.get('innuendo_count', 0)} ({inn_stamps})"
            })

        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    # Automatic active prediction week calculation
    active_pred_week = st.session_state.current_week
    st.info(f"🔒 **Current Active Voting Period:** **Week {active_pred_week}**. (Automatically unlocked based on Admin published results).")
    
    # REQ 2: Password protection for player submissions
    user_player = st.selectbox("Select Your Player Profile Submitting Predictions:", ALL_HUMAN_PLAYERS, index=0)
    p_pin = st.session_state.league_members[user_player].get("pin")
    is_authed = st.session_state.authenticated_players.get(user_player, False)

    if p_pin is None:
        st.info(f"🔑 **First Visit for {user_player}?** Please create a 4-digit Security PIN to protect your prediction ballot.")
        with st.form(f"pin_setup_form_{user_player}"):
            new_pin = st.text_input("Create 4-Digit Security PIN", type="password", max_chars=4)
            confirm_pin = st.text_input("Confirm 4-Digit Security PIN", type="password", max_chars=4)
            if st.form_submit_button("Set Security PIN"):
                if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                    st.session_state.league_members[user_player]["pin"] = new_pin
                    st.session_state.authenticated_players[user_player] = True
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Security PIN set successfully for {user_player}! Your ballot is unlocked.")
                    st.rerun()
                else:
                    st.error("PINs must be exactly 4 digits and match!")
    elif not is_authed:
        st.warning(f"🔒 Profile **{user_player}** is PIN protected.")
        with st.form(f"pin_verify_form_{user_player}"):
            entered_pin = st.text_input(f"Enter 4-Digit PIN for {user_player}", type="password", max_chars=4)
            if st.form_submit_button("Unlock Ballot"):
                if entered_pin == p_pin:
                    st.session_state.authenticated_players[user_player] = True
                    st.success(f"PIN verified! Welcome back, {user_player}.")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again.")
    else:
        st.success(f"🔓 **Authenticated as {user_player}**")
        
        # 1. Visual Baker Cheat Sheet
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
                        st.markdown(f"[🔗 View Profile]({info['url']})")
                    st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(f"📅 Submit Predictions for {user_player}: Week {active_pred_week}")

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

        current_eliminated = eliminated_bakers_by_week.get(active_pred_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_opts = ["-- Select Baker --"] + active_bakers

        prev_week_num = active_pred_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")

        st.info(f"Active Bakers in Tent for Week {active_pred_week}: " + ", ".join(active_bakers))

        is_double_elim = False
        if active_pred_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)

        # Post-Week 1 Season-Long Predictions if active week is 2
        if active_pred_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts]", baker_opts, key="user_win_pick")
                remaining_for_semis = [b for b in active_bakers if b != user_winner]
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", remaining_for_semis, max_selections=3)

                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts]", min_value=0, value=5)
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts]", min_value=0, value=10)
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts]", min_value=0, value=40)

                if st.button("Lock Season-Long Predictions"):
                    if user_winner.startswith("-- Select"):
                        st.error("Please select a valid season winner!")
                    elif len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members[user_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success(f"Season long predictions saved successfully for {user_player}!")

        # REQ 4 & REQ 5: Weekly Ballot with individual fields for each technical position & placeholder "-- Select Baker --"
        st.markdown(f"### Weekly Ballot: Week {active_pred_week}")
        with st.form("weekly_predictions_form"):
            weekly_picks = {}

            if active_pred_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_opts)
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key="pred_t1_w10")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key="pred_t2_w10")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key="pred_t3_w10")
                weekly_picks["tech_rank"] = [t1, t2, t3]

            elif active_pred_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts)
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key="pred_elim_1_w9")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key="pred_elim_2_w9")
                    weekly_picks["eliminated"] = [e1, e2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts)

                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key="pred_t1_w9")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key="pred_t2_w9")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key="pred_t3_w9")
                t4 = st.selectbox("Technical 4th Place [3 pts]", baker_opts, key="pred_t4_w9")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif active_pred_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts)
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key="pred_elim_1_w8")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key="pred_elim_2_w8")
                        weekly_picks["eliminated"] = [e1, e2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_opts, key="pred_trb_w8")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_opts)

                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key="pred_t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key="pred_t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key="pred_t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", baker_opts, key="pred_t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", baker_opts, key="pred_t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]

            else:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts)
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key="pred_elim_1_std")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key="pred_elim_2_std")
                        weekly_picks["eliminated"] = [e1, e2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_opts, key="pred_trb_std")
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_opts)

                st.markdown("---")
                st.write("Predict Top 3 Technical Challenge Placements:")
                col_tt1, col_tt2, col_tt3 = st.columns(3)
                with col_tt1:
                    tt1 = st.selectbox("Technical 1st Place", baker_opts, key="pred_tt1_std")
                with col_tt2:
                    tt2 = st.selectbox("Technical 2nd Place", baker_opts, key="pred_tt2_std")
                with col_tt3:
                    tt3 = st.selectbox("Technical 3rd Place", baker_opts, key="pred_tt3_std")
                weekly_picks["tech_top_3"] = [tt1, tt2, tt3]

                st.write("Predict Bottom 3 Technical Challenge Placements:")
                col_tb1, col_tb2, col_tb3 = st.columns(3)
                with col_tb1:
                    tb1 = st.selectbox("Technical 3rd-to-Last Place", baker_opts, key="pred_tb1_std")
                with col_tb2:
                    tb2 = st.selectbox("Technical 2nd-to-Last Place", baker_opts, key="pred_tb2_std")
                with col_tb3:
                    tb3 = st.selectbox("Technical Last Place", baker_opts, key="pred_tb3_std")
                weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]

            submitted = st.form_submit_button(f"Submit Week {active_pred_week} Predictions")
            if submitted:
                st.session_state.league_members[user_player]["weekly_picks"][active_pred_week] = weekly_picks
                ai_picks = generate_ai_brian_weekly_picks(active_pred_week, active_bakers, is_double_elim=is_double_elim)
                st.session_state.league_members["AI Brian"]["weekly_picks"][active_pred_week] = ai_picks
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Predictions submitted successfully for {user_player} (Week {active_pred_week})!")

# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    # REQ 2: Admin Authentication with Password PIN 6284
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Lock Screen**")
        with st.form("admin_login_form"):
            admin_pin_input = st.text_input("Enter Admin Security PIN", type="password")
            if st.form_submit_button("Unlock Admin Console"):
                if admin_pin_input == "6284":
                    st.session_state.admin_authenticated = True
                    st.success("Admin console unlocked!")
                    st.rerun()
                else:
                    st.error("Incorrect Admin PIN. Please try again.")
    else:
        st.success("🔓 **Authenticated as Administrator**")
        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.markdown("---")
        admin_selected_week = st.selectbox("Select Week to Record or Review Broadcast Results:", list(range(1, 11)), index=0, key="admin_selected_week_dropdown")
        
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
        baker_opts = ["-- Select Baker --"] + active_bakers

        # Pre-population helper
        saved_w = st.session_state.weekly_results.get(admin_selected_week, {})

        def get_opt_idx(val, options):
            if isinstance(val, str) and val in options:
                return options.index(val)
            return 0

        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}

            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts, index=get_opt_idx(saved_w.get("show_champion"), baker_opts))
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=get_opt_idx(saved_w.get("star_baker"), baker_opts))
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, default=[b for b in saved_w.get("in_line_sb", []) if b in active_bakers])
                with col2:
                    saved_elim = saved_w.get("eliminated", "Single Elimination")
                    elim_init_idx = 0
                    if saved_elim == "None": elim_init_idx = 1
                    elif isinstance(saved_elim, list): elim_init_idx = 2

                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], index=elim_init_idx, horizontal=True, key=f"admin_elim_type_w{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        s_el = saved_elim if isinstance(saved_elim, str) else "-- Select Baker --"
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=get_opt_idx(s_el, baker_opts), key=f"act_elim_single_w{admin_selected_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=[b for b in saved_w.get("in_trouble", []) if b in active_bakers], key=f"admin_trb_single_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, default=[b for b in saved_w.get("in_trouble", []) if b in active_bakers], key=f"admin_trb_none_w{admin_selected_week}")
                    else:
                        e1 = saved_elim[0] if isinstance(saved_elim, list) and len(saved_elim) > 0 else "-- Select Baker --"
                        e2 = saved_elim[1] if isinstance(saved_elim, list) and len(saved_elim) > 1 else "-- Select Baker --"
                        act_e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts, index=get_opt_idx(e1, baker_opts), key=f"admin_act_elim_1_w{admin_selected_week}")
                        act_e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts, index=get_opt_idx(e2, baker_opts), key=f"admin_act_elim_2_w{admin_selected_week}")
                        actuals["eliminated"] = [act_e1, act_e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=[b for b in saved_w.get("in_trouble", []) if b in active_bakers], key=f"admin_trb_dbl_w{admin_selected_week}")

            # REQ 6: Admin fields for EVERY technical placement available in that week (1st through Nth place)
            st.markdown("---")
            st.markdown(f"### 📊 Actual Technical Challenge Rankings (1st through {len(active_bakers)}th Place)")
            num_bakers = len(active_bakers)
            cols_per_row = 3
            admin_tech_ranks = []

            saved_tech_ranks = saved_w.get("tech_rank", [])
            if not saved_tech_ranks:
                saved_tech_ranks = saved_w.get("tech_top_3", []) + saved_w.get("tech_bottom_3", [])

            for i in range(num_bakers):
                rank_num = i + 1
                ord_str = "1st" if rank_num == 1 else ("2nd" if rank_num == 2 else ("3rd" if rank_num == 3 else f"{rank_num}th"))
                if i % cols_per_row == 0:
                    t_cols = st.columns(min(cols_per_row, num_bakers - i))
                col = t_cols[i % cols_per_row]
                with col:
                    key_r = f"admin_full_tech_w{admin_selected_week}_r{rank_num}"
                    prev_val = saved_tech_ranks[i] if i < len(saved_tech_ranks) else "-- Select Baker --"
                    idx = get_opt_idx(prev_val, baker_opts)
                    sel_baker = st.selectbox(f"Actual Technical {ord_str} Place", baker_opts, index=idx, key=key_r)
                    admin_tech_ranks.append(sel_baker)

            actuals["tech_rank"] = admin_tech_ranks
            if len(admin_tech_ranks) >= 3:
                actuals["tech_top_3"] = admin_tech_ranks[:3]
                actuals["tech_bottom_3"] = admin_tech_ranks[-3:]
            else:
                actuals["tech_top_3"] = admin_tech_ranks
                actuals["tech_bottom_3"] = admin_tech_ranks

            # REQ 7 & REQ 8: Handshake multi-select counter + Timestamps & Crying/Innuendo Occurrences + Circumstances
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            with col_hs1:
                saved_hs_bakers = saved_w.get("handshake_bakers", [])
                act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", active_bakers, default=[b for b in saved_hs_bakers if b in active_bakers], key=f"admin_hs_bakers_w{admin_selected_week}")
                act_hs_cnt = len(act_hs_bakers)
                st.write(f"**Total Handshakes Count This Week:** `{act_hs_cnt}`")
            with col_hs2:
                act_hs_stamps = st.text_input("Handshake Circumstances & Video Timestamps", value=saved_w.get("handshake_timestamps", ""), placeholder="e.g. Clara @ 14:22 Signature, Tom @ 42:10 Showstopper", key=f"admin_hs_stamps_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            with col_cry1:
                act_cry_cnt = st.number_input("Number of Crying Occurrences", min_value=0, value=saved_w.get("crying_count", 0), key=f"admin_cry_cnt_w{admin_selected_week}")
            with col_cry2:
                act_cry_stamps = st.text_input("Crying Circumstances & Video Timestamps", value=saved_w.get("crying_timestamps", ""), placeholder="e.g. Mo after technical @ 34:12", key=f"admin_cry_stamps_w{admin_selected_week}")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            with col_inn1:
                act_inn_cnt = st.number_input("Number of Innuendo Occurrences", min_value=0, value=saved_w.get("innuendo_count", 0), key=f"admin_inn_cnt_w{admin_selected_week}")
            with col_inn2:
                act_inn_stamps = st.text_input("Innuendo Circumstances & Video Timestamps", value=saved_w.get("innuendo_timestamps", ""), placeholder="e.g. Paul soggy bottom comment @ 18:45", key=f"admin_inn_stamps_w{admin_selected_week}")

            actuals["handshake_bakers"] = act_hs_bakers
            actuals["handshake_count"] = act_hs_cnt
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt
            actuals["innuendo_timestamps"] = act_inn_stamps

            if admin_selected_week == 10:
                st.markdown("---")
                st.subheader("Season Final Broadcast Outcomes")
                act_winner = st.selectbox("Actual Season Winner", baker_opts, key="admin_act_season_winner")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", active_bakers, max_selections=4, key="admin_act_season_semis")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", active_bakers, max_selections=3, key="admin_act_season_finalists")
                act_hs_tot = st.number_input("Actual Total Seasonal Handshakes", min_value=0, value=5, key="admin_act_season_hs")
                act_cry_tot = st.number_input("Actual Total Seasonal Crying Events", min_value=0, value=12, key="admin_act_season_cry")
                act_inn_tot = st.number_input("Actual Total Seasonal Sexual Innuendos", min_value=0, value=48, key="admin_act_season_inn")

                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_hs_tot,
                    "crying": act_cry_tot,
                    "innuendos": act_inn_tot
                }

            submit_admin = st.form_submit_button(f"Publish Official Week {admin_selected_week} Results & Recalculate Standings")
            if submit_admin:
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10:
                    st.session_state.season_results = actuals_season

                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)

                # Recalculate Standings
                for m_name in ALL_LEAGUE_MEMBERS:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}

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
                        if max_raw > 0:
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

                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Leaderboard updated! Week {admin_selected_week} results published successfully.")
                st.rerun()
