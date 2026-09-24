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

# Custom Styling for a beautiful, cozy baking theme (Adaptive for Light & Dark Mode)
st.markdown("""
<style>
    .reportview-container {
        background: #FFF9F2;
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
        background-color: rgba(255, 243, 224, 0.2);
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

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
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
        if (predictions.get("in_line_sb") in actuals.get("in_line_sb", [])) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2
        if (predictions.get("in_trouble") in actuals.get("in_trouble", [])) and (predictions.get("in_trouble") != actuals.get("eliminated")):
            score += 2
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return 0
        
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    
    # 1. Season Winner (40 points) or finalist consolation (15 points)
    pred_winner = predictions.get("winner")
    if pred_winner == act_winner:
        score += 40
    elif pred_winner in actuals.get("finalists", act_semis):
        score += 15  # Consolation for predicted winner reaching finale
        
    # 2. Semifinalists (10 points each for other 3)
    pred_semis = predictions.get("semifinalists", [])
    for b in pred_semis:
        if b != pred_winner and b in act_semis:
            score += 10
            
    # 3. Hollywood Handshakes (Spot-on = 20 pts, +/- 1 = 10 pts)
    pred_hs = predictions.get("handshakes", 0)
    act_hs = actuals.get("handshakes", 0)
    diff_hs = abs(pred_hs - act_hs)
    if diff_hs == 0:
        score += 20
    elif diff_hs <= 1:
        score += 10
        
    # 4. Crying Events (Spot-on = 20 pts, +/- 5 = 10 pts)
    pred_cry = predictions.get("crying", 0)
    act_cry = actuals.get("crying", 0)
    diff_cry = abs(pred_cry - act_cry)
    if diff_cry == 0:
        score += 20
    elif diff_cry <= 5:
        score += 10
        
    # 5. Sexual Innuendos (Spot-on = 20 pts, +/- 5 = 10 pts)
    pred_inn = predictions.get("innuendos", 0)
    act_inn = actuals.get("innuendos", 0)
    diff_inn = abs(pred_inn - act_inn)
    if diff_inn == 0:
        score += 20
    elif diff_inn <= 5:
        score += 10
        
    return score


# --- 3. CONSTANTS & UTILITIES ---
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
                return payload.get("league_members", {}), payload.get("weekly_results", {}), payload.get("season_results", {})
        except Exception:
            pass
    return None, None, None


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


def load_ai_brian_avatar():
    """Smart image loader for AI Brian's avatar (prioritizes assets/aibrian.jpg)."""
    priority_paths = [
        "assets/aibrian.jpg", "assets/aibrian.JPG", "assets/aibrian.jpeg", "assets/aibrian.PNG",
        "assets/ai_brian.jpg", "assets/AIBrian.jpg", "aibrian.jpg"
    ]
    for p in priority_paths:
        if os.path.exists(p):
            try:
                return Image.open(p)
            except Exception:
                pass
    return None


def load_logo_image():
    """Smart image loader for header logo (prioritizes normanbeaver.jpg)."""
    priority_paths = [
        "assets/normanbeaver.jpg", "assets/normanbeaver.JPG", "assets/normanbeaver.jpeg", "assets/normanbeaver.png",
        "assets/norman_beaver.jpg", "assets/NormanBeaver.jpg", "normanbeaver.jpg",
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


def apply_elimination_overlay(img):
    """Applies semi-transparent red shading and bold red 'X' over an eliminated baker photo."""
    try:
        canvas = img.convert('RGBA')
        w, h = canvas.size
        
        red_tint = Image.new('RGBA', (w, h), (220, 30, 30, 95))
        tinted = Image.alpha_composite(canvas, red_tint)
        
        draw = ImageDraw.Draw(tinted)
        stroke_w = max(5, int(min(w, h) / 10))
        outline_w = stroke_w + 3
        
        draw.line([(0, 0), (w, h)], fill=(40, 0, 0, 200), width=outline_w)
        draw.line([(0, h), (w, 0)], fill=(40, 0, 0, 200), width=outline_w)
        
        draw.line([(0, 0), (w, h)], fill=(230, 20, 20, 240), width=stroke_w)
        draw.line([(0, h), (w, 0)], fill=(230, 20, 20, 240), width=stroke_w)
        
        return tinted
    except Exception:
        return img


def get_current_eliminated_bakers(week_num):
    """Get list of eliminated bakers dynamically driven strictly by admin broadcast results."""
    elim = []
    if "weekly_results" in st.session_state:
        for w in sorted(st.session_state.weekly_results.keys()):
            if w <= week_num:
                res = st.session_state.weekly_results[w]
                act_el = res.get("eliminated")
                if isinstance(act_el, list):
                    for b in act_el:
                        if b and b != "None" and b not in elim:
                            elim.append(b)
                elif isinstance(act_el, str) and act_el and act_el != "None":
                    if act_el not in elim:
                        elim.append(act_el)
    return elim


# Check for AI Brian avatar
brian_avatar_img = load_ai_brian_avatar()
if brian_avatar_img is not None and "AI Brian" in st.session_state.league_members:
    st.session_state.league_members["AI Brian"]["avatar"] = brian_avatar_img


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
            eliminated = random.sample(elim_pool, 2) if len(elim_pool) >= 2 else random.sample(active_bakers, min(2, len(active_bakers)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
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
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}
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

if "AI Brian" in st.session_state.league_members and not st.session_state.league_members["AI Brian"].get("season_picks"):
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()


# --- 5. APP INTERFACE LAYOUT & HEADER ---
logo_img = load_logo_image()
if logo_img is not None:
    col_logo, col_title = st.columns([1, 7], vertical_alignment="center")
    with col_logo:
        st.image(logo_img, width=90)
    with col_title:
        st.title("Great British Baking Show Fantasy League 2026")
else:
    st.title("🧁 Great British Baking Show Fantasy League 2026")


# --- SIDEBAR: PLAYER PROFILE, AVATAR UPLOAD & PERSISTENT POINTS REMINDER ---
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
    st.markdown("""
        <div class='status-box'>
            <h4>💡 Scoring Reminder</h4>
            <p>Predicting <strong>Star Baker</strong> or <strong>Eliminated Baker</strong> earns <strong>5 pts</strong>. Predicting <strong>In Line</strong> or <strong>In Trouble</strong> consolations earns <strong>2 pts</strong>!</p>
        </div>
    """, unsafe_allow_html=True)


# --- MAIN TABS ---
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
    with col_hr:
        st.markdown("**Rank**")
    with col_ha:
        st.markdown("**Avatar**")
    with col_hp:
        st.markdown("**Player Name**")
    with col_hs:
        st.markdown("**Total Points**")
    st.markdown("<hr style='margin: 4px 0 12px 0; border-top: 2px solid #D36B5F;'>", unsafe_allow_html=True)

    for rank, (member_name, data) in enumerate(sorted_members, 1):
        col_r, col_a, col_p, col_s = st.columns([1, 1.2, 5, 2])
        
        rank_badge = f"#{rank}"
        if rank == 1: rank_badge = "🥇 1st"
        elif rank == 2: rank_badge = "🥈 2nd"
        elif rank == 3: rank_badge = "🥉 3rd"

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
        st.subheader(f"📊 {selected_player}'s Performance Summary")
        st.markdown(f"**Total Combined Score:** `{p_data['total_score']} pts`")
        
        w_breakdown = p_data.get("weekly_breakdown", {})
        if w_breakdown:
            st.markdown("#### 📅 Weekly Episodic Scorecards")
            for w_num in sorted(w_breakdown.keys()):
                pred_w = p_data["weekly_picks"].get(w_num, {})
                act_w = st.session_state.weekly_results.get(w_num, {})
                raw_pts = calculate_weekly_score(pred_w, act_w, w_num)
                
                # Check for Star Member bonus
                all_weekly_raws = {m: calculate_weekly_score(m_d["weekly_picks"].get(w_num, {}), act_w, w_num) for m, m_d in st.session_state.league_members.items()}
                max_r = max(all_weekly_raws.values()) if all_weekly_raws else 0
                has_star_bonus = (raw_pts == max_r and raw_pts > 0)
                
                with st.expander(f"Week {w_num} Breakdown ({p_data['weekly_breakdown'].get(w_num, 0)} pts awarded)"):
                    st.markdown(f"**Episodic Raw Score:** `{raw_pts} pts`" + (f" | 🌟 **Star League Member Bonus:** `+5 pts` *(Highest weekly scorer!)*" if has_star_bonus else ""))
                    st.markdown(f"**Week {w_num} Total Awarded:** `{p_data['weekly_breakdown'].get(w_num, raw_pts + (5 if has_star_bonus else 0))} pts`")

        if p_data.get("season_picks"):
            st.markdown("#### 🌟 Season-Long Predictions")
            with st.expander("Inspect Season-Long Predictions"):
                sp = p_data["season_picks"]
                st.write(f"- **Predicted Season Champion:** {sp.get('winner', 'None')}")
                st.write(f"- **Predicted Semifinalists:** {', '.join(sp.get('semifinalists', []))}")
                st.write(f"- **Predicted Handshakes Total:** `{sp.get('handshakes', 0)}`")
                st.write(f"- **Predicted Crying Total:** `{sp.get('crying', 0)}`")
                st.write(f"- **Predicted Innuendos Total:** `{sp.get('innuendos', 0)}`")
                st.markdown(f"**Season Projections Points Earned:** `{p_data.get('season_score', 0)} pts`")


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Prediction Ballot Portal")
    st.write("Submit or update your predictions for the upcoming week and lock in your season-long projections!")

    active_roster = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    active_sub_player = st.selectbox("Select Your Profile:", ["-- Select Your Name --"] + active_roster)
    
    if active_sub_player != "-- Select Your Name --":
        p_pin = st.session_state.league_members[active_sub_player].get("pin")
        is_authed = st.session_state.authenticated_players.get(active_sub_player, False)
        
        if p_pin is None:
            st.info(f"🔑 **Security PIN Setup for {active_sub_player}**")
            st.write("Please set a 4-digit PIN to protect your prediction ballot.")
            with st.form(f"pin_setup_form_{active_sub_player}"):
                new_pin = st.text_input("Create 4-Digit PIN", type="password", max_chars=4)
                confirm_pin = st.text_input("Confirm 4-Digit PIN", type="password", max_chars=4)
                set_pin_btn = st.form_submit_button("Set My Security PIN")
                if set_pin_btn:
                    if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                        st.session_state.league_members[active_sub_player]["pin"] = new_pin
                        st.session_state.authenticated_players[active_sub_player] = True
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success("Security PIN successfully set! Unlocking ballot...")
                        st.rerun()
                    else:
                        st.error("PINs must match and be exactly 4 digits.")
        elif not is_authed:
            st.warning(f"🔒 **Ballot Locked for {active_sub_player}**")
            with st.form(f"pin_verify_form_{active_sub_player}"):
                verify_pin = st.text_input("Enter Your 4-Digit Security PIN", type="password", max_chars=4)
                verify_btn = st.form_submit_button("Unlock Ballot")
                if verify_btn:
                    if verify_pin == p_pin:
                        st.session_state.authenticated_players[active_sub_player] = True
                        st.success("PIN verified! Accessing ballot...")
                        st.rerun()
                    else:
                        st.error("Incorrect PIN. Please try again.")
        else:
            st.success(f"🔓 **Authenticated as {active_sub_player}**")
            
            # --- SEASON-LONG PREDICTIONS PORTAL ---
            with st.expander("🌟 Season-Long Projections (Locked Pre-Week 2)", expanded=(st.session_state.current_week == 1)):
                existing_season = st.session_state.league_members[active_sub_player].get("season_picks", {})
                if existing_season and st.session_state.current_week > 1:
                    st.info("🔒 Season-long predictions locked pre-Week 2.")
                    st.write(f"- **Predicted Winner:** {existing_season.get('winner')}")
                    st.write(f"- **Predicted Semifinalists:** {', '.join(existing_season.get('semifinalists', []))}")
                    st.write(f"- **Handshakes Total:** `{existing_season.get('handshakes', 0)}`")
                    st.write(f"- **Crying Total:** `{existing_season.get('crying', 0)}`")
                    st.write(f"- **Innuendos Total:** `{existing_season.get('innuendos', 0)}`")
                else:
                    with st.form(f"season_form_{active_sub_player}"):
                        st.subheader("Predict Full Season Milestones")
                        def_win = existing_season.get("winner", ALL_BAKERS[0])
                        win_idx = ALL_BAKERS.index(def_win) if def_win in ALL_BAKERS else 0
                        
                        user_winner = st.selectbox("Predict Season Champion [40 pts]", ALL_BAKERS, index=win_idx)
                        rem_bakers = [b for b in ALL_BAKERS if b != user_winner]
                        def_semis = existing_season.get("semifinalists", rem_bakers[:3])
                        user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", rem_bakers, default=[b for b in def_semis if b in rem_bakers][:3], max_selections=3)
                        
                        user_hs = st.number_input("Predict Total Hollywood Handshakes across Season", min_value=0, value=existing_season.get("handshakes", 5))
                        user_cry = st.number_input("Predict Total Crying Incidents across Season", min_value=0, value=existing_season.get("crying", 12))
                        user_inn = st.number_input("Predict Total Sexual Innuendos across Season", min_value=0, value=existing_season.get("innuendos", 45))
                        
                        save_season_btn = st.form_submit_button("Save Season-Long Projections")
                        if save_season_btn:
                            st.session_state.league_members[active_sub_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_hs,
                                "crying": user_cry,
                                "innuendos": user_inn
                            }
                            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                            st.success("Season projections saved!")
                            st.rerun()

            # --- WEEKLY EPISODIC BALLOT ---
            st.markdown("---")
            current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            
            with st.form(f"weekly_form_{active_sub_player}_w{st.session_state.current_week}"):
                st.subheader(f"Week {st.session_state.current_week} Episodic Ballot")
                existing_w = st.session_state.league_members[active_sub_player].get("weekly_picks", {}).get(st.session_state.current_week, {})
                weekly_picks = {}
                
                if st.session_state.current_week == 10:
                    def_champ = existing_w.get("show_champion", active_bakers[0])
                    champ_idx = active_bakers.index(def_champ) if def_champ in active_bakers else 0
                    weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", active_bakers, index=champ_idx)
                else:
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        def_sb = existing_w.get("star_baker", active_bakers[0])
                        sb_idx = active_bakers.index(def_sb) if def_sb in active_bakers else 0
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers, index=sb_idx)
                        
                        if st.session_state.current_week < 9:
                            def_inl = existing_w.get("in_line_sb", active_bakers[1] if len(active_bakers)>1 else active_bakers[0])
                            inl_idx = active_bakers.index(def_inl) if def_inl in active_bakers else 0
                            weekly_picks["in_line_sb"] = st.selectbox("Predict 'In Line' Nominee [2 pts]", active_bakers, index=inl_idx)
                            
                    with col_b2:
                        def_el = existing_w.get("eliminated", active_bakers[-1])
                        if isinstance(def_el, list): def_el = def_el[0]
                        el_idx = active_bakers.index(def_el) if def_el in active_bakers else 0
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers, index=el_idx)
                        
                        if st.session_state.current_week < 9:
                            def_trb = existing_w.get("in_trouble", active_bakers[-2] if len(active_bakers)>1 else active_bakers[0])
                            trb_idx = active_bakers.index(def_trb) if def_trb in active_bakers else 0
                            weekly_picks["in_trouble"] = st.selectbox("Predict 'In Trouble' Nominee [2 pts]", active_bakers, index=trb_idx)

                # Technical Challenge Section
                st.markdown("---")
                if st.session_state.current_week >= 8:
                    st.write(f"Predict Technical Challenge Rankings (1st through {len(active_bakers)}th Place):")
                    ex_tr = existing_w.get("tech_rank", [])
                    user_tr = []
                    for r_i in range(len(active_bakers)):
                        def_b = ex_tr[r_i] if r_i < len(ex_tr) and ex_tr[r_i] in active_bakers else active_bakers[r_i]
                        b_i = active_bakers.index(def_b)
                        sel_b = st.selectbox(f"Technical #{r_i+1} Place", active_bakers, index=b_i, key=f"user_tech_w{st.session_state.current_week}_r{r_i+1}")
                        user_tr.append(sel_b)
                    weekly_picks["tech_rank"] = user_tr
                else:
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.write("Predict Top 3 Technical Finishers:")
                        ex_t3 = existing_w.get("tech_top_3", active_bakers[:3])
                        t3_def = [b for b in ex_t3 if b in active_bakers]
                        if len(t3_def) < 3: t3_def = active_bakers[:3]
                        weekly_picks["tech_top_3"] = st.multiselect("Top 3 (1st, 2nd, 3rd)", active_bakers, default=t3_def[:3], max_selections=3)
                    with col_t2:
                        st.write("Predict Bottom 3 Technical Finishers:")
                        ex_b3 = existing_w.get("tech_bottom_3", active_bakers[-3:])
                        b3_def = [b for b in ex_b3 if b in active_bakers]
                        if len(b3_def) < 3: b3_def = active_bakers[-3:]
                        weekly_picks["tech_bottom_3"] = st.multiselect("Bottom 3 (3rd-last, 2nd-last, Last)", active_bakers, default=b3_def[:3], max_selections=3)

                save_weekly_btn = st.form_submit_button(f"Submit Week {st.session_state.current_week} Predictions")
                if save_weekly_btn:
                    if "weekly_picks" not in st.session_state.league_members[active_sub_player]:
                        st.session_state.league_members[active_sub_player]["weekly_picks"] = {}
                    st.session_state.league_members[active_sub_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                    
                    # Generate AI Brian's picks
                    if "AI Brian" in st.session_state.league_members:
                        ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                        
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Week {st.session_state.current_week} prediction ballot saved!")
                    st.rerun()


# --- TAB 3: BAKER ANALYTICS ---
with tab_analytics:
    st.header("📈 Baker Performance Analytics")
    st.write("Inspect technical trajectory trends, star baker counts, and broadcast accolades for all 12 bakers!")
    
    all_weeks = sorted(list(st.session_state.weekly_results.keys()))
    
    baker_stats = {b: {
        "star_baker_cnt": 0,
        "in_line_cnt": 0,
        "in_trouble_cnt": 0,
        "handshake_cnt": 0,
        "tech_ranks": [],
        "tech_rank_pcts": []
    } for b in ALL_BAKERS}
    
    for w in all_weeks:
        res = st.session_state.weekly_results[w]
        sb = res.get("star_baker")
        if sb and sb in baker_stats:
            baker_stats[sb]["star_baker_cnt"] += 1
            
        for inl in res.get("in_line_sb", []):
            if inl in baker_stats: baker_stats[inl]["in_line_cnt"] += 1
            
        for trb in res.get("in_trouble", []):
            if trb in baker_stats: baker_stats[trb]["in_trouble_cnt"] += 1
            
        for hs in res.get("handshake_bakers", []):
            if hs in baker_stats: baker_stats[hs]["handshake_cnt"] += 1
            
        tr = res.get("tech_rank", [])
        if tr:
            num_b = len(tr)
            for pos_0, b_name in enumerate(tr):
                if b_name in baker_stats:
                    pos = pos_0 + 1
                    pct = round(((num_b - pos + 1) / num_b) * 100, 1) if num_b > 0 else 50.0
                    baker_stats[b_name]["tech_ranks"].append((w, pos))
                    baker_stats[b_name]["tech_rank_pcts"].append(pct)

    current_eliminated_latest = get_current_eliminated_bakers(10)
    
    # A. Baker Comparison Matrix
    with st.expander("📊 Baker Performance Matrix Summary", expanded=True):
        matrix_rows = []
        for b_name in ALL_BAKERS:
            s = baker_stats[b_name]
            is_elim = b_name in current_eliminated_latest
            avg_fin = round(sum(pos for _, pos in s["tech_ranks"]) / len(s["tech_ranks"]), 1) if s["tech_ranks"] else "N/A"
            avg_pct = round(sum(s["tech_rank_pcts"]) / len(s["tech_rank_pcts"]), 1) if s["tech_rank_pcts"] else "N/A"
            
            matrix_rows.append({
                "Baker": b_name,
                "Status": "❌ Eliminated" if is_elim else "🟢 Active",
                "Avg Tech Rank %": f"{avg_pct}%" if avg_pct != "N/A" else "N/A",
                "Avg Tech Finish": f"#{avg_fin}" if avg_fin != "N/A" else "N/A",
                "Star Bakers 🌟": s["star_baker_cnt"],
                "In Line 📈": s["in_line_cnt"],
                "In Trouble ⚠️": s["in_trouble_cnt"],
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
                st.image(disp_img, caption=f"{selected_ana_baker} (Eliminated)", use_column_width=True)
            else:
                st.image(b_img_orig, caption=f"{selected_ana_baker} (Active)", use_column_width=True)
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

    # C. Official Chaos Log
    st.markdown("---")
    with st.expander("📝 Official Broadcast Timestamps & Descriptions Log", expanded=False):
        st.write("Review the Admin's published notes and timestamps for key episode events:")
        if all_weeks:
            for w in all_weeks:
                res = st.session_state.weekly_results[w]
                st.markdown(f"#### 📍 Week {w} Broadcast Log")
                hs_stamps = res.get("handshake_timestamps", "")
                cry_stamps = res.get("crying_timestamps", "")
                inn_cnt = res.get("innuendo_count", 0)
                inn_stamps = res.get("innuendo_timestamps", "")
                
                st.markdown(f"- **🤝 Handshakes:** {hs_stamps if hs_stamps else 'None recorded'}")
                st.markdown(f"- **😢 Crying Scenes:** {cry_stamps if cry_stamps else 'None recorded'}")
                st.markdown(f"- **💬 Sexual Innuendos Count:** `{inn_cnt}` " + (f"({inn_stamps})" if inn_stamps else ""))
                st.markdown("<hr style='margin: 4px 0;'>", unsafe_allow_html=True)
        else:
            st.info("No broadcast results published yet.")


# --- TAB 4: ADMIN PANEL (PIN PROTECTED) ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Lock Screen**")
        st.write("This section is restricted to the League Administrator. Please enter your Admin PIN to unlock broadcast input controls.")
        
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
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Security PIN reset for {p_to_reset}! They can now set a new 4-digit PIN when they select their profile.")
                    st.rerun()

        st.markdown("---")
        st.write("Use this form to input actual broadcast results. Publishing results will score all player predictions and update the live leaderboard!")
        
        current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
            actuals = {}
            
            if st.session_state.current_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers)
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", active_bakers, key="act_w10_winner")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, default=active_bakers if len(active_bakers)<=4 else active_bakers[:4], key="act_w10_semis")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, default=active_bakers if len(active_bakers)<=3 else active_bakers[:3], key="act_w10_finalists")
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
                actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers)
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", [b for b in active_bakers if b != actuals.get("star_baker")])
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                    st.info("No baker was eliminated this week. Consolation and other categories are still scored normally.")
                else:
                    act_elim_1 = st.selectbox("Actual Eliminated Baker #1", [b for b in active_bakers if b != actuals.get("star_baker")], key="admin_act_elim_1_w9")
                    act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b not in [actuals.get("star_baker"), act_elim_1]], key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [act_elim_1, act_elim_2]

            else:
                # Standard Weeks 1-8
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", active_bakers)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line for Star Baker' Nominees", [b for b in active_bakers if b != actuals.get("star_baker")])
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{st.session_state.current_week}")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", active_bakers)
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble of Elimination' Nominees", [b for b in active_bakers if b != actuals.get("eliminated")])
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("No baker was eliminated this week. Predicting elimination scores 0.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble of Elimination' Nominees (Sickness consolations)", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key=f"admin_act_elim_1_w{st.session_state.current_week}")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key=f"admin_act_elim_2_w{st.session_state.current_week}")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble of Elimination' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])
                    
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
                        
                    # Score each week that has results
                    all_weeks_scored = sorted(list(st.session_state.weekly_results.keys()))
                    
                    for w in all_weeks_scored:
                        act_w = st.session_state.weekly_results[w]
                        
                        weekly_raw = {}
                        for m_name, m_data in st.session_state.league_members.items():
                            pred_w = m_data["weekly_picks"].get(w, {})
                            raw_score = calculate_weekly_score(pred_w, act_w, w)
                            weekly_raw[m_name] = raw_score
                            m_data["weekly_breakdown"][w] = raw_score
                            
                        # Weekly Star Member Bonus (+5 points) to the weekly high scorer
                        if weekly_raw:
                            max_raw = max(weekly_raw.values())
                            for m_name, raw_s in weekly_raw.items():
                                if raw_s == max_raw and raw_s > 0:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                    
                    # Score Season-Long projections if Week 10 has results
                    if st.session_state.season_results:
                        for m_name, m_data in st.session_state.league_members.items():
                            season_pred = m_data["season_picks"]
                            season_score = calculate_season_score(season_pred, st.session_state.season_results)
                            m_data["season_score"] = season_score
                            
                    # Recompile total scores
                    for m_name, m_data in st.session_state.league_members.items():
                        weekly_total = sum(m_data["weekly_breakdown"].values())
                        season_total = m_data.get("season_score", 0)
                        m_data["total_score"] = weekly_total + season_total
                        
                    st.success("Leaderboard updated! All player predictions scored and verified against official rule constraints.")

        # --- COMMISSIONER DATA RESET PORTAL ---
        st.markdown("---")
        with st.expander("🧹 Reset Season Data (Post-Testing Wipe)", expanded=False):
            st.warning("⚠️ **Danger Zone: Reset League Predictions & Scores**")
            st.write("Use this tool after completing test submissions to wipe all player predictions, scores, and broadcast actuals so the league starts clean at 0 points for Episode 1.")
            
            confirm_reset = st.checkbox("I confirm I want to wipe all predictions and reset all player scores to zero.", key="admin_confirm_reset_data")
            
            if st.button("🧹 Reset All League Data To Zero", key="admin_reset_data_btn"):
                if confirm_reset:
                    # Reset all player scores, breakdowns, and predictions
                    for m_name in st.session_state.league_members:
                        st.session_state.league_members[m_name]["total_score"] = 0
                        st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                        st.session_state.league_members[m_name]["weekly_picks"] = {}
                        st.session_state.league_members[m_name]["season_picks"] = {}
                        st.session_state.league_members[m_name]["season_score"] = 0
                        
                    # Regenerate AI Brian's initial clean season picks
                    if "AI Brian" in st.session_state.league_members:
                        st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()
                        
                    # Wipe broadcast results and disputes
                    st.session_state.weekly_results = {}
                    st.session_state.season_results = {}
                    st.session_state.disputes = []
                    
                    # Persist clean payload
                    save_league_data(st.session_state.league_members, {}, {})
                    
                    st.success("🎉 All predictions, weekly scores, and broadcast results have been reset to zero! The league is clean and ready for Episode 1.")
                    st.rerun()
                else:
                    st.error("Please check the confirmation box above before resetting league data.")
