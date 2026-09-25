import streamlit as st
import json
import pandas as pd
import random
from PIL import Image, ImageDraw
import io
import base64
import os

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for a clean, cozy baking theme with dark/light mode compatibility
st.markdown("""
<style>
    /* Responsive Dark Mode & Light Mode Typography */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color, inherit) !important;
    }
    p, span, label, div {
        color: var(--text-color, inherit);
    }
    
    .stButton>button {
        background-color: #D36B5F;
        color: white !important;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #B54E43;
        color: white !important;
    }
    
    .status-box {
        background-color: rgba(255, 243, 224, 0.15);
        color: var(--text-color, inherit);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FFB74D;
        margin-bottom: 15px;
    }
    .leaderboard-table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
        color: var(--text-color, inherit);
    }
    
    /* Remove outlines & glows on Streamlit header anchors */
    a.aria-label, a[data-testid="stHeaderAnchor"], .stHeaderAnchor {
        outline: none !important;
        box-shadow: none !important;
        text-decoration: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENCE & DATA STORAGE HANDLERS ---
DATA_FILE = "league_data.json"

def save_league_data(league_members, weekly_results, season_results):
    """Saves league session state data to persistent league_data.json file."""
    try:
        members_copy = {}
        for name, data in league_members.items():
            m_dict = dict(data)
            if "avatar" in m_dict and not isinstance(m_dict["avatar"], (str, type(None))):
                m_dict["avatar"] = None
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
                
                # Normalize string keys to int keys in weekly_results
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

def get_current_eliminated_bakers(week_num):
    """Get list of eliminated bakers dynamically driven strictly by admin broadcast results."""
    elim = []
    try:
        target_week = int(week_num)
    except (ValueError, TypeError):
        target_week = 10
        
    for w_int in get_sorted_weekly_result_weeks():
        if w_int <= target_week:
            res = get_weekly_result(w_int)
            act_el = res.get("eliminated")
            if isinstance(act_el, list):
                for b in act_el:
                    if b and b != "None" and b not in elim:
                        elim.append(b)
            elif isinstance(act_el, str) and act_el and act_el != "None":
                if act_el not in elim:
                    elim.append(act_el)
    return elim

def get_sorted_weekly_result_weeks():
    """Returns integer week numbers sorted numerically from st.session_state.weekly_results."""
    if "weekly_results" not in st.session_state or not st.session_state.weekly_results:
        return []
    weeks = []
    for k in st.session_state.weekly_results.keys():
        try:
            weeks.append(int(k))
        except (ValueError, TypeError):
            pass
    return sorted(list(set(weeks)))

def get_weekly_result(week):
    """Gets weekly results dict whether week key is int or str."""
    if "weekly_results" not in st.session_state or not st.session_state.weekly_results:
        return {}
    try:
        w_int = int(week)
    except (ValueError, TypeError):
        w_int = week
    return st.session_state.weekly_results.get(w_int) or st.session_state.weekly_results.get(str(w_int)) or {}


def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions:
        return 0
    
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
        # Standard Weeks 1-7
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
        act_inl = actuals.get("in_line_sb", [])
        if isinstance(act_inl, str): act_inl = [act_inl]
        pred_inl = predictions.get("in_line_sb")
        if pred_inl and pred_inl in act_inl and pred_inl != actuals.get("star_baker"):
            score += 2
            
        act_trbl = actuals.get("in_trouble", [])
        if isinstance(act_trbl, str): act_trbl = [act_trbl]
        pred_trbl = predictions.get("in_trouble")
        act_elim_raw = actuals.get("eliminated", [])
        if isinstance(act_elim_raw, str): act_elim_raw = [act_elim_raw]
        if pred_trbl and pred_trbl in act_trbl and pred_trbl not in act_elim_raw:
            score += 2
            
    return score

def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    # 1. Season Winner (40 points) or finalist consolation (15 points)
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and pred_winner in act_finalists:
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

# --- 4. MEDIA LOADERS ---
def load_logo_image():
    """Smart image loader for Norman Beaver header photo (assets/normanbeaver.jpg)."""
    priority_paths = [
        "assets/normanbeaver.jpg", "assets/normanbeaver.JPG", "assets/normanbeaver.jpeg", "assets/normanbeaver.JPEG",
        "assets/normanbeaver.png", "assets/normanbeaver.PNG", "assets/normanbeaver.webp",
        "assets/norman_beaver.jpg", "assets/norman_beaver.png", "assets/norman-beaver.jpg",
        "assets/NormanBeaver.jpg", "assets/Norman_Beaver.jpg", "normanbeaver.jpg", "normanbeaver.JPG", "normanbeaver.png",
        "assets/gbbslogo.jpg", "assets/gbbslogo.png"
    ]
    for p in priority_paths:
        if os.path.exists(p):
            try:
                return Image.open(p)
            except Exception:
                pass

    if os.path.exists("assets"):
        try:
            for filename in os.listdir("assets"):
                stem, ext = os.path.splitext(filename)
                clean_stem = stem.lower().replace("_", "").replace("-", "").strip()
                if ("norman" in clean_stem or "beaver" in clean_stem or "gbbs" in clean_stem) and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    try:
                        return Image.open(os.path.join("assets", filename))
                    except Exception:
                        pass
        except Exception:
            pass
    return None

def load_ai_brian_avatar():
    """Smart image loader for AI Brian's avatar (prioritizes assets/aibrian.jpg)."""
    priority_paths = [
        "assets/aibrian.jpg", "assets/aibrian.JPG", "assets/aibrian.jpeg", "assets/aibrian.JPEG",
        "assets/aibrian.png", "assets/aibrian.PNG", "assets/aibrian.webp",
        "assets/ai_brian.jpg", "assets/ai_brian.JPG", "assets/ai_brian.png",
        "assets/AIBrian.jpg", "assets/AIBrian.JPG", "assets/AI_Brian.jpg", "assets/AI_Brian.JPG",
        "assets/AI Brian.jpg", "assets/AI Brian.JPG",
        "aibrian.jpg", "aibrian.JPG", "aibrian.png", "ai_brian.jpg", "AI Brian.jpg"
    ]
    for p in priority_paths:
        if os.path.exists(p):
            try:
                return Image.open(p)
            except Exception:
                pass

    if os.path.exists("assets"):
        try:
            for filename in os.listdir("assets"):
                stem, ext = os.path.splitext(filename)
                clean_stem = stem.lower().replace("_", "").replace(" ", "").strip()
                if clean_stem in ["aibrian", "brian"] and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    try:
                        return Image.open(os.path.join("assets", filename))
                    except Exception:
                        pass
        except Exception:
            pass
    return None

def load_baker_image(baker_name):
    """Smart case-insensitive and multi-extension image loader."""
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

def apply_elimination_overlay(img):
    """Applies a semi-transparent red shading layer and a bold red 'X' over an eliminated baker photo."""
    try:
        canvas = img.convert('RGBA')
        w, h = canvas.size
        
        # 1. Semi-transparent red shading overlay
        red_tint = Image.new('RGBA', (w, h), (220, 30, 30, 95))
        tinted = Image.alpha_composite(canvas, red_tint)
        
        # 2. Draw thick red 'X' across the portrait
        draw = ImageDraw.Draw(tinted)
        stroke_w = max(5, int(min(w, h) / 10))
        
        # Draw dark outline for maximum contrast
        outline_w = stroke_w + 3
        draw.line([(0, 0), (w, h)], fill=(40, 0, 0, 200), width=outline_w)
        draw.line([(0, h), (w, 0)], fill=(40, 0, 0, 200), width=outline_w)
        
        # Draw main bright red X lines
        draw.line([(0, 0), (w, h)], fill=(230, 20, 20, 240), width=stroke_w)
        draw.line([(0, h), (w, 0)], fill=(230, 20, 20, 240), width=stroke_w)
        
        return tinted
    except Exception:
        return img

# --- 5. DATABASE & ROSTER INITIALIZATION ---
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

DEFAULT_ROSTER = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C", 
    "Taliah", "Tressa"
]

