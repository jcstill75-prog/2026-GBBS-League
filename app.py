import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
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

# Custom Styling for cozy baking theme and high contrast dark/light mode
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
        color: var(--text-color, #5D4037);
    }
    .status-box {
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FFB74D;
        margin-bottom: 15px;
    }
    .leaderboard-table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
    }
    /* Dark Mode adaptive text colors for header and tables */
    .header-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--text-color, #5D4037);
        margin-bottom: 0px;
    }
    [data-theme="dark"] .header-title,
    .stApp[data-theme="dark"] .header-title,
    @media (prefers-color-scheme: dark) {
        .header-title {
            color: #FFFFFF !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS & DISK PERSISTENCE ---

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

def load_ai_brian_avatar():
    """Finds AI Brian avatar path or image."""
    for b_path in ["ai_brian.jpg", "AI Brian.jpg", "assets/ai_brian.jpg", "assets/AI_Brian.jpg", "assets/ai_brian.png", "assets/AI_Brian.png"]:
        if os.path.exists(b_path):
            return b_path
    return None

def render_player_avatar(avatar_val, width=100, caption=None):
    """Safely renders a player avatar using Streamlit native components or fallbacks."""
    if isinstance(avatar_val, str):
        if avatar_val.startswith("data:image"):
            st.image(avatar_val, width=width, caption=caption)
            return
        elif os.path.exists(avatar_val):
            st.image(avatar_val, width=width, caption=caption)
            return
        elif avatar_val == "🤖":
            b_path = load_ai_brian_avatar()
            if b_path and os.path.exists(b_path):
                st.image(b_path, width=width, caption=caption or "AI Brian")
            else:
                st.markdown(f"<h1 style='font-size: {width//2}px; margin: 0;'>🤖</h1>", unsafe_allow_html=True)
            return
    elif isinstance(avatar_val, Image.Image):
        st.image(avatar_val, width=width, caption=caption)
        return
    
    st.markdown(f"<h1 style='font-size: {width//2}px; margin: 0;'>🍪</h1>", unsafe_allow_html=True)

def save_league_data(members_data, weekly_results_data, season_results_data):
    """Saves league state to league_data.json safely with Base64 image encoding."""
    try:
        clean_members = {}
        for player, info in members_data.items():
            clean_info = dict(info)
            av = clean_info.get("avatar")
            if isinstance(av, Image.Image):
                buf = io.BytesIO()
                av.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                clean_info["avatar"] = f"data:image/png;base64,{b64}"
            clean_members[player] = clean_info
            
        data_payload = {
            "members": clean_members,
            "weekly_results": weekly_results_data,
            "season_results": season_results_data
        }
        with open("league_data.json", "w") as f:
            json.dump(data_payload, f, indent=2)
    except Exception as e:
        pass

# --- 3. THE 2026 OFFICIAL SCORING ENGINE ---

def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
    # A. Main Episode Results
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
            
    # B. Technical Challenge (Dynamic Scaling)
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

    # C. Consolations (+2 Pts for "In Line" and "In Trouble")
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

# --- 4. CORE BAKERS & OFFICIAL LEAGUE ROSTER ---

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

# Official 15-Member Fantasy League Roster (14 Human Players + AI Brian)
LEAGUE_ROSTER = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", 
    "Stacy C.", "Taliah", "Tressa", "AI Brian"
]

# Initialize Session State
if "league_members" not in st.session_state:
    st.session_state.league_members = {}
    for player in LEAGUE_ROSTER:
        st.session_state.league_members[player] = {
            "avatar": "🤖" if player == "AI Brian" else None,
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

# AI Brian Auto Pick Generators
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
        eliminated = random.sample(elim_pool, min(2 if is_double_elim else 1, len(elim_pool)))
        if not is_double_elim and isinstance(eliminated, list):
            eliminated = eliminated[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2 if is_double_elim else 1, len(elim_pool)))
        if not is_double_elim and isinstance(eliminated, list):
            eliminated = eliminated[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2 if is_double_elim else 1, len(elim_pool)))
        if not is_double_elim and isinstance(eliminated, list):
            eliminated = eliminated[0]
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bottom, min(3, len(rem_bottom))) if len(rem_bottom) >= 3 else random.sample(active_bakers, min(3, len(active_bakers)))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker])
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_top_3": tech_top_3, "tech_bottom_3": tech_bottom_3, "in_line_sb": in_line_sb, "in_trouble": in_trouble}

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. HEADER LAYOUT WITH NORMAN BEAVER ---

