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
</style>
""", unsafe_allow_html=True)

# --- 2. GLOBAL CONSTANTS & ROSTER ---
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
        member: {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None,
            "season_score": 0
        }
        for member in ROSTER_ALPHABETICAL
    }

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

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

# Helper: load baker image safely
def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        path = os.path.join("assets", target + ext)
        if os.path.exists(path):
            try:
                return Image.open(path)
            except Exception:
                pass
    return None

# --- 4. SCORING ENGINE ---
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
        if predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5

        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim:
                        score += 5
            elif isinstance(pred_elim, str) and pred_elim in act_elim:
                score += 5
        elif act_elim != "None":
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim == act_elim:
                score += 5

    # Technical Challenge
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        if len(pred_rank) > 0 and len(pred_rank) == len(act_rank):
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == len(pred_rank):
                if week == 8: score += 25
                elif week == 9: score += 20
                elif week == 10: score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, len(pred_rank)-1]:
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

    # Consolations
    if week < 9:
        pred_in_line = predictions.get("in_line_sb")
        act_in_line = actuals.get("in_line_sb", [])
        if pred_in_line and pred_in_line in act_in_line and pred_in_line != actuals.get("star_baker"):
            score += 2

        pred_in_trouble = predictions.get("in_trouble")
        act_in_trouble = actuals.get("in_trouble", [])
        if pred_in_trouble and pred_in_trouble in act_in_trouble:
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

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    if not active_bakers:
        return {}
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
        in_line = random.choice([b for b in active_bakers if b != star_baker])
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
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
        eliminated = random.sample(elim_pool, 2) if (is_double_elim and len(elim_pool) >= 2) else random.choice(elim_pool)
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])])
        tech_top3 = random.sample(active_bakers, 3) if len(active_bakers) >= 3 else active_bakers
        rem_for_bot = [b for b in active_bakers if b not in tech_top3]
        tech_bot3 = random.sample(rem_for_bot, 3) if len(rem_for_bot) >= 3 else rem_for_bot
        return {
            "star_baker": star_baker,
            "in_line_sb": in_line,
            "eliminated": eliminated,
            "in_trouble": in_trouble,
            "tech_top_3": tech_top3,
            "tech_bottom_3": tech_bot3
        }

# --- 5. APP LAYOUT & HEADER ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    norman_img = None
    for n_path in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.png"]:
        if os.path.exists(n_path):
            try:
                norman_img = Image.open(n_path)
                break
            except Exception:
                pass
    if norman_img is not None:
        st.image(norman_img, width=110)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)

with col_title:
    st.title("Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: POINTS REFERENCE GUIDE ---
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
        * **Week 8 (Quarterfinal - 5 bakers):** Star Baker (5pts), Eliminated (5pts), Technical Sweep (25pts flat)
        * **Week 9 (Semifinal - 4 bakers):** Star Baker (5pts), Eliminated (5pts), Technical Sweep (20pts flat)
        * **Week 10 (Grand Finale - 3 bakers):** Show Champion (15pts), Technical Sweep (15pts flat)
        """)

# --- MAIN TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings",
    "📝 Submit Predictions",
    "📈 Contestant Analytics",
    "👑 Admin Panel"
])