loaded_members, loaded_weekly, loaded_season = load_league_data()

if "league_members" not in st.session_state:
    if loaded_members:
        st.session_state.league_members = loaded_members
    else:
        st.session_state.league_members = {
            "AI Brian": {
                "avatar": "🤖",
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
        }
        for p_name in DEFAULT_ROSTER:
            st.session_state.league_members[p_name] = {
                "avatar": None,
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
else:
    for p_name in DEFAULT_ROSTER:
        if p_name not in st.session_state.league_members:
            st.session_state.league_members[p_name] = {
                "avatar": None,
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
        elif "pin" not in st.session_state.league_members[p_name]:
            st.session_state.league_members[p_name]["pin"] = None

# Check for AI Brian's custom profile picture
brian_avatar_img = load_ai_brian_avatar()
if brian_avatar_img is not None:
    st.session_state.league_members["AI Brian"]["avatar"] = brian_avatar_img

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = loaded_weekly if loaded_weekly is not None else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = loaded_season if loaded_season is not None else {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

# --- 6. DYNAMIC AUTOMATION: "AI BRIAN" PICK GENERATOR ---
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
            eliminated = random.sample(elim_pool, 2) if len(elim_pool) >= 2 else random.sample(active_bakers, min(2, len(active_bakers)))
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
            eliminated = random.sample(elim_pool, 2) if len(elim_pool) >= 2 else random.sample(active_bakers, min(2, len(active_bakers)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
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
            eliminated = random.sample(elim_pool, 2) if len(elim_pool) >= 2 else random.sample(active_bakers, min(2, len(active_bakers)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        remaining_for_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(remaining_for_bottom, 3) if len(remaining_for_bottom) >= 3 else random.sample(active_bakers, min(3, len(active_bakers)))
            
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

# --- 7. APP HEADER LAYOUT ---
logo_img = load_logo_image()
if logo_img is not None:
    col_logo, col_title = st.columns([1, 7], vertical_alignment="center")
    with col_logo:
        st.image(logo_img, width=90)
    with col_title:
        st.title("Great British Baking Show Fantasy League 2026")
else:
    st.title("🧁 Great British Baking Show Fantasy League 2026")

# --- 8. SIDEBAR: PLAYER PROFILE & POINTS REFERENCE GUIDE ---
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
            st.info("Unlock your profile in the **📝 Submit Predictions** tab using your 4-digit PIN to upload an avatar!")
        else:
            uploaded_file = st.file_uploader(f"Choose Photo for {sb_player}", type=["png", "jpg", "jpeg"])
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                image = image.resize((150, 150))
                st.session_state.league_members[sb_player]["avatar"] = image
                st.image(image, caption=f"{sb_player}'s Active Avatar", width=150)
                st.success(f"Avatar updated for {sb_player}!")
            else:
                cur_av = st.session_state.league_members[sb_player].get("avatar")
                if isinstance(cur_av, Image.Image):
                    st.image(cur_av, caption=f"{sb_player}'s Avatar", width=150)

    st.markdown("---")
    st.subheader("🗓️ Active Competition Week")
    st.session_state.current_week = st.slider("Select Episode Week:", 1, 10, st.session_state.current_week)
    
    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of what points are at stake for each prediction!")
    st.warning("⏰ **Weekly voting window ends on Tuesdays at 2:00 PM CT (Houston) / 8:00 PM BST right before the UK broadcast.**")
    
    with st.expander("🌟 Season-Long Projections (130 Max Pts)", expanded=False):
        st.markdown("""
        *   **Season Winner:** 40 pts
        *   **Finalist Consolation:** 15 pts *(if picked winner makes Top 3 but loses)*
        *   **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        *   **Hollywood Handshakes:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
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

# --- 9. MAIN APP TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Baker Analytics", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    sorted_members = sorted(
        st.session_state.league_members.items(),
        key=lambda item: item[1]["total_score"],
        reverse=True
    )

    col_hr, col_ha, col_hp, col_hs = st.columns([1, 1.2, 5, 2])
    with col_hr: st.markdown("**Rank**")
    with col_ha: st.markdown("**Avatar**")
    with col_hp: st.markdown("**Player Name**")
    with col_hs: st.markdown("**Total Points**")
    st.markdown("<hr style='margin: 4px 0 12px 0; border-top: 2px solid #D36B5F;'>", unsafe_allow_html=True)

    for idx, (member_name, data) in enumerate(sorted_members):
        rank = idx + 1
        rank_badge = f"#{rank}"
        if rank == 1: rank_badge = "🥇 #1"
        elif rank == 2: rank_badge = "🥈 #2"
        elif rank == 3: rank_badge = "🥉 #3"

        col_r, col_a, col_p, col_s = st.columns([1, 1.2, 5, 2])
        with col_r:
            st.markdown(f"<div style='padding-top:12px;'><h3>{rank_badge}</h3></div>", unsafe_allow_html=True)
        with col_a:
            p_av = data.get("avatar")
            if isinstance(p_av, Image.Image):
                st.image(p_av, width=50)
            elif member_name == "AI Brian":
                b_img = load_ai_brian_avatar()
                if b_img:
                    st.image(b_img, width=50)
                else:
                    st.markdown("<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
            else:
                st.markdown("<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)
        with col_p:
            st.markdown(f"<div style='padding-top:12px;'><h3><strong>{member_name}</strong></h3></div>", unsafe_allow_html=True)
        with col_s:
            st.markdown(f"<div style='padding-top:12px;'><h3><strong>{data['total_score']} pts</strong></h3></div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    st.markdown("---")
    st.header("🔍 Individual Player Scorecards")
    st.write("Select a player below to inspect their full, line-item point calculations across every completed week and season projection!")

    player_names = list(st.session_state.league_members.keys())
    selected_player = st.selectbox("Choose Player Scorecard to View:", player_names)
    
    p_data = st.session_state.league_members[selected_player]
    p_avatar = p_data.get("avatar")
    
    col_sc1, col_sc2 = st.columns([1, 4])
    with col_sc1:
        if isinstance(p_avatar, Image.Image):
            st.image(p_avatar, caption=f"{selected_player}'s Avatar", width=120)
        elif selected_player == "AI Brian":
            b_img = load_ai_brian_avatar()
            if b_img:
                st.image(b_img, caption="AI Brian", width=120)
            else:
                st.markdown("<h1 style='font-size: 60px; margin: 0;'>🤖</h1>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='font-size: 60px; margin: 0;'>🍪</h1>", unsafe_allow_html=True)
            
    with col_sc2:
        st.subheader(f"📊 Detailed Point Matrix: {selected_player}")
        st.markdown(f"**Total Combined Score:** `{p_data['total_score']} pts`")
        
        all_weeks = get_sorted_weekly_result_weeks()
        if not all_weeks:
            st.info("No episode broadcast results published yet. Weekly line-item calculations will appear here after Episode 1!")
        else:
            st.markdown("#### 📅 Weekly Episodic Scorecards")
            for w_num in all_weeks:
                res = get_weekly_result(w_num)
                pred_w = p_data["weekly_picks"].get(w_num, {})
                
                with st.expander(f"Week {w_num} Breakdown (Episode Results)", expanded=False):
                    raw_pts = calculate_weekly_score(pred_w, res, w_num)
                    
                    # Check for Star Member bonus
                    weekly_scores_all = {m: calculate_weekly_score(m_data["weekly_picks"].get(w_num, {}), res, w_num) for m, m_data in st.session_state.league_members.items()}
                    max_score_w = max(weekly_scores_all.values()) if weekly_scores_all else 0
                    has_star_bonus = (raw_pts == max_score_w and raw_pts > 0)
                    
                    st.write(f"**Episode Results:** Star Baker: `{res.get('star_baker', 'N/A')}` | Eliminated: `{res.get('eliminated', 'N/A')}`")
                    st.write(f"**Your Predictions:** Star Baker: `{pred_w.get('star_baker', 'None')}` | Eliminated: `{pred_w.get('eliminated', 'None')}`")
                    st.markdown(f"**Episodic Raw Score:** `{raw_pts} pts`" + (f" | 🌟 **Star League Member Bonus:** `+5 pts` *(Highest weekly scorer!)*" if has_star_bonus else ""))
                    st.markdown(f"**Week {w_num} Total Awarded:** `{p_data['weekly_breakdown'].get(w_num, raw_pts + (5 if has_star_bonus else 0))} pts`")

            if st.session_state.season_results:
                st.markdown("#### 🌟 Season-Long Predictions")
                with st.expander("Final Season Projections Scorecard", expanded=True):
                    s_pred = p_data["season_picks"]
                    s_act = st.session_state.season_results
                    s_pts = calculate_season_score(s_pred, s_act)
                    st.write(f"**Season Winner Pick:** `{s_pred.get('winner', 'None')}` (Actual: `{s_act.get('winner', 'N/A')}`)")
                    st.write(f"**Semifinalists Pick:** `{', '.join(s_pred.get('semifinalists', []))}`")
                    st.markdown(f"**Season Projections Total Points Earned:** `{s_pts} pts`")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Your Predictions")
    
    active_roster = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    
    col_p1, col_p2 = st.columns([2, 3])
    with col_p1:
        active_sub_player = st.selectbox("Select Player Profile Submitting Predictions:", active_roster, index=0)
        
    p_pin = st.session_state.league_members[active_sub_player].get("pin")
    is_authed = st.session_state.authenticated_players.get(active_sub_player, False)
    
    if p_pin is None:
        st.info(f"🔑 **First Visit for {active_sub_player}?** Please create a 4-digit Security PIN to lock and protect your prediction ballot.")
        with st.form(f"pin_setup_form_{active_sub_player}"):
            new_pin = st.text_input("Create 4-Digit Security PIN", type="password", max_chars=4)
            confirm_pin = st.text_input("Confirm 4-Digit Security PIN", type="password", max_chars=4)
            set_pin_btn = st.form_submit_button("Set My Security PIN")
            if set_pin_btn:
                if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                    st.session_state.league_members[active_sub_player]["pin"] = new_pin
                    st.session_state.authenticated_players[active_sub_player] = True
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Security PIN set successfully for {active_sub_player}! Your ballot is unlocked.")
                    st.rerun()
                else:
                    st.error("PINs must be exactly 4 digits and match!")
    elif not is_authed:
        st.warning(f"🔒 Profile **{active_sub_player}** is PIN protected.")
        with st.form(f"pin_verify_form_{active_sub_player}"):
            entered_pin = st.text_input(f"Enter 4-Digit PIN for {active_sub_player}", type="password", max_chars=4)
            verify_btn = st.form_submit_button("Unlock Ballot")
            if verify_btn:
                if entered_pin == p_pin:
                    st.session_state.authenticated_players[active_sub_player] = True
                    st.success(f"PIN verified! Welcome back, {active_sub_player}.")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again or ask the Administrator to reset it.")
    else:
        st.success(f"🔓 **Ballot Unlocked for {active_sub_player}**")
        if st.button("🔒 Lock Profile Session"):
            st.session_state.authenticated_players[active_sub_player] = False
            st.rerun()
            
        st.markdown("---")
        
        # 1. VISUAL BAKER GALLERY
        with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
            cols = st.columns(4)
            for idx, baker in enumerate(ALL_BAKERS):
                info = BAKER_INFO.get(baker, {"url": "#"})
                with cols[idx % 4]:
                    img = load_baker_image(baker)
                    if img is not None:
                        st.image(img, use_container_width=True)
                        st.markdown(f"**{baker}**")
                    else:
                        st.markdown(f"**{baker}**")
                        st.markdown(f"[🔗 View Photo Page]({info['url']})")

        # 2. SEASON-LONG PREDICTIONS FORM (LOCKS PRE-WEEK 2)
        if st.session_state.current_week <= 2:
            st.markdown("---")
            with st.expander("🌟 Season-Long Projections (130 Max Pts | Locks Pre-Week 2)", expanded=(st.session_state.current_week == 2)):
                existing_s = st.session_state.league_members[active_sub_player].get("season_picks", {})
                def_winner = existing_s.get("winner")
                def_winner_idx = ALL_BAKERS.index(def_winner) if def_winner in ALL_BAKERS else 0
                
                user_winner = st.selectbox(
                    "Predict Season Winner (Show Champion) [40 pts if winner, 15 pts if runner-up consolation]", 
                    ALL_BAKERS, 
                    index=def_winner_idx,
                    key=f"{active_sub_player}_win_pick_w2"
                )
                remaining_for_semis = [b for b in ALL_BAKERS if b != user_winner]
                def_semis = [b for b in existing_s.get("semifinalists", []) if b in remaining_for_semis]
                
                user_semis = st.multiselect(
                    "Predict Other 3 Semifinalists [10 pts each | 30 pts max]", 
                    remaining_for_semis, 
                    default=def_semis,
                    max_selections=3,
                    key=f"{active_sub_player}_semis_pick_w2"
                )
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=existing_s.get("handshakes", 5), key=f"{active_sub_player}_hs_pick_w2")
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=existing_s.get("crying", 12), key=f"{active_sub_player}_cry_pick_w2")
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=existing_s.get("innuendos", 48), key=f"{active_sub_player}_inn_pick_w2")
                
                if st.button(f"Lock Season-Long Predictions for {active_sub_player}", key=f"btn_lock_season_{active_sub_player}"):
                    if len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members[active_sub_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success(f"Season long projections saved for {active_sub_player}!")

        # 3. WEEKLY BALLOT FORM
        st.markdown("---")
        st.subheader(f"📅 Submit Weekly Predictions: Week {st.session_state.current_week}")
        
        current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
        
        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, key=f"dbl_elim_chk_{active_sub_player}_w{st.session_state.current_week}")

        existing_w = st.session_state.league_members[active_sub_player]["weekly_picks"].get(st.session_state.current_week, {})
        
        with st.form(f"weekly_predictions_form_{active_sub_player}_w{st.session_state.current_week}"):
            weekly_picks = {}
            
            if st.session_state.current_week == 10:
                def_champ = existing_w.get("show_champion")
                def_champ_idx = active_bakers.index(def_champ) if def_champ in active_bakers else 0
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", active_bakers, index=def_champ_idx, placeholder="-- Select Show Champion --")
                
                st.write("Predict Technical Challenge Final Rank:")
                t_ranks_exist = existing_w.get("tech_rank", [])
                t1_i = active_bakers.index(t_ranks_exist[0]) if len(t_ranks_exist) > 0 and t_ranks_exist[0] in active_bakers else 0
                t2_i = active_bakers.index(t_ranks_exist[1]) if len(t_ranks_exist) > 1 and t_ranks_exist[1] in active_bakers else (1 if len(active_bakers) > 1 else 0)
                t3_i = active_bakers.index(t_ranks_exist[2]) if len(t_ranks_exist) > 2 and t_ranks_exist[2] in active_bakers else (2 if len(active_bakers) > 2 else 0)
                
                tech_1st = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="w10_t1")
                tech_2nd = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="w10_t2")
                tech_3rd = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="w10_t3")
                weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]
                
            elif st.session_state.current_week == 9:
                def_sb = existing_w.get("star_baker")
                def_sb_i = active_bakers.index(def_sb) if def_sb in active_bakers else 0
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers, index=def_sb_i, placeholder="-- Select Star Baker --")
                
                def_el = existing_w.get("eliminated")
                if is_double_elim:
                    el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                    el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                    el1_i = active_bakers.index(el1) if el1 in active_bakers else 0
                    el2_i = active_bakers.index(el2) if el2 in active_bakers else (1 if len(active_bakers) > 1 else 0)
                    elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, index=el1_i, placeholder="-- Select Eliminated Baker #1 --", key="pred_elim_1_w9")
                    elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", active_bakers, index=el2_i, placeholder="-- Select Eliminated Baker #2 --", key="pred_elim_2_w9")
                    weekly_picks["eliminated"] = [elim_1, elim_2]
                else:
                    def_el_i = active_bakers.index(def_el) if isinstance(def_el, str) and def_el in active_bakers else 0
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers, index=def_el_i, placeholder="-- Select Eliminated Baker --")
                
                st.write("Predict Technical Challenge Final Rank:")
                t_ranks_exist = existing_w.get("tech_rank", [])
                t1_i = active_bakers.index(t_ranks_exist[0]) if len(t_ranks_exist) > 0 and t_ranks_exist[0] in active_bakers else 0
                t2_i = active_bakers.index(t_ranks_exist[1]) if len(t_ranks_exist) > 1 and t_ranks_exist[1] in active_bakers else (1 if len(active_bakers) > 1 else 0)
                t3_i = active_bakers.index(t_ranks_exist[2]) if len(t_ranks_exist) > 2 and t_ranks_exist[2] in active_bakers else (2 if len(active_bakers) > 2 else 0)
                t4_i = active_bakers.index(t_ranks_exist[3]) if len(t_ranks_exist) > 3 and t_ranks_exist[3] in active_bakers else (3 if len(active_bakers) > 3 else 0)
                
                t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="w9_t1")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="w9_t2")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="w9_t3")
                t4 = st.selectbox("Technical 4th Place [3 pts]", active_bakers, index=t4_i, placeholder="-- Select 4th Place --", key="w9_t4")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif st.session_state.current_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    def_sb = existing_w.get("star_baker")
                    def_sb_i = active_bakers.index(def_sb) if def_sb in active_bakers else 0
                    def_inl = existing_w.get("in_line_sb")
                    def_inl_i = active_bakers.index(def_inl) if def_inl in active_bakers else 0
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers, index=def_sb_i, placeholder="-- Select Star Baker --")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", active_bakers, index=def_inl_i, placeholder="-- Select In Line Baker --")
                with col2:
                    def_el = existing_w.get("eliminated")
                    def_trb = existing_w.get("in_trouble")
                    def_trb_i = active_bakers.index(def_trb) if def_trb in active_bakers else 0
                    if is_double_elim:
                        el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                        el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                        el1_i = active_bakers.index(el1) if el1 in active_bakers else 0
                        el2_i = active_bakers.index(el2) if el2 in active_bakers else (1 if len(active_bakers) > 1 else 0)
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, index=el1_i, placeholder="-- Select Eliminated Baker #1 --", key="pred_elim_1_w8")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", active_bakers, index=el2_i, placeholder="-- Select Eliminated Baker #2 --", key="pred_elim_2_w8")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                    else:
                        def_el_i = active_bakers.index(def_el) if isinstance(def_el, str) and def_el in active_bakers else 0
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers, index=def_el_i, placeholder="-- Select Eliminated Baker --")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                
                st.write("Predict Technical Challenge Final Rank:")
                t_ranks_exist = existing_w.get("tech_rank", [])
                t1_i = active_bakers.index(t_ranks_exist[0]) if len(t_ranks_exist) > 0 and t_ranks_exist[0] in active_bakers else 0
                t2_i = active_bakers.index(t_ranks_exist[1]) if len(t_ranks_exist) > 1 and t_ranks_exist[1] in active_bakers else (1 if len(active_bakers) > 1 else 0)
                t3_i = active_bakers.index(t_ranks_exist[2]) if len(t_ranks_exist) > 2 and t_ranks_exist[2] in active_bakers else (2 if len(active_bakers) > 2 else 0)
                t4_i = active_bakers.index(t_ranks_exist[3]) if len(t_ranks_exist) > 3 and t_ranks_exist[3] in active_bakers else (3 if len(active_bakers) > 3 else 0)
                t5_i = active_bakers.index(t_ranks_exist[4]) if len(t_ranks_exist) > 4 and t_ranks_exist[4] in active_bakers else (4 if len(active_bakers) > 4 else 0)
                
                t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", active_bakers, index=t4_i, placeholder="-- Select 4th Place --", key="t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", active_bakers, index=t5_i, placeholder="-- Select 5th Place --", key="t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                
            else:
                # Standard Weeks 1-7
                col1, col2 = st.columns(2)
                with col1:
                    def_sb = existing_w.get("star_baker")
                    def_sb_i = active_bakers.index(def_sb) if def_sb in active_bakers else 0
                    def_inl = existing_w.get("in_line_sb")
                    def_inl_i = active_bakers.index(def_inl) if def_inl in active_bakers else 0
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers, index=def_sb_i, placeholder="-- Select Star Baker --")
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", active_bakers, index=def_inl_i, placeholder="-- Select In Line Baker --")
                with col2:
                    def_el = existing_w.get("eliminated")
                    def_trb = existing_w.get("in_trouble")
                    def_trb_i = active_bakers.index(def_trb) if def_trb in active_bakers else 0
                    if is_double_elim:
                        el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                        el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                        el1_i = active_bakers.index(el1) if el1 in active_bakers else 0
                        el2_i = active_bakers.index(el2) if el2 in active_bakers else (1 if len(active_bakers) > 1 else 0)
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, index=el1_i, placeholder="-- Select Eliminated Baker #1 --", key="pred_elim_1_std")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", active_bakers, index=el2_i, placeholder="-- Select Eliminated Baker #2 --", key="pred_elim_2_std")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                    else:
                        def_el_i = active_bakers.index(def_el) if isinstance(def_el, str) and def_el in active_bakers else 0
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers, index=def_el_i, placeholder="-- Select Eliminated Baker --")
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                    
                st.markdown("---")
                st.write("Predict Technical Challenge Placements:")
                col_t_top, col_t_bot = st.columns(2)
                
                def_top3 = [b for b in existing_w.get("tech_top_3", []) if b in active_bakers]
                def_bot3 = [b for b in existing_w.get("tech_bottom_3", []) if b in active_bakers]
                
                with col_t_top:
                    t1_i = active_bakers.index(def_top3[0]) if len(def_top3) > 0 else 0
                    t2_i = active_bakers.index(def_top3[1]) if len(def_top3) > 1 else (1 if len(active_bakers) > 1 else 0)
                    t3_i = active_bakers.index(def_top3[2]) if len(def_top3) > 2 else (2 if len(active_bakers) > 2 else 0)
                    t1 = st.selectbox("1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="std_t1")
                    t2 = st.selectbox("2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="std_t2")
                    t3 = st.selectbox("3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="std_t3")
                    weekly_picks["tech_top_3"] = [t1, t2, t3]
                    
                with col_t_bot:
                    b3_i = active_bakers.index(def_bot3[0]) if len(def_bot3) > 0 else (len(active_bakers) - 3 if len(active_bakers) >= 3 else 0)
                    b2_i = active_bakers.index(def_bot3[1]) if len(def_bot3) > 1 else (len(active_bakers) - 2 if len(active_bakers) >= 2 else 0)
                    b1_i = active_bakers.index(def_bot3[2]) if len(def_bot3) > 2 else (len(active_bakers) - 1 if len(active_bakers) >= 1 else 0)
                    b_3rd_last = st.selectbox("3rd-to-last Place [2 pts]", active_bakers, index=b3_i, placeholder="-- Select 3rd-to-last Place --", key="std_b3")
                    b_2nd_last = st.selectbox("2nd-to-last Place [2 pts]", active_bakers, index=b2_i, placeholder="-- Select 2nd-to-last Place --", key="std_b2")
                    b_last = st.selectbox("Last Place [3 pts]", active_bakers, index=b1_i, placeholder="-- Select Last Place --", key="std_b1")
                    weekly_picks["tech_bottom_3"] = [b_3rd_last, b_2nd_last, b_last]

            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                st.session_state.league_members[active_sub_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                
                ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Predictions saved for {active_sub_player}! AI Brian has also submitted his randomized picks.")

# --- TAB 3: BAKER ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Career Performance Matrix")
    st.write("Inspect how contestants are performing across Star Baker wins, nomination consolations, Hollywood Handshakes, and technical challenge finishes.")
    
    current_eliminated_latest = get_current_eliminated_bakers(10)
    
    # A. Overall Baker Performance Matrix
    baker_stats = {}
    for baker in ALL_BAKERS:
        baker_stats[baker] = {
            "star_baker_cnt": 0,
            "in_line_cnt": 0,
            "in_trouble_cnt": 0,
            "handshake_cnt": 0,
            "tech_ranks": [],  # [(week, pos)]
            "tech_rank_pcts": []
        }
        
    for w in get_sorted_weekly_result_weeks():
        res = get_weekly_result(w)
        
        sb = res.get("star_baker")
        if sb and sb in baker_stats:
            baker_stats[sb]["star_baker_cnt"] += 1
            
        for inl in res.get("in_line_sb", []):
            if inl in baker_stats:
                baker_stats[inl]["in_line_cnt"] += 1
                
        for trb in res.get("in_trouble", []):
            if trb in baker_stats:
                baker_stats[trb]["in_trouble_cnt"] += 1
                
        for hs in res.get("handshake_bakers", []):
            if hs in baker_stats:
                baker_stats[hs]["handshake_cnt"] += 1
                
        t_ranks = res.get("tech_rank", [])
        if t_ranks:
            num_in_tech = len(t_ranks)
            for pos_idx, baker in enumerate(t_ranks):
                if baker in baker_stats:
                    pos = pos_idx + 1
                    baker_stats[baker]["tech_ranks"].append((w, pos))
                    pct = round(((num_in_tech - pos + 1) / num_in_tech) * 100, 1)
                    baker_stats[baker]["tech_rank_pcts"].append(pct)

    with st.expander("📊 Contestant Performance Matrix Summary", expanded=True):
        matrix_rows = []
        for baker in ALL_BAKERS:
            s = baker_stats[baker]
            avg_fin = round(sum(pos for _, pos in s["tech_ranks"]) / len(s["tech_ranks"]), 1) if s["tech_ranks"] else "N/A"
            avg_pct = round(sum(s["tech_rank_pcts"]) / len(s["tech_rank_pcts"]), 1) if s["tech_rank_pcts"] else "N/A"
            is_elim = baker in current_eliminated_latest
            
            matrix_rows.append({
                "Contestant": baker + (" ❌" if is_elim else " 🧁"),
                "Status": "Eliminated" if is_elim else "Active",
                "Star Baker Titles 🌟": s["star_baker_cnt"],
                "In Line Nominee 📈": s["in_line_cnt"],
                "In Trouble Nominee ⚠️": s["in_trouble_cnt"],
                "Avg Tech Rank": avg_fin,
                "Relative Tech Rank %": f"{avg_pct}%" if avg_pct != "N/A" else "N/A",
                "Handshakes 🤝": s["handshake_cnt"]
            })
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)

    # B. Individual Baker Inspection
    st.markdown("---")
    selected_ana_baker = st.selectbox("Select Baker to Inspect:", ALL_BAKERS, key="ana_baker_select")
    
    ana_s = baker_stats[selected_ana_baker]
    is_baker_elim = selected_ana_baker in current_eliminated_latest
    b_img_orig = load_baker_image(selected_ana_baker)
    
    col_ana1, col_ana2 = st.columns([1, 3])
    with col_ana1:
        if b_img_orig is not None:
            if is_baker_elim:
                disp_img = apply_elimination_overlay(b_img_orig)
                st.image(disp_img, caption=f"{selected_ana_baker} (Eliminated)", use_container_width=True)
            else:
                st.image(b_img_orig, caption=f"{selected_ana_baker} (Active)", use_container_width=True)
        else:
            st.markdown(f"### **{selected_ana_baker}**" + (" *(Eliminated)*" if is_baker_elim else ""))

    with col_ana2:
        st.markdown(f"#### 🏅 {selected_ana_baker}'s Career Accolades")
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Star Baker", f"{ana_s['star_baker_cnt']} 🌟")
        with m2: st.metric("In Line", f"{ana_s['in_line_cnt']} 📈")
        with m3: st.metric("In Trouble", f"{ana_s['in_trouble_cnt']} ⚠️")
        with m4: st.metric("Handshakes", f"{ana_s['handshake_cnt']} 🤝")
            
        st.markdown("---")
        avg_fin_val = round(sum(pos for _, pos in ana_s["tech_ranks"]) / len(ana_s["tech_ranks"]), 1) if ana_s["tech_ranks"] else "N/A"
        avg_pct_val = round(sum(ana_s["tech_rank_pcts"]) / len(ana_s["tech_rank_pcts"]), 1) if ana_s["tech_rank_pcts"] else "N/A"
        
        st.markdown(f"**Average Technical Finish:** `{avg_fin_val}` | **Technical Relative Rank %:** `{avg_pct_val}%`")
        
        if ana_s["tech_ranks"]:
            st.markdown("##### 📈 Technical Placement Trajectory")
            df_chart = pd.DataFrame({
                "Week": [f"W{w}" for w, _ in ana_s["tech_ranks"]],
                "Technical Position": [pos for _, pos in ana_s["tech_ranks"]]
            }).set_index("Week")
            st.line_chart(df_chart)
        else:
            st.info("No technical challenge rank data recorded for this baker yet.")
            
        all_logged_weeks = get_sorted_weekly_result_weeks()
        if len(all_logged_weeks) >= 3:
            st.markdown("##### 🏷️ Performance Classification")
            if ana_s["star_baker_cnt"] >= 2 or (avg_pct_val != "N/A" and avg_pct_val >= 75):
                st.success("🌟 **Top Contender:** Consistently ranks at the top of technicals and wins Star Baker titles.")
            elif ana_s["in_trouble_cnt"] >= 2 or (avg_pct_val != "N/A" and avg_pct_val <= 30):
                st.warning("⚠️ **High Risk:** Frequently in the bottom tier of technicals or nominated in trouble.")
            else:
                st.info("🧁 **Steady Performer:** Holds solid middle-tier technical finishes and steady performance.")

    st.markdown("---")
    
    # C. Official Chaos & Event Log
    with st.expander("📝 Official Broadcast Timestamps & Descriptions Log", expanded=False):
        st.write("Review the Admin's published notes and timestamps for key episode events:")
        for w in get_sorted_weekly_result_weeks():
            res = get_weekly_result(w)
            st.markdown(f"#### 📍 Week {w} Broadcast Log")
            hs_stamps = res.get("handshake_timestamps", "")
            cry_stamps = res.get("crying_timestamps", "")
            inn_cnt = res.get("innuendo_count", 0)
            
            st.markdown(f"- **🤝 Handshakes:** {hs_stamps if hs_stamps else 'None recorded'}")
            st.markdown(f"- **😢 Crying Scenes:** {cry_stamps if cry_stamps else 'None recorded'}")
            st.markdown(f"- **💬 Sexual Innuendos Count:** `{inn_cnt}`")
            st.markdown("<hr style='margin: 4px 0;'>", unsafe_allow_html=True)

# --- TAB 4: ADMIN PANEL (PIN PROTECTED) ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Lock Screen**")
        st.write("This section is restricted to the League Administrator. Please enter your Admin PIN to unlock the broadcast input controls.")
        
        with st.form("admin_login_form"):
            pin_input = st.text_input("Enter Admin PIN", type="password")
            login_btn = st.form_submit_button("Unlock Admin Panel")
            if login_btn:
                if pin_input == "6284":
                    st.session_state.admin_authenticated = True
                    st.success("Admin PIN verified! Unlocking console...")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again.")
    else:
        st.success("🔓 **Authenticated as League Administrator**")
        if st.button("🔒 Lock Console Session"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        
        # --- COMMISSIONER PIN RESET OVERRIDE ---
        with st.expander("🔑 Player Security PIN Management & Reset", expanded=False):
            st.write("If a player forgets their 4-digit PIN, you can reset it here so they can create a new code on their next visit.")
            active_roster = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
            p_to_reset = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + active_roster)
            if p_to_reset != "-- Select Player --":
                cur_p_status = "Locked 🔒" if st.session_state.league_members[p_to_reset].get("pin") else "Unset 🔓"
                st.write(f"Current PIN Status for **{p_to_reset}**: `{cur_p_status}`")
                if st.button(f"Reset PIN for {p_to_reset}"):
                    st.session_state.league_members[p_to_reset]["pin"] = None
                    if p_to_reset in st.session_state.authenticated_players:
                        st.session_state.authenticated_players[p_to_reset] = False
                    st.success(f"Security PIN reset for {p_to_reset}! They can now set a new 4-digit PIN when they select their profile.")
                    st.rerun()

        st.markdown("---")
        st.write("Use this tab to input the actual results from the broadcast. Submitting actual results will score all predictions and update the live leaderboard!")
        
        current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
            actuals = {}
            
            if st.session_state.current_week == 10:
                opts_sc = ["-- Select Show Champion --"] + active_bakers
                act_sc_sel = st.selectbox("Actual Show Champion", opts_sc, index=0, key="admin_act_sc_w10")
                actuals["show_champion"] = act_sc_sel if not act_sc_sel.startswith("-- Select") else "None"
                
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                opts_win = ["-- Select Season Winner --"] + active_bakers
                act_winner_sel = st.selectbox("Actual Season Winner (Show Champion)", opts_win, index=0, key="act_w10_winner")
                act_winner = act_winner_sel if not act_winner_sel.startswith("-- Select") else "None"
                
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, default=[], key="act_w10_semis")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, default=[], key="act_w10_finalists")
                act_handshakes = st.number_input("Actual Total Handshakes across Season", min_value=0, value=5, key="act_w10_hs")
                act_crying = st.number_input("Actual Total Crying Scenes across Season", min_value=0, value=12, key="act_w10_cry")
                act_innuendos = st.number_input("Actual Total Sexual Innuendos across Season", min_value=0, value=48, key="act_w10_inn")
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }
                
            elif st.session_state.current_week == 9:
                opts_sb9 = ["-- Select Star Baker --"] + active_bakers
                act_sb9_sel = st.selectbox("Actual Star Baker", opts_sb9, index=0, key="admin_act_sb_w9")
                actuals["star_baker"] = act_sb9_sel if not act_sb9_sel.startswith("-- Select") else "None"
                
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    opts_el9 = ["-- Select Eliminated Baker --"] + active_bakers
                    act_el9_sel = st.selectbox("Actual Eliminated Baker", opts_el9, index=0, key="admin_act_elim_w9")
                    actuals["eliminated"] = act_el9_sel if not act_el9_sel.startswith("-- Select") else "None"
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week. Consolation and other categories are still scored normally.")
                else:
                    opts_el9_1 = ["-- Select Eliminated Baker #1 --"] + active_bakers
                    act_el9_1 = st.selectbox("Actual Eliminated Baker #1", opts_el9_1, index=0, key="admin_act_elim_1_w9")
                    opts_el9_2 = ["-- Select Eliminated Baker #2 --"] + active_bakers
                    act_el9_2 = st.selectbox("Actual Eliminated Baker #2", opts_el9_2, index=0, key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [b for b in [act_el9_1, act_el9_2] if not b.startswith("-- Select")]

            else:
                # Standard Weeks 1-8
                col1, col2 = st.columns(2)
                with col1:
                    opts_sb = ["-- Select Star Baker --", "None (No Star Baker)"] + active_bakers
                    act_sb_sel = st.selectbox("Actual Star Baker", opts_sb, index=0, key=f"admin_act_sb_w{st.session_state.current_week}")
                    actuals["star_baker"] = act_sb_sel if act_sb_sel not in ["-- Select Star Baker --", "None (No Star Baker)"] else "None"
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, key=f"admin_in_line_w{st.session_state.current_week}")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{st.session_state.current_week}")
                    if elim_type == "Single Elimination":
                        opts_el = ["-- Select Eliminated Baker --"] + active_bakers
                        act_el_sel = st.selectbox("Actual Eliminated Baker", opts_el, index=0, key=f"admin_act_elim_w{st.session_state.current_week}")
                        actuals["eliminated"] = act_el_sel if not act_el_sel.startswith("-- Select") else "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"admin_in_trouble_w{st.session_state.current_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("No baker was eliminated this week. Predicting elimination scores 0.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, key=f"admin_in_trouble_w{st.session_state.current_week}")
                    else:
                        opts_el1 = ["-- Select Eliminated Baker #1 --"] + active_bakers
                        act_el1_sel = st.selectbox("Actual Eliminated Baker #1", opts_el1, index=0, key=f"admin_act_elim_1_w{st.session_state.current_week}")
                        opts_el2 = ["-- Select Eliminated Baker #2 --"] + active_bakers
                        act_el2_sel = st.selectbox("Actual Eliminated Baker #2", opts_el2, index=0, key=f"admin_act_elim_2_w{st.session_state.current_week}")
                        actuals["eliminated"] = [b for b in [act_el1_sel, act_el2_sel] if not b.startswith("-- Select")]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"admin_in_trouble_w{st.session_state.current_week}")
                    
            # --- UNIVERSAL TECHNICAL CHALLENGE RANKINGS FOR ALL WEEKS ---
            st.markdown("---")
            st.markdown(f"### 📊 Actual Technical Challenge Rankings (1st through {len(active_bakers)}th Place)")
            st.write("Select the exact placement for every baker in the technical challenge:")
            
            num_bakers = len(active_bakers)
            cols_per_row = 3
            
            selected_by_rank = {}
            for r in range(1, num_bakers + 1):
                k = f"admin_full_tech_w{st.session_state.current_week}_r{r}"
                v = st.session_state.get(k)
                if v and not str(v).startswith("-- Select"):
                    selected_by_rank[r] = v

            full_tech_ranks = []
            
            for i in range(num_bakers):
                rank_num = i + 1
                if rank_num == 1: ord_str = "1st"
                elif rank_num == 2: ord_str = "2nd"
                elif rank_num == 3: ord_str = "3rd"
                else: ord_str = f"{rank_num}th"
                
                if i % cols_per_row == 0:
                    t_cols = st.columns(min(cols_per_row, num_bakers - i))
                
                col = t_cols[i % cols_per_row]
                with col:
                    key_r = f"admin_full_tech_w{st.session_state.current_week}_r{rank_num}"
                    placeholder = f"-- Select {ord_str} Place --"
                    
                    others_selected = [v for r_num, v in selected_by_rank.items() if r_num != rank_num]
                    available_bakers = [b for b in active_bakers if b not in others_selected]
                    opts = [placeholder] + available_bakers
                    
                    curr_val = st.session_state.get(key_r)
                    idx = opts.index(curr_val) if curr_val in opts else 0
                    
                    sel_baker = st.selectbox(
                        f"Actual Technical {ord_str} Place",
                        opts,
                        index=idx,
                        key=key_r
                    )
                    if sel_baker and not str(sel_baker).startswith("-- Select"):
                        full_tech_ranks.append(sel_baker)
                    else:
                        full_tech_ranks.append(None)

            cleaned_tech_ranks = [b for b in full_tech_ranks if b is not None]
            actuals["tech_rank"] = cleaned_tech_ranks
            if len(cleaned_tech_ranks) >= 3:
                actuals["tech_top_3"] = cleaned_tech_ranks[:3]
                actuals["tech_bottom_3"] = cleaned_tech_ranks[-3:]
            else:
                actuals["tech_top_3"] = cleaned_tech_ranks
                actuals["tech_bottom_3"] = cleaned_tech_ranks

            # --- WEEKLY HANDSHAKE & CRYING TIMESTAMPS & INNUENDOS ---
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            with col_hs1:
                act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"handshake_bakers_w{st.session_state.current_week}")
                act_handshake_cnt = st.number_input("Number of Handshakes in Episode", min_value=0, value=len(act_handshake_bakers), key=f"handshake_cnt_w{st.session_state.current_week}")
            with col_hs2:
                act_handshake_stamps = st.text_input("Description & Video Timestamps (e.g. 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper')", value="", key=f"handshake_stamps_w{st.session_state.current_week}")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Incidents in Episode", min_value=0, value=0, key=f"crying_cnt_w{st.session_state.current_week}")
            with col_cry2:
                act_crying_stamps = st.text_input("Description & Video Timestamps (e.g. 'Mo during technical @ 24:15, Molly @ 54:02')", value="", key=f"crying_stamps_w{st.session_state.current_week}")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Sexual Innuendos in Episode", min_value=0, value=0, key=f"innuendo_cnt_w{st.session_state.current_week}")
            with col_inn2:
                act_innuendo_stamps = st.text_input("Description & Video Timestamps (e.g. 'Paul & Prue soggy bottom banter @ 18:05')", value="", key=f"innuendo_stamps_w{st.session_state.current_week}")

            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_count"] = act_handshake_cnt
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            actuals["innuendo_timestamps"] = act_innuendo_stamps
            
            submit_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if submit_actuals:
                if len(actuals.get("tech_rank", [])) < len(active_bakers):
                    st.error(f"⚠️ Please select a baker for all {len(active_bakers)} Technical Challenge ranks before publishing!")
                else:
                    st.session_state.weekly_results[st.session_state.current_week] = actuals
                    if st.session_state.current_week == 10:
                        st.session_state.season_results = actuals_season
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    
                    # TRIGGER RECALCULATION
                    for member_name in st.session_state.league_members:
                        st.session_state.league_members[member_name]["total_score"] = 0
                        st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                        
                    all_weeks_scored = get_sorted_weekly_result_weeks()
                    for w in all_weeks_scored:
                        act_w = get_weekly_result(w)
                        
                        weekly_raw = {}
                        for m_name, m_data in st.session_state.league_members.items():
                            pred_w = m_data["weekly_picks"].get(w, {})
                            raw_score = calculate_weekly_score(pred_w, act_w, w)
                            weekly_raw[m_name] = raw_score
                            m_data["weekly_breakdown"][w] = raw_score
                            
                        if weekly_raw:
                            max_raw = max(weekly_raw.values())
                            for m_name, raw_s in weekly_raw.items():
                                if raw_s == max_raw and raw_s > 0:
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
                        
                    st.success("Leaderboard updated! All player predictions scored and verified against official rule constraints.")

        # --- POST-TESTING SEASON RESET TOOL ---
        st.markdown("---")
        st.subheader("🧹 Reset Season Data (Post-Testing Wipe)")
        st.write("Use this tool when you are finished testing and ready to launch Episode 1. Resetting clears all test predictions, weekly scores, breakdown logs, published broadcast actuals, player PINs, and widget selections.")
        
        if st.session_state.get("reset_banner"):
            st.success("🎉 All league data, predictions, player scores, and submitted ballots have been completely reset to zero! The league is fresh and ready for Episode 1.")
            st.session_state.reset_banner = False

        confirm_reset = st.checkbox("I confirm I want to wipe all test predictions, weekly scores, and published results for all participants.", key="chk_confirm_season_reset")
        if st.button("🧹 Reset All League Data To Zero", type="primary"):
            if not confirm_reset:
                st.error("⚠️ Please check the confirmation box above before resetting!")
            else:
                # 1. Build clean default roster
                clean_members = {
                    "AI Brian": {
                        "avatar": "🤖",
                        "weekly_picks": {},
                        "season_picks": {},
                        "total_score": 0,
                        "weekly_breakdown": {},
                        "pin": None
                    }
                }
                for p_name in DEFAULT_ROSTER:
                    clean_members[p_name] = {
                        "avatar": None,
                        "weekly_picks": {},
                        "season_picks": {},
                        "total_score": 0,
                        "weekly_breakdown": {},
                        "pin": None
                    }
                
                # Check for AI Brian custom avatar
                b_av = load_ai_brian_avatar()
                if b_av is not None:
                    clean_members["AI Brian"]["avatar"] = b_av
                
                # 2. Save clean payload directly to league_data.json
                save_league_data(clean_members, {}, {})
                
                # 3. Clear all widget keys from session state so selectboxes/form inputs don't retain old selections
                keys_to_clear = [k for k in list(st.session_state.keys()) if k != "admin_authenticated"]
                for k in keys_to_clear:
                    del st.session_state[k]
                
                # 4. Re-assign clean session state variables
                st.session_state.league_members = clean_members
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                st.session_state.current_week = 1
                st.session_state.authenticated_players = {}
                st.session_state.reset_banner = True
                
                st.rerun()
