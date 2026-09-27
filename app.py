import os
import streamlit as st
import pandas as pd
import random
from PIL import Image
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
    if pred_sb and act_sb and pred_sb == act_sb and not str(pred_sb).startswith("--Select"):
        score += 5
        
    # 2. In Line for Star Baker Consolation (+2 pts)
    pred_in_line = predictions.get("in_line_sb")
    act_in_line_list = actuals.get("in_line_sb", [])
    if pred_in_line and act_in_line_list and pred_in_line in act_in_line_list and not str(pred_in_line).startswith("--Select"):
        if pred_in_line != act_sb:
            score += 2

    # 3. Eliminated Baker (+5 pts)
    pred_elim = predictions.get("eliminated")
    act_elim = actuals.get("eliminated")
    if pred_elim and act_elim and act_elim != "None":
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for pe in pred_elim:
                    if pe in act_elim and not str(pe).startswith("--Select"):
                        score += 5
            else:
                if pred_elim in act_elim and not str(pred_elim).startswith("--Select"):
                    score += 5
        elif isinstance(pred_elim, list):
            if act_elim in pred_elim and not str(act_elim).startswith("--Select"):
                score += 5
        else:
            if pred_elim == act_elim and not str(pred_elim).startswith("--Select"):
                score += 5

    # 4. In Trouble of Elimination Consolation (+2 pts)
    pred_trouble = predictions.get("in_trouble")
    act_trouble_list = actuals.get("in_trouble", [])
    if pred_trouble and act_trouble_list and pred_trouble in act_trouble_list and not str(pred_trouble).startswith("--Select"):
        if pred_trouble != act_elim and (not isinstance(act_elim, list) or pred_trouble not in act_elim):
            score += 2

    # 5. Technical Challenge Rankings
    if week_num >= 8:
        p_rank = [b for b in predictions.get("tech_rank", []) if b and not str(b).startswith("--Select")]
        a_rank = [b for b in actuals.get("tech_rank", []) if b and not str(b).startswith("--Select")]
        if p_rank and a_rank and len(p_rank) == len(a_rank):
            if p_rank == a_rank:
                sweep_pts = {8: 25, 9: 20, 10: 15}
                score += sweep_pts.get(week_num, 15)
            else:
                for idx, baker in enumerate(p_rank):
                    if a_rank[idx] == baker:
                        p_val = 3 if idx in [0, len(p_rank)-1] else 2
                        score += p_val
    else:
        p_top3 = [b for b in predictions.get("tech_top_3", []) if b and not str(b).startswith("--Select")]
        a_top3 = [b for b in actuals.get("tech_top_3", []) if b and not str(b).startswith("--Select")]
        if len(p_top3) == 3 and len(a_top3) == 3:
            if p_top3 == a_top3:
                score += 10
            else:
                if len(p_top3) > 0 and len(a_top3) > 0 and p_top3[0] == a_top3[0]: score += 3
                if len(p_top3) > 1 and len(a_top3) > 1 and p_top3[1] == a_top3[1]: score += 2
                if len(p_top3) > 2 and len(a_top3) > 2 and p_top3[2] == a_top3[2]: score += 2
                for idx, baker in enumerate(p_top3):
                    if baker in a_top3 and baker != a_top3[idx]:
                        score += 1

        p_bot3 = [b for b in predictions.get("tech_bottom_3", []) if b and not str(b).startswith("--Select")]
        a_bot3 = [b for b in actuals.get("tech_bottom_3", []) if b and not str(b).startswith("--Select")]
        if len(p_bot3) == 3 and len(a_bot3) == 3:
            if p_bot3 == a_bot3:
                score += 10
            else:
                if len(p_bot3) > 0 and len(a_bot3) > 0 and p_bot3[0] == a_bot3[0]: score += 2
                if len(p_bot3) > 1 and len(a_bot3) > 1 and p_bot3[1] == a_bot3[1]: score += 2
                if len(p_bot3) > 2 and len(a_bot3) > 2 and p_bot3[2] == a_bot3[2]: score += 3
                for idx, baker in enumerate(p_bot3):
                    if baker in a_bot3 and baker != a_bot3[idx]:
                        score += 1

    return score