# ==========================================
# TAB 1: LEADERBOARD & STANDINGS
# ==========================================
with tab_lead:
    st.header("🏆 Live Leaderboard")

    lb_data = []
    for member_name in ROSTER_ALPHABETICAL:
        data = st.session_state.league_members.get(member_name, {})
        tot_pts = data.get("total_score", 0)
        lb_data.append({
            "League Member": member_name,
            "Total Points": f"{tot_pts} pts",
            "pts_raw": tot_pts
        })

    df_lb = pd.DataFrame(lb_data).sort_values(by="pts_raw", ascending=False).reset_index(drop=True)

    ranks = []
    for idx in range(len(df_lb)):
        r = idx + 1
        if r == 1: ranks.append("🥇 #1")
        elif r == 2: ranks.append("🥈 #2")
        elif r == 3: ranks.append("🥉 #3")
        else: ranks.append(f"#{r}")

    df_lb["Rank"] = ranks
    df_display = df_lb[["Rank", "League Member", "Total Points"]]

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecard & Projections")

    selected_scorecard_player = st.selectbox(
        "Select Player to View Scorecard:",
        ROSTER_ALPHABETICAL,
        key="lb_scorecard_player_select"
    )

    p_data = st.session_state.league_members.get(selected_scorecard_player, {})
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})

    st.markdown(f"### **{selected_scorecard_player}'s Scorecard (Total Points: {p_pts} pts)**")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### **🌟 Season-Long Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")

        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")

    with col_s2:
        st.markdown("#### **📅 Weekly Predictions Log**")
        if not p_weekly:
            st.info("No weekly prediction ballots submitted yet.")
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
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet.")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_cnt = w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
            hs_desc = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_cnt = w_act.get("crying_count", 0)
            cry_desc = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            inn_desc = w_act.get("innuendo_timestamps", "N/A") or "N/A"

            tot_hs += hs_cnt
            tot_cry += cry_cnt
            tot_inn += inn_cnt

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{hs_cnt} ({hs_desc})",
                "Crying Scenes": f"{cry_cnt} ({cry_desc})",
                "Innuendos": f"{inn_cnt} ({inn_desc})"
            })

        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
        st.markdown(f"**Cumulative Broadcast Running Totals:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("Submit a dispute with video timestamp evidence if an episode result requires correction.")

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
            disp_evidence = st.text_area("Video Timestamp & Evidence Context")
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
                st.success("Dispute submitted successfully! It has been logged below for review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: SUBMIT PREDICTIONS
# ==========================================
with tab_submit:
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
                    st.markdown(f"[🔗 Official Profile Page]({info['url']})")

    st.markdown("---")
    st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")

    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    baker_options = ["--Select Baker--"] + active_bakers

    human_roster = sorted([m for m in st.session_state.league_members.keys() if m != "AI Brian"])
    roster_options = ["-- Select Your Name --"] + human_roster
    
    active_user = st.selectbox("Select Your Player Profile:", roster_options, index=0, key="sub_player_select")

    pin_authenticated = False

    if active_user != "-- Select Your Name --":
        user_pin = st.session_state.league_members[active_user].get("pin")
        
        # Check if already authenticated this session
        if st.session_state.authenticated_players.get(active_user, False):
            pin_authenticated = True
            st.success(f"🔓 Authenticated as **{active_user}**!")
        elif user_pin is None:
            st.info(f"Welcome **{active_user}**! Please create a 4-digit PIN password to secure your prediction ballot.")
            with st.form(key=f"pin_create_form_{active_user}"):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    new_pin = st.text_input("Create 4-Digit PIN:", type="password", max_chars=4, key=f"create_pin_1_{active_user}")
                with col_p2:
                    confirm_pin = st.text_input("Confirm 4-Digit PIN:", type="password", max_chars=4, key=f"create_pin_2_{active_user}")
                
                submit_create_btn = st.form_submit_button("Set My 4-Digit Password PIN")
                if submit_create_btn:
                    if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                        st.session_state.league_members[active_user]["pin"] = new_pin
                        st.session_state.authenticated_players[active_user] = True
                        st.success(f"4-Digit PIN set successfully for {active_user}! Your ballot is unlocked.")
                        st.rerun()
                    elif len(new_pin) != 4 or not new_pin.isdigit():
                        st.error("❌ PIN must be exactly 4 numeric digits!")
                        st.info("Example: `1234`, `6284`, `9999`")
                    elif new_pin != confirm_pin:
                        st.error("❌ PINs do not match! Please check both fields and re-enter.")
        else:
            with st.form(key=f"pin_login_form_{active_user}"):
                entered_pin = st.text_input(f"Enter 4-Digit PIN Password for {active_user}:", type="password", max_chars=4, key=f"login_pin_{active_user}")
                submit_login_btn = st.form_submit_button("Submit Password & Unlock Ballot")
                if submit_login_btn:
                    if entered_pin == user_pin:
                        st.session_state.authenticated_players[active_user] = True
                        st.success(f"🔓 Authenticated as **{active_user}**!")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect 4-digit PIN! Please try again or ask the Admin to reset your PIN.")

    if pin_authenticated:
        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))

        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")

        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)

        if st.session_state.current_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner", baker_options, key="user_win_pick")
                user_semis = st.multiselect("Predict Other 3 Semifinalists (Select 3)", active_bakers, max_selections=3)
                user_handshakes = st.number_input("Predict Seasonal Handshakes", min_value=0, value=5)
                user_crying = st.number_input("Predict Seasonal Crying", min_value=0, value=10)
                user_innuendos = st.number_input("Predict Seasonal Innuendos", min_value=0, value=40)

                if st.button("Lock Season-Long Predictions"):
                    if user_winner == "--Select Baker--" or len(user_semis) != 3 or user_winner in user_semis:
                        st.error("Please select a valid season winner and exactly 3 distinct semifinalists!")
                    else:
                        st.session_state.league_members[active_user]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        st.success("Season long predictions saved successfully!")

        st.markdown("### Weekly Ballot")
        with st.form("weekly_predictions_form"):
            weekly_picks = {}

            if st.session_state.current_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_options, key="w10_champ")
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", baker_options, key="w10_t1")
                t2 = st.selectbox("Technical 2nd Place", baker_options, key="w10_t2")
                t3 = st.selectbox("Technical 3rd Place", baker_options, key="w10_t3")
                weekly_picks["tech_rank"] = [t1, t2, t3]

            elif st.session_state.current_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="w9_sb")
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="w9_e1")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="w9_e2")
                    weekly_picks["eliminated"] = [e1, e2]
                else:
                    e = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w9_e")
                    weekly_picks["eliminated"] = e

                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", baker_options, key="w9_t1")
                t2 = st.selectbox("Technical 2nd Place", baker_options, key="w9_t2")
                t3 = st.selectbox("Technical 3rd Place", baker_options, key="w9_t3")
                t4 = st.selectbox("Technical 4th Place", baker_options, key="w9_t4")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="w8_sb")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="w8_inl")
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="w8_e1")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="w8_e2")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        e = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w8_e")
                        weekly_picks["eliminated"] = e
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="w8_intr")

                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", baker_options, key="w8_t1")
                t2 = st.selectbox("Technical 2nd Place", baker_options, key="w8_t2")
                t3 = st.selectbox("Technical 3rd Place", baker_options, key="w8_t3")
                t4 = st.selectbox("Technical 4th Place", baker_options, key="w8_t4")
                t5 = st.selectbox("Technical 5th Place", baker_options, key="w8_t5")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]

            else:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="std_sb")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="std_inl")
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="std_e1")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="std_e2")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        e = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="std_e")
                        weekly_picks["eliminated"] = e
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="std_intr")

                st.markdown("---")
                st.write("Predict Top 3 Technical Placements:")
                tt1 = st.selectbox("Technical 1st Place", baker_options, key="std_tt1")
                tt2 = st.selectbox("Technical 2nd Place", baker_options, key="std_tt2")
                tt3 = st.selectbox("Technical 3rd Place", baker_options, key="std_tt3")

                st.write("Predict Bottom 3 Technical Placements:")
                tb1 = st.selectbox("Technical 3rd-to-Last Place", baker_options, key="std_tb1")
                tb2 = st.selectbox("Technical 2nd-to-Last Place", baker_options, key="std_tb2")
                tb3 = st.selectbox("Technical Last Place", baker_options, key="std_tb3")

                weekly_picks["tech_top_3"] = [tt1, tt2, tt3]
                weekly_picks["tech_bottom_3"] = [tb1, tb2, tb3]

            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                # Validation 1: All fields selected
                all_selections = []
                for k, v in weekly_picks.items():
                    if isinstance(v, list):
                        all_selections.extend(v)
                    else:
                        all_selections.append(v)

                if "--Select Baker--" in all_selections:
                    st.error("⚠️ Please select a valid baker for all prediction fields!")
                else:
                    # Validation 2: Episodic picks duplicates
                    episodic_picks = []
                    if "star_baker" in weekly_picks: episodic_picks.append(weekly_picks["star_baker"])
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
                        # Validation 3: Technical picks duplicates
                        tech_picks = []
                        if "tech_rank" in weekly_picks:
                            tech_picks = weekly_picks["tech_rank"]
                        else:
                            tech_picks = weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])

                        if len(tech_picks) != len(set(tech_picks)):
                            st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            st.session_state.league_members[active_user]["weekly_picks"][st.session_state.current_week] = weekly_picks

                            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks

                            st.success(f"Predictions submitted for Week {st.session_state.current_week}! AI Brian has also submitted his randomized picks.")