col_h1, col_h2 = st.columns([1, 6])
with col_h1:
    if os.path.exists("normanbeaver.jpg"):
        st.image("normanbeaver.jpg", width=110)
    elif os.path.exists("assets/normanbeaver.jpg"):
        st.image("assets/normanbeaver.jpg", width=110)
    else:
        st.markdown("<h1 style='font-size: 70px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)

with col_h2:
    st.markdown("<div class='header-title'>🧁 Great British Baking Show Fantasy League 2026</div>", unsafe_allow_html=True)

# --- 6. SIDEBAR CONTROLS & AVATAR MANAGEMENT ---

with st.sidebar:
    st.header("📸 Upload Avatar Photo")
    st.write("Select your player name below to upload or manage your profile picture!")
    
    human_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sb_player = st.selectbox("Select Player Profile:", ["-- Select Your Name --"] + human_players)
    
    if sb_player != "-- Select Your Name --":
        os.makedirs("assets/avatars", exist_ok=True)
        avatar_path = f"assets/avatars/{sb_player}.png"
        
        uploaded_file = st.file_uploader(f"Choose Photo for {sb_player}", type=["png", "jpg", "jpeg"], key=f"uploader_{sb_player}")
        if uploaded_file is not None:
            try:
                img = Image.open(uploaded_file).convert("RGB").resize((300, 300))
                img.save(avatar_path, format="PNG")
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                data_url = f"data:image/png;base64,{b64_str}"
                
                st.session_state.league_members[sb_player]["avatar"] = avatar_path
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Avatar saved permanently for {sb_player}!")
            except Exception as e:
                st.error(f"Error saving image: {e}")
        
        cur_av = st.session_state.league_members[sb_player].get("avatar")
        if not cur_av or (isinstance(cur_av, str) and not os.path.exists(cur_av) and not cur_av.startswith("data:image")):
            if os.path.exists(avatar_path):
                cur_av = avatar_path
                st.session_state.league_members[sb_player]["avatar"] = avatar_path
        
        if cur_av:
            render_player_avatar(cur_av, width=140, caption=f"{sb_player}'s Avatar")
            
    st.markdown("---")
    st.header("⚙️ Game Controls")
    selected_week = st.slider("Select App Active Week", min_value=1, max_value=10, value=st.session_state.current_week)
    st.session_state.current_week = selected_week

    st.markdown("---")
    st.header("📜 Competition Rules Overview")
    st.markdown("""
    - **Scouting Phase:** Week 1 allows evaluating bakers before locking projections.
    - **Lock Projections:** Season projections lock in Week 2.
    - **Weekly Ballots:** Due prior to the broadcast each week.
    - **Star Baker:** +5 pts.
    - **Eliminated Baker:** +5 pts.
    - **Technical Placements:** Top 3 / Bottom 3 scoring in Weeks 2-7; Full Rankings in Weeks 8-10.
    - **In Line / In Trouble:** +2 pts each.
    - **Chaos Counts:** Hollywood Handshakes, Crying, and Sexual Innuendos.
    """)

# --- 7. MAIN TABS INTERFACE ---

tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "🏆 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📊 Contestant Analytics", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    lb_data = []
    for name, data in st.session_state.league_members.items():
        tot_pts = data.get("total_score", 0)
        av_val = data.get("avatar")
        lb_data.append({
            "member": name,
            "points": tot_pts,
            "avatar": av_val,
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
            av_val = row["avatar"]
            
            if isinstance(av_val, str) and av_val.startswith("data:image"):
                av_html = f'<img src="{av_val}" style="width:42px; height:42px; border-radius:50%; object-fit:cover;">'
            elif isinstance(av_val, str) and os.path.exists(av_val):
                try:
                    with open(av_val, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    ext = "png" if av_val.endswith(".png") else "jpeg"
                    av_html = f'<img src="data:image/{ext};base64,{b64}" style="width:42px; height:42px; border-radius:50%; object-fit:cover;">'
                except Exception:
                    av_html = "🍪"
            elif av_val == "🤖" or m_name == "AI Brian":
                b_path = load_ai_brian_avatar()
                if b_path and os.path.exists(b_path):
                    try:
                        with open(b_path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                        av_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:42px; height:42px; border-radius:50%; object-fit:cover;">'
                    except Exception:
                        av_html = "🤖"
                else:
                    av_html = "🤖"
            else:
                av_html = "🍪"
                
            rank_badge = f"#{rank}"
            if rank == 1: rank_badge = "🥇 #1"
            elif rank == 2: rank_badge = "🥈 #2"
            elif rank == 3: rank_badge = "🥉 #3"
            
            html_rows.append(f"""
            <tr>
                <td class="lb-rank">{rank_badge}</td>
                <td style="width: 50px; text-align: center;">{av_html}</td>
                <td class="lb-name">{m_name}</td>
                <td class="lb-pts">{m_pts} pts</td>
            </tr>
            """)
            
        table_html = f"""
        <table class="lb-table">
            <thead>
                <tr>
                    <th style="width: 80px;">Rank</th>
                    <th style="width: 60px; text-align: center;">Avatar</th>
                    <th>League Member</th>
                    <th style="text-align: right; width: 100px;">Total Points</th>
                </tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    # Detailed Player Scorecards
    st.subheader("📋 Player Scorecards & Locked Projections")
    for p_name, p_data in st.session_state.league_members.items():
        with st.expander(f"👤 {p_name}'s Profile & Ballots (Score: {p_data.get('total_score', 0)} pts)", expanded=False):
            col_sc1, col_sc2 = st.columns([1, 3])
            with col_sc1:
                render_player_avatar(p_data.get("avatar"), width=120, caption=f"{p_name}'s Profile")
            with col_sc2:
                st.markdown("**Locked Season Projections:**")
                sp = p_data.get("season_picks", {})
                if sp:
                    st.write(f"- **Picked Winner:** {sp.get('winner', 'None')}")
                    st.write(f"- **Semifinalists:** {', '.join(sp.get('semifinalists', [])) if sp.get('semifinalists') else 'None'}")
                    st.write(f"- **Handshakes Pick:** {sp.get('handshakes', 'N/A')} | **Crying Pick:** {sp.get('crying', 'N/A')} | **Innuendos Pick:** {sp.get('innuendos', 'N/A')}")
                else:
                    st.info("No season projections locked yet.")
            
            st.markdown("**Weekly Predictions Log:**")
            st.json(p_data.get("weekly_picks", {}))

    # Broadcast Chaos Metrics
    st.markdown("---")
    st.header("📺 Broadcast Chaos Metrics & Timestamps")
    
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    audit_rows = []
    
    for w_num in sorted(st.session_state.weekly_results.keys()):
        w_act = st.session_state.weekly_results[w_num]
        hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
        hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
        cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
        inn_cnt = w_act.get("innuendo_count", 0)

        tot_hs += len(w_act.get("handshake_bakers", []))
        if w_act.get("crying_timestamps"):
            tot_cry += len([s for s in w_act.get("crying_timestamps").split(",") if s.strip()])
        tot_inn += inn_cnt

        audit_rows.append({
            "Week": f"Week {w_num}",
            "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
            "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
            "Handshake Bakers": hs_bakers,
            "Handshake Timestamps": hs_stamps,
            "Crying Timestamps": cry_stamps,
            "Innuendos": inn_cnt
        })

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("🤝 Total Handshakes", tot_hs)
    col_m2.metric("😢 Total Crying Incidents", tot_cry)
    col_m3.metric("💬 Total Innuendos", tot_inn)
    
    if audit_rows:
        with st.expander("🔍 View Detailed Episode Audit Log", expanded=False):
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
    
    if st.session_state.current_week == 1:
        st.info("👀 **Week 1 Scouting Phase is Active!** Watch Episode 1 to evaluate the bakers before locking your season projections in Week 2.")
    else:
        st.warning("⏰ **Weekly Voting Window:** Ballots lock prior to the broadcast on **Tuesdays right before the episode airs in the UK**.")
        
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
        
        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
        
        # Season Long Projections Form (Week 2 Lock)
        if st.session_state.current_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts]", active_bakers, key="user_win_pick")
                remaining_for_semis = [b for b in active_bakers if b != user_winner]
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", remaining_for_semis, max_selections=3)
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [20 pts]", min_value=0, value=5)
                user_crying = st.number_input("Predict Seasonal Crying [20 pts]", min_value=0, value=10)
                user_innuendos = st.number_input("Predict Seasonal Innuendos [20 pts]", min_value=0, value=40)
                
                if st.button("Lock Season-Long Predictions"):
                    if len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members["Jasmine"]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        st.success("Season long predictions saved successfully!")

        # Weekly Ballot Form
        st.markdown("### Weekly Ballot")
        with st.form("weekly_predictions_form"):
            weekly_picks = {}
            
            if st.session_state.current_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", active_bakers)
                tech_1st = st.selectbox("Technical 1st Place", active_bakers, index=0)
                tech_2nd = st.selectbox("Technical 2nd Place", [b for b in active_bakers if b != tech_1st], index=0)
                tech_3rd = st.selectbox("Technical 3rd Place", [b for b in active_bakers if b not in [tech_1st, tech_2nd]], index=0)
                weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
                with col2:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers)
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b != weekly_picks.get("eliminated")])
                
                st.markdown("---")
                tech_top_3 = st.multiselect("Top 3 Technical (Order: 1st, 2nd, 3rd)", active_bakers, max_selections=3)
                tech_bottom_3 = st.multiselect("Bottom 3 Technical (Order: 3rd-to-last, 2nd-to-last, Last)", [b for b in active_bakers if b not in tech_top_3], max_selections=3)
                weekly_picks["tech_top_3"] = tech_top_3
                weekly_picks["tech_bottom_3"] = tech_bottom_3
                
            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                st.session_state.league_members["Jasmine"]["weekly_picks"][st.session_state.current_week] = weekly_picks
                ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers)
                st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                st.success(f"Predictions submitted for Week {st.session_state.current_week}!")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📊 Series 17 Contestant Analytics & Cheat Sheet")
    st.write("Browse official bios, photographs, and profiles for the Class of 2026 bakers.")
    
    cols = st.columns(4)
    for idx, baker in enumerate(ALL_BAKERS):
        info = BAKER_INFO.get(baker, {"url": "#"})
        with cols[idx % 4]:
            st.markdown(f"### {baker}")
            img = load_baker_image(baker)
            if img is not None:
                st.image(img, use_container_width=True)
            else:
                st.info(f"📸 Photograph of {baker}")
                st.markdown(f"[🔗 View {baker}'s Profile Page]({info['url']})")
            st.markdown("<br>", unsafe_allow_html=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Input actual broadcast results to score ballots and update the leaderboard.")
    
    if st.session_state.current_week > 1:
        eliminated_bakers_by_week = {
            2: ["Yannis"], 3: ["Yannis", "Nikki"], 4: ["Yannis", "Nikki", "Connie"],
            5: ["Yannis", "Nikki", "Connie", "Gary"], 6: ["Yannis", "Nikki", "Connie", "Gary", "Moyin"],
            7: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara"],
            8: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon"],
            9: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly"],
            10: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly", "Danni"]
        }
        current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        with st.form("admin_results_form"):
            actuals = {}
            actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers)
            actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals["star_baker"]])
            actuals["in_line_sb"] = st.multiselect("Actual 'In Line for Star Baker' Nominees", [b for b in active_bakers if b != actuals["star_baker"]])
            actuals["in_trouble"] = st.multiselect("Actual 'In Trouble of Elimination' Nominees", [b for b in active_bakers if b != actuals["eliminated"]])
            
            st.markdown("---")
            act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0)
            act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0)
            act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0)
            actuals["tech_top_3"] = [act_t1, act_t2, act_t3]
            
            sub_admin = st.form_submit_button("Publish Week Results & Update Standings")
            if sub_admin:
                st.session_state.weekly_results[st.session_state.current_week] = actuals
                
                for m_name, m_data in st.session_state.league_members.items():
                    m_data["total_score"] = 0
                    m_data["weekly_breakdown"] = {}
                    for w in st.session_state.weekly_results:
                        w_pred = m_data.get("weekly_picks", {}).get(w, {})
                        w_act = st.session_state.weekly_results.get(w, {})
                        w_score = calculate_weekly_score(w_pred, w_act, week=w)
                        m_data["weekly_breakdown"][w] = w_score
                        m_data["total_score"] += w_score
                
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success("Results published and standings updated!")
