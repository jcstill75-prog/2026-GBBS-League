import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import json
import base64
import os

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
    .leaderboard-table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "league_data.json"

def save_league_data(members, weekly_results, season_results):
    """Saves league data safely to JSON."""
    try:
        sanitized_members = {}
        for k, v in members.items():
            member_copy = dict(v)
            av = member_copy.get("avatar")
            if isinstance(av, Image.Image):
                buf = io.BytesIO()
                av.save(buf, format="PNG")
                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                member_copy["avatar"] = f"data:image/png;base64,{b64_str}"
            elif isinstance(av, str) and (os.path.exists(av) or av.startswith("data:image") or av == "🤖"):
                member_copy["avatar"] = av
            else:
                member_copy["avatar"] = None
            sanitized_members[k] = member_copy
            
        payload = {
            "league_members": sanitized_members,
            "weekly_results": weekly_results,
            "season_results": season_results
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def load_league_data():
    """Loads saved league session state from league_data.json if present."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                payload = json.load(f)
                members = payload.get("league_members", {})
                raw_weekly = payload.get("weekly_results", {})
                season = payload.get("season_results", {})
                
                weekly = {}
                if isinstance(raw_weekly, dict):
                    for k, v in raw_weekly.items():
                        try:
                            weekly[int(k)] = v
                        except (ValueError, TypeError):
                            weekly[k] = v
                            
                return members, weekly, season
        except Exception:
            pass
    return None, None, None

def load_ai_brian_avatar():
    for brian_path in ["ai_brian.jpg", "AI Brian.jpg", "assets/ai_brian.jpg", "assets/AI_Brian.jpg", "assets/ai_brian.png", "assets/AI_Brian.png"]:
        if os.path.exists(brian_path):
            return brian_path
    return None

def render_player_avatar(avatar_val, width=50, caption=None):
    if not avatar_val:
        st.markdown(f"<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)
        return

    if isinstance(avatar_val, str) and os.path.exists(avatar_val):
        try:
            img = Image.open(avatar_val)
            st.image(img, width=width, caption=caption)
            return
        except Exception:
            pass

    if isinstance(avatar_val, str) and avatar_val.startswith("data:image"):
        try:
            header, b64_data = avatar_val.split(",", 1)
            img_data = base64.b64decode(b64_data)
            img = Image.open(io.BytesIO(img_data))
            st.image(img, width=width, caption=caption)
            return
        except Exception:
            pass

    if isinstance(avatar_val, Image.Image):
        st.image(avatar_val, width=width, caption=caption)
        return

    if avatar_val == "🤖":
        b_img = load_ai_brian_avatar()
        if b_img:
            if isinstance(b_img, str) and os.path.exists(b_img):
                try:
                    st.image(Image.open(b_img), width=width, caption=caption)
                    return
                except Exception:
                    pass
            elif isinstance(b_img, Image.Image):
                st.image(b_img, width=width, caption=caption)
                return
        st.markdown(f"<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
        return

    st.markdown(f"<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
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
                    if p in act_elim: score += 5
            elif isinstance(pred_elim, str):
                if pred_elim in act_elim: score += 5
        elif act_elim == "None":
            pass
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: score += 5
            elif pred_elim == act_elim: score += 5
            
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
                    if baker in act_top3 and baker != act_top3[idx]: score += 1
                        
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
                    if baker in act_bottom3 and baker != act_bottom3[idx]: score += 1

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
        if pred_handshakes == act_handshakes: score += 20
        elif abs(pred_handshakes - act_handshakes) <= 1: score += 10
            
    pred_crying = predictions.get("crying")
    act_crying = actuals.get("crying")
    if pred_crying is not None and act_crying is not None:
        if pred_crying == act_crying: score += 20
        elif abs(pred_crying - act_crying) <= 5: score += 10
            
    pred_innuendos = predictions.get("innuendos")
    act_innuendos = actuals.get("innuendos")
    if pred_innuendos is not None and act_innuendos is not None:
        if pred_innuendos == act_innuendos: score += 20
        elif abs(pred_innuendos - act_innuendos) <= 5: score += 10
            
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
                except Exception: pass
    except Exception: pass
    return None

# --- 3. SHOW BAKERS & FANTASY LEAGUE ROSTER ---
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

# 14 HUMAN PLAYERS + AI BRIAN (15 TOTAL)
DEFAULT_HUMAN_PLAYERS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle",
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.",
    "Taliah", "Tressa"
]

# Initialize Session State
saved_members, saved_weekly, saved_season = load_league_data()

if "league_members" not in st.session_state:
    if saved_members is not None:
        st.session_state.league_members = saved_members
    else:
        clean_m = {
            "AI Brian": {
                "avatar": "🤖",
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {}
            }
        }
        for p in DEFAULT_HUMAN_PLAYERS:
            clean_m[p] = {
                "avatar": None,
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {}
            }
        b_av = load_ai_brian_avatar()
        if b_av: clean_m["AI Brian"]["avatar"] = b_av
        st.session_state.league_members = clean_m

# Ensure all 14 human players + AI Brian exist
for p in DEFAULT_HUMAN_PLAYERS:
    if p not in st.session_state.league_members:
        st.session_state.league_members[p] = {
            "avatar": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }
    else:
        # Disk auto-recovery for missing avatars
        cur_p_av = st.session_state.league_members[p].get("avatar")
        if not cur_p_av:
            for check_path in [f"assets/avatars/{p}.png", f"assets/avatars/{p}.jpg", f"assets/{p}.png", f"assets/{p}.jpg"]:
                if os.path.exists(check_path):
                    st.session_state.league_members[p]["avatar"] = check_path
                    break

if "AI Brian" not in st.session_state.league_members:
    st.session_state.league_members["AI Brian"] = {
        "avatar": "🤖",
        "weekly_picks": {},
        "season_picks": {},
        "total_score": 0,
        "weekly_breakdown": {}
    }

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_weekly if saved_weekly is not None else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_season if saved_season is not None else {}

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
        return {
            "star_baker": star_baker, "eliminated": eliminated,
            "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble
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
        tech_bottom_3 = random.sample(remaining_for_bottom, min(3, len(remaining_for_bottom)))
            
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        
        return {
            "star_baker": star_baker, "eliminated": eliminated,
            "tech_top_3": tech_top_3, "tech_bottom_3": tech_bottom_3,
            "in_line_sb": in_line_sb, "in_trouble": in_trouble
        }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. APP INTERFACE LAYOUT & HEADER ---
col_head1, col_head2 = st.columns([1, 6])
with col_head1:
    norman_path = None
    for np in ["normanbeaver.jpg", "Normanbeaver.jpg", "assets/normanbeaver.jpg", "assets/Normanbeaver.jpg"]:
        if os.path.exists(np):
            norman_path = np
            break
    if norman_path:
        st.image(norman_path, width=110)
    else:
        st.markdown("<h1 style='font-size: 70px; margin: 0;'>🦫</h1>", unsafe_allow_html=True)
with col_head2:
    st.title("Great British Baking Show Fantasy League 2026")

# --- SIDEBAR: USER ACCOUNT, AVATAR UPLOAD & COMPETITION RULES ---
with st.sidebar:
    st.header("📸 Upload Avatar Photo")
    st.write("Select your player name below to upload or manage your profile picture!")
    
    roster_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sb_player = st.selectbox("Select Player Profile:", ["-- Select Your Name --"] + roster_players)
    
    if sb_player and sb_player != "-- Select Your Name --":
        os.makedirs("assets/avatars", exist_ok=True)
        avatar_path = f"assets/avatars/{sb_player}.png"
        
        uploaded_file = st.file_uploader(f"Choose Photo for {sb_player}", type=["png", "jpg", "jpeg"], key=f"uploader_{sb_player}")
        if uploaded_file is not None:
            try:
                img = Image.open(uploaded_file)
                img = img.convert("RGB")
                img = img.resize((300, 300))
                img.save(avatar_path, format="PNG")
                
                st.session_state.league_members[sb_player]["avatar"] = avatar_path
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Avatar updated and saved permanently for {sb_player}!")
            except Exception as e:
                st.error(f"Error saving image: {e}")
        
        cur_av = st.session_state.league_members[sb_player].get("avatar")
        if not cur_av or (isinstance(cur_av, str) and not os.path.exists(cur_av) and not cur_av.startswith("data:image")):
            if os.path.exists(avatar_path):
                cur_av = avatar_path
                st.session_state.league_members[sb_player]["avatar"] = avatar_path
        
        if cur_av:
            render_player_avatar(cur_av, width=150, caption=f"{sb_player}'s Avatar")
            
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

# --- MAIN TABS ---
tab_lead, tab_submit, tab_admin, tab_bakers = st.tabs([
    "🏆 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "👑 Admin Panel",
    "📊 Contestant Analytics"
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
                    <th style="width: 90px;">Rank</th>
                    <th style="width: 60px; text-align: center;">Avatar</th>
                    <th>League Member</th>
                    <th style="text-align: right; width: 120px;">Total Points</th>
                </tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Player Projections & Scorecard Breakdown")
    for rank, row in df_lb.iterrows():
        p_name = row["member"]
        p_data = row["data"]
        p_pts = row["points"]
        
        with st.expander(f"👤 {p_name} — {p_pts} pts Total", expanded=False):
            col_sc1, col_sc2 = st.columns([1, 3])
            with col_sc1:
                render_player_avatar(p_data.get("avatar"), width=120, caption=f"{p_name}'s Profile")
            with col_sc2:
                st.write("**Locked Season Projections:**")
                sp = p_data.get("season_picks", {})
                if sp:
                    st.write(f"- **Predicted Winner:** {sp.get('winner', 'None')}")
                    st.write(f"- **Predicted Semifinalists:** {', '.join(sp.get('semifinalists', [])) if sp.get('semifinalists') else 'None'}")
                    st.write(f"- **Predicted Counts:** Handshakes: {sp.get('handshakes', 0)} | Crying: {sp.get('crying', 0)} | Innuendos: {sp.get('innuendos', 0)}")
                else:
                    st.info("No season predictions locked yet.")
                
                st.write("**Weekly Predictions Log:**")
                wp = p_data.get("weekly_picks", {})
                if wp:
                    st.json(wp)
                else:
                    st.info("No weekly predictions submitted yet.")

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps")
    
    audit_rows = []
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0

    if st.session_state.weekly_results:
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
    col_m2.metric("😢 Crying Incidents", tot_cry)
    col_m3.metric("💬 Sexual Innuendos", tot_inn)

    if audit_rows:
        with st.expander("🔍 Detailed Episode-by-Episode Broadcast Log", expanded=False):
            df_audit = pd.DataFrame(audit_rows)
            st.dataframe(df_audit, use_container_width=True)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("Browse photos and bios of the Series 17 bakers competing in the tent!")
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
                    st.markdown(f"[🔗 View {baker}'s Photo Page]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    
    if st.session_state.current_week == 1:
        st.header("🔍 Week 1: Scouting Phase")
        st.info("Welcome to the Week 1 Scouting Phase! Use Episode 1 to evaluate the bakers before locking in your official season projections and weekly ballots in Week 2.")
    else:
        st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
        st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the broadcast on **Tuesdays right before the episode airs in the UK**.")
        
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
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)
        
        if st.session_state.current_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts]", active_bakers, key="user_win_pick")
                remaining_for_semis = [b for b in active_bakers if b != user_winner]
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", remaining_for_semis, max_selections=3)
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts]", min_value=0, value=5)
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts]", min_value=0, value=10)
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts]", min_value=0, value=40)
                
                if st.button("Lock Season-Long Predictions"):
                    if len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        for p in st.session_state.league_members:
                            st.session_state.league_members[p]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_handshakes,
                                "crying": user_crying,
                                "innuendos": user_innuendos
                            }
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success("Season-long predictions locked successfully!")

        st.markdown("### Weekly Ballot")
        with st.form("weekly_predictions_form"):
            weekly_picks = {}
            
            if st.session_state.current_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", active_bakers)
                st.write("Predict Technical Challenge Final Rank:")
                tech_1st = st.selectbox("Technical 1st Place", active_bakers, index=0)
                tech_2nd = st.selectbox("Technical 2nd Place", [b for b in active_bakers if b != tech_1st], index=0)
                tech_3rd = st.selectbox("Technical 3rd Place", [b for b in active_bakers if b not in [tech_1st, tech_2nd]], index=0)
                weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]
                
            elif st.session_state.current_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                if is_double_elim:
                    elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", [b for b in active_bakers if b != weekly_picks.get("star_baker")], key="pred_elim_1_w9")
                    elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", [b for b in active_bakers if b not in [weekly_picks.get("star_baker"), elim_1]], key="pred_elim_2_w9")
                    weekly_picks["eliminated"] = [elim_1, elim_2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
                
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", active_bakers, index=0)
                t2 = st.selectbox("Technical 2nd Place", [b for b in active_bakers if b != t1], index=0)
                t3 = st.selectbox("Technical 3rd Place", [b for b in active_bakers if b not in [t1, t2]], index=0)
                t4 = st.selectbox("Technical 4th Place", [b for b in active_bakers if b not in [t1, t2, t3]], index=0)
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
                with col2:
                    if is_double_elim:
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", active_bakers, key="pred_elim_1_w8")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", [b for b in active_bakers if b != elim_1], key="pred_elim_2_w8")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b not in weekly_picks["eliminated"]])
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b != weekly_picks.get("eliminated")])
                
                st.write("Predict Technical Challenge Final Rank:")
                t1 = st.selectbox("Technical 1st Place", active_bakers, index=0, key="t1_w8")
                t2 = st.selectbox("Technical 2nd Place", [b for b in active_bakers if b != t1], index=0, key="t2_w8")
                t3 = st.selectbox("Technical 3rd Place", [b for b in active_bakers if b not in [t1, t2]], index=0, key="t3_w8")
                t4 = st.selectbox("Technical 4th Place", [b for b in active_bakers if b not in [t1, t2, t3]], index=0, key="t4_w8")
                t5 = st.selectbox("Technical 5th Place", [b for b in active_bakers if b not in [t1, t2, t3, t4]], index=0, key="t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                
            else:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
                with col2:
                    if is_double_elim:
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", active_bakers, key="pred_elim_1_std")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", [b for b in active_bakers if b != elim_1], key="pred_elim_2_std")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b not in weekly_picks["eliminated"]])
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b != weekly_picks.get("eliminated")])
                    
                st.markdown("---")
                tech_top_3 = st.multiselect("Top 3 Technical (Order: 1st, 2nd, 3rd - Max 3)", active_bakers, max_selections=3)
                tech_bottom_3 = st.multiselect("Bottom 3 Technical (Order: 3rd-to-last, 2nd-to-last, Last - Max 3)", [b for b in active_bakers if b not in tech_top_3], max_selections=3)
                
                weekly_picks["tech_top_3"] = tech_top_3
                weekly_picks["tech_bottom_3"] = tech_bottom_3
                
            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                for p in st.session_state.league_members:
                    if p != "AI Brian":
                        st.session_state.league_members[p]["weekly_picks"][st.session_state.current_week] = weekly_picks
                
                ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Predictions submitted for Week {st.session_state.current_week}! AI Brian has also submitted his randomized picks.")

# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Input actual broadcast results to score predictions and update the live leaderboard!")
    
    eliminated_bakers_by_week = {
        2: ["Yannis"], 3: ["Yannis", "Nikki"], 4: ["Yannis", "Nikki", "Connie"],
        5: ["Yannis", "Nikki", "Connie", "Gary"], 6: ["Yannis", "Nikki", "Connie", "Gary", "Moyin"],
        7: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara"], 8: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon"],
        9: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly"], 10: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly", "Danni"]
    }
    
    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    
    with st.form("admin_results_form"):
        actuals = {}
        st.subheader(f"Log Actual Results for Week {st.session_state.current_week}")
        
        if st.session_state.current_week == 10:
            actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers)
            act_t1 = st.selectbox("Actual Technical 1st Place", active_bakers, index=0)
            act_t2 = st.selectbox("Actual Technical 2nd Place", [b for b in active_bakers if b != act_t1], index=0)
            act_t3 = st.selectbox("Actual Technical 3rd Place", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0)
            actuals["tech_rank"] = [act_t1, act_t2, act_t3]
        else:
            actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers)
            is_grace_week = st.checkbox("📢 Grace Week (No Elimination)?", value=False)
            
            if is_grace_week:
                actuals["eliminated"] = "None"
            else:
                is_admin_double_elim = st.checkbox("📢 Double-Elimination Week?", value=False)
                if not is_admin_double_elim:
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")])
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], key="admin_act_elim_1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), act_elim_1]], key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]
            
            st.markdown("---")
            if st.session_state.current_week >= 8:
                act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0)
                act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0)
                act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0)
                if len(active_bakers) >= 4:
                    act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0)
                    actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]
                if len(active_bakers) >= 5:
                    act_t5 = st.selectbox("Actual Technical 5th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], index=0)
                    actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
            else:
                act_top_3 = st.multiselect("Actual Top 3 Technical (Order: 1st, 2nd, 3rd - Max 3)", active_bakers, max_selections=3)
                act_bottom_3 = st.multiselect("Actual Bottom 3 Technical (Order: 3rd-to-last, 2nd-to-last, Last - Max 3)", [b for b in active_bakers if b not in act_top_3], max_selections=3)
                actuals["tech_top_3"] = act_top_3
                actuals["tech_bottom_3"] = act_bottom_3
                
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line for Star Baker' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
                actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in (actuals["eliminated"] if isinstance(actuals.get("eliminated"), list) else [actuals.get("eliminated")])])

        st.markdown("---")
        st.subheader("📺 Chaos Counts & Broadcast Evidence")
        hs_bakers = st.multiselect("Hollywood Handshake Recipients", active_bakers)
        hs_stamps = st.text_input("Hollywood Handshake Timestamps (e.g., '14:20 (Clara), 38:45 (Gary)')")
        cry_stamps = st.text_input("Crying Scene Timestamps (e.g., '12:10 (Nikki), 42:00 (Molly)')")
        inn_count = st.number_input("Innuendo Count", min_value=0, value=0)

        actuals["handshake_bakers"] = hs_bakers
        actuals["handshake_timestamps"] = hs_stamps
        actuals["crying_timestamps"] = cry_stamps
        actuals["innuendo_count"] = inn_count

        sub_admin = st.form_submit_button("Publish Broadcast Results & Score League")
        if sub_admin:
            st.session_state.weekly_results[st.session_state.current_week] = actuals
            
            # Recalculate Scores across all weeks
            for member_name in st.session_state.league_members:
                st.session_state.league_members[member_name]["total_score"] = 0
                st.session_state.league_members[member_name]["weekly_breakdown"] = {}

            for w, w_act in st.session_state.weekly_results.items():
                weekly_scores = {}
                for m_name, m_data in st.session_state.league_members.items():
                    m_picks = m_data["weekly_picks"].get(w, {})
                    w_pts = calculate_weekly_score(m_picks, w_act, week=w)
                    st.session_state.league_members[m_name]["weekly_breakdown"][w] = w_pts
                    weekly_scores[m_name] = w_pts

                if weekly_scores:
                    max_pts = max(weekly_scores.values())
                    if max_pts > 0:
                        for m_name, pts in weekly_scores.items():
                            if pts == max_pts:
                                st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5

            for m_name, m_data in st.session_state.league_members.items():
                m_data["total_score"] = sum(m_data["weekly_breakdown"].values())
                
                if st.session_state.season_results:
                    s_pts = calculate_season_score(m_data["season_picks"], st.session_state.season_results)
                    m_data["total_score"] += s_pts

            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
            st.success(f"Results for Week {st.session_state.current_week} published! All scores updated.")

# --- TAB 4: CONTESTANT ANALYTICS ---
with tab_bakers:
    st.header("📊 Contestant Analytics (Series 17)")
    st.write("Inspect bio details, photographs, and episode performance for the 12 bakers competing in the tent.")
    
    sel_baker = st.selectbox("Select Contestant to Inspect:", ALL_BAKERS)
    if sel_baker:
        col_ba1, col_ba2 = st.columns([1, 2])
        with col_ba1:
            b_img = load_baker_image(sel_baker)
            if b_img:
                st.image(b_img, caption=sel_baker, use_container_width=True)
            else:
                st.info(f"📸 Photograph of {sel_baker}")
                info = BAKER_INFO.get(sel_baker, {"url": "#"})
                st.markdown(f"[🔗 View {sel_baker}'s Official Photo Page]({info['url']})")
        with col_ba2:
            st.subheader(f"Contestant Profile: {sel_baker}")
            info = BAKER_INFO.get(sel_baker, {"url": "#"})
            st.markdown(f"**Show Profile Page:** [Official Bio Link]({info['url']})")
            
            # Show historical stats if weekly_results exist
            if st.session_state.weekly_results:
                st.write("**Broadcast Statistics:**")
                sb_count = sum(1 for w in st.session_state.weekly_results.values() if w.get("star_baker") == sel_baker or w.get("show_champion") == sel_baker)
                hs_count = sum(1 for w in st.session_state.weekly_results.values() if sel_baker in w.get("handshake_bakers", []))
                
                st.write(f"- ⭐ **Star Baker Titles:** {sb_count}")
                st.write(f"- 🤝 **Hollywood Handshakes:** {hs_count}")
