import streamlit as st
import pandas as pd
import random
import os
import json
import base64
import io
from PIL import Image

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

# --- 2. CORE BAKERS & DEFAULT ROSTER ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

DEFAULT_ROSTER = [
    "Ana", "Becca", "Clara", "Connie", "Danni", "Gabe", "Gary", 
    "Mo", "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
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

# --- 3. PERSISTENCE & DATA STORAGE HANDLERS ---
DATA_FILE = "league_data.json"

def save_league_data(league_members, weekly_results, season_results):
    """Saves league session state data to persistent league_data.json safely."""
    try:
        members_copy = {}
        for name, data in league_members.items():
            m_dict = dict(data)
            av = m_dict.get("avatar")
            if isinstance(av, Image.Image):
                buf = io.BytesIO()
                av.convert("RGB").save(buf, format="PNG")
                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                m_dict["avatar"] = f"data:image/png;base64,{b64_str}"
            elif av is not None and not isinstance(av, str):
                m_dict["avatar"] = str(av)
            members_copy[name] = m_dict
            
        payload = {
            "league_members": members_copy,
            "weekly_results": weekly_results,
            "season_results": season_results
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

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
    """Smart image loader for AI Brian robot avatar."""
    for p in ["assets/aibrian.jpg", "assets/aibrian.png", "aibrian.jpg", "aibrian.png"]:
        if os.path.exists(p):
            return p
    return None

def load_baker_image(baker_name):
    """Smart case-insensitive and multi-extension baker image loader."""
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

def render_player_avatar(avatar_val, width=50, caption=None):
    """Safely renders player avatars using Streamlit native components."""
    if not avatar_val:
        st.markdown(f"<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)
        return

    # Case 1: Disk File Path
    if isinstance(avatar_val, str) and os.path.exists(avatar_val):
        try:
            img = Image.open(avatar_val)
            st.image(img, width=width, caption=caption)
            return
        except Exception:
            pass

    # Case 2: Base64 Data URL
    if isinstance(avatar_val, str) and avatar_val.startswith("data:image"):
        try:
            header, b64_data = avatar_val.split(",", 1)
            img_data = base64.b64decode(b64_data)
            img = Image.open(io.BytesIO(img_data))
            st.image(img, width=width, caption=caption)
            return
        except Exception:
            pass

    # Case 3: PIL Image
    if isinstance(avatar_val, Image.Image):
        st.image(avatar_val, width=width, caption=caption)
        return

    # Case 4: Special robot icon for AI Brian
    if avatar_val == "🤖":
        b_img = load_ai_brian_avatar()
        if b_img:
            if isinstance(b_img, str) and os.path.exists(b_img):
                try:
                    st.image(Image.open(b_img), width=width, caption=caption)
                    return
                except Exception:
                    pass
        st.markdown(f"<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
        return

    st.markdown(f"<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)

# --- 4. SCORING ENGINE ---
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
            elif pred_elim == act_elim:
                score += 5
            
    # Technical Challenge Scoring
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            if pred_rank == act_rank:
                score += 25
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx in [0, 4] else 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            if pred_rank == act_rank:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx in [0, 3] else 2
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            if pred_rank == act_rank:
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
        eliminated = random.sample(elim_pool, min(2 if is_double_elim else 1, len(elim_pool))) if elim_pool else [active_bakers[0]]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated[0] if not is_double_elim else eliminated, "tech_rank": tech_rank}
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        eliminated = random.sample(elim_pool, min(2 if is_double_elim else 1, len(elim_pool))) if elim_pool else [active_bakers[0]]
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bottom, min(3, len(rem_bottom))) if rem_bottom else random.sample(active_bakers, min(3, len(active_bakers)))
        in_line = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble = random.choice([b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]) if active_bakers else active_bakers[0]
        
        return {
            "star_baker": star_baker,
            "eliminated": eliminated[0] if not is_double_elim else eliminated,
            "tech_top_3": tech_top_3,
            "tech_bottom_3": tech_bottom_3,
            "in_line_sb": in_line,
            "in_trouble": in_trouble
        }

# --- 5. INITIALIZE SESSION STATE ---
saved_members, saved_weekly, saved_season = load_league_data()

if "league_members" not in st.session_state:
    if saved_members is not None and len(saved_members) > 2:
        st.session_state.league_members = saved_members
    else:
        clean_m = {
            "AI Brian": {
                "avatar": "🤖",
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
        }
        for p in DEFAULT_ROSTER:
            clean_m[p] = {
                "avatar": None,
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
        b_av = load_ai_brian_avatar()
        if b_av: clean_m["AI Brian"]["avatar"] = b_av
        st.session_state.league_members = clean_m

# Ensure ALL members of DEFAULT_ROSTER exist in session state
for p in DEFAULT_ROSTER:
    if p not in st.session_state.league_members:
        st.session_state.league_members[p] = {
            "avatar": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None
        }
    # Auto-recover disk avatars
    cur_p_av = st.session_state.league_members[p].get("avatar")
    if not cur_p_av:
        for check_path in [f"assets/avatars/{p}.png", f"assets/avatars/{p}.jpg", f"assets/{p}.png", f"assets/{p}.jpg"]:
            if os.path.exists(check_path):
                st.session_state.league_members[p]["avatar"] = check_path
                break

# Remove legacy keys if present
for old_key in ["Steve", "Craig", "You"]:
    if old_key in st.session_state.league_members:
        del st.session_state.league_members[old_key]

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_weekly if saved_weekly is not None else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_season if saved_season is not None else {}

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

# Generate AI Brian's season picks if missing
if not st.session_state.league_members.get("AI Brian", {}).get("season_picks"):
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 6. HEADER WITH NORMAN BEAVER ---
norman_path = None
for p in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.png"]:
    if os.path.exists(p):
        norman_path = p
        break

if norman_path:
    try:
        with open(norman_path, "rb") as f:
            b64_beaver = base64.b64encode(f.read()).decode("utf-8")
        ext = "png" if norman_path.endswith(".png") else "jpeg"
        st.markdown(f"""
        <style>
            .header-container {{
                display: flex;
                align-items: center;
                gap: 18px;
                margin-top: 5px;
                margin-bottom: 22px;
            }}
            .header-title {{
                margin: 0;
                padding: 0;
                font-size: 2.2rem;
                font-weight: 800;
                line-height: 1.2;
                color: var(--text-color, #2C1810);
            }}
            [data-theme="dark"] .header-title,
            .stApp[data-theme="dark"] .header-title,
            @media (prefers-color-scheme: dark) {{
                .header-title {{
                    color: #FFFFFF !important;
                }}
            }}
        </style>
        <div class="header-container">
            <img src="data:image/{ext};base64,{b64_beaver}" style="height: 80px; width: auto; border-radius: 8px; object-fit: contain;">
            <h1 class="header-title">Great British Baking Show Fantasy League 2026</h1>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.title("Great British Baking Show Fantasy League 2026")
else:
    st.title("Great British Baking Show Fantasy League 2026")

# --- 7. SIDEBAR ---
with st.sidebar:
    st.header("📸 Upload Avatar Photo")
    st.write("Select your player name below to upload or manage your profile picture!")
    
    roster_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sb_player = st.selectbox("Select Player Profile:", ["-- Select Your Name --"] + roster_players)
    
    if sb_player != "-- Select Your Name --":
        p_pin = st.session_state.league_members[sb_player].get("pin")
        is_authed = st.session_state.authenticated_players.get(sb_player, False)
        
        if p_pin is not None and not is_authed:
            st.warning(f"🔒 Profile locked for **{sb_player}**.")
            st.info("Unlock your profile in the **📝 Submit Predictions** tab using your 4-digit PIN!")
        else:
            os.makedirs("assets/avatars", exist_ok=True)
            avatar_path = f"assets/avatars/{sb_player}.png"
            
            uploaded_file = st.file_uploader(f"Choose Photo for {sb_player}", type=["png", "jpg", "jpeg"], key=f"uploader_{sb_player}")
            if uploaded_file is not None:
                try:
                    img = Image.open(uploaded_file)
                    img = img.convert("RGB")
                    img = img.resize((300, 300))
                    img.save(avatar_path, format="PNG")
                    
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                    data_url = f"data:image/png;base64,{b64_str}"
                    
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
    - **Weekly Ballots:** Due prior to broadcast each week.
    - **Star Baker:** +5 pts.
    - **Eliminated Baker:** +5 pts.
    - **Technical Placements:** Top 3 / Bottom 3 scoring in Weeks 2-7; Full Rankings in Weeks 8-10.
    - **In Line / In Trouble:** +2 pts each.
    - **Chaos Counts:** Hollywood Handshakes, Crying, and Sexual Innuendos.
    """)

# --- 8. MAIN TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📊 Contestant Analytics", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    # Compile Leaderboard Data for ALL Members
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
        
        # Styled Leaderboard Table
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
                    <th style="width: 80px;">Rank</th>
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
    st.header("🎭 Broadcast Chaos Metrics Summary")
    
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    for w_num, w_act in st.session_state.weekly_results.items():
        tot_hs += len(w_act.get("handshake_bakers", []))
        if w_act.get("crying_timestamps"):
            tot_cry += len([s for s in w_act.get("crying_timestamps").split(",") if s.strip()])
        tot_inn += w_act.get("innuendo_count", 0)

    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Hollywood Handshakes", f"{tot_hs} 🤝")
    with m2: st.metric("Crying Incidents", f"{tot_cry} 😢")
    with m3: st.metric("Sexual Innuendos", f"{tot_inn} 💬")

    with st.expander("📊 Episode-by-Episode Chaos Breakdown", expanded=False):
        if not st.session_state.weekly_results:
            st.info("No weekly results published yet.")
        else:
            audit_rows = []
            for w_num in sorted(st.session_state.weekly_results.keys()):
                w_act = st.session_state.weekly_results[w_num]
                audit_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker": w_act.get("star_baker", "N/A"),
                    "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                    "Handshake Bakers": ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None",
                    "Crying Timestamps": w_act.get("crying_timestamps", "N/A") or "N/A",
                    "Innuendos": w_act.get("innuendo_count", 0)
                })
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)

    st.markdown("---")
    st.header("📜 Player Scorecards & Prediction Logs")
    for p_name in sorted(st.session_state.league_members.keys()):
        p_data = st.session_state.league_members[p_name]
        with st.expander(f"👤 {p_name} — Total Score: {p_data.get('total_score', 0)} pts"):
            col_av, col_details = st.columns([1, 3])
            with col_av:
                render_player_avatar(p_data.get("avatar"), width=120, caption=f"{p_name}'s Profile")
            with col_details:
                st.markdown("**Season-Long Predictions:**")
                st.json(p_data.get("season_picks", {}))
                st.markdown("**Weekly Predictions Log:**")
                st.write(p_data.get("weekly_picks", {}))

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", roster_players)
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
            
            if st.form_submit_button("Submit Dispute"):
                st.session_state.disputes.append({
                    "Player": disp_player,
                    "Week": disp_week,
                    "Category": disp_cat,
                    "Evidence": disp_evidence,
                    "Correction": disp_correction,
                    "Status": "Pending Review 🗳️"
                })
                st.success("Dispute submitted successfully!")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header(f"📅 Submit Predictions: Week {st.session_state.current_week}")
    
    if st.session_state.current_week == 1:
        st.info("🔎 **Week 1 Scouting Phase Active:** Evaluate the contestants during Week 1! Official prediction ballots open in Week 2.")
    else:
        # Determine active bakers
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
        
        # Player Authentication Check for Ballot
        sel_auth_player = st.selectbox("Select Your Profile to Submit Ballot:", ["-- Select Your Name --"] + roster_players)
        
        if sel_auth_player != "-- Select Your Name --":
            p_pin = st.session_state.league_members[sel_auth_player].get("pin")
            is_authed = st.session_state.authenticated_players.get(sel_auth_player, False)
            
            if p_pin is not None and not is_authed:
                entered_pin = st.text_input("Enter 4-Digit Security PIN:", type="password", key=f"pin_entry_{sel_auth_player}")
                if st.button("Unlock Profile"):
                    if entered_pin == p_pin:
                        st.session_state.authenticated_players[sel_auth_player] = True
                        st.success("Profile unlocked!")
                        st.rerun()
                    else:
                        st.error("Incorrect PIN.")
            else:
                # Season Predictions Form (Locks in Week 2)
                if st.session_state.current_week == 2:
                    with st.expander("🌟 Submit Season-Long Predictions (Locks Week 2 | 130 pts total)", expanded=True):
                        user_winner = st.selectbox("Predict Season Winner [40 pts]", active_bakers, key="win_pick")
                        user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", [b for b in active_bakers if b != user_winner], max_selections=3)
                        user_hs = st.number_input("Predict Seasonal Handshakes", min_value=0, value=5)
                        user_cry = st.number_input("Predict Seasonal Crying", min_value=0, value=10)
                        user_inn = st.number_input("Predict Seasonal Innuendos", min_value=0, value=40)
                        
                        if st.button("Save Season Predictions"):
                            if len(user_semis) != 3:
                                st.error("Please select exactly 3 other semifinalists.")
                            else:
                                st.session_state.league_members[sel_auth_player]["season_picks"] = {
                                    "winner": user_winner,
                                    "semifinalists": user_semis,
                                    "handshakes": user_hs,
                                    "crying": user_cry,
                                    "innuendos": user_inn
                                }
                                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                                st.success("Season predictions saved!")

                # Weekly Ballot Form
                st.markdown(f"### Weekly Prediction Ballot for {sel_auth_player}")
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=False)
                
                with st.form("weekly_ballot_form"):
                    weekly_picks = {}
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        sb_pick = st.selectbox("Predict Star Baker [5 pts]", active_bakers, key="sb_ballot")
                        in_line_pick = st.selectbox("Predict In Line for Star Baker [2 pts]", active_bakers, key="inline_ballot")
                    with col2:
                        if is_double_elim:
                            elim_1 = st.selectbox("Predict Eliminated #1 [5 pts]", active_bakers, key="elim1_ballot")
                            elim_2 = st.selectbox("Predict Eliminated #2 [5 pts]", active_bakers, key="elim2_ballot")
                            elim_pick = [elim_1, elim_2]
                        else:
                            elim_pick = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers, key="elim_ballot")
                        in_trouble_pick = st.selectbox("Predict In Trouble [2 pts]", active_bakers, key="trouble_ballot")

                    st.markdown("---")
                    st.write("Predict Technical Challenge Rankings:")
                    tech_top_3 = st.multiselect("Top 3 Technical (1st, 2nd, 3rd)", active_bakers, max_selections=3)
                    tech_bot_3 = st.multiselect("Bottom 3 Technical (9th, 10th, 11th)", [b for b in active_bakers if b not in tech_top_3], max_selections=3)
                    
                    submitted = st.form_submit_button("Submit Weekly Predictions")
                    if submitted:
                        main_picks = [sb_pick, in_line_pick, in_trouble_pick]
                        if isinstance(elim_pick, list): main_picks.extend(elim_pick)
                        else: main_picks.append(elim_pick)
                        
                        if len(main_picks) != len(set(main_picks)):
                            st.error("⚠️ Main Categories Error: Do not select duplicate bakers within Star Baker, Eliminated, In Line, and In Trouble.")
                        else:
                            weekly_picks = {
                                "star_baker": sb_pick,
                                "eliminated": elim_pick,
                                "in_line_sb": in_line_pick,
                                "in_trouble": in_trouble_pick,
                                "tech_top_3": tech_top_3,
                                "tech_bottom_3": tech_bot_3
                            }
                            st.session_state.league_members[sel_auth_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                            
                            ai_p = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_p
                            
                            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                            st.success(f"Predictions saved for {sel_auth_player}!")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📊 Individual Contestant Deep Dive")
    sel_baker = st.selectbox("Select Baker to Inspect:", ALL_BAKERS)
    
    col_img, col_metrics = st.columns([1, 2])
    with col_img:
        b_img = load_baker_image(sel_baker)
        if b_img:
            st.image(b_img, width=220, caption=f"{sel_baker} ('Class of 2026')")
        else:
            st.markdown(f"### 🧁 {sel_baker}")
            st.write("*(No portrait uploaded)*")
            
        b_url = BAKER_INFO.get(sel_baker, {}).get("url")
        if b_url:
            st.markdown(f"👉 [Read Official Bio on Bake Off Website]({b_url})")
            
    with col_metrics:
        st.markdown(f"### Contestant Overview: **{sel_baker}**")
        st.write("Track stats, wins, handshakes, and nominations across the season!")
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Star Baker Wins", "0 🌟")
        with m2: st.metric("In Trouble", "0 ⚠️")
        with m3: st.metric("Handshakes", "0 🤝")

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    admin_pwd = st.text_input("Enter Administrator Password:", type="password")
    if admin_pwd == "gbbs2026":
        st.session_state.admin_authenticated = True
        st.success("Admin authenticated!")
        
        st.markdown("---")
        st.subheader(f"Enter Actual Results for Week {st.session_state.current_week}")
        
        with st.form("admin_results_form"):
            act_sb = st.selectbox("Actual Star Baker:", ALL_BAKERS)
            act_elim = st.selectbox("Actual Eliminated Baker:", ALL_BAKERS)
            act_inline = st.multiselect("Actual In Line Nominees:", ALL_BAKERS)
            act_trouble = st.multiselect("Actual In Trouble Nominees:", ALL_BAKERS)
            act_hs_bakers = st.multiselect("Handshake Recipients:", ALL_BAKERS)
            act_cry_stamps = st.text_input("Crying Timestamps (comma separated):")
            act_inn_cnt = st.number_input("Sexual Innuendo Count:", min_value=0, value=0)
            
            if st.form_submit_button("Publish Results & Recalculate Standings"):
                st.session_state.weekly_results[st.session_state.current_week] = {
                    "star_baker": act_sb,
                    "eliminated": act_elim,
                    "in_line_sb": act_inline,
                    "in_trouble": act_trouble,
                    "handshake_bakers": act_hs_bakers,
                    "crying_timestamps": act_cry_stamps,
                    "innuendo_count": act_inn_cnt
                }
                
                for name, m_data in st.session_state.league_members.items():
                    tot = 0
                    for w_num, w_picks in m_data.get("weekly_picks", {}).items():
                        w_act = st.session_state.weekly_results.get(w_num)
                        if w_act:
                            tot += calculate_weekly_score(w_picks, w_act, week=w_num)
                    m_data["total_score"] = tot
                    
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Results for Week {st.session_state.current_week} published and scores updated!")
