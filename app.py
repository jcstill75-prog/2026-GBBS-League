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
        member: {
            "pin": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "season_score": 0
        }
        for member in ROSTER_ALPHABETICAL
    }
else:
    # Ensure all members have "pin" key even if loaded from older session state
    for member in ROSTER_ALPHABETICAL:
        if member not in st.session_state.league_members:
            st.session_state.league_members[member] = {
                "pin": None,
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "season_score": 0
            }
        elif "pin" not in st.session_state.league_members[member]:
            st.session_state.league_members[member]["pin"] = None

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

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
            elif pred_elim == act_elim:
                score += 5
            
    # Technical Challenge
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            if sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b) == 5:
                score += 25
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx in [0, 4] else 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            if sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b) == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx in [0, 3] else 2
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            if sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b) == 3:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx == 0 else 2
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
        pred_inline = predictions.get("in_line_sb")
        if pred_inline and (pred_inline in actuals.get("in_line_sb", [])) and (pred_inline != actuals.get("star_baker")):
            score += 2
        
        pred_trouble = predictions.get("in_trouble")
        if pred_trouble and (pred_trouble in actuals.get("in_trouble", [])):
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
            
    if predictions.get("handshakes") is not None and actuals.get("handshakes") is not None:
        diff = abs(predictions["handshakes"] - actuals["handshakes"])
        if diff == 0: score += 20
        elif diff <= 1: score += 10
            
    if predictions.get("crying") is not None and actuals.get("crying") is not None:
        diff = abs(predictions["crying"] - actuals["crying"])
        if diff == 0: score += 20
        elif diff <= 5: score += 10
            
    if predictions.get("innuendos") is not None and actuals.get("innuendos") is not None:
        diff = abs(predictions["innuendos"] - actuals["innuendos"])
        if diff == 0: score += 20
        elif diff <= 5: score += 10
            
    return score

def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    try:
        for fname in os.listdir("assets"):
            stem, ext = os.path.splitext(fname)
            if stem.lower().strip() == target and ext.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                return Image.open(os.path.join("assets", fname))
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
    if len(active_bakers) < 2:
        return {}
    if week == 10:
        champ = random.choice(active_bakers)
        rank = random.sample(active_bakers, len(active_bakers))
        return {"show_champion": champ, "tech_rank": rank}
    elif week in [8, 9]:
        sb = random.choice(active_bakers)
        pool = [b for b in active_bakers if b != sb]
        elim = random.sample(pool, 2) if is_double_elim else random.choice(pool)
        rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": sb, "eliminated": elim, "tech_rank": rank}
    else:
        sb = random.choice(active_bakers)
        inline = random.choice([b for b in active_bakers if b != sb])
        elim_pool = [b for b in active_bakers if b != sb]
        elim = random.sample(elim_pool, 2) if is_double_elim else random.choice(elim_pool)
        trouble_pool = [b for b in active_bakers if b not in (elim if isinstance(elim, list) else [elim])]
        trouble = random.choice(trouble_pool) if trouble_pool else random.choice(active_bakers)
        
        top3 = random.sample(active_bakers, 3)
        rem = [b for b in active_bakers if b not in top3]
        bot3 = random.sample(rem, 3) if len(rem) >= 3 else rem
        return {
            "star_baker": sb,
            "in_line_sb": inline,
            "eliminated": elim,
            "in_trouble": trouble,
            "tech_top_3": top3,
            "tech_bottom_3": bot3
        }

# Generate AI Brian's picks automatically if missing
if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# Determine currently unlocked week
completed_weeks = len(st.session_state.weekly_results)
unlocked_max_week = completed_weeks + 1 if completed_weeks < 10 else 10

# --- 5. APP INTERFACE ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("normanbeaver.jpg"):
        st.image("normanbeaver.jpg", width=110)
    elif os.path.exists("assets/normanbeaver.jpg"):
        st.image("assets/normanbeaver.jpg", width=110)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🧁</h1>", unsafe_allow_html=True)
