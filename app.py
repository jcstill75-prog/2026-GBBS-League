import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import os

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-contrast CSS for both Dark and Light mode legibility
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
    
    /* Dark Mode High-Contrast Overrides */
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3,
    .stApp[data-theme="dark"] h1, .stApp[data-theme="dark"] h2, .stApp[data-theme="dark"] h3 {
        color: #FFFFFF !important;
    }
    
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

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
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
        t1 = predictions.get("tech_1st")
        t2 = predictions.get("tech_2nd")
        t3 = predictions.get("tech_3rd")
        b3 = predictions.get("tech_3rd_last")
        b2 = predictions.get("tech_2nd_last")
        b1 = predictions.get("tech_last")
        
        act_top3 = actuals.get("tech_top_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        
        pred_top3 = [t for t in [t1, t2, t3] if t and t != "--Select Baker--"]
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
                        
        pred_bottom3 = [b for b in [b3, b2, b1] if b and b != "--Select Baker--"]
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
    if pred_winner and pred_winner != "--Select Baker--":
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

ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
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

# --- 3. SESSION STATE INITIALIZATION ---
if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for name in ROSTER_HUMANS + ["AI Brian"]:
        st.session_state.league_members[name] = {
            "pin": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

for name in st.session_state.league_members:
    if "pin" not in st.session_state.league_members[name]:
        st.session_state.league_members[name]["pin"] = None

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

# AI Brian pick generators
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
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool)
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}
    else:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker])
        
        sample_size = min(len(active_bakers), 6)
        tech_sample = random.sample(active_bakers, sample_size)
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_1st": tech_sample[0],
            "tech_2nd": tech_sample[1] if sample_size > 1 else tech_sample[0],
            "tech_3rd": tech_sample[2] if sample_size > 2 else tech_sample[0],
            "tech_3rd_last": tech_sample[3] if sample_size > 3 else tech_sample[0],
            "tech_2nd_last": tech_sample[4] if sample_size > 4 else tech_sample[0],
            "tech_last": tech_sample[5] if sample_size > 5 else tech_sample[0],
            "in_line_sb": in_line_sb,
            "in_trouble": in_trouble
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 4. APP INTERFACE LAYOUT ---
if os.path.exists("normanbeaver.jpg"):
    st.image("normanbeaver.jpg", width=120)
elif os.path.exists("assets/normanbeaver.jpg"):
    st.image("assets/normanbeaver.jpg", width=120)

st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: STATUS ONLY ---
all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
active_prediction_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_prediction_week > 10: active_prediction_week = 10

