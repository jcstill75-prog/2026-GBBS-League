import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
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

# --- 2. THE 2026 OFFICIAL SCORING ENGINE (INTERNALIZED FOR PORTABILITY) ---
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
        
        # Sickness / Double Elimination Safe Scoring for standard weeks
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
            score += 2
        if (predictions.get("in_trouble") in actuals.get("in_trouble", [])) and (predictions.get("in_trouble") != actuals.get("eliminated")):
            score += 2
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    # 1. Season Winner (40 points) or finalist consolation (15 points)
    pred_winner = predictions.get("winner")
    if pred_winner and act_winner:
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
            
    # 2. Other 3 Semifinalists (10 points each)
    pred_semis = predictions.get("semifinalists", [])
    if pred_semis and act_semis:
        for baker in pred_semis:
            if baker in act_semis:
                score += 10
                
    # 3. Hollywood Handshakes (Spot-on = 20 pts, +/- 1 = 10 pts)
    pred_hs = predictions.get("handshakes")
    act_hs = actuals.get("handshakes")
    if pred_hs is not None and act_hs is not None:
        if pred_hs == act_hs:
            score += 20
        elif abs(pred_hs - act_hs) <= 1:
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
    """Smart case-insensitive image loader for show contestants (assets/clara.jpg etc.)."""
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

# --- 3. CORE BAKERS LIST & DATABASE INITIALIZATION ---
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

