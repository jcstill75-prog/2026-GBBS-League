import streamlit as st
import pandas as pd
import random
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
    .lb-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        margin-bottom: 25px;
    }
    .lb-table th {
        background-color: #5D4037;
        color: #FFFFFF;
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
        color: var(--text-color, #2C1810);
    }
    .lb-name {
        font-weight: 800;
        font-size: 1.2rem;
        color: var(--text-color, #2C1810);
    }
    .lb-pts {
        font-weight: 800;
        font-size: 1.25rem;
        color: #D36B5F;
        text-align: right;
    }
    [data-theme="dark"] .lb-name,
    .stApp[data-theme="dark"] .lb-name,
    [data-theme="dark"] .lb-rank,
    .stApp[data-theme="dark"] .lb-rank,
    @media (prefers-color-scheme: dark) {
        .lb-name, .lb-rank {
            color: #FFFFFF !important;
        }
        .lb-pts {
            color: #FF8A80 !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- PERSISTENCE ENGINE ---
DATA_FILE = "league_data.json"

def save_league_data():
    data_to_save = {
        "league_members": st.session_state.league_members,
        "weekly_results": st.session_state.weekly_results,
        "season_results": st.session_state.season_results,
        "disputes": st.session_state.get("disputes", [])
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data_to_save, f, indent=4)
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

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week_num):
    if not predictions or not actuals:
        return 0

    score = 0
    
    # 1. Star Baker (+5 pts)
    pred_sb = predictions.get("star_baker")
    act_sb = actuals.get("star_baker")
    if pred_sb and act_sb and pred_sb == act_sb:
        score += 5
        
    # 2. In Line for Star Baker Consolation (+2 pts)
    pred_in_line = predictions.get("in_line_sb")
    act_in_line_list = actuals.get("in_line_sb", [])
    if pred_in_line and act_in_line_list and pred_in_line in act_in_line_list:
        if pred_in_line != act_sb:
            score += 2

    # 3. Eliminated Baker (+5 pts)
    pred_elim = predictions.get("eliminated")
    act_elim = actuals.get("eliminated")
    if pred_elim and act_elim:
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for pe in pred_elim:
                    if pe in act_elim:
                        score += 5
            else:
                if pred_elim in act_elim:
                    score += 5
        elif isinstance(pred_elim, list):
            if act_elim in pred_elim:
                score += 5
        else:
            if pred_elim == act_elim:
                score += 5

    # 4. In Trouble of Elimination Consolation (+2 pts)
    pred_trouble = predictions.get("in_trouble")
    act_trouble_list = actuals.get("in_trouble", [])
    if pred_trouble and act_trouble_list and pred_trouble in act_trouble_list:
        act_elim_set = set(act_elim) if isinstance(act_elim, list) else {act_elim}
        if pred_trouble not in act_elim_set:
            score += 2

    # 5. Technical Challenge Scoring
    pred_tech = predictions.get("tech_rank", [])
    act_tech = actuals.get("tech_rank", [])
    
    if pred_tech and act_tech and len(pred_tech) == len(act_tech):
        if pred_tech == act_tech:
            if len(act_tech) == 3:
                score += 15
            elif len(act_tech) == 4:
                score += 20
            elif len(act_tech) == 5:
                score += 25
            else:
                score += 15
        else:
            for idx, baker in enumerate(pred_tech):
                if idx < len(act_tech) and baker == act_tech[idx]:
                    if idx == 0 or idx == len(act_tech) - 1:
                        score += 3
                    else:
                        score += 2
    elif "tech_top_3" in predictions and ("tech_top_3" in actuals or "tech_rank" in actuals):
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        if not act_top3 and "tech_rank" in actuals:
            act_top3 = actuals["tech_rank"][:3]
            
        if pred_top3 and act_top3:
            if pred_top3 == act_top3:
                score += 10
            else:
                for idx, baker in enumerate(pred_top3):
                    if idx < len(act_top3) and baker == act_top3[idx]:
                        score += 3 if idx == 0 else 2
                    elif baker in act_top3:
                        score += 1

        pred_bot3 = predictions.get("tech_bottom_3", [])
        act_bot3 = actuals.get("tech_bottom_3", [])
        if not act_bot3 and "tech_rank" in actuals:
            act_bot3 = actuals["tech_rank"][-3:]
            
        if pred_bot3 and act_bot3:
            if pred_bot3 == act_bot3:
                score += 10
            else:
                for idx, baker in enumerate(pred_bot3):
                    if idx < len(act_bot3) and baker == act_bot3[idx]:
                        score += 3 if idx == 2 else 2
                    elif baker in act_bot3:
                        score += 1

    return score

def calculate_season_score(predictions, actuals):
    if not predictions or not actuals:
        return 0

    score = 0
    act_winner = actuals.get("winner")
    act_semis = set(actuals.get("semifinalists", []))
    act_finalists = set(actuals.get("finalists", []))

    pred_winner = predictions.get("winner")
    if pred_winner and act_winner:
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15

    pred_semis = set(predictions.get("semifinalists", []))
    if pred_semis and act_semis:
        correct_semis = pred_semis.intersection(act_semis)
        score += len(correct_semis) * 10

    if "handshakes" in predictions and "handshakes" in actuals:
        diff = abs(predictions["handshakes"] - actuals["handshakes"])
        if diff == 0:
            score += 20
        elif diff == 1:
            score += 10

    if "crying" in predictions and "crying" in actuals:
        diff = abs(predictions["crying"] - actuals["crying"])
        if diff == 0:
            score += 20
        elif diff <= 5:
            score += 10

    if "innuendos" in predictions and "innuendos" in actuals:
        diff = abs(predictions["innuendos"] - actuals["innuendos"])
        if diff == 0:
            score += 20
        elif diff <= 5:
            score += 10

    return score

# --- 3. CORE BAKERS LIST & DATABASE INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo",
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

ROSTER_ALPHABETICAL = [
    "AI Brian", "Ana", "Becca", "Brian", "Cassie", "Emma",
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam",
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma",
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam",
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

eliminated_bakers_by_week = {
    1: [],  # Week 1 Scouting Phase: All 12 bakers active!
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

# Streamlit Session State Initialization
saved_data = load_league_data()

if "league_members" not in st.session_state:
    if saved_data and "league_members" in saved_data:
        st.session_state.league_members = saved_data["league_members"]
    else:
        st.session_state.league_members = {
            m: {
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            } for m in ROSTER_ALPHABETICAL
        }

# Ensure pin key exists for all members safely
for m in st.session_state.league_members:
    if "pin" not in st.session_state.league_members[m]:
        st.session_state.league_members[m]["pin"] = None

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_data.get("weekly_results", {}) if saved_data else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_data.get("season_results", {}) if saved_data else {}

if "disputes" not in st.session_state:
    st.session_state.disputes = saved_data.get("disputes", []) if saved_data else []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

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
        eliminated = random.sample(elim_pool, 2 if is_double_elim and len(elim_pool) >= 2 else 1)
        if not is_double_elim: eliminated = eliminated[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2 if is_double_elim and len(elim_pool) >= 2 else 1)
        if not is_double_elim: eliminated = eliminated[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, 2 if is_double_elim and len(elim_pool) >= 2 else 1)
        if not is_double_elim: eliminated = eliminated[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}

if not st.session_state.league_members["AI Brian"].get("season_picks"):
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# Determine active competition week based on scored results
all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
active_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_week > 10:
    active_week = 10
st.session_state.current_week = active_week

# --- 5. APP INTERFACE LAYOUT ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
st.markdown("### Powered by the Balanced 2026 Competition Rules Engine")

# --- SIDEBAR: COMPETITION PROGRESS & PERSISTENT POINTS REMINDER ---
with st.sidebar:
    st.header("📌 Competition Progress")
    if active_week == 1:
        st.info("🟢 **Active Status:** Week 1 (Scouting Phase & Season-Long Predictions)")
    else:
        st.info(f"🟢 **Active Competition Week:** Week {active_week}")

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
        * **Technical Placements (Exact Spot):** 1st/Last (3 pts), 2nd/3rd/etc. (2 pts)
        * **Perfect Technical Sweep:** Flat Bonus
        * **Star League Member:** +5 pts *(weekly high scorer)*
        """)
        
    with st.expander("🏁 Weeks 8, 9 & 10 (Dynamic Scaling)", expanded=False):
        st.markdown("""
        * **Week 8 (Quarterfinal - 5 bakers):** Star Baker (5 pts), Eliminated (5 pts), Perfect Tech Sweep (25 pts)
        * **Week 9 (Semifinal - 4 bakers):** Star Baker (5 pts), Eliminated (5 pts), Perfect Tech Sweep (20 pts)
        * **Week 10 (Grand Finale - 3 bakers):** Champion (15 pts), Perfect Tech Sweep (15 pts)
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
    for name in ROSTER_ALPHABETICAL:
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
    
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="lb_player_card_sel")
    
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Season Projections (Total Score: {p_pts} pts)**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
            
        if p_weekly:
            st.markdown("#### **Weekly Predictions Log:**")
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                tr = ", ".join(w_picks.get("tech_rank", [])) if w_picks.get("tech_rank") else "N/A"
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Rankings": tr
                })
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True)

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)

            tot_hs += w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
            tot_cry += w_act.get("crying_count", 0)
            tot_inn += inn_cnt

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshake_count', 0)} ({hs_bakers})",
                "Handshake Details": hs_stamps,
                "Crying Details": cry_stamps,
                "Innuendos": inn_cnt
            })

        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)
        st.markdown(f"**Cumulative Broadcast Totals:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying: `{tot_cry}` | 💬 Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
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
                save_league_data()
                st.success("Dispute submitted successfully!")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    current_eliminated = eliminated_bakers_by_week.get(active_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    
    # Player Selection & 4-Digit PIN Authentication
    sel_player = st.selectbox("Select Your Player Name:", ROSTER_HUMANS, key="pred_player_select")
    player_data = st.session_state.league_members[sel_player]
    player_pin = player_data.get("pin")
    
    authenticated = False
    
    if player_pin is None:
        st.warning(f"🔒 First-time setup for **{sel_player}**: Please create a 4-digit security PIN to protect your predictions ballot!")
        col1, col2 = st.columns(2)
        with col1:
            new_pin = st.text_input("Create 4-Digit PIN:", type="password", key="create_pin_1")
        with col2:
            confirm_pin = st.text_input("Confirm 4-Digit PIN:", type="password", key="create_pin_2")
            
        if st.button("Set PIN & Unlock Ballot"):
            if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                player_data["pin"] = new_pin
                save_league_data()
                st.success("4-digit PIN saved successfully!")
                st.rerun()
            else:
                st.error("PINs must be exactly 4 digits and match!")
    else:
        entered_pin = st.text_input(f"Enter 4-Digit PIN for **{sel_player}**:", type="password", key="login_pin_input")
        if entered_pin == player_pin:
            authenticated = True
            st.success(f"🔓 Authenticated as **{sel_player}**!")
        elif entered_pin != "":
            st.error("Incorrect 4-digit PIN!")

    if authenticated:
        st.markdown("---")
        
        # Season-Long Entry Form (Post-Week 1 / Scouting Phase)
        if active_week == 1:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks After Week 1! | 130 pts total)", expanded=True):
                s_win = st.selectbox("Predict Season Winner [40 pts]", ["--Select Baker--"] + active_bakers, key="s_win_sel")
                s_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", [b for b in active_bakers if b != s_win], max_selections=3, key="s_semis_sel")
                s_hs = st.number_input("Predict Seasonal Handshakes [20 pts spot-on]", min_value=0, value=None, placeholder="Enter total handshakes", key="s_hs_num")
                s_cry = st.number_input("Predict Seasonal Crying Incidents [20 pts spot-on]", min_value=0, value=None, placeholder="Enter total crying incidents", key="s_cry_num")
                s_inn = st.number_input("Predict Seasonal Innuendos [20 pts spot-on]", min_value=0, value=None, placeholder="Enter total innuendos", key="s_inn_num")
                
                if st.button("Lock Season-Long Predictions"):
                    if s_win == "--Select Baker--" or len(s_semis) != 3 or s_hs is None or s_cry is None or s_inn is None:
                        st.error("Please fill out all season projection fields (select winner, 3 semifinalists, and enter counts)!")
                    else:
                        player_data["season_picks"] = {
                            "winner": s_win,
                            "semifinalists": s_semis,
                            "handshakes": s_hs,
                            "crying": s_cry,
                            "innuendos": s_inn
                        }
                        save_league_data()
                        st.success("Season-long projections saved successfully!")

        st.markdown(f"### 📅 Submit Episodic Predictions: Week {active_week}")
        
        if active_week == 1 and not st.session_state.weekly_results.get(1):
            st.info("🔒 **Week 2 Predictions Are Currently Locked!** Predictions for Week 2 will unlock automatically once the Administrator posts the official broadcast results for Week 1.")
        else:
            is_double_elim = st.checkbox("📢 Double-Elimination Week?", value=False, key=f"dbl_elim_chk_w{active_week}")
            
            with st.form("weekly_ballot_form"):
                st.subheader(f"Week {active_week} Prediction Ballot")
                p_picks = {}
                
                # Active bakers options for dropdowns
                baker_options = ["--Select Baker--"] + active_bakers
                
                if active_week == 10:
                    p_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_options, key="p_champ_s")
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w10")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w10")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w10")
                    p_picks["tech_rank"] = [t1, t2, t3]
                    
                elif active_week == 9:
                    p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="p_sb_w9")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="p_e1_w9")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="p_e2_w9")
                        p_picks["eliminated"] = [e1, e2]
                    else:
                        p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="p_e1_w9_s")
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w9")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w9")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w9")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", baker_options, key="p_t4_w9")
                    p_picks["tech_rank"] = [t1, t2, t3, t4]
                    
                elif active_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="p_sb_w8")
                        p_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="p_inline_w8")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="p_e1_w8")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="p_e2_w8")
                            p_picks["eliminated"] = [e1, e2]
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_w8")
                        else:
                            p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="p_e1_w8_s")
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_w8_s")
                            
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w8")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w8")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w8")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", baker_options, key="p_t4_w8")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", baker_options, key="p_t5_w8")
                    p_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="p_sb_std")
                        p_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="p_inline_std")
                    with col2:
                        if is_double_elim:
                            e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_options, key="p_e1_std")
                            e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_options, key="p_e2_std")
                            p_picks["eliminated"] = [e1, e2]
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_std")
                        else:
                            p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="p_e1_std_s")
                            p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_options, key="p_tr_std_s")
                            
                    st.markdown("---")
                    st.write("Predict Technical Challenge Individual Positions:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_std")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_std")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_std")
                    t_bot3 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_options, key="p_tbot3_std")
                    t_bot2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_options, key="p_tbot2_std")
                    t_last = st.selectbox("Technical Last Place [3 pts]", baker_options, key="p_tlast_std")
                    p_picks["tech_rank"] = [t1, t2, t3, t_bot3, t_bot2, t_last]

                sub_ballot = st.form_submit_button("Submit Weekly Prediction Ballot")
                if sub_ballot:
                    # DUPLICATE & MISSING SELECTION VALIDATION
                    main_selections = []
                    for k in ["star_baker", "in_line_sb", "in_trouble", "show_champion"]:
                        if k in p_picks and p_picks[k] != "--Select Baker--":
                            main_selections.append(p_picks[k])
                    if "eliminated" in p_picks:
                        el_val = p_picks["eliminated"]
                        if isinstance(el_val, list):
                            for ev in el_val:
                                if ev != "--Select Baker--": main_selections.append(ev)
                        elif el_val != "--Select Baker--":
                            main_selections.append(el_val)
                            
                    tech_selections = [t for t in p_picks.get("tech_rank", []) if t != "--Select Baker--"]
                    
                    # Check missing selections
                    all_picks_flat = main_selections + tech_selections
                    has_placeholder = False
                    
                    for k, v in p_picks.items():
                        if v == "--Select Baker--": has_placeholder = True
                        if isinstance(v, list):
                            for item in v:
                                if item == "--Select Baker--": has_placeholder = True
                                
                    if has_placeholder:
                        st.error("⚠️ Missing Selection Error: Please select a valid baker for all prediction fields before submitting!")
                    elif len(main_selections) != len(set(main_selections)):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    elif len(tech_selections) != len(set(tech_selections)):
                        st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                    else:
                        player_data["weekly_picks"][active_week] = p_picks
                        
                        # Trigger AI Brian
                        ai_picks = generate_ai_brian_weekly_picks(active_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][active_week] = ai_picks
                        
                        save_league_data()
                        st.success(f"Predictions submitted for Week {active_week}! AI Brian has also submitted his picks.")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Performance & Momentum Analytics")
    if not st.session_state.weekly_results:
        st.info("Analytics matrix will populate as broadcast results are logged by the Administrator!")
    else:
        st.write("Visual analytics and baker momentum metrics across logged episodes.")

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        st.info("🔒 Admin Panel Locked. Please enter the Administrator PIN to access controls.")
        admin_pin_in = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_gate")
        if st.button("Unlock Admin Panel"):
            if admin_pin_in == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN!")
    else:
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        st.markdown("### 📅 Select Episode Results to Input / Update")
        
        default_admin_week = active_week
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=default_admin_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        current_eliminated = eliminated_bakers_by_week.get(admin_selected_week, [])
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_opts_admin = ["--Select Baker--"] + admin_active_bakers
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts_admin, key="adm_champ")
                st.write("Actual Technical Challenge Rankings:")
                t1 = st.selectbox("Technical 1st Place", baker_opts_admin, key="adm_t1_w10")
                t2 = st.selectbox("Technical 2nd Place", baker_opts_admin, key="adm_t2_w10")
                t3 = st.selectbox("Technical 3rd Place", baker_opts_admin, key="adm_t3_w10")
                actuals["tech_rank"] = [t1, t2, t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts_admin, key=f"adm_sb_w{admin_selected_week}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, key=f"adm_inline_w{admin_selected_week}")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"adm_elim_type_w{admin_selected_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts_admin, key=f"adm_elim_s_w{admin_selected_week}")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key=f"adm_tr_s_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key=f"adm_tr_g_w{admin_selected_week}")
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts_admin, key=f"adm_e1_d_w{admin_selected_week}")
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts_admin, key=f"adm_e2_d_w{admin_selected_week}")
                        actuals["eliminated"] = [e1, e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, key=f"adm_tr_d_w{admin_selected_week}")
                
                st.write(f"Actual Technical Challenge Rankings (All {len(admin_active_bakers)} Bakers):")
                tech_rank_inputs = []
                for i_pos in range(len(admin_active_bakers)):
                    pos_label = f"Technical Position #{i_pos + 1}"
                    if i_pos == 0: pos_label += " (1st Place)"
                    elif i_pos == len(admin_active_bakers) - 1: pos_label += f" ({i_pos+1}th / Last Place)"
                    t_val = st.selectbox(pos_label, baker_opts_admin, key=f"adm_tech_pos_{i_pos}_w{admin_selected_week}")
                    tech_rank_inputs.append(t_val)
                actuals["tech_rank"] = tech_rank_inputs

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            act_hs_cnt = st.number_input("Handshakes Count", min_value=0, value=None, placeholder="Enter handshake count", key=f"adm_hs_cnt_w{admin_selected_week}")
            act_hs_stamps = st.text_input("Handshake Descriptions & Timestamps", value="", placeholder="e.g. Clara @ 14:22 Signature, Tom @ 42:10 Showstopper", key=f"adm_hs_stamps_w{admin_selected_week}")
            
            st.markdown("### 😢 Crying Incidents")
            act_cry_cnt = st.number_input("Crying Incidents Count", min_value=0, value=None, placeholder="Enter crying count", key=f"adm_cry_cnt_w{admin_selected_week}")
            act_cry_stamps = st.text_input("Crying Descriptions & Timestamps", value="", placeholder="e.g. Gabe @ 24:15 Technical", key=f"adm_cry_stamps_w{admin_selected_week}")
            
            st.markdown("### 💬 Sexual Innuendos")
            act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=None, placeholder="Enter innuendo count", key=f"adm_inn_cnt_w{admin_selected_week}")
            act_inn_stamps = st.text_input("Innuendos Descriptions & Timestamps", value="", placeholder="e.g. Paul @ 18:05 Soggy Bottom", key=f"adm_inn_stamps_w{admin_selected_week}")
            
            actuals["handshake_count"] = act_hs_cnt or 0
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt or 0
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt or 0
            actuals["innuendo_timestamps"] = act_inn_stamps
            
            if admin_selected_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                s_winner = st.selectbox("Actual Season Winner", baker_opts_admin, key="adm_s_winner")
                s_semis = st.multiselect("Actual Semifinalists (4 Bakers)", ALL_BAKERS, key="adm_s_semis")
                s_finalists = st.multiselect("Actual Finalists (3 Bakers)", ALL_BAKERS, key="adm_s_finalists")
                
                s_hs_tot = st.number_input("Actual Total Season Handshakes", min_value=0, value=5, key="adm_s_hs")
                s_cry_tot = st.number_input("Actual Total Season Crying", min_value=0, value=12, key="adm_s_cry")
                s_inn_tot = st.number_input("Actual Total Season Innuendos", min_value=0, value=48, key="adm_s_inn")
                
                actuals_season = {
                    "winner": s_winner,
                    "semifinalists": s_semis,
                    "finalists": s_finalists,
                    "handshakes": s_hs_tot,
                    "crying": s_cry_tot,
                    "innuendos": s_inn_tot
                }

            sub_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if sub_actuals:
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # Recalculate Scores
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    
                all_weeks_scored = sorted(list(st.session_state.weekly_results.keys()))
                for w in all_weeks_scored:
                    act_w = st.session_state.weekly_results[w]
                    weekly_raw = {}
                    for m_name, m_data in st.session_state.league_members.items():
                        pred_w = m_data["weekly_picks"].get(w, {})
                        raw_s = calculate_weekly_score(pred_w, act_w, w)
                        weekly_raw[m_name] = raw_s
                        m_data["weekly_breakdown"][w] = raw_s
                        
                    if weekly_raw:
                        max_r = max(weekly_raw.values())
                        for m_name, raw_s in weekly_raw.items():
                            if raw_s == max_r:
                                st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                
                if st.session_state.season_results:
                    for m_name, m_data in st.session_state.league_members.items():
                        s_pred = m_data["season_picks"]
                        s_score = calculate_season_score(s_pred, st.session_state.season_results)
                        m_data["season_score"] = s_score
                        
                for m_name, m_data in st.session_state.league_members.items():
                    w_tot = sum(m_data["weekly_breakdown"].values())
                    s_tot = m_data.get("season_score", 0)
                    m_data["total_score"] = w_tot + s_tot
                    
                save_league_data()
                st.success(f"Results published for Week {admin_selected_week}! Leaderboard updated.")
                st.rerun()

        # --- PLAYER PASSWORD RESET ---
        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_HUMANS, key="admin_pwd_reset_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            save_league_data()
            st.success(f"Password PIN for {reset_player} has been cleared! They can now set a new 4-digit PIN.")

        # --- ERASE ALL SAVED DATA ---
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
                    try: os.remove(DATA_FILE)
                    except: pass
                st.success("All saved data, test predictions, actuals, disputes, and player PINs have been permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed with erasing all data.")