# ==========================================
# TAB 3: CONTESTANT ANALYTICS
# ==========================================
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

# ==========================================
# TAB 4: ADMIN PANEL
# ==========================================
with tab_admin:
    st.header("👑 League Administrator Console")

    if not st.session_state.admin_authenticated:
        st.info("🔒 Admin Panel Locked. Please enter the Administrator PIN to access controls.")
        admin_input_pin = st.text_input("Enter Administrator PIN:", type="password", key="admin_pin_input_field")
        if st.button("Unlock Admin Panel"):
            if admin_input_pin == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Administrator PIN!")
    else:
        col_ad_hdr, col_ad_lock = st.columns([4, 1])
        with col_ad_lock:
            if st.button("🔒 Lock Admin Panel"):
                st.session_state.admin_authenticated = False
                st.rerun()

        st.write("Input actual episode broadcast results below to score prediction ballots and update standings:")

        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]

        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
            actuals = {}

            if st.session_state.current_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers, index=0)
                st.write("Actual Technical Challenge Rankings (1st through 3rd):")
                act_tech_ranks = []
                for idx in range(len(active_bakers)):
                    rem_bakers = [b for b in active_bakers if b not in act_tech_ranks]
                    pos_baker = st.selectbox(f"Actual Technical Position #{idx+1}", rem_bakers, index=0, key=f"act_t_w10_{idx}")
                    act_tech_ranks.append(pos_baker)
                actuals["tech_rank"] = act_tech_ranks

            elif st.session_state.current_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")], index=0)
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], index=0, key="admin_act_elim_1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), act_elim_1]], index=0, key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]

                st.write("Actual Technical Challenge Rankings (1st through 4th):")
                act_tech_ranks = []
                for idx in range(len(active_bakers)):
                    rem_bakers = [b for b in active_bakers if b not in act_tech_ranks]
                    pos_baker = st.selectbox(f"Actual Technical Position #{idx+1}", rem_bakers, index=0, key=f"act_t_w9_{idx}")
                    act_tech_ranks.append(pos_baker)
                actuals["tech_rank"] = act_tech_ranks

            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0)
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")])
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key="admin_act_elim_1_w8")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], index=0, key="admin_act_elim_2_w8")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])

                st.write("Actual Technical Challenge Rankings (Position by Position):")
                act_tech_ranks = []
                for idx in range(len(active_bakers)):
                    rem_bakers = [b for b in active_bakers if b not in act_tech_ranks]
                    pos_baker = st.selectbox(f"Actual Technical Position #{idx+1}", rem_bakers, index=0, key=f"act_t_w8_{idx}")
                    act_tech_ranks.append(pos_baker)
                actuals["tech_rank"] = act_tech_ranks

            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_std")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers, index=0)
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")])
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, index=0, key="admin_act_elim_1_std")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], index=0, key="admin_act_elim_2_std")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])

                st.write("Actual Technical Challenge Rankings (Every Position Separately):")
                act_tech_ranks = []
                for idx in range(len(active_bakers)):
                    rem_bakers = [b for b in active_bakers if b not in act_tech_ranks]
                    pos_baker = st.selectbox(f"Actual Technical Position #{idx+1}", rem_bakers, index=0, key=f"act_t_std_{idx}")
                    act_tech_ranks.append(pos_baker)

                actuals["tech_rank"] = act_tech_ranks
                if len(act_tech_ranks) >= 3:
                    actuals["tech_top_3"] = act_tech_ranks[:3]
                    actuals["tech_bottom_3"] = act_tech_ranks[-3:]

            # --- CHAOS CATEGORIES (2 FIELDS EACH) ---
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns([1, 2])
            with col_hs1:
                act_hs_cnt = st.number_input("Handshakes Count", min_value=0, value=0, key="act_hs_cnt_key")
            with col_hs2:
                act_hs_stamps = st.text_input("Handshakes Descriptions & Timestamps", key="act_hs_stamps_key")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns([1, 2])
            with col_cry1:
                act_cry_cnt = st.number_input("Crying Incidents Count", min_value=0, value=0, key="act_cry_cnt_key")
            with col_cry2:
                act_cry_stamps = st.text_input("Crying Descriptions & Timestamps", key="act_cry_stamps_key")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns([1, 2])
            with col_inn1:
                act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=0, key="act_inn_cnt_key")
            with col_inn2:
                act_inn_stamps = st.text_input("Sexual Innuendos Descriptions & Timestamps", key="act_inn_stamps_key")

            actuals["handshake_count"] = act_hs_cnt
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt
            actuals["innuendo_timestamps"] = act_inn_stamps

            if st.session_state.current_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner", active_bakers, index=0)
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
                act_tot_hs = st.number_input("Actual Total Handshakes", min_value=0, value=5)
                act_tot_cry = st.number_input("Actual Total Crying Scenes", min_value=0, value=12)
                act_tot_inn = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48)

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

                # RECALCULATE LEADERBOARD
                for m_name in st.session_state.league_members:
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

                st.success("Leaderboard updated! All predictions scored and verified against the 2026 rules.")

        # --- PLAYER PASSWORD RESET ---
        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_ALPHABETICAL, key="admin_pwd_reset_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"Password PIN for {reset_player} has been cleared! They can now set a new 4-digit PIN on the Submit Predictions tab.")

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
                st.success("All saved data, test predictions, actuals, disputes, and player PINs have been permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed with erasing all data.")