HUMAN_PLAYERS = [
    "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]
ALL_MEMBERS = HUMAN_PLAYERS + ["AI Brian"]

# Streamlit Session State Initialization for persistence
if "league_members" not in st.session_state:
    st.session_state.league_members = {}

# Ensure all 15 members are initialized cleanly without legacy keys
for member_name in ALL_MEMBERS:
    if member_name not in st.session_state.league_members:
        st.session_state.league_members[member_name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }

if "current_week" not in st.session_state:
    st.session_state.current_week = 2

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
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
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
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
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

# --- 5. APP INTERFACE LAYOUT & HEADER ---
col_hdr1, col_hdr2 = st.columns([1, 5])
with col_hdr1:
    if os.path.exists("normanbeaver.jpg"):
        st.image("normanbeaver.jpg", width=100)
    elif os.path.exists("assets/normanbeaver.jpg"):
        st.image("assets/normanbeaver.jpg", width=100)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_hdr2:
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
        
        html_rows = []
        for rank, row in df_lb.iterrows():
            m_name = row["member"]
            m_pts = row["points"]
            
            rank_badge = f"#{rank}"
            if rank == 1: rank_badge = "🥇 #1"
            elif rank == 2: rank_badge = "🥈 #2"
            elif rank == 3: rank_badge = "🥉 #3"
            
            html_rows.append(f"""
            <tr>
                <td class="lb-rank">{rank_badge}</td>
                <td class="lb-name">{m_name}</td>
                <td class="lb-pts">{m_pts} pts</td>
            </tr>
            """)
            
        table_html = f"""
        <table class="lb-table">
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
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    for rank, row in df_lb.iterrows():
        p_name = row["member"]
        p_data = row["data"]
        p_pts = row["points"]
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        with st.expander(f"👤 {p_name} — Total Score: {p_pts} pts", expanded=(p_name == "AI Brian")):
            st.markdown(f"### **{p_name}'s Season Projections**")
            win_pick = p_season.get("winner", "Not submitted yet")
            semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
            hs_pick = p_season.get("handshakes", "N/A")
            cry_pick = p_season.get("crying", "N/A")
            inn_pick = p_season.get("innuendos", "N/A")

            st.write(f"🏆 **Predicted Winner:** {win_pick}")
            st.write(f"🎯 **Predicted Semifinalists:** {semis_pick}")
            st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")

            st.markdown("---")
            st.markdown(f"### **{p_name}'s Weekly Predictions Log**")
            if not p_weekly:
                st.info("No weekly prediction ballots submitted yet.")
            else:
                for w_num in sorted(p_weekly.keys()):
                    w_picks = p_weekly[w_num]
                    w_score = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                    st.markdown(f"**Week {w_num} (Score: {w_score} pts)**")
                    st.json(w_picks)

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps (Verify Counts)")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 2!")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_bakers = ", ".join(w_act.get("crying_bakers", [])) if w_act.get("crying_bakers") else "None"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            hs_cnt = w_act.get("handshakes", 0)
            cry_cnt = w_act.get("crying", 0)
            inn_cnt = w_act.get("innuendos", 0)

            tot_hs += hs_cnt
            tot_cry += cry_cnt
            tot_inn += inn_cnt

            audit_rows.append({
                "Episode": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", "N/A"),
                "Eliminated": ", ".join(w_act.get("eliminated", [])) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": hs_cnt,
                "Handshake Recipients & Timestamps": f"{hs_bakers} ({hs_stamps})",
                "Crying Scenes": cry_cnt,
                "Crying Bakers & Timestamps": f"{cry_bakers} ({cry_stamps})",
                "Innuendos": inn_cnt
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True)
        st.markdown(f"**Cumulative Broadcast Totals Across Logged Weeks:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Innuendos: `{tot_inn}`")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    # 1. VISUAL BAKER CHEAT SHEET (With photos, emojis, bios)
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("Browse the Series 17 contestants below. Photographs load dynamically from the local assets folder if present.")
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
    st.subheader("📝 Submit Prediction Ballot")
    
    sel_player = st.selectbox("Select Your Name / Player Profile", ["-- Select Your Name --"] + HUMAN_PLAYERS)
    
    if sel_player != "-- Select Your Name --":
        st.success(f"Logging predictions for player profile: **{sel_player}**")
        
        # Dynamic active bakers list
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

        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]

        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")

        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))

        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, help="Automatically checked if the previous week was a sickness grace week with no elimination!")

        # 1. Season long entry if week is 1 or 2
        if st.session_state.current_week in [1, 2]:
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
                        st.session_state.league_members[sel_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        st.success(f"Season long predictions saved for {sel_player}!")

        # 2. Weekly Form based on active week
        st.markdown(f"### Weekly Ballot for Week {st.session_state.current_week}")
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
                tech_top_3 = st.multiselect("Top 3 Technical (Order: 1st, 2nd, 3rd - Max 3) [Up to 10 pts total]", active_bakers, max_selections=3)
                tech_bottom_3 = st.multiselect("Bottom 3 Technical (Order: 3rd-to-last, 2nd-to-last, Last - Max 3) [Up to 10 pts total]", [b for b in active_bakers if b not in tech_top_3], max_selections=3)

                weekly_picks["tech_top_3"] = tech_top_3
                weekly_picks["tech_bottom_3"] = tech_bottom_3

            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                st.session_state.league_members[sel_player]["weekly_picks"][st.session_state.current_week] = weekly_picks

                # Trigger AI Brian
                ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks

                st.success(f"Predictions submitted for {sel_player} for Week {st.session_state.current_week}! AI Brian has also submitted his randomized picks.")

    st.markdown("---")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ["-- Select Your Name --"] + HUMAN_PLAYERS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 2"])
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
                st.success("Dispute submitted successfully!")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        df_disp = pd.DataFrame(st.session_state.disputes)
        st.dataframe(df_disp, use_container_width=True)

# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Use this tab to input the actual results from the broadcast. Submitting actual results will score the predictions and update the leaderboard!")
    
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

    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    
    with st.form("admin_actuals_form"):
        st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
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
            act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0)
            act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0)
            act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0)
            act_t4 = st.selectbox("Actual Technical 4th Place", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0)
            act_t5 = st.selectbox("Actual Technical 5th Place", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], index=0)
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

            st.write("Actual Technical Challenge Placements:")
            act_top_3 = st.multiselect("Actual Top 3 Technical (1st, 2nd, 3rd in exact order)", active_bakers, max_selections=3)
            act_bottom_3 = st.multiselect("Actual Bottom 3 Technical (Bottom 3 in exact order: 9th, 10th, 11th)", [b for b in active_bakers if b not in act_top_3], max_selections=3)

            actuals["tech_top_3"] = act_top_3
            actuals["tech_bottom_3"] = act_bottom_3

        st.markdown("---")
        st.markdown("### 🤝 Broadcast Audit Counts & Video Timestamps")
        act_hs_cnt = st.number_input("Hollywood Handshakes Count in Episode", min_value=0, value=0, key=f"hs_cnt_w{st.session_state.current_week}")
        act_hs_bakers = st.multiselect("Handshake Recipients", ALL_BAKERS, key=f"hs_bakers_w{st.session_state.current_week}")
        act_hs_stamps = st.text_input("Handshake Video Timestamps (e.g., '14:20 Signature, 42:10 Showstopper')", key=f"hs_stamps_w{st.session_state.current_week}")

        act_cry_cnt = st.number_input("Crying Scenes Count in Episode", min_value=0, value=0, key=f"cry_cnt_w{st.session_state.current_week}")
        act_cry_bakers = st.multiselect("Crying Bakers", ALL_BAKERS, key=f"cry_bakers_w{st.session_state.current_week}")
        act_cry_stamps = st.text_input("Crying Scene Video Timestamps (e.g., '08:15 Technical panic, 55:00 Elimination')", key=f"cry_stamps_w{st.session_state.current_week}")

        act_innuendo_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0, key=f"innuendo_cnt_w{st.session_state.current_week}")

        actuals["handshakes"] = act_hs_cnt
        actuals["handshake_bakers"] = act_hs_bakers
        actuals["handshake_timestamps"] = act_hs_stamps
        actuals["crying"] = act_cry_cnt
        actuals["crying_bakers"] = act_cry_bakers
        actuals["crying_timestamps"] = act_cry_stamps
        actuals["innuendos"] = act_innuendo_cnt

        if st.session_state.current_week == 10:
            st.markdown("---")
            st.markdown("### 🏆 Actual Season Finale Results (For Scoring Season-Long Projections)")
            act_season_winner = st.selectbox("Actual Season Champion", ALL_BAKERS)
            act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
            act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
            act_handshakes = st.number_input("Actual Total Season Hollywood Handshakes", min_value=0, value=8)
            act_crying = st.number_input("Actual Total Season Crying Scenes", min_value=0, value=14)
            act_innuendos = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48)

            actuals["season_results"] = {
                "winner": act_season_winner,
                "semifinalists": act_semis,
                "finalists": act_finalists,
                "handshakes": act_handshakes,
                "crying": act_crying,
                "innuendos": act_innuendos
            }

        sub_admin = st.form_submit_button(f"Publish Results & Score Week {st.session_state.current_week}")
        if sub_admin:
            st.session_state.weekly_results[st.session_state.current_week] = actuals

            # Recalculate scores for all 15 members
            for member_name in st.session_state.league_members:
                st.session_state.league_members[member_name]["total_score"] = 0
                st.session_state.league_members[member_name]["weekly_breakdown"] = {}

            # 1. Weekly Scores
            for w in sorted(st.session_state.weekly_results.keys()):
                w_act = st.session_state.weekly_results[w]
                w_scores = {}
                for m_name, m_data in st.session_state.league_members.items():
                    m_picks = m_data["weekly_picks"].get(w, {})
                    sc = calculate_weekly_score(m_picks, w_act, week=w)
                    w_scores[m_name] = sc
                    m_data["weekly_breakdown"][w] = sc
                    m_data["total_score"] += sc

                # Star League Bonus (+5 to high scorer)
                if w_scores:
                    max_sc = max(w_scores.values())
                    if max_sc > 0:
                        for m_name, sc_val in w_scores.items():
                            if sc_val == max_sc:
                                st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                st.session_state.league_members[m_name]["total_score"] += 5

            # 2. Season-Long Scores (if Week 10 published)
            if st.session_state.current_week == 10 and "season_results" in actuals:
                st.session_state.season_results = actuals["season_results"]
                for m_name, m_data in st.session_state.league_members.items():
                    s_picks = m_data.get("season_picks", {})
                    s_sc = calculate_season_score(s_picks, st.session_state.season_results)
                    m_data["total_score"] += s_sc

            st.success(f"Week {st.session_state.current_week} results published! All player scores and the Live Leaderboard have been updated.")
