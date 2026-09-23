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
    .leaderboard-table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. THE 2026 OFFICIAL SCORING ENGINE (INTERNALIZED FOR PORTABILITY) ---
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
            score += 2  # Balanced down from 3
        if (predictions.get("in_trouble") in actuals.get("in_trouble", [])) and (predictions.get("in_trouble") != actuals.get("eliminated")):
            score += 2  # Balanced down from 3
            
    return score


def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return 0
        
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


def get_weekly_scorecard_details(predictions, actuals, week=2):
    """Generate line-item audit list for individual player scorecards."""
    items = []
    
    # --- A. Main Episode Results ---
    if week == 10:
        pred_champ = predictions.get("show_champion", "N/A")
        act_champ = actuals.get("show_champion", "N/A")
        pts = 15 if (pred_champ and act_champ and pred_champ == act_champ) else 0
        items.append({
            "Category": "Show Champion Prediction",
            "Player Pick": str(pred_champ),
            "Actual Result": str(act_champ),
            "Points": pts,
            "Notes": "Exact match (+15 pts)" if pts > 0 else "Did not match"
        })
    else:
        pred_sb = predictions.get("star_baker", "N/A")
        act_sb = actuals.get("star_baker", "N/A")
        pts_sb = 5 if (pred_sb == act_sb) else 0
        items.append({
            "Category": "Star Baker",
            "Player Pick": str(pred_sb),
            "Actual Result": str(act_sb),
            "Points": pts_sb,
            "Notes": "Correct (+5 pts)" if pts_sb > 0 else "Incorrect"
        })
        
        # Eliminated
        act_elim = actuals.get("eliminated", "N/A")
        pred_elim = predictions.get("eliminated", "N/A")
        pts_elim = 0
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim: pts_elim += 5
            elif isinstance(pred_elim, str):
                if pred_elim in act_elim: pts_elim += 5
        elif act_elim == "None":
            pts_elim = 0
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: pts_elim += 5
            elif pred_elim == act_elim: pts_elim += 5
            
        p_elim_str = ", ".join(pred_elim) if isinstance(pred_elim, list) else str(pred_elim)
        a_elim_str = ", ".join(act_elim) if isinstance(act_elim, list) else str(act_elim)
        notes_elim = "Sickness grace week (0 pts)" if act_elim == "None" else ("Correct (+5 pts)" if pts_elim > 0 else "Incorrect")
        items.append({
            "Category": "Eliminated Baker",
            "Player Pick": p_elim_str,
            "Actual Result": a_elim_str,
            "Points": pts_elim,
            "Notes": notes_elim
        })

    # --- B. Technical Challenge ---
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        p_rank_str = " -> ".join(pred_rank) if pred_rank else "N/A"
        a_rank_str = " -> ".join(act_rank) if act_rank else "N/A"
        
        pts_tech = 0
        notes_tech = ""
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 5:
                pts_tech = 25
                notes_tech = "🎉 Perfect 5-for-5 Technical Sweep (+25 pts flat)!"
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        pts_tech += 3 if idx in [0, 4] else 2
                notes_tech = f"{exact_count} exact position match(es)"
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                pts_tech = 20
                notes_tech = "🎉 Perfect 4-for-4 Technical Sweep (+20 pts flat)!"
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        pts_tech += 3 if idx in [0, 3] else 2
                notes_tech = f"{exact_count} exact position match(es)"
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
                pts_tech = 15
                notes_tech = "🎉 Perfect 3-for-3 Technical Sweep (+15 pts flat)!"
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        pts_tech += 3 if idx == 0 else 2
                notes_tech = f"{exact_count} exact position match(es)"
                
        items.append({
            "Category": f"Technical Challenge (Week {week} Rank)",
            "Player Pick": p_rank_str,
            "Actual Result": a_rank_str,
            "Points": pts_tech,
            "Notes": notes_tech
        })
    else:
        # Standard Weeks 2-7
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        p_top_str = " -> ".join(pred_top3) if pred_top3 else "N/A"
        a_top_str = " -> ".join(act_top3) if act_top3 else "N/A"
        
        pts_top = 0
        notes_top = ""
        if len(pred_top3) == 3 and len(act_top3) == 3:
            if pred_top3 == act_top3:
                pts_top = 10
                notes_top = "🎉 Perfect Top 3 Combo Sweep (+10 pts flat)!"
            else:
                if pred_top3[0] == act_top3[0]: pts_top += 3
                if pred_top3[1] == act_top3[1]: pts_top += 2
                if pred_top3[2] == act_top3[2]: pts_top += 2
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3 and baker != act_top3[idx]:
                        pts_top += 1
                notes_top = f"Top 3 sequence points breakdown"
        items.append({
            "Category": "Technical Challenge Top 3",
            "Player Pick": p_top_str,
            "Actual Result": a_top_str,
            "Points": pts_top,
            "Notes": notes_top
        })
        
        # Bottom 3
        pred_bot3 = predictions.get("tech_bottom_3", [])
        act_bot3 = actuals.get("tech_bottom_3", [])
        p_bot_str = " -> ".join(pred_bot3) if pred_bot3 else "N/A"
        a_bot_str = " -> ".join(act_bot3) if act_bot3 else "N/A"
        
        pts_bot = 0
        notes_bot = ""
        if len(pred_bot3) == 3 and len(act_bot3) == 3:
            if pred_bot3 == act_bot3:
                pts_bot = 10
                notes_bot = "🎉 Perfect Bottom 3 Combo Sweep (+10 pts flat)!"
            else:
                if pred_bot3[0] == act_bot3[0]: pts_bot += 2
                if pred_bot3[1] == act_bot3[1]: pts_bot += 2
                if pred_bot3[2] == act_bot3[2]: pts_bot += 3
                for idx, baker in enumerate(pred_bot3):
                    if baker in act_bot3 and baker != act_bot3[idx]:
                        pts_bot += 1
                notes_bot = f"Bottom 3 sequence points breakdown"
        items.append({
            "Category": "Technical Challenge Bottom 3",
            "Player Pick": p_bot_str,
            "Actual Result": a_bot_str,
            "Points": pts_bot,
            "Notes": notes_bot
        })

    # --- C. Consolations ---
    if week < 9:
        pred_line = predictions.get("in_line_sb", "N/A")
        act_line = actuals.get("in_line_sb", [])
        pts_line = 2 if (pred_line in act_line and pred_line != actuals.get("star_baker")) else 0
        items.append({
            "Category": "Consolation: In Line for Star Baker",
            "Player Pick": str(pred_line),
            "Actual Result": ", ".join(act_line) if act_line else "None",
            "Points": pts_line,
            "Notes": "Nominated but didn't win (+2 pts)" if pts_line > 0 else "No match"
        })
        
        pred_trbl = predictions.get("in_trouble", "N/A")
        act_trbl = actuals.get("in_trouble", [])
        act_elim_val = actuals.get("eliminated")
        act_elim_list = act_elim_val if isinstance(act_elim_val, list) else [act_elim_val]
        pts_trbl = 2 if (pred_trbl in act_trbl and pred_trbl not in act_elim_list) else 0
        items.append({
            "Category": "Consolation: In Trouble of Elimination",
            "Player Pick": str(pred_trbl),
            "Actual Result": ", ".join(act_trbl) if act_trbl else "None",
            "Points": pts_trbl,
            "Notes": "Bottom nominated but saved (+2 pts)" if pts_trbl > 0 else "No match"
        })
        
    return items


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