with col_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📌 Competition Progress")
    if completed_weeks == 0:
        st.info("🟢 **Scouting Phase (Week 1)**\n\nPost-Week 1 Season-Long Predictions are currently OPEN! Week 2 Predictions will unlock automatically once Week 1 results are posted.")
    else:
        st.success(f"🏆 **Week {completed_weeks} Broadcast Results Posted!**\n\nWeek {unlocked_max_week} predictions are now UNLOCKED and accepting ballots.")
        
    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.write("A persistent guide of points at stake for each prediction!")
    st.warning("⏰ **Weekly voting window ends on Tuesdays right before the show airs in the UK.**")
    
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(runner-up)*
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
        * **Top 3 Technical:** Exact: 1st=3pts, 2nd/3rd=2pts | Wrong spot=1pt | Sweep=10pts
        * **Bottom 3 Technical:** Exact: 9th=2pts, 10th=2pts, 11th=3pts | Wrong spot=1pt | Sweep=10pts
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)
        
    with st.expander("🏁 Weeks 8, 9 & 10 (Dynamic Scaling)", expanded=False):
        st.markdown("""
        * **Week 8 (Quarterfinal - 5 bakers):** Star/Elim=5pts | Perfect 5-for-5 Sweep=25pts
        * **Week 9 (Semifinal - 4 bakers):** Star/Elim=5pts | Perfect 4-for-4 Sweep=20pts
        * **Week 10 (Grand Finale - 3 bakers):** Champion=15pts | Perfect 3-for-3 Sweep=15pts
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
    
    lb_rows = []
    for member_name in ROSTER_ALPHABETICAL:
        data = st.session_state.league_members[member_name]
        lb_rows.append({
            "member": member_name,
            "points": data.get("total_score", 0),
            "data": data
        })
        
    df_lb = pd.DataFrame(lb_rows).sort_values(by="points", ascending=False).reset_index(drop=True)
    df_lb.index = df_lb.index + 1
    
    table_display_rows = []
    for rank, row in df_lb.iterrows():
        rank_badge = f"🥇 #{rank}" if rank == 1 else (f"🥈 #{rank}" if rank == 2 else (f"🥉 #{rank}" if rank == 3 else f"#{rank}"))
        table_display_rows.append({
            "Rank": rank_badge,
            "League Member": row["member"],
            "Total Points": f"{row['points']} pts"
        })
        
    st.dataframe(pd.DataFrame(table_display_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    selected_sc_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="sc_player_select")
    p_data = st.session_state.league_members[selected_sc_player]
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### **{selected_sc_player}'s Season Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
        
    with col2:
        st.markdown("### **Weekly Predictions Log:**")
        if p_weekly:
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el
                })
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No weekly predictions logged yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    st.write("Review administrator's episode logging and video timestamps to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        tot_hs, tot_cry, tot_inn = 0, 0, 0
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_cnt = w_act.get("handshake_count", 0)
            cry_cnt = w_act.get("crying_count", 0)
            inn_cnt = w_act.get("innuendo_count", 0)
            
            tot_hs += hs_cnt
            tot_cry += cry_cnt
            tot_inn += inn_cnt

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{hs_cnt} ({w_act.get('handshake_timestamps', 'N/A')})",
                "Crying Scenes": f"{cry_cnt} ({w_act.get('crying_timestamps', 'N/A')})",
                "Innuendos": f"{inn_cnt} ({w_act.get('innuendo_timestamps', 'N/A')})"
            })

        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
        st.markdown(f"**Cumulative Broadcast Totals:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("Submit video timestamp evidence to contest a result for democratic GroupMe review.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_ALPHABETICAL)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 1"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Evidence (e.g., 'At 28:14 in Episode 3, Paul shakes Tom's hand')")
            disp_correction = st.text_input("Requested Correction (e.g., 'Add +1 Handshake for Tom in Week 3')")
            
            if st.form_submit_button("Submit Dispute for League Vote"):
                st.session_state.disputes.append({
                    "Player": disp_player,
                    "Week": disp_week,
                    "Category": disp_cat,
                    "Evidence": disp_evidence,
                    "Correction": disp_correction,
                    "Status": "Pending GroupMe Vote 🗳️"
                })
                st.success("Dispute submitted successfully! It has been logged for GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Player Predictions")
    
    sub_player = st.selectbox("Select Your Player Profile:", ROSTER_ALPHABETICAL, key="sub_player_profile")
    p_info = st.session_state.league_members[sub_player]
    
    # Safe PIN access using .get("pin")
    saved_pin = p_info.get("pin")
    is_authed = False
    
    if sub_player == "AI Brian":
        st.info("🤖 AI Brian is an automated bot simulator. His predictions are generated automatically.")
    elif saved_pin is None:
        st.warning(f"🔒 First Time Logging In as **{sub_player}**? Please create a 4-digit PIN below:")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            new_pin = st.text_input("Create 4-Digit Password PIN", type="password", key=f"new_pin_{sub_player}", max_chars=4)
        with col_p2:
            conf_pin = st.text_input("Confirm 4-Digit Password PIN", type="password", key=f"conf_pin_{sub_player}", max_chars=4)
            
        if st.button("Set PIN & Unlock Ballot", key=f"btn_set_pin_{sub_player}"):
            if len(new_pin) == 4 and new_pin.isdigit() and new_pin == conf_pin:
                p_info["pin"] = new_pin
                st.success("PIN set successfully! Loading your ballot...")
                st.rerun()
            else:
                st.error("PINs must match and be exactly 4 digits!")
    else:
        entered_pin = st.text_input(f"Enter 4-Digit Password PIN for {sub_player}:", type="password", key=f"login_pin_{sub_player}", max_chars=4)
        if entered_pin == saved_pin:
            is_authed = True
            st.success(f"🔓 Authenticated as {sub_player}!")
        elif entered_pin:
            st.error("Incorrect Password PIN!")

    if is_authed and sub_player != "AI Brian":
        st.markdown("---")
        
        # 1. Season-Long Predictions Option if in Scouting Phase
        if completed_weeks == 0:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                s_bakers = ALL_BAKERS
                s_win = st.selectbox("Predict Season Winner [40 pts]", ["--Select Baker--"] + s_bakers, key="sl_win")
                rem_semis = [b for b in s_bakers if b != s_win and b != "--Select Baker--"]
                s_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", rem_semis, max_selections=3)
                
                s_hs = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=5)
                s_cry = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=10)
                s_inn = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=40)
                
                if st.button("Lock Season-Long Predictions"):
                    if s_win == "--Select Baker--":
                        st.error("Please select a valid Season Winner.")
                    elif len(s_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        p_info["season_picks"] = {
                            "winner": s_win,
                            "semifinalists": s_semis,
                            "handshakes": s_hs,
                            "crying": s_cry,
                            "innuendos": s_inn
                        }
                        st.success("Season-long predictions saved successfully!")

        st.markdown("---")
        st.subheader("📅 Weekly Predictions Ballot")
        
        target_week = unlocked_max_week
        st.info(f"Submitting predictions for **Week {target_week}**.")
        
        eliminated_so_far = eliminated_bakers_by_week.get(target_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in eliminated_so_far]
        baker_opts = ["--Select Baker--"] + active_bakers
        
        prev_w_results = st.session_state.weekly_results.get(target_week - 1, {})
        prev_was_grace = (prev_w_results.get("eliminated") == "None")
        is_double_elim = False
        if target_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_was_grace)

        with st.form(f"weekly_form_w{target_week}_{sub_player}"):
            weekly_picks = {}
            
            if target_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_opts)
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key=f"t1_w10_{sub_player}")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key=f"t2_w10_{sub_player}")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key=f"t3_w10_{sub_player}")
                weekly_picks["tech_rank"] = [t1, t2, t3]
                
            elif target_week in [8, 9]:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts)
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key=f"e1_w{target_week}_{sub_player}")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key=f"e2_w{target_week}_{sub_player}")
                    weekly_picks["eliminated"] = [e1, e2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts)
                    
                st.write(f"Predict Technical Challenge Rankings (1st through {len(active_bakers)}th):")
                tech_picks = []
                for pos in range(1, len(active_bakers) + 1):
                    tp = st.selectbox(f"Technical Placement #{pos}", baker_opts, key=f"tech_p{pos}_w{target_week}_{sub_player}")
                    tech_picks.append(tp)
                weekly_picks["tech_rank"] = tech_picks
                
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts, key=f"sb_w{target_week}_{sub_player}")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts, key=f"il_w{target_week}_{sub_player}")
                with col_b:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key=f"e1_std_{sub_player}")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key=f"e2_std_{sub_player}")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, key=f"elim_std_{sub_player}")
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_opts, key=f"it_std_{sub_player}")
                    
                st.markdown("---")
                st.write("Predict Technical Challenge Placements:")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.write("**Top 3 Technical:**")
                    tt1 = st.selectbox("Technical 1st Place", baker_opts, key=f"tt1_{sub_player}")
                    tt2 = st.selectbox("Technical 2nd Place", baker_opts, key=f"tt2_{sub_player}")
                    tt3 = st.selectbox("Technical 3rd Place", baker_opts, key=f"tt3_{sub_player}")
                    weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                with col_t2:
                    st.write("**Bottom 3 Technical:**")
                    tb1 = st.selectbox("Technical 3rd-to-Last Place", baker_opts, key=f"tb1_{sub_player}")
                    tb2 = st.selectbox("Technical 2nd-to-Last Place", baker_opts, key=f"tb2_{sub_player}")
                    tb3 = st.selectbox("Technical Last Place", baker_opts, key=f"tb3_{sub_player}")
                    weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]

            sub_ballot = st.form_submit_button("Submit Prediction Ballot")
            if sub_ballot:
                # Validation
                all_selections = []
                episodic_picks = []
                tech_picks = []
                
                for k, v in weekly_picks.items():
                    if isinstance(v, list):
                        for item in v:
                            all_selections.append(item)
                            if "tech" in k: tech_picks.append(item)
                            else: episodic_picks.append(item)
                    else:
                        all_selections.append(v)
                        if "tech" in k: tech_picks.append(v)
                        else: episodic_picks.append(v)
                        
                if "--Select Baker--" in all_selections:
                    st.error("⚠️ Please select a valid baker for all prediction fields!")
                elif len(episodic_picks) != len(set(episodic_picks)):
                    st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                elif len(tech_picks) != len(set(tech_picks)):
                    st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                else:
                    p_info["weekly_picks"][target_week] = weekly_picks
                    
                    # Auto trigger AI Brian
                    ai_p = generate_ai_brian_weekly_picks(target_week, active_bakers, is_double_elim=is_double_elim)
                    st.session_state.league_members["AI Brian"]["weekly_picks"][target_week] = ai_p
                    
                    st.success(f"Predictions successfully locked in for Week {target_week}! AI Brian has also submitted his randomized picks.")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles for the Series 17 Bakers:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS)
    
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
        st.info("🔒 Admin Panel Locked. Please enter the Administrator PIN to access controls.")
        admin_pin_input = st.text_input("Enter Administrator PIN:", type="password", key="admin_auth_pin_input")
        if st.button("Unlock Admin Panel"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Administrator PIN!")
    else:
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        admin_week = st.selectbox("Select Week to Input Results:", list(range(1, 11)), index=completed_weeks if completed_weeks < 10 else 9)
        
        eliminated_so_far_admin = eliminated_bakers_by_week.get(admin_week, [])
        active_bakers_admin = [b for b in ALL_BAKERS if b not in eliminated_so_far_admin]
        
        with st.form(f"admin_results_form_w{admin_week}"):
            st.subheader(f"Input Broadcast Results for Week {admin_week}")
            actuals = {}
            
            if admin_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers_admin)
                st.write("Actual Technical Rankings:")
                act_t_ranks = []
                for pos in range(1, len(active_bakers_admin) + 1):
                    act_tp = st.selectbox(f"Actual Technical #{pos}", active_bakers_admin, index=pos-1, key=f"admin_t_{pos}_w10")
                    act_t_ranks.append(act_tp)
                actuals["tech_rank"] = act_t_ranks
            else:
                col_sb, col_el = st.columns(2)
                with col_sb:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers_admin, key=f"adm_sb_w{admin_week}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers_admin, key=f"adm_il_w{admin_week}")
                with col_b:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key=f"adm_elim_type_w{admin_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers_admin, key=f"adm_el_w{admin_week}")
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", active_bakers_admin, key=f"adm_e1_w{admin_week}")
                        e2 = st.selectbox("Actual Eliminated Baker #2", active_bakers_admin, key=f"adm_e2_w{admin_week}")
                        actuals["eliminated"] = [e1, e2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers_admin, key=f"adm_it_w{admin_week}")
                    
                st.markdown("---")
                if admin_week >= 8:
                    st.write(f"Actual Technical Rankings (1st through {len(active_bakers_admin)}th):")
                    act_t_ranks = []
                    for pos in range(1, len(active_bakers_admin) + 1):
                        act_tp = st.selectbox(f"Actual Technical #{pos}", active_bakers_admin, index=pos-1, key=f"adm_t_{pos}_w{admin_week}")
                        act_t_ranks.append(act_tp)
                    actuals["tech_rank"] = act_t_ranks
                else:
                    st.write("Actual Technical Rankings:")
                    col_at1, col_at2 = st.columns(2)
                    with col_at1:
                        st.write("**Actual Top 3 Technical:**")
                        at1 = st.selectbox("Actual Top 1st", active_bakers_admin, index=0, key=f"adm_at1_w{admin_week}")
                        at2 = st.selectbox("Actual Top 2nd", active_bakers_admin, index=1 if len(active_bakers_admin)>1 else 0, key=f"adm_at2_w{admin_week}")
                        at3 = st.selectbox("Actual Top 3rd", active_bakers_admin, index=2 if len(active_bakers_admin)>2 else 0, key=f"adm_at3_w{admin_week}")
                        actuals["tech_top_3"] = [at1, at2, at3]
                    with col_at2:
                        st.write("**Actual Bottom 3 Technical:**")
                        ab1 = st.selectbox("Actual Bottom 3rd-to-Last", active_bakers_admin, index=len(active_bakers_admin)-3 if len(active_bakers_admin)>=3 else 0, key=f"adm_ab1_w{admin_week}")
                        ab2 = st.selectbox("Actual Bottom 2nd-to-Last", active_bakers_admin, index=len(active_bakers_admin)-2 if len(active_bakers_admin)>=2 else 0, key=f"adm_ab2_w{admin_week}")
                        ab3 = st.selectbox("Actual Bottom Last", active_bakers_admin, index=len(active_bakers_admin)-1 if len(active_bakers_admin)>=1 else 0, key=f"adm_ab3_w{admin_week}")
                        actuals["tech_bottom_3"] = [ab1, ab2, ab3]

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            hs_cnt = st.number_input("Handshakes Count", min_value=0, value=0, key=f"adm_hs_cnt_w{admin_week}")
            hs_stamps = st.text_input("Handshake Descriptions & Timestamps", key=f"adm_hs_stamps_w{admin_week}")
            
            st.markdown("### 😢 Crying Incidents")
            cry_cnt = st.number_input("Crying Incidents Count", min_value=0, value=0, key=f"adm_cry_cnt_w{admin_week}")
            cry_stamps = st.text_input("Crying Descriptions & Timestamps", key=f"adm_cry_stamps_w{admin_week}")
            
            st.markdown("### 💬 Sexual Innuendos")
            inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=0, key=f"adm_inn_cnt_w{admin_week}")
            inn_stamps = st.text_input("Innuendos Descriptions & Timestamps", key=f"adm_inn_stamps_w{admin_week}")
            
            actuals["handshake_count"] = hs_cnt
            actuals["handshake_timestamps"] = hs_stamps
            actuals["crying_count"] = cry_cnt
            actuals["crying_timestamps"] = cry_stamps
            actuals["innuendo_count"] = inn_cnt
            actuals["innuendo_timestamps"] = inn_stamps

            if admin_week == 10:
                st.markdown("### 🏆 Final Season Outcomes")
                s_act_win = st.selectbox("Actual Season Winner", active_bakers_admin)
                s_act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
                s_act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
                s_act_hs = st.number_input("Actual Total Handshakes", min_value=0, value=5)
                s_act_cry = st.number_input("Actual Total Crying Scenes", min_value=0, value=12)
                s_act_inn = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48)
                actuals_season = {
                    "winner": s_act_win,
                    "semifinalists": s_act_semis,
                    "finalists": s_act_finalists,
                    "handshakes": s_act_hs,
                    "crying": s_act_cry,
                    "innuendos": s_act_inn
                }

            if st.form_submit_button("Publish Actual Results & Recalculate Standings"):
                st.session_state.weekly_results[admin_week] = actuals
                if admin_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # Recalculate scores cleanly
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    
                for w in sorted(st.session_state.weekly_results.keys()):
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
                    
                st.success(f"Broadcast results for Week {admin_week} published and standings recalculated!")
                st.rerun()

        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to clear their password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_ALPHABETICAL, key="adm_reset_pwd_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"Password PIN for {reset_player} has been cleared! They can now set a new PIN on the Submit Predictions tab.")

        st.markdown("---")
        st.markdown("### 🚨 Erase All Saved Data (Reset App State)")
        st.write("Wipe all test predictions, weekly broadcast actuals, disputes, and player passwords back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords", key="confirm_erase_chk_final")
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