def calculate_season_score(predictions, actuals):
    if not predictions or not actuals:
        return 0

    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and not str(pred_winner).startswith("--Select"):
        if pred_winner == act_winner:
            score += 40
        elif pred_winner in act_finalists:
            score += 15
            
    pred_semis = [b for b in predictions.get("semifinalists", []) if b and not str(b).startswith("--Select")]
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    p_hs = predictions.get("handshakes")
    a_hs = actuals.get("handshakes")
    if p_hs is not None and a_hs is not None:
        if p_hs == a_hs:
            score += 20
        elif abs(p_hs - a_hs) <= 1:
            score += 10
            
    p_cry = predictions.get("crying")
    a_cry = actuals.get("crying")
    if p_cry is not None and a_cry is not None:
        if p_cry == a_cry:
            score += 20
        elif abs(p_cry - a_cry) <= 5:
            score += 10
            
    p_inn = predictions.get("innuendos")
    a_inn = actuals.get("innuendos")
    if p_inn is not None and a_inn is not None:
        if p_inn == a_inn:
            score += 20
        elif abs(p_inn - a_inn) <= 5:
            score += 10

    return score

# --- 3. ROSTER & GLOBAL CONSTANTS ---
ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma",
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam",
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ROSTER_ALPHABETICAL = ["AI Brian"] + ROSTER_HUMANS

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

def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    try:
        for filename in os.listdir("assets"):
            stem, ext = os.path.splitext(filename)
            if stem.lower().strip() == target and ext.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                full_path = os.path.join("assets", filename)
                try:
                    return Image.open(full_path)
                except Exception:
                    pass
    except Exception:
        pass
    return None

# --- 4. SESSION STATE INITIALIZATION ---
loaded_data = load_league_data()

if "league_members" not in st.session_state:
    if loaded_data and "league_members" in loaded_data:
        st.session_state.league_members = loaded_data["league_members"]
    else:
        st.session_state.league_members = {
            member: {
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "season_score": 0,
                "pin": None
            }
            for member in ROSTER_ALPHABETICAL
        }

for m in ROSTER_ALPHABETICAL:
    if m not in st.session_state.league_members:
        st.session_state.league_members[m] = {
            "weekly_picks": {}, "season_picks": {}, "total_score": 0, "weekly_breakdown": {}, "season_score": 0, "pin": None
        }

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = loaded_data.get("weekly_results", {}) if loaded_data else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = loaded_data.get("season_results", {}) if loaded_data else {}

if "disputes" not in st.session_state:
    st.session_state.disputes = loaded_data.get("disputes", []) if loaded_data else []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