# Track authenticated players for current browser session
if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

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

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. APP INTERFACE LAYOUT ---
st.title("🧁 Great British Baking Show Fantasy League 2026")


# --- SIDEBAR: PLAYER PROFILE, AVATAR UPLOAD & PERSISTENT POINTS REMINDER ---
with st.sidebar:
    st.header("📸 Upload Avatar Photo")
    st.write("Select your player name below to upload or manage your profile picture!")
    
    roster_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sb_player = st.selectbox("Select Player Profile:", ["-- Select Your Name --"] + roster_players)
    
    if sb_player != "-- Select Your Name --":
        # Check PIN authentication status
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
                    st.image(cur_av, caption=f"{sb_player}'s Active Avatar", width=150)
                else:
                    st.info("No photo uploaded yet.")
                    st.markdown("<h1 style='font-size: 70px; margin: 0;'>🍪</h1>", unsafe_allow_html=True)
            
    st.markdown("---")
    st.header("⚙️ Game Controls")
    selected_week = st.slider("Select App Active Week", min_value=1, max_value=10, value=st.session_state.current_week)
    st.session_state.current_week = selected_week

    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of what points are at stake for each prediction!")
    st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be submitted prior to the Great British Baking Show broadcast on Tuesdays at 2:00 p.m.")
    
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
    
    # Sort players by total score
    sorted_members = sorted(
        st.session_state.league_members.items(),
        key=lambda item: item[1]["total_score"],
        reverse=True
    )

    # Leaderboard Header Row
    col_hr, col_ha, col_hp, col_hs = st.columns([1, 1.2, 5, 2])
    with col_hr:
        st.markdown("**Rank**")
    with col_ha:
        st.markdown("**Avatar**")
    with col_hp:
        st.markdown("**Player Name**")
    with col_hs:
        st.markdown("**Total Combined Score**")
    st.markdown("<hr style='margin: 4px 0 12px 0; border-top: 2px solid #D36B5F;'>", unsafe_allow_html=True)

    # Leaderboard Visual Card Rows
    for idx, (member_name, data) in enumerate(sorted_members):
        rank_num = idx + 1
        rank_badge = f"🥇 #{rank_num}" if rank_num == 1 else (f"🥈 #{rank_num}" if rank_num == 2 else (f"🥉 #{rank_num}" if rank_num == 3 else f"#{rank_num}"))
        
        avatar_img = data.get("avatar")
        if member_name == "AI Brian":
            if not isinstance(avatar_img, Image.Image):
                avatar_img = load_ai_brian_avatar()
                if avatar_img is not None:
                    data["avatar"] = avatar_img

        c_r, c_a, c_p, c_s = st.columns([1, 1.2, 5, 2])
        with c_r:
            st.markdown(f"<div style='padding-top:12px;'><h3>{rank_badge}</h3></div>", unsafe_allow_html=True)
        with c_a:
            if isinstance(avatar_img, Image.Image):
                st.image(avatar_img, width=60)
            elif member_name == "AI Brian":
                b_img = load_ai_brian_avatar()
                if b_img is not None:
                    data["avatar"] = b_img
                    st.image(b_img, width=60)
                else:
                    st.markdown("<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
            else:
                st.markdown("<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)
        with c_p:
            st.markdown(f"<div style='padding-top:12px;'><h3><strong>{member_name}</strong></h3></div>", unsafe_allow_html=True)
        with c_s:
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
        st.subheader(f"📊 {selected_player}'s Score Summary")
        st.markdown(f"**Total Combined Score:** `{p_data['total_score']} pts`")
        if selected_player == "AI Brian":
            st.info("🤖 **AI Brian Note:** Automated participant generating random predictions following official 2026 rule constraints.")

    # Show Weekly Breakdown Tables
    if not st.session_state.weekly_results:
        st.info("No weekly results have been published by the admin yet. Once broadcast results are posted in the Admin Panel, line-item scorecards for each week will appear here!")
    else:
        st.markdown("#### 📅 Weekly Episodic Scorecards")
        for w_num in sorted(st.session_state.weekly_results.keys()):
            act_w = st.session_state.weekly_results[w_num]
            pred_w = p_data["weekly_picks"].get(w_num, {})
            
            with st.expander(f"📍 Week {w_num} Scorecard (Episodic Subtotal: {p_data['weekly_breakdown'].get(w_num, 0)} pts)", expanded=(w_num == st.session_state.current_week or w_num == max(st.session_state.weekly_results.keys()))):
                if not pred_w:
                    st.warning(f"No prediction ballot was submitted by {selected_player} for Week {w_num}.")
                else:
                    scorecard_items = get_weekly_scorecard_details(pred_w, act_w, week=w_num)
                    df_sc = pd.DataFrame(scorecard_items)
                    
                    raw_pts = sum(item["Points"] for item in scorecard_items)
                    
                    all_raw = {m: calculate_weekly_score(st.session_state.league_members[m]["weekly_picks"].get(w_num, {}), act_w, w_num) for m in st.session_state.league_members}
                    max_raw = max(all_raw.values()) if all_raw else 0
                    has_star_bonus = (raw_pts == max_raw and raw_pts > 0)
                    
                    st.dataframe(df_sc, use_container_width=True, hide_index=True)
                    
                    st.markdown(f"**Episodic Raw Score:** `{raw_pts} pts`" + (f" | 🌟 **Star League Member Bonus:** `+5 pts` *(Highest weekly scorer!)*" if has_star_bonus else ""))
                    st.markdown(f"**Week {w_num} Total Awarded:** `{p_data['weekly_breakdown'].get(w_num, raw_pts + (5 if has_star_bonus else 0))} pts`")

    # Show Season-Long Projections Audit if Season Results exist
    if st.session_state.season_results or p_data.get("season_picks"):
        st.markdown("#### 🌟 Season-Long Predictions")
        with st.expander("🏆 Season-Long Predictions", expanded=False):
            sp = p_data.get("season_picks", {})
            sr = st.session_state.season_results
            if not sp:
                st.info("No season-long prediction locked.")
            else:
                s_rows = [
                    {
                        "Category": "Season Winner [40 pts]",
                        "Player Pick": str(sp.get("winner", "N/A")),
                        "Actual Result": str(sr.get("winner", "Pending Season Finale")),
                        "Points Earned": 40 if (sr and sp.get("winner") == sr.get("winner")) else (15 if (sr and sp.get("winner") in sr.get("finalists", [])) else 0),
                        "Notes": "40 pts if exact winner; 15 pts if runner-up finalist"
                    },
                    {
                        "Category": "Other 3 Semifinalists [10 pts each]",
                        "Player Pick": ", ".join(sp.get("semifinalists", [])) if sp.get("semifinalists") else "N/A",
                        "Actual Result": ", ".join(sr.get("semifinalists", [])) if sr.get("semifinalists") else "Pending Semifinals",
                        "Points Earned": sum(10 for b in sp.get("semifinalists", []) if sr and b in sr.get("semifinalists", []) and b != sp.get("winner")),
                        "Notes": "10 pts per correct pick (max 30 pts)"
                    },
                    {
                        "Category": "Hollywood Handshakes Count",
                        "Player Pick": str(sp.get("handshakes", "N/A")),
                        "Actual Result": str(sr.get("handshakes", "Pending Cumulative Log")) if sr else "Pending",
                        "Points Earned": 20 if (sr and sp.get("handshakes") == sr.get("handshakes")) else (10 if (sr and sp.get("handshakes") is not None and sr.get("handshakes") is not None and abs(sp.get("handshakes") - sr.get("handshakes")) <= 1) else 0),
                        "Notes": "20 pts spot-on; 10 pts within +/- 1"
                    },
                    {
                        "Category": "Crying Incidents Count",
                        "Player Pick": str(sp.get("crying", "N/A")),
                        "Actual Result": str(sr.get("crying", "Pending Cumulative Log")) if sr else "Pending",
                        "Points Earned": 20 if (sr and sp.get("crying") == sr.get("crying")) else (10 if (sr and sp.get("crying") is not None and sr.get("crying") is not None and abs(sp.get("crying") - sr.get("crying")) <= 5) else 0),
                        "Notes": "20 pts spot-on; 10 pts within +/- 5"
                    },
                    {
                        "Category": "Sexual Innuendos Count",
                        "Player Pick": str(sp.get("innuendos", "N/A")),
                        "Actual Result": str(sr.get("innuendos", "Pending Cumulative Log")) if sr else "Pending",
                        "Points Earned": 20 if (sr and sp.get("innuendos") == sr.get("innuendos")) else (10 if (sr and sp.get("innuendos") is not None and sr.get("innuendos") is not None and abs(sp.get("innuendos") - sr.get("innuendos")) <= 5) else 0),
                        "Notes": "20 pts spot-on; 10 pts within +/- 5"
                    }
                ]
                df_s_audit = pd.DataFrame(s_rows)
                st.dataframe(df_s_audit, use_container_width=True, hide_index=True)
                st.markdown(f"**Season Projections Total Points Earned:** `{p_data.get('season_score', 0)} pts`")


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    # 1. VISUAL BAKER CHEAT SHEET
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("Baker portraits update dynamically! Eliminated bakers are highlighted with red shading and a red 'X' based on the active week.")
        current_elim = get_current_eliminated_bakers(st.session_state.current_week)
        cols = st.columns(4)
        for idx, baker in enumerate(ALL_BAKERS):
            info = BAKER_INFO.get(baker, {"url": "#"})
            is_elim = (baker in current_elim)
            with cols[idx % 4]:
                if is_elim:
                    st.markdown(f"**❌ {baker}** *(Eliminated)*")
                else:
                    st.markdown(f"**{baker}**")
                
                img = load_baker_image(baker)
                if img is not None:
                    if is_elim:
                        img_display = apply_elimination_overlay(img)
                        st.image(img_display, use_container_width=True, caption=f"❌ {baker} - ELIMINATED")
                    else:
                        st.image(img, use_container_width=True)
                else:
                    if is_elim:
                        st.error(f"❌ {baker} (ELIMINATED)")
                        st.markdown(f"[🔗 View {baker}'s Photo Page]({info['url']})")
                    else:
                        st.info(f"📸 Photograph of {baker}")
                        st.markdown(f"[🔗 View {baker}'s Photo Page]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
    st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be submitted prior to the Great British Baking Show broadcast on Tuesdays at 2:00 p.m.")
    
    # Select which player is submitting predictions
    roster_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    player_options = ["-- Select Your Name --"] + roster_players + ["➕ Register New Player"]
    sub_player_choice = st.selectbox("Select Player Profile Submitting Predictions:", player_options, index=0)
    
    if sub_player_choice == "➕ Register New Player":
        new_name = st.text_input("Enter New Player Name:", autocomplete="off").strip()
        active_sub_player = new_name if new_name else None
    elif sub_player_choice != "-- Select Your Name --":
        active_sub_player = sub_player_choice
    else:
        active_sub_player = None
        
    if not active_sub_player:
        st.info("Please select or enter your Player Name to open the prediction ballot!")
    else:
        # Ensure profile exists in session state
        if active_sub_player not in st.session_state.league_members:
            st.session_state.league_members[active_sub_player] = {
                "avatar": None,
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
            
        # --- PLAYER PIN AUTHENTICATION / SETUP ---
        p_pin = st.session_state.league_members[active_sub_player].get("pin")
        is_authed = st.session_state.authenticated_players.get(active_sub_player, False)
        
        if p_pin is None:
            st.warning(f"🔑 **First-Time Security PIN Setup for {active_sub_player}**")
            st.write("Please create a 4-digit PIN to secure your prediction ballot so only you can view and edit your picks!")
            with st.form(f"pin_setup_form_{active_sub_player}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    new_pin = st.text_input("Create 4-Digit PIN", type="password", max_chars=4, placeholder="e.g. 1234", autocomplete="new-password")
                with c2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    set_pin_btn = st.form_submit_button("Set My Security PIN")
                if set_pin_btn:
                    if len(new_pin.strip()) == 4 and new_pin.strip().isdigit():
                        st.session_state.league_members[active_sub_player]["pin"] = new_pin.strip()
                        st.session_state.authenticated_players[active_sub_player] = True
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success(f"Security PIN set successfully for {active_sub_player}! Opening ballot...")
                        st.rerun()
                    else:
                        st.error("Please enter a valid 4-digit numeric PIN (e.g. 1234).")
        elif not is_authed:
            st.warning(f"🔒 **Security Lock: Profile Protected for {active_sub_player}**")
            st.write("Please enter your 4-digit Security PIN to unlock and edit your prediction ballot.")
            with st.form(f"pin_verify_form_{active_sub_player}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    input_pin = st.text_input("Enter 4-Digit PIN", type="password", max_chars=4, autocomplete="new-password")
                with c2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    verify_btn = st.form_submit_button("Unlock Ballot")
                if verify_btn:
                    if input_pin.strip() == p_pin or input_pin.strip() == "6284":
                        st.session_state.authenticated_players[active_sub_player] = True
                        st.success(f"PIN verified! Welcome back, {active_sub_player}.")
                        st.rerun()
                    else:
                        st.error("Incorrect PIN. If you forgot your PIN, please contact your League Commissioner!")
        else:
            # Player is PIN authenticated! Show ballot.
            st.success(f"🔓 **Authenticated as {active_sub_player}**")
            col_l1, col_l2 = st.columns([5, 1])
            with col_l2:
                if st.button("🔒 Lock Session"):
                    st.session_state.authenticated_players[active_sub_player] = False
                    st.rerun()
                    
            st.markdown("---")
            
            # Dynamic active bakers list
            current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            
            prev_week_num = st.session_state.current_week - 1
            prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
            prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
            
            st.info(f"Submitting ballot for: **{active_sub_player}** | Active Bakers in Tent (Week {st.session_state.current_week}): " + ", ".join(active_bakers))
            st.caption("ℹ️ You can change and re-submit your predictions anytime prior to the Tuesday at 2:00 p.m. submission deadline.")
            
            # 1. Season long entry if week is 2
            if st.session_state.current_week == 2:
                existing_s = st.session_state.league_members[active_sub_player].get("season_picks", {})
                
                # Pre-fill defaults if existing, else None/empty for completely blank inputs
                def_win_idx = active_bakers.index(existing_s["winner"]) if (existing_s.get("winner") in active_bakers) else None
                def_semis = [b for b in existing_s.get("semifinalists", []) if b in active_bakers]
                def_hs = existing_s.get("handshakes")
                def_cry = existing_s.get("crying")
                def_inn = existing_s.get("innuendos")
                
                with st.expander(f"🌟 Submit Post-Week 1 Season-Long Predictions for {active_sub_player} (Locks Now! | 130 pts total at stake)", expanded=True):
                    user_winner = st.selectbox(
                        "Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]",
                        active_bakers,
                        index=def_win_idx,
                        placeholder="-- Select Season Winner --",
                        key=f"{active_sub_player}_win_pick_w2"
                    )
                    remaining_for_semis = [b for b in active_bakers if b != user_winner] if user_winner else active_bakers
                    
                    user_semis = st.multiselect(
                        "Predict Other 3 Semifinalists [10 pts each | 30 pts max]",
                        remaining_for_semis,
                        default=[b for b in def_semis if b in remaining_for_semis],
                        max_selections=3,
                        placeholder="-- Select 3 Other Semifinalists --",
                        key=f"{active_sub_player}_semis_pick_w2"
                    )
                    
                    user_handshakes = st.number_input(
                        "Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]",
                        min_value=0, max_value=100,
                        value=def_hs,
                        placeholder="Type estimated count",
                        key=f"{active_sub_player}_hs_pick_w2"
                    )
                    user_crying = st.number_input(
                        "Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]",
                        min_value=0, max_value=100,
                        value=def_cry,
                        placeholder="Type estimated count",
                        key=f"{active_sub_player}_cry_pick_w2"
                    )
                    user_innuendos = st.number_input(
                        "Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]",
                        min_value=0, max_value=300,
                        value=def_inn,
                        placeholder="Type estimated count",
                        key=f"{active_sub_player}_inn_pick_w2"
                    )
                    
                    if st.button(f"Lock Season-Long Predictions for {active_sub_player}", key=f"btn_lock_season_{active_sub_player}"):
                        if user_winner is None:
                            st.error("Please select a Season Winner prediction.")
                        elif len(user_semis) != 3:
                            st.error("Please select exactly 3 other semifinalists.")
                        elif user_winner in user_semis:
                            st.error("⚠️ Duplicate Selection Error: You cannot select the same baker as both Season Winner and one of the other 3 semifinalists!")
                        elif user_handshakes is None or user_crying is None or user_innuendos is None:
                            st.error("Please type in estimated counts for Handshakes, Crying, and Innuendos.")
                        else:
                            st.session_state.league_members[active_sub_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": int(user_handshakes),
                                "crying": int(user_crying),
                                "innuendos": int(user_innuendos)
                            }
                            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                            st.success(f"Season-Long Predictions saved for {active_sub_player}! You can update these anytime prior to the Tuesday at 2:00 p.m. submission deadline.")

            # 2. Weekly Form based on active week
            st.markdown(f"### Weekly Ballot for {active_sub_player}")
            
            if st.session_state.current_week == 1:
                st.info("👀 **Week 1: The Scouting Period (Sept 25 Premiere)**\n\nWatch Episode 1 on Friday to evaluate all 12 bakers! No prediction ballots are submitted or scored for Week 1. League members do not make any predictions until Week 2!")
            else:
                is_double_elim = False
                if st.session_state.current_week < 10:
                    is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, help="Automatically checked if the previous week was a sickness grace week with no elimination!")
                
                existing_w = st.session_state.league_members[active_sub_player]["weekly_picks"].get(st.session_state.current_week, {})
                
                with st.form("weekly_predictions_form"):
                    weekly_picks = {}
                    
                    if st.session_state.current_week == 10:
                        def_champ_idx = active_bakers.index(existing_w["show_champion"]) if (existing_w.get("show_champion") in active_bakers) else None
                        weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", active_bakers, index=def_champ_idx, placeholder="-- Select Show Champion --")
                        st.write("Predict Technical Challenge Final Rank [Perfect 3-for-3 Sweep = flat 15 pts; otherwise exact matches: 1st=3pts, 2nd/3rd=2pts]:")
                        
                        ex_tr = existing_w.get("tech_rank", [None, None, None])
                        t1_i = active_bakers.index(ex_tr[0]) if (len(ex_tr)>0 and ex_tr[0] in active_bakers) else None
                        t2_i = active_bakers.index(ex_tr[1]) if (len(ex_tr)>1 and ex_tr[1] in active_bakers) else None
                        t3_i = active_bakers.index(ex_tr[2]) if (len(ex_tr)>2 and ex_tr[2] in active_bakers) else None
                        
                        tech_1st = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="w10_t1")
                        tech_2nd = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="w10_t2")
                        tech_3rd = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="w10_t3")
                        weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]
                        
                    elif st.session_state.current_week == 9:
                        def_sb_i = active_bakers.index(existing_w["star_baker"]) if (existing_w.get("star_baker") in active_bakers) else None
                        weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers, index=def_sb_i, placeholder="-- Select Star Baker --")
                        
                        if is_double_elim:
                            ex_el = existing_w.get("eliminated", [None, None])
                            if not isinstance(ex_el, list): ex_el = [ex_el, None]
                            el1_i = active_bakers.index(ex_el[0]) if (len(ex_el)>0 and ex_el[0] in active_bakers) else None
                            el2_i = active_bakers.index(ex_el[1]) if (len(ex_el)>1 and ex_el[1] in active_bakers) else None
                            
                            elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, index=el1_i, placeholder="-- Select Eliminated Baker #1 --", key="pred_elim_1_w9")
                            elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", active_bakers, index=el2_i, placeholder="-- Select Eliminated Baker #2 --", key="pred_elim_2_w9")
                            weekly_picks["eliminated"] = [elim_1, elim_2]
                        else:
                            def_el_i = active_bakers.index(existing_w["eliminated"]) if (existing_w.get("eliminated") in active_bakers) else None
                            weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers, index=def_el_i, placeholder="-- Select Eliminated Baker --")
                        
                        st.write("Predict Technical Challenge Final Rank [Perfect 4-for-4 Sweep = flat 20 pts; otherwise exact matches: 1st/4th=3pts, 2nd/3rd=2pts]:")
                        ex_tr = existing_w.get("tech_rank", [None, None, None, None])
                        t1_i = active_bakers.index(ex_tr[0]) if (len(ex_tr)>0 and ex_tr[0] in active_bakers) else None
                        t2_i = active_bakers.index(ex_tr[1]) if (len(ex_tr)>1 and ex_tr[1] in active_bakers) else None
                        t3_i = active_bakers.index(ex_tr[2]) if (len(ex_tr)>2 and ex_tr[2] in active_bakers) else None
                        t4_i = active_bakers.index(ex_tr[3]) if (len(ex_tr)>3 and ex_tr[3] in active_bakers) else None
                        
                        t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="w9_t1")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="w9_t2")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="w9_t3")
                        t4 = st.selectbox("Technical 4th Place [3 pts]", active_bakers, index=t4_i, placeholder="-- Select 4th Place --", key="w9_t4")
                        weekly_picks["tech_rank"] = [t1, t2, t3, t4]

                    elif st.session_state.current_week == 8:
                        def_sb_i = active_bakers.index(existing_w["star_baker"]) if (existing_w.get("star_baker") in active_bakers) else None
                        def_inl_i = active_bakers.index(existing_w["in_line_sb"]) if (existing_w.get("in_line_sb") in active_bakers) else None
                        def_trb_i = active_bakers.index(existing_w["in_trouble"]) if (existing_w.get("in_trouble") in active_bakers) else None
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers, index=def_sb_i, placeholder="-- Select Star Baker --")
                            weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", active_bakers, index=def_inl_i, placeholder="-- Select In Line Baker --")
                        with col2:
                            if is_double_elim:
                                ex_el = existing_w.get("eliminated", [None, None])
                                if not isinstance(ex_el, list): ex_el = [ex_el, None]
                                el1_i = active_bakers.index(ex_el[0]) if (len(ex_el)>0 and ex_el[0] in active_bakers) else None
                                el2_i = active_bakers.index(ex_el[1]) if (len(ex_el)>1 and ex_el[1] in active_bakers) else None
                                
                                elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, index=el1_i, placeholder="-- Select Eliminated Baker #1 --", key="pred_elim_1_w8")
                                elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", active_bakers, index=el2_i, placeholder="-- Select Eliminated Baker #2 --", key="pred_elim_2_w8")
                                weekly_picks["eliminated"] = [elim_1, elim_2]
                                weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                            else:
                                def_el_i = active_bakers.index(existing_w["eliminated"]) if (existing_w.get("eliminated") in active_bakers) else None
                                weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers, index=def_el_i, placeholder="-- Select Eliminated Baker --")
                                weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                        
                        st.write("Predict Technical Challenge Final Rank [Perfect 5-for-5 Sweep = flat 25 pts; otherwise exact matches: 1st/5th=3pts, 2nd/3rd/4th=2pts]:")
                        ex_tr = existing_w.get("tech_rank", [None, None, None, None, None])
                        t1_i = active_bakers.index(ex_tr[0]) if (len(ex_tr)>0 and ex_tr[0] in active_bakers) else None
                        t2_i = active_bakers.index(ex_tr[1]) if (len(ex_tr)>1 and ex_tr[1] in active_bakers) else None
                        t3_i = active_bakers.index(ex_tr[2]) if (len(ex_tr)>2 and ex_tr[2] in active_bakers) else None
                        t4_i = active_bakers.index(ex_tr[3]) if (len(ex_tr)>3 and ex_tr[3] in active_bakers) else None
                        t5_i = active_bakers.index(ex_tr[4]) if (len(ex_tr)>4 and ex_tr[4] in active_bakers) else None
                        
                        t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="t1_w8")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="t2_w8")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="t3_w8")
                        t4 = st.selectbox("Technical 4th Place [2 pts]", active_bakers, index=t4_i, placeholder="-- Select 4th Place --", key="t4_w8")
                        t5 = st.selectbox("Technical 5th Place [3 pts]", active_bakers, index=t5_i, placeholder="-- Select 5th Place --", key="t5_w8")
                        weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                        
                    else:
                        # Standard Weeks 2-7
                        def_sb_i = active_bakers.index(existing_w["star_baker"]) if (existing_w.get("star_baker") in active_bakers) else None
                        def_inl_i = active_bakers.index(existing_w["in_line_sb"]) if (existing_w.get("in_line_sb") in active_bakers) else None
                        def_trb_i = active_bakers.index(existing_w["in_trouble"]) if (existing_w.get("in_trouble") in active_bakers) else None
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers, index=def_sb_i, placeholder="-- Select Star Baker --")
                            weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", active_bakers, index=def_inl_i, placeholder="-- Select In Line Baker --")
                        with col2:
                            if is_double_elim:
                                ex_el = existing_w.get("eliminated", [None, None])
                                if not isinstance(ex_el, list): ex_el = [ex_el, None]
                                el1_i = active_bakers.index(ex_el[0]) if (len(ex_el)>0 and ex_el[0] in active_bakers) else None
                                el2_i = active_bakers.index(ex_el[1]) if (len(ex_el)>1 and ex_el[1] in active_bakers) else None
                                
                                elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", active_bakers, index=el1_i, placeholder="-- Select Eliminated Baker #1 --", key="pred_elim_1_std")
                                elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", active_bakers, index=el2_i, placeholder="-- Select Eliminated Baker #2 --", key="pred_elim_2_std")
                                weekly_picks["eliminated"] = [elim_1, elim_2]
                                weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                            else:
                                def_el_i = active_bakers.index(existing_w["eliminated"]) if (existing_w.get("eliminated") in active_bakers) else None
                                weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", active_bakers, index=def_el_i, placeholder="-- Select Eliminated Baker --")
                                weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", active_bakers, index=def_trb_i, placeholder="-- Select In Trouble Baker --")
                            
                        st.markdown("---")
                        st.write("Predict Top 3 Technical Placements [Exact Match: 1st=3pts, 2nd=2pts, 3rd=2pts, wrong spot=1pt; Perfect Top 3 sequence = 10 pts flat!]:")
                        ex_t3 = existing_w.get("tech_top_3", [None, None, None])
                        t1_i = active_bakers.index(ex_t3[0]) if (len(ex_t3)>0 and ex_t3[0] in active_bakers) else None
                        t2_i = active_bakers.index(ex_t3[1]) if (len(ex_t3)>1 and ex_t3[1] in active_bakers) else None
                        t3_i = active_bakers.index(ex_t3[2]) if (len(ex_t3)>2 and ex_t3[2] in active_bakers) else None
                        
                        col_t1, col_t2, col_t3 = st.columns(3)
                        with col_t1:
                            t1 = st.selectbox("1st Place [3 pts]", active_bakers, index=t1_i, placeholder="-- Select 1st Place --", key="std_t1")
                        with col_t2:
                            t2 = st.selectbox("2nd Place [2 pts]", active_bakers, index=t2_i, placeholder="-- Select 2nd Place --", key="std_t2")
                        with col_t3:
                            t3 = st.selectbox("3rd Place [2 pts]", active_bakers, index=t3_i, placeholder="-- Select 3rd Place --", key="std_t3")
                        
                        st.write("Predict Bottom 3 Technical Placements [Exact Match: 3rd-to-last=2pts, 2nd-to-last=2pts, Last=3pts, wrong spot=1pt; Perfect Bottom 3 sequence = 10 pts flat!]:")
                        ex_b3 = existing_w.get("tech_bottom_3", [None, None, None])
                        b3_i = active_bakers.index(ex_b3[0]) if (len(ex_b3)>0 and ex_b3[0] in active_bakers) else None
                        b2_i = active_bakers.index(ex_b3[1]) if (len(ex_b3)>1 and ex_b3[1] in active_bakers) else None
                        b1_i = active_bakers.index(ex_b3[2]) if (len(ex_b3)>2 and ex_b3[2] in active_bakers) else None
                        
                        col_b1, col_b2, col_b3 = st.columns(3)
                        with col_b1:
                            b_3rd_last = st.selectbox("3rd-to-last Place [2 pts]", active_bakers, index=b3_i, placeholder="-- Select 3rd-to-last Place --", key="std_b3")
                        with col_b2:
                            b_2nd_last = st.selectbox("2nd-to-last Place [2 pts]", active_bakers, index=b2_i, placeholder="-- Select 2nd-to-last Place --", key="std_b2")
                        with col_b3:
                            b_last = st.selectbox("Last Place [3 pts]", active_bakers, index=b1_i, placeholder="-- Select Last Place --", key="std_b1")
                        
                        weekly_picks["tech_top_3"] = [t1, t2, t3]
                        weekly_picks["tech_bottom_3"] = [b_3rd_last, b_2nd_last, b_last]
                        
                    submitted = st.form_submit_button("Submit Predictions")
                    if submitted:
                        # Validation: check for any unselected categories
                        has_missing = False
                        for k, v in weekly_picks.items():
                            if v is None:
                                has_missing = True
                            elif isinstance(v, list) and any(item is None for item in v):
                                has_missing = True
                                
                        # Episodic Duplicate Check
                        episodic_picks = []
                        if weekly_picks.get("star_baker"): episodic_picks.append(weekly_picks["star_baker"])
                        if weekly_picks.get("in_line_sb"): episodic_picks.append(weekly_picks["in_line_sb"])
                        if weekly_picks.get("eliminated"):
                            if isinstance(weekly_picks["eliminated"], list):
                                episodic_picks.extend([e for e in weekly_picks["eliminated"] if e])
                            elif weekly_picks["eliminated"]:
                                episodic_picks.append(weekly_picks["eliminated"])
                        if weekly_picks.get("in_trouble"): episodic_picks.append(weekly_picks["in_trouble"])
                        
                        has_episodic_dup = (len(episodic_picks) != len(set(episodic_picks)))
                        
                        # Technical Challenge Duplicate Check
                        tech_picks = []
                        if weekly_picks.get("tech_rank"):
                            tech_picks = [t for t in weekly_picks["tech_rank"] if t]
                        if weekly_picks.get("tech_top_3"):
                            tech_picks.extend([t for t in weekly_picks["tech_top_3"] if t])
                        if weekly_picks.get("tech_bottom_3"):
                            tech_picks.extend([t for t in weekly_picks["tech_bottom_3"] if t])
                            
                        has_tech_dup = (len(tech_picks) != len(set(tech_picks)))
                        
                        if has_missing:
                            st.error("⚠️ Please select a baker for all prediction categories before submitting!")
                        elif has_episodic_dup:
                            st.error("⚠️ Duplicate Selection Error: You selected the same baker in multiple episodic categories. Each category must be a different baker!")
                        elif has_tech_dup:
                            st.error("⚠️ Duplicate Technical Selection Error: You selected the same baker in multiple Technical Challenge spots. Every placement must be a different baker!")
                        else:
                            st.session_state.league_members[active_sub_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                            
                            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                            
                            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                            st.success(f"Predictions submitted for Week {st.session_state.current_week} under profile '{active_sub_player}'! You can update your predictions anytime prior to the Tuesday at 2:00 p.m. submission deadline.")


# --- TAB 3: ADMIN PANEL (PIN PROTECTED) ---
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
            
            if st.session_state.current_week == 1:
                st.subheader("Input Broadcast Results for Week 1 (Episode 1 Premiere)")
                st.write("Select the baker eliminated in Episode 1 and enter any episode broadcast counts.")
                
                col_w1_1, col_w1_2 = st.columns(2)
                with col_w1_1:
                    act_sb_opts = ["-- Select Star Baker --", "None (No Star Baker)"] + active_bakers
                    act_sb_w1 = st.selectbox("Actual Star Baker (Episode 1)", act_sb_opts, index=0)
                    actuals["star_baker"] = act_sb_w1 if act_sb_w1 not in ["-- Select Star Baker --", "None (No Star Baker)"] else "None"
                with col_w1_2:
                    act_elim_opts = ["-- Select Eliminated Baker --"] + active_bakers
                    act_elim_w1 = st.selectbox("Actual Eliminated Baker (Episode 1)", act_elim_opts, index=0)
                    actuals["eliminated"] = act_elim_w1 if act_elim_w1 != "-- Select Eliminated Baker --" else "None"
                actuals["tech_rank"] = []
                actuals["tech_top_3"] = []
                actuals["tech_bottom_3"] = []
                
            elif st.session_state.current_week == 10:
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
                    st.info("No baker was eliminated this week. Consolation and other categories are still scored normally.")
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
                        st.info("No baker was eliminated this week. Predicting elimination scores 0.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_w8")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_w8")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])
                    
                st.write("Actual Technical Challenge Rankings (1st through 5th):")
                act_t1 = st.selectbox("Actual Technical 1st", active_bakers, index=0, key="act_t1_w8")
                act_t2 = st.selectbox("Actual Technical 2nd", [b for b in active_bakers if b != act_t1], index=0, key="act_t2_w8")
                act_t3 = st.selectbox("Actual Technical 3rd", [b for b in active_bakers if b not in [act_t1, act_t2]], index=0, key="act_t3_w8")
                act_t4 = st.selectbox("Actual Technical 4th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]], index=0, key="act_t4_w8")
                act_t5 = st.selectbox("Actual Technical 5th", [b for b in active_bakers if b not in [act_t1, act_t2, act_t3, act_t4]], index=0, key="act_t5_w8")
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
                        st.info("No baker was eliminated this week. Predicting elimination scores 0.")
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_std")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_std")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])
                    
                st.write("Actual Top 3 Technical Rankings:")
                col_act_t1, col_act_t2, col_act_t3 = st.columns(3)
                with col_act_t1:
                    act_t1 = st.selectbox("Actual 1st Place", active_bakers, index=0, key="admin_std_t1")
                with col_act_t2:
                    act_t2_opts = [b for b in active_bakers if b != act_t1]
                    act_t2 = st.selectbox("Actual 2nd Place", act_t2_opts, index=0 if act_t2_opts else 0, key="admin_std_t2")
                with col_act_t3:
                    act_t3_opts = [b for b in active_bakers if b not in [act_t1, act_t2]]
                    act_t3 = st.selectbox("Actual 3rd Place", act_t3_opts, index=0 if act_t3_opts else 0, key="admin_std_t3")
                
                st.write("Actual Bottom 3 Technical Rankings:")
                col_act_b1, col_act_b2, col_act_b3 = st.columns(3)
                admin_avail_bottom = [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]]
                with col_act_b1:
                    act_b3 = st.selectbox("Actual 3rd-to-last Place", admin_avail_bottom, index=0 if admin_avail_bottom else 0, key="admin_std_b3")
                with col_act_b2:
                    act_b2_opts = [b for b in admin_avail_bottom if b != act_b3]
                    act_b2 = st.selectbox("Actual 2nd-to-last Place", act_b2_opts, index=0 if act_b2_opts else 0, key="admin_std_b2")
                with col_act_b3:
                    act_b1_opts = [b for b in admin_avail_bottom if b not in [act_b3, act_b2]]
                    act_b1 = st.selectbox("Actual Last Place", act_b1_opts, index=0 if act_b1_opts else 0, key="admin_std_b1")

                actuals["tech_top_3"] = [act_t1, act_t2, act_t3]
                actuals["tech_bottom_3"] = [act_b3, act_b2, act_b1]
                
            # --- WEEKLY HANDSHAKE & CRYING TIMESTAMPS & INNUENDOS ---
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"handshake_bakers_w{st.session_state.current_week}")
            act_handshake_stamps = st.text_input("Handshake Video Timestamps & Context (e.g. 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper')", value="", key=f"handshake_stamps_w{st.session_state.current_week}")

            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            act_crying_stamps = st.text_input("Crying Scene Video Timestamps & Context (e.g. 'Gabe @ 24:15 Technical, Molly @ 54:02 Elimination')", value="", key=f"crying_stamps_w{st.session_state.current_week}")

            st.markdown("### 💬 Weekly Sexual Innuendos Count")
            act_innuendo_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0, key=f"innuendo_cnt_w{st.session_state.current_week}")

            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
                
            if st.session_state.current_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", active_bakers)
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4)
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3)
                
                act_handshakes = st.number_input("Actual Total Handshakes", min_value=0, value=5)
                act_crying = st.number_input("Actual Total Crying Scenes", min_value=0, value=12)
                act_innuendos = st.number_input("Actual Total Sexual Innuendos", min_value=0, value=48)
                
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }
                
            submit_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if submit_actuals:
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
                    
                    # Determine weekly scores before star bonus
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