with st.sidebar:
    st.header("📌 Competition Progress")
    if not all_scored_weeks:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nParticipants can evaluate the bakers during Episode 1. Season-wide & Week 2 predictions unlock once Week 1 results are posted by Admin!")
    else:
        st.success(f"🟢 **Active Competition Week: Week {active_prediction_week}**\n\nBroadcast results published through Week {max(all_scored_weeks)}.")
        
    st.markdown("---")
    st.header("🎯 Points Reference Guide")
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
        *   **Top 3 Technical Challenge:** Exact positions 1st (3 pts), 2nd/3rd (2 pts); Perfect Sweep = **10 pts**
        *   **Bottom 3 Technical Challenge:** Exact positions 3rd-last/2nd-last (2 pts), Last (3 pts); Perfect Sweep = **10 pts**
        *   **Star League Member:** +5 pts *(weekly high scorer)*
        """)

# --- MAIN TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "📈 Baker Analytics", "👑 Admin Panel"])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
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

    # RELOCATED CHAOS CATEGORIES RUNNING TOTALS (Below Leaderboard, Above Player Scorecards)
    st.markdown("---")
    st.subheader("🌀 Running Broadcast Chaos Categories Totals")
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
        st.metric("🤝 Hollywood Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Sexual Innuendos", f"{tot_inn}")

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    player_names_sorted = sorted([m for m in st.session_state.league_members])
    selected_card_player = st.selectbox("Select Player to View Scorecard:", player_names_sorted, key="lb_player_card_sel")
    
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_pts = p_data.get("total_score", 0)
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        p_pin = p_data.get("pin")
        
        st.markdown(f"### **{selected_card_player}'s Profile & Scorecard (Total: {p_pts} pts)**")
        
        # Season Projections Password Protection
        st.markdown(f"#### 🌟 {selected_card_player}'s Season Projections")
        if selected_card_player == "AI Brian":
            win_pick = p_season.get("winner", "Not submitted")
            semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted"
            hs_pick = p_season.get("handshakes", "N/A")
            cry_pick = p_season.get("crying", "N/A")
            inn_pick = p_season.get("innuendos", "N/A")
            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
            st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
        else:
            if "unlocked_scorecards" not in st.session_state:
                st.session_state.unlocked_scorecards = set()
                
            if selected_card_player in st.session_state.unlocked_scorecards:
                win_pick = p_season.get("winner", "Not submitted")
                semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted"
                hs_pick = p_season.get("handshakes", "N/A")
                cry_pick = p_season.get("crying", "N/A")
                inn_pick = p_season.get("innuendos", "N/A")
                st.write(f"🏆 **Predicted Winner:** {win_pick}")
                st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
                st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
                if st.button("🔒 Re-Lock Season Projections", key=f"relock_{selected_card_player}"):
                    st.session_state.unlocked_scorecards.remove(selected_card_player)
                    st.rerun()
            else:
                st.info(f"🔒 {selected_card_player}'s season-wide predictions are PIN protected.")
                sc_pin_input = st.text_input(f"Enter 4-digit PIN for {selected_card_player} to view Season Predictions:", type="password", key=f"sc_pin_{selected_card_player}")
                if st.button("Unlock Season Predictions", key=f"sc_unlock_btn_{selected_card_player}"):
                    if p_pin and sc_pin_input == str(p_pin):
                        st.session_state.unlocked_scorecards.add(selected_card_player)
                        st.success("Unlocked season predictions!")
                        st.rerun()
                    else:
                        st.error("Incorrect PIN!")

        # Weekly Predictions Log - Unlocked for everyone!
        st.markdown(f"#### 📅 {selected_card_player}'s Weekly Predictions Log (Public)")
        if p_weekly:
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                
                t1 = w_picks.get("tech_1st", "N/A")
                t2 = w_picks.get("tech_2nd", "N/A")
                t3 = w_picks.get("tech_3rd", "N/A")
                t3_l = w_picks.get("tech_3rd_last", "N/A")
                t2_l = w_picks.get("tech_2nd_last", "N/A")
                t1_l = w_picks.get("tech_last", "N/A")
                
                tech_summary = f"Top: {t1}, {t2}, {t3} | Bot: {t3_l}, {t2_l}, {t1_l}" if t1 != "N/A" else ", ".join(w_picks.get("tech_rank", []))
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker": sb,
                    "Eliminated": el,
                    "Technical Predictions": tech_summary
                })
            st.dataframe(pd.DataFrame(w_rows), use_container_width=True)
        else:
            st.write("No weekly predictions logged yet.")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("Contestants in the tent:")
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
    
    # Check if Week 1 scouting phase or week 2+ predictions open
    if not all_scored_weeks:
        st.info("🔒 **Week 1 Scouting Phase Active!** Weekly and season-long prediction ballots will unlock automatically once the Administrator posts the official broadcast results for Week 1!")
    else:
        st.subheader(f"📅 Submit Predictions Ballot (Active Week: Week {active_prediction_week})")
        
        # Player Authentication for ballot
        st.markdown("### 👤 Player Login")
        auth_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="auth_player_select")
        p_info = st.session_state.league_members[auth_player]
        
        is_authenticated = False
        if p_info.get("pin") is None:
            st.info(f"Welcome {auth_player}! Please set your personal 4-digit PIN for the season:")
            new_pin = st.text_input("Create 4-digit PIN:", type="password", key="create_pin_input")
            confirm_pin = st.text_input("Confirm 4-digit PIN:", type="password", key="confirm_pin_input")
            if st.button("Set PIN & Unlock Ballot"):
                if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                    p_info["pin"] = new_pin
                    st.success("PIN set successfully!")
                    st.rerun()
                else:
                    st.error("PINs must be exactly 4 digits and match!")
        else:
            entered_pin = st.text_input(f"Enter 4-digit PIN for {auth_player}:", type="password", key="login_pin_input")
            if entered_pin == str(p_info.get("pin")):
                st.success(f"Authenticated as {auth_player}!")
                is_authenticated = True
            elif entered_pin:
                st.error("Incorrect PIN!")

        if is_authenticated:
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
            
            current_eliminated = eliminated_bakers_by_week.get(active_prediction_week, [])
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            baker_options = ["--Select Baker--"] + active_bakers
            
            # SEASON PREDICTIONS (Required at Week 2 together with Week 2 predictions)
            if active_prediction_week == 2:
                st.markdown("---")
                with st.expander("🌟 Season-Long Projections (Submitted in Week 2 | 130 pts total)", expanded=True):
                    s_winner = st.selectbox("Predict Season Winner [40 pts]", baker_options, key="s_win_sel")
                    s_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", active_bakers, max_selections=3, key="s_semis_sel")
                    s_hs = st.number_input("Predict Seasonal Handshakes", min_value=0, value=None, placeholder="e.g. 5", key="s_hs_num")
                    s_cry = st.number_input("Predict Seasonal Crying Scenes", min_value=0, value=None, placeholder="e.g. 10", key="s_cry_num")
                    s_inn = st.number_input("Predict Seasonal Innuendos", min_value=0, value=None, placeholder="e.g. 40", key="s_inn_num")
                    
                    if st.button("Save Season-Long Projections"):
                        if s_winner == "--Select Baker--" or len(s_semis) != 3 or s_hs is None or s_cry is None or s_inn is None:
                            st.error("⚠️ Please fill out all season-long prediction fields completely!")
                        else:
                            p_info["season_picks"] = {
                                "winner": s_winner,
                                "semifinalists": s_semis,
                                "handshakes": s_hs,
                                "crying": s_cry,
                                "innuendos": s_inn
                            }
                            st.success(f"Season-long projections saved for {auth_player}!")
            
            st.markdown("---")
            st.markdown(f"### 📝 Week {active_prediction_week} Prediction Ballot")
            
            with st.form("weekly_ballot_form"):
                weekly_picks = {}
                has_duplicate = False
                dup_message = ""
                
                if active_prediction_week == 10:
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_options, key="w10_champ")
                    t1 = st.selectbox("Technical 1st Place", baker_options, key="w10_t1")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, key="w10_t2")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, key="w10_t3")
                    weekly_picks["tech_rank"] = [t1, t2, t3]
                    
                elif active_prediction_week == 9:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="w9_sb")
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w9_elim")
                    t1 = st.selectbox("Technical 1st Place", baker_options, key="w9_t1")
                    t2 = st.selectbox("Technical 2nd Place", baker_options, key="w9_t2")
                    t3 = st.selectbox("Technical 3rd Place", baker_options, key="w9_t3")
                    t4 = st.selectbox("Technical 4th Place", baker_options, key="w9_t4")
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]
                    
                elif active_prediction_week == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_options, key="w8_sb")
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="w8_inline")
                    with col2:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="w8_elim")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="w8_trouble")
                        
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
                        weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_options, key="std_inline")
                    with col2:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_options, key="std_elim")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", baker_options, key="std_trouble")
                        
                    st.markdown("#### Technical Challenge Positions")
                    weekly_picks["tech_1st"] = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="std_t1")
                    weekly_picks["tech_2nd"] = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="std_t2")
                    weekly_picks["tech_3rd"] = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="std_t3")
                    weekly_picks["tech_3rd_last"] = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_options, key="std_t3_last")
                    weekly_picks["tech_2nd_last"] = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_options, key="std_t2_last")
                    weekly_picks["tech_last"] = st.selectbox("Technical Last Place [3 pts]", baker_options, key="std_t1_last")

                sub_ballot = st.form_submit_button("Lock & Submit Weekly Predictions")
                
                if sub_ballot:
                    # VALIDATION CHECK 1: Missing Selections
                    missing_fields = [k for k, v in weekly_picks.items() if v == "--Select Baker--"]
                    if missing_fields:
                        st.error("⚠️ Missing Selection Error: Please select a valid baker for all prediction fields before submitting!")
                    else:
                        # VALIDATION CHECK 2: Main Picks Duplicates
                        main_keys = ["star_baker", "in_line_sb", "eliminated", "in_trouble"]
                        main_picks = [weekly_picks[k] for k in main_keys if k in weekly_picks and weekly_picks[k] != "--Select Baker--"]
                        if len(main_picks) != len(set(main_picks)):
                            has_duplicate = True
                            dup_message = "❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!"
                            
                        # VALIDATION CHECK 3: Technical Positions Duplicates
                        tech_keys = ["tech_1st", "tech_2nd", "tech_3rd", "tech_3rd_last", "tech_2nd_last", "tech_last"]
                        if "tech_rank" in weekly_picks:
                            tech_picks = weekly_picks["tech_rank"]
                        else:
                            tech_picks = [weekly_picks[k] for k in tech_keys if k in weekly_picks and weekly_picks[k] != "--Select Baker--"]
                            
                        if len(tech_picks) != len(set(tech_picks)):
                            has_duplicate = True
                            dup_message = "❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!"
                            
                        if has_duplicate:
                            st.error(dup_message)
                        else:
                            # SAVE VALIDATED PICKS
                            p_info["weekly_picks"][active_prediction_week] = weekly_picks
                            
                            # Trigger AI Brian
                            ai_picks = generate_ai_brian_weekly_picks(active_prediction_week, active_bakers)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][active_prediction_week] = ai_picks
                            
                            st.success(f"Predictions successfully locked and submitted for {auth_player} (Week {active_prediction_week})! AI Brian has also submitted his picks.")

# --- TAB 3: BAKER ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Explore detailed performance matrices and official profiles for the Series 17 Bakers:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS, key="analytics_baker_sel")
    
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
        
        # Calculate Baker Stats across logged weeks
        if st.session_state.weekly_results:
            st.markdown("#### **Broadcast Trajectory & Performance Matrix:**")
            b_rows = []
            for w_num in sorted(st.session_state.weekly_results.keys()):
                w_act = st.session_state.weekly_results[w_num]
                sb = w_act.get("star_baker", w_act.get("show_champion", "None"))
                el = w_act.get("eliminated", "None")
                if isinstance(el, list): el = ", ".join(el)
                hs_list = w_act.get("handshake_bakers", [])
                
                status = "Active in Tent"
                if selected_baker == sb: status = "🌟 Star Baker"
                elif selected_baker in el: status = "❌ Eliminated"
                elif selected_baker in hs_list: status = "🤝 Hollywood Handshake"
                
                b_rows.append({
                    "Episode": f"Week {w_num}",
                    "Status / Performance": status
                })
            st.dataframe(pd.DataFrame(b_rows), use_container_width=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
        
    if not st.session_state.admin_authenticated:
        st.info("🔒 Admin Panel Locked. Please enter the Administrator PIN to access controls.")
        admin_pass = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_prompt")
        if st.button("Unlock Admin Panel", key="unlock_admin_btn"):
            if admin_pass == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN!")
    else:
        if st.button("🔒 Lock Admin Panel", key="lock_admin_btn"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        st.markdown("### 📅 Select Episode Results to Input / Update")
        
        default_admin_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
        if default_admin_week > 10: default_admin_week = 10
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=default_admin_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
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
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", admin_baker_options, key="adm_w10_champ")
                st.write("Actual Technical Challenge Final Ranks:")
                act_tech = []
                for pos in range(1, len(active_bakers) + 1):
                    act_tech.append(st.selectbox(f"Actual Technical {pos}st/nd/rd Place", admin_baker_options, key=f"adm_w10_t{pos}"))
                actuals["tech_rank"] = act_tech
                
            elif admin_selected_week in [8, 9]:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key=f"adm_w{admin_selected_week}_sb")
                actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, key=f"adm_w{admin_selected_week}_elim")
                
                st.write("Actual Technical Challenge Ranks (All Active Positions):")
                act_tech = []
                for pos in range(1, len(active_bakers) + 1):
                    act_tech.append(st.selectbox(f"Actual Technical Position #{pos}", admin_baker_options, key=f"adm_w{admin_selected_week}_t{pos}"))
                actuals["tech_rank"] = act_tech
                
            else:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", admin_baker_options, key=f"adm_std_sb_w{admin_selected_week}")
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, key=f"adm_inline_w{admin_selected_week}")
                with col2:
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", admin_baker_options, key=f"adm_std_elim_w{admin_selected_week}")
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"adm_trouble_w{admin_selected_week}")
                    
                st.markdown("#### Position-by-Position Technical Challenge Rankings")
                st.write(f"Select actual placements for all {len(active_bakers)} active bakers:")
                
                act_tech_positions = []
                for pos in range(1, len(active_bakers) + 1):
                    act_tech_positions.append(st.selectbox(f"Actual Technical Place #{pos}", admin_baker_options, key=f"adm_t_pos_{pos}_w{admin_selected_week}"))
                    
                actuals["tech_positions_all"] = act_tech_positions
                if len(act_tech_positions) >= 6:
                    actuals["tech_top_3"] = act_tech_positions[:3]
                    actuals["tech_bottom_3"] = [act_tech_positions[-3], act_tech_positions[-2], act_tech_positions[-1]]

            # CHAOS CATEGORIES: 2 EXPLICIT FIELDS FOR EACH CATEGORY (Count + Circumstances/Timestamps)
            st.markdown("---")
            st.markdown("### 🌀 Broadcast Chaos Categories Logging")
            
            st.subheader("1. 🤝 Hollywood Handshakes")
            act_hs_count = st.number_input("How many Hollywood Handshakes happened in the episode?", min_value=0, value=0, key=f"adm_hs_cnt_w{admin_selected_week}")
            act_hs_details = st.text_area("Circumstances of the Handshakes & Video Timestamps:", value="", placeholder="e.g. 'Paul shook Clara's hand @ 14:22 during Signature bake for perfectly baked macarons'", key=f"adm_hs_det_w{admin_selected_week}")
            
            st.subheader("2. 😢 Crying Incidents")
            act_cry_count = st.number_input("How many Crying Incidents happened in the episode?", min_value=0, value=0, key=f"adm_cry_cnt_w{admin_selected_week}")
            act_cry_details = st.text_area("Circumstances of the Crying Incidents & Video Timestamps:", value="", placeholder="e.g. 'Gabe cried @ 24:15 during Technical judging; Molly cried @ 54:02 during Elimination announcement'", key=f"adm_cry_det_w{admin_selected_week}")
            
            st.subheader("3. 💬 Sexual Innuendos")
            act_inn_count = st.number_input("How many Sexual Innuendos happened in the episode?", min_value=0, value=0, key=f"adm_inn_cnt_w{admin_selected_week}")
            act_inn_details = st.text_area("Circumstances of the Innuendos & Video Timestamps:", value="", placeholder="e.g. 'Prue made a soggy bottom joke @ 12:10; Paul mentioned big nuts @ 33:45'", key=f"adm_inn_det_w{admin_selected_week}")

            actuals["handshake_count"] = act_hs_count
            actuals["handshake_timestamps"] = act_hs_details
            actuals["crying_count"] = act_cry_count
            actuals["crying_timestamps"] = act_cry_details
            actuals["innuendo_count"] = act_inn_count
            actuals["innuendo_timestamps"] = act_inn_details

            submit_admin = st.form_submit_button(f"Publish Official Week {admin_selected_week} Results & Recalculate Scores")
            
            if submit_admin:
                st.session_state.weekly_results[admin_selected_week] = actuals
                
                # Recalculate all scores
                for member_name in st.session_state.league_members:
                    st.session_state.league_members[member_name]["total_score"] = 0
                    st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                    
                for w in sorted(st.session_state.weekly_results.keys()):
                    w_act = st.session_state.weekly_results[w]
                    w_scores = {}
                    for m_name, m_data in st.session_state.league_members.items():
                        p_picks = m_data["weekly_picks"].get(w, {})
                        w_pts = calculate_weekly_score(p_picks, w_act, week=w)
                        m_data["weekly_breakdown"][w] = w_pts
                        w_scores[m_name] = w_pts
                        
                    if w_scores:
                        max_pts = max(w_scores.values())
                        if max_pts > 0:
                            for m_name, pts in w_scores.items():
                                if pts == max_pts:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                    
                for m_name, m_data in st.session_state.league_members.items():
                    m_data["total_score"] = sum(m_data["weekly_breakdown"].values())
                    if st.session_state.season_results:
                        m_data["total_score"] += calculate_season_score(m_data["season_picks"], st.session_state.season_results)
                        
                st.success(f"Official results published for Week {admin_selected_week}! All player scores updated.")

        # ADMIN TOOL 2: PLAYER PIN RESET
        st.markdown("---")
        st.subheader("🔑 Administrator Player PIN Reset Console")
        reset_player = st.selectbox("Select Player Profile to Reset PIN:", ROSTER_HUMANS, key="admin_pin_reset_player")
        if st.button("Reset Player PIN"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"PIN reset for {reset_player}! They can set a new 4-digit PIN on their next login.")

        # ADMIN TOOL 3: ERASE ALL SAVED DATA AT VERY BOTTOM
        st.markdown("---")
        st.subheader("🚨 ERASE ALL SAVED DATA (RESET LEAGUE)")
        st.warning("⚠️ Warning: Erasing all data will permanently wipe all player predictions, PINs, broadcast actuals, and scores.")
        confirm_erase = st.checkbox("I confirm I want to wipe all league data back to a clean state.")
        if st.button("Erase All Saved Data"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                for name in st.session_state.league_members:
                    st.session_state.league_members[name]["pin"] = None
                    st.session_state.league_members[name]["weekly_picks"] = {}
                    st.session_state.league_members[name]["season_picks"] = {}
                    st.session_state.league_members[name]["total_score"] = 0
                    st.session_state.league_members[name]["weekly_breakdown"] = {}
                st.success("All league data erased successfully!")
                st.rerun()
            else:
                st.error("Please check the confirmation checkbox before clicking Erase!")