all_published = sorted(list(st.session_state.weekly_results.keys()))
unlocked_max_week = max(all_published) + 1 if all_published else 1
if unlocked_max_week > 10: unlocked_max_week = 10
st.session_state.current_week = unlocked_max_week

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
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}
    else:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bot = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bot, min(3, len(rem_bot))) if rem_bot else random.sample(active_bakers, min(3, len(active_bakers)))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_top_3": tech_top_3, "tech_bottom_3": tech_bottom_3, "in_line_sb": in_line_sb, "in_trouble": in_trouble}

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. HEADER & SIDEBAR ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("normanbeaver.jpg"):
        st.image("normanbeaver.jpg", width=90)
    elif os.path.exists("assets/normanbeaver.jpg"):
        st.image("assets/normanbeaver.jpg", width=90)
    else:
        st.markdown("<h1 style='font-size: 60px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

with st.sidebar:
    st.header("📌 Competition Progress")
    if unlocked_max_week == 1:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nSubmit your Season-Long Predictions now! Week 2 predictions will unlock automatically once Week 1 results are posted.")
    else:
        st.success(f"🟢 **Active Status: Week {unlocked_max_week} Open**\n\nWeekly predictions are open up through Week {unlocked_max_week}.")

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

# --- MAIN TABS (4 DISTINCT TABS) ---
tab_lead, tab_submit, tab_show_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings",
    "📝 Submit Predictions",
    "📺 Show Results",
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS (ONLY LIVE LEADERBOARD & SCORECARDS) ---
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

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    current_eliminated = eliminated_bakers_by_week.get(unlocked_max_week, [])
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
        if unlocked_max_week == 1:
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

        st.markdown(f"### 📅 Submit Episodic Predictions: Week {unlocked_max_week}")
        
        if unlocked_max_week == 1 and not st.session_state.weekly_results.get(1):
            st.info("🔒 **Week 2 Predictions Are Currently Locked!** Predictions for Week 2 will unlock automatically once the Administrator posts the official broadcast results for Week 1.")
        else:
            is_double_elim = st.checkbox("📢 Double-Elimination Week?", value=False, key=f"dbl_elim_chk_w{unlocked_max_week}")
            
            with st.form("weekly_ballot_form"):
                st.subheader(f"Week {unlocked_max_week} Prediction Ballot")
                p_picks = {}
                baker_options = ["--Select Baker--"] + active_bakers
                
                if unlocked_max_week == 10:
                    p_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_options, key="p_champ_s")
                    st.write("Predict Technical Challenge Final Rank:")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_options, key="p_t1_w10")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_options, key="p_t2_w10")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_options, key="p_t3_w10")
                    p_picks["tech_rank"] = [t1, t2, t3]
                    
                elif unlocked_max_week == 9:
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
                    
                elif unlocked_max_week == 8:
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
                        player_data["weekly_picks"][unlocked_max_week] = p_picks
                        
                        ai_picks = generate_ai_brian_weekly_picks(unlocked_max_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][unlocked_max_week] = ai_picks
                        
                        save_league_data()
                        st.success(f"Predictions submitted for Week {unlocked_max_week}! AI Brian has also submitted his picks.")

# --- TAB 3: SHOW RESULTS (CHAOS TOTALS AT TOP, WEEKLY SUMMARY WITH 1st PLACE TECH, AUDIT & DISPUTES) ---
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # 1. CHAOS CATEGORIES RUNNING TOTALS (AT TOP)
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    for w_num, w_act in st.session_state.weekly_results.items():
        tot_hs += w_act.get("handshakes", w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))) or 0
        tot_cry += w_act.get("crying_count", 0) or 0
        tot_inn += w_act.get("innuendo_count", 0) or 0

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("🤝 Total Handshakes", f"{tot_hs}")
    with col_c2:
        st.metric("😢 Total Crying Incidents", f"{tot_cry}")
    with col_c3:
        st.metric("💬 Total Sexual Innuendos", f"{tot_inn}")

    st.markdown("---")
    
    # 2. WEEKLY SHOW RESULTS (FEATURING EXPLICIT 1st PLACE TECHNICAL FINISHER)
    st.subheader("📅 Weekly Broadcast Results Breakdown")
    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            with st.expander(f"📺 Week {w_num} Broadcast Results", expanded=(w_num == max(st.session_state.weekly_results.keys()))):
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.markdown("#### **🏆 Main Episode Awards**")
                    sb_val = w_act.get("star_baker", w_act.get("show_champion", "None"))
                    st.write(f"🌟 **Star Baker / Champion:** {sb_val}")
                    
                    in_line_val = w_act.get("in_line_sb", [])
                    if isinstance(in_line_val, list):
                        in_line_str = ", ".join(in_line_val) if in_line_val else "None"
                    else:
                        in_line_str = str(in_line_val)
                    st.write(f"🎖️ **In Line for Star Baker:** {in_line_str}")
                    
                    elim_val = w_act.get("eliminated", "None")
                    if isinstance(elim_val, list):
                        elim_str = ", ".join(elim_val) if elim_val else "None (Sickness Grace Week)"
                    else:
                        elim_str = str(elim_val)
                    st.write(f"🚪 **Eliminated Baker:** {elim_str}")
                    
                    in_tr_val = w_act.get("in_trouble", [])
                    if isinstance(in_tr_val, list):
                        in_tr_str = ", ".join(in_tr_val) if in_tr_val else "None"
                    else:
                        in_tr_str = str(in_tr_val)
                    st.write(f"⚠️ **In Trouble of Elimination:** {in_tr_str}")
                    
                with col_w2:
                    st.markdown("#### **🔥 Chaos Metrics & Descriptions**")
                    hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                    hs_cnt = w_act.get("handshakes", w_act.get("handshake_count", len(w_act.get("handshake_bakers", []))))
                    st.write(f"🤝 **Handshakes ({hs_cnt}):** {hs_bakers}")
                    
                    cry_cnt = w_act.get("crying_count", 0)
                    cry_stamps = w_act.get("crying_timestamps", "None") or "None"
                    st.write(f"😢 **Crying Incidents ({cry_cnt}):** {cry_stamps}")
                    
                    inn_cnt = w_act.get("innuendo_count", 0)
                    inn_stamps = w_act.get("innuendo_timestamps", "None") or "None"
                    st.write(f"💬 **Sexual Innuendos ({inn_cnt}):** {inn_stamps}")
                
                # Technical Challenge Placement (PROMINENTLY FEATURING 1ST PLACE FINISHER)
                tech_ranks = [b for b in w_act.get("tech_rank", []) if b and not str(b).startswith("--Select")]
                if tech_ranks:
                    st.markdown("#### **📊 Technical Challenge Rankings (1st Place through Last)**")
                    tech_items = []
                    for idx, baker in enumerate(tech_ranks):
                        rank_num = idx + 1
                        if rank_num == 1:
                            ord_label = "🥇 1st Place"
                        elif rank_num == 2:
                            ord_label = "🥈 2nd Place"
                        elif rank_num == 3:
                            ord_label = "🥉 3rd Place"
                        else:
                            ord_label = f"**{rank_num}th Place**"
                        tech_items.append(f"{ord_label}: **{baker}**")
                    st.write(" | ".join(tech_items))

    # 3. BROADCAST AUDIT SUMMARY TABLE
    st.markdown("---")
    st.subheader("📋 Broadcast Audit Summary Table")
    if st.session_state.weekly_results:
        audit_rows = []
        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            cry_cnt = w_act.get("crying_count", 0)
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)
            
            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshakes": f"{w_act.get('handshakes', w_act.get('handshake_count', 0))} ({hs_bakers})",
                "Crying Incidents": f"{cry_cnt} ({cry_stamps})",
                "Sexual Innuendos": f"{inn_cnt}"
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

    # 4. BROADCAST RESULT DISPUTES SUBMISSION & LOG
    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")
    
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form_show_res"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS, key="disp_player_show_res")
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in range(1, 11)], key="disp_week_show_res")
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ], key="disp_cat_show_res")
            disp_evidence = st.text_area("Video Timestamp & Evidence", key="disp_ev_show_res")
            disp_correction = st.text_input("Requested Correction", key="disp_corr_show_res")
            sub_disp = st.form_submit_button("Submit Dispute for League Vote")
            if sub_disp:
                st.session_state.disputes.append({
                    "Player": disp_player, "Week": disp_week, "Category": disp_cat,
                    "Evidence": disp_evidence, "Correction": disp_correction, "Status": "Pending GroupMe Vote 🗳️"
                })
                save_league_data()
                st.success("Dispute submitted successfully! It has been logged for democratic review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)

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
        
        # 1. PLAYER PASSWORD RESET
        with st.expander("🔑 Player Security PIN Management & Reset", expanded=False):
            reset_p = st.selectbox("Select Player Profile to Reset Password PIN:", ["--Select Player--"] + ROSTER_HUMANS, key="adm_reset_pin_sel")
            if reset_p != "--Select Player--":
                cur_pin = st.session_state.league_members[reset_p].get("pin")
                st.write(f"Current PIN Status for **{reset_p}**: `{'Locked 🔒' if cur_pin else 'Unset 🔓'}`")
                if st.button(f"Reset Password PIN for {reset_p}"):
                    st.session_state.league_members[reset_p]["pin"] = None
                    save_league_data()
                    st.success(f"PIN reset for {reset_p}! They can now create a new 4-digit PIN.")
                    st.rerun()

        # 2. DISPUTE RESOLUTION FEATURE
        st.markdown("---")
        st.subheader("⚖️ Dispute Resolution & Management Console")
        st.write("Review active player disputes submitted via the Show Results tab. Update dispute statuses after GroupMe league votes.")
        
        if not st.session_state.disputes:
            st.info("No active result disputes currently logged.")
        else:
            for d_idx, d_item in enumerate(st.session_state.disputes):
                d_status = d_item.get("Status", "Pending GroupMe Vote 🗳️")
                status_color = "🟡" if "Pending" in d_status else ("🟢" if "Accepted" in d_status else "🔴")
                
                with st.expander(f"{status_color} Dispute #{d_idx + 1}: {d_item.get('Player')} - {d_item.get('Week')} ({d_status})", expanded=True):
                    st.write(f"👤 **Submitted By:** {d_item.get('Player')}")
                    st.write(f"📅 **Week Contested:** {d_item.get('Week')}")
                    st.write(f"🎯 **Category:** {d_item.get('Category')}")
                    st.write(f"📹 **Video Evidence:** {d_item.get('Evidence')}")
                    st.write(f"✏️ **Requested Correction:** {d_item.get('Correction')}")
                    st.write(f"📊 **Current Status:** `{d_status}`")
                    
                    status_options = ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"]
                    curr_status_idx = status_options.index(d_status) if d_status in status_options else 0
                    
                    new_status_val = st.selectbox(
                        "Update Resolution Status after GroupMe Vote:",
                        status_options,
                        index=curr_status_idx,
                        key=f"disp_status_select_{d_idx}"
                    )
                    
                    col_u1, col_u2 = st.columns([2, 1])
                    with col_u1:
                        if st.button(f"Save Resolution Status for Dispute #{d_idx + 1}", key=f"btn_save_disp_{d_idx}"):
                            st.session_state.disputes[d_idx]["Status"] = new_status_val
                            save_league_data()
                            st.success(f"Dispute #{d_idx + 1} updated to **{new_status_val}**!")
                            st.rerun()
                    with col_u2:
                        if st.button(f"🗑️ Delete Dispute #{d_idx + 1}", key=f"btn_del_disp_{d_idx}"):
                            st.session_state.disputes.pop(d_idx)
                            save_league_data()
                            st.success(f"Dispute #{d_idx + 1} removed!")
                            st.rerun()

        # 3. RECORD / REVIEW BROADCAST RESULTS
        st.markdown("---")
        st.subheader("📢 Record or Review Broadcast Episode Results")
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Record or Review Broadcast Results:",
            options=list(range(1, 11)),
            index=unlocked_max_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        cur_w = admin_selected_week
        current_eliminated = eliminated_bakers_by_week.get(cur_w, [])
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_opts_admin = ["--Select Baker--"] + admin_active_bakers
        
        saved_actuals = st.session_state.weekly_results.get(cur_w, {})
        is_already_published = cur_w in st.session_state.weekly_results
        
        if is_already_published:
            st.info(f"🟢 **Week {cur_w} Results Recorded & Saved in System**\n\nReviewing saved entries below. Fields are locked by default to protect player scores.")
            enable_edit = st.checkbox(f"🔓 Enable Editing for Week {cur_w} (Requires Verification before Overwriting Saved Results)", key=f"unlock_edit_w{cur_w}")
        else:
            enable_edit = True
            
        # Interactive Elimination Radio OUTSIDE Form for instant UI reruns
        if cur_w < 10:
            saved_elim = saved_actuals.get("eliminated", "None")
            default_elim_idx = 0
            if saved_elim == "None":
                default_elim_idx = 1
            elif isinstance(saved_elim, list):
                default_elim_idx = 2
                
            elim_type = st.radio(
                "Elimination Status",
                ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"],
                index=default_elim_idx,
                horizontal=True,
                key=f"adm_elim_type_radio_w{cur_w}",
                disabled=(is_already_published and not enable_edit)
            )
        else:
            elim_type = "Single Elimination"

        with st.form(f"admin_actuals_form_w{cur_w}"):
            st.subheader(f"Broadcast Results Form: Week {cur_w}")
            if is_already_published and not enable_edit:
                st.warning("🔒 Saved Entry Protection Active: Check the 'Enable Editing' box above to modify published results.")
                
            actuals = {}
            
            if cur_w == 10:
                saved_sc = saved_actuals.get("show_champion", "--Select Baker--")
                sc_idx = baker_opts_admin.index(saved_sc) if saved_sc in baker_opts_admin else 0
                act_sc = st.selectbox("Actual Show Champion", baker_opts_admin, index=sc_idx, key="adm_champ_w10", disabled=(is_already_published and not enable_edit))
                actuals["show_champion"] = act_sc if not act_sc.startswith("--Select") else "None"
                
                st.write("Actual Technical Challenge Rankings:")
                saved_tech = saved_actuals.get("tech_rank", [])
                t1_saved = saved_tech[0] if len(saved_tech) > 0 else "--Select Baker--"
                t2_saved = saved_tech[1] if len(saved_tech) > 1 else "--Select Baker--"
                t3_saved = saved_tech[2] if len(saved_tech) > 2 else "--Select Baker--"
                
                t1 = st.selectbox("Technical 1st Place", baker_opts_admin, index=baker_opts_admin.index(t1_saved) if t1_saved in baker_opts_admin else 0, key="adm_t1_w10", disabled=(is_already_published and not enable_edit))
                t2 = st.selectbox("Technical 2nd Place", baker_opts_admin, index=baker_opts_admin.index(t2_saved) if t2_saved in baker_opts_admin else 0, key="adm_t2_w10", disabled=(is_already_published and not enable_edit))
                t3 = st.selectbox("Technical 3rd Place", baker_opts_admin, index=baker_opts_admin.index(t3_saved) if t3_saved in baker_opts_admin else 0, key="adm_t3_w10", disabled=(is_already_published and not enable_edit))
                actuals["tech_rank"] = [t1, t2, t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    saved_sb = saved_actuals.get("star_baker", "--Select Baker--")
                    sb_idx = baker_opts_admin.index(saved_sb) if saved_sb in baker_opts_admin else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts_admin, index=sb_idx, key=f"adm_sb_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    
                    saved_inline = [b for b in saved_actuals.get("in_line_sb", []) if b in admin_active_bakers]
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, default=saved_inline, placeholder="--Select Baker(s)--", key=f"adm_inline_w{cur_w}", disabled=(is_already_published and not enable_edit))
                
                with col2:
                    saved_trouble = [b for b in saved_actuals.get("in_trouble", []) if b in admin_active_bakers]
                    
                    if elim_type == "Single Elimination":
                        saved_e = saved_actuals.get("eliminated", "--Select Baker--")
                        s_el_str = saved_e if isinstance(saved_e, str) else "--Select Baker--"
                        el_idx = baker_opts_admin.index(s_el_str) if s_el_str in baker_opts_admin else 0
                        
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts_admin, index=el_idx, key=f"adm_elim_single_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=saved_trouble, placeholder="--Select Baker(s)--", key=f"adm_tr_s_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("ℹ️ No baker was eliminated this week (Sickness/Grace Week).")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", admin_active_bakers, default=saved_trouble, placeholder="--Select Baker(s)--", key=f"adm_tr_g_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    else:
                        saved_e_list = saved_actuals.get("eliminated", [])
                        s_e1 = saved_e_list[0] if isinstance(saved_e_list, list) and len(saved_e_list) > 0 else "--Select Baker--"
                        s_e2 = saved_e_list[1] if isinstance(saved_e_list, list) and len(saved_e_list) > 1 else "--Select Baker--"
                        
                        e1_idx = baker_opts_admin.index(s_e1) if s_e1 in baker_opts_admin else 0
                        e2_idx = baker_opts_admin.index(s_e2) if s_e2 in baker_opts_admin else 0
                        
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts_admin, index=e1_idx, key=f"adm_e1_d_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts_admin, index=e2_idx, key=f"adm_e2_d_w{cur_w}", disabled=(is_already_published and not enable_edit))
                        actuals["eliminated"] = [e1, e2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=saved_trouble, placeholder="--Select Baker(s)--", key=f"adm_tr_d_w{cur_w}", disabled=(is_already_published and not enable_edit))

                st.write(f"Actual Technical Challenge Rankings (All {len(admin_active_bakers)} Bakers):")
                tech_rank_inputs = []
                saved_tech_list = saved_actuals.get("tech_rank", [])
                
                for i_pos in range(len(admin_active_bakers)):
                    pos_label = f"Technical Position #{i_pos + 1}"
                    if i_pos == 0: pos_label += " (🥇 1st Place)"
                    elif i_pos == len(admin_active_bakers) - 1: pos_label += f" ({i_pos+1}th / Last Place)"
                    
                    saved_b_for_pos = saved_tech_list[i_pos] if i_pos < len(saved_tech_list) else "--Select Baker--"
                    b_pos_idx = baker_opts_admin.index(saved_b_for_pos) if saved_b_for_pos in baker_opts_admin else 0
                    
                    t_val = st.selectbox(pos_label, baker_opts_admin, index=b_pos_idx, key=f"adm_tech_pos_{i_pos}_w{cur_w}", disabled=(is_already_published and not enable_edit))
                    tech_rank_inputs.append(t_val)
                actuals["tech_rank"] = tech_rank_inputs

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            saved_hs_bakers = [b for b in saved_actuals.get("handshake_bakers", []) if b in admin_active_bakers]
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", admin_active_bakers, default=saved_hs_bakers, placeholder="--Select Baker(s)--", key=f"adm_hs_bakers_w{cur_w}", disabled=(is_already_published and not enable_edit))
            saved_hs_stamps = saved_actuals.get("handshake_timestamps", "")
            act_hs_stamps = st.text_input("Handshake Descriptions & Timestamps", value=saved_hs_stamps, placeholder="e.g. Clara @ 14:22 Signature, Tom @ 42:10 Showstopper", key=f"adm_hs_stamps_w{cur_w}", disabled=(is_already_published and not enable_edit))
            
            st.markdown("### 😢 Crying Incidents")
            saved_cry_cnt = saved_actuals.get("crying_count")
            act_cry_cnt = st.number_input("Crying Incidents Count", min_value=0, value=saved_cry_cnt, placeholder="Enter crying count", key=f"adm_cry_cnt_w{cur_w}", disabled=(is_already_published and not enable_edit))
            saved_cry_stamps = saved_actuals.get("crying_timestamps", "")
            act_cry_stamps = st.text_input("Crying Descriptions & Timestamps", value=saved_cry_stamps, placeholder="e.g. Gabe @ 24:15 Technical", key=f"adm_cry_stamps_w{cur_w}", disabled=(is_already_published and not enable_edit))
            
            st.markdown("### 💬 Sexual Innuendos")
            saved_inn_cnt = saved_actuals.get("innuendo_count")
            act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=saved_inn_cnt, placeholder="Enter innuendo count", key=f"adm_inn_cnt_w{cur_w}", disabled=(is_already_published and not enable_edit))
            saved_inn_stamps = saved_actuals.get("innuendo_timestamps", "")
            act_inn_stamps = st.text_input("Innuendos Descriptions & Timestamps", value=saved_inn_stamps, placeholder="e.g. Paul @ 18:05 Soggy Bottom", key=f"adm_inn_stamps_w{cur_w}", disabled=(is_already_published and not enable_edit))
            
            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_count"] = len(act_handshake_bakers)
            actuals["handshakes"] = len(act_handshake_bakers)
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt or 0
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt or 0
            actuals["innuendo_timestamps"] = act_inn_stamps
            
            if cur_w == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                saved_s_res = st.session_state.season_results
                saved_s_win = saved_s_res.get("winner", "--Select Baker--")
                s_win_idx = baker_opts_admin.index(saved_s_win) if saved_s_win in baker_opts_admin else 0
                s_winner = st.selectbox("Actual Season Winner", baker_opts_admin, index=s_win_idx, key="adm_s_winner_w10", disabled=(is_already_published and not enable_edit))
                
                saved_s_semis = [b for b in saved_s_res.get("semifinalists", []) if b in ALL_BAKERS]
                s_semis = st.multiselect("Actual Semifinalists (4 Bakers)", ALL_BAKERS, default=saved_s_semis, key="adm_s_semis_w10", disabled=(is_already_published and not enable_edit))
                
                saved_s_fin = [b for b in saved_s_res.get("finalists", []) if b in ALL_BAKERS]
                s_finalists = st.multiselect("Actual Finalists (3 Bakers)", ALL_BAKERS, default=saved_s_fin, key="adm_s_finalists_w10", disabled=(is_already_published and not enable_edit))
                
                s_hs_tot = st.number_input("Actual Total Season Handshakes", min_value=0, value=saved_s_res.get("handshakes"), key="adm_s_hs_w10", disabled=(is_already_published and not enable_edit))
                s_cry_tot = st.number_input("Actual Total Season Crying", min_value=0, value=saved_s_res.get("crying"), key="adm_s_cry_w10", disabled=(is_already_published and not enable_edit))
                s_inn_tot = st.number_input("Actual Total Season Innuendos", min_value=0, value=saved_s_res.get("innuendos"), key="adm_s_inn_w10", disabled=(is_already_published and not enable_edit))
                
                actuals_season = {
                    "winner": s_winner,
                    "semifinalists": s_semis,
                    "finalists": s_finalists,
                    "handshakes": s_hs_tot,
                    "crying": s_cry_tot,
                    "innuendos": s_inn_tot
                }

            btn_label = "Update & Recalculate Saved Results" if is_already_published else "Publish Actual Results & Recalculate Standings"
            sub_actuals = st.form_submit_button(btn_label, disabled=(is_already_published and not enable_edit))
            if sub_actuals:
                if is_already_published and not enable_edit:
                    st.error("🔒 Overwrite Blocked: You must check 'Enable Editing' above before saving changes to a published week!")
                else:
                    st.session_state.weekly_results[cur_w] = actuals
                    if cur_w == 10:
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
                                if raw_s == max_r and raw_s > 0:
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
                    st.success(f"Results saved for Week {cur_w}! Leaderboard updated.")
                    st.rerun()

        # 4. ERASE ALL SAVED DATA
        st.markdown("---")
        st.markdown("### 🚨 Erase All Saved Data (Reset App State)")
        st.write("Wipe all test predictions, weekly broadcast actuals, disputes, and player passwords back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords", key="confirm_erase_chk_master")
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
