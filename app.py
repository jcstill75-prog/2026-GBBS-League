import os
from PIL import Image
import streamlit as st
import streamlit as st
import pandas as pd
import random
from PIL import Image, ImageDraw
import io
import base64

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


def get_avatar_data_uri(avatar_obj, default_symbol='🍪'):
    """Convert PIL Image, image file path, or default symbol into a base64 Data URI for dataframe rendering."""
    if isinstance(avatar_obj, Image.Image):
        try:
            buf = io.BytesIO()
            if avatar_obj.mode in ('RGBA', 'LA'):
                bg = Image.new('RGB', avatar_obj.size, (255, 255, 255))
                bg.paste(avatar_obj, mask=avatar_obj.split()[-1])
                img_to_save = bg
            else:
                img_to_save = avatar_obj.convert('RGB')
            img_to_save.save(buf, format='JPEG', quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{b64}"
        except Exception:
            pass
    
    if isinstance(avatar_obj, str) and len(avatar_obj) > 3 and ('.' in avatar_obj or '/' in avatar_obj):
        if os.path.exists(avatar_obj):
            try:
                img = Image.open(avatar_obj)
                return get_avatar_data_uri(img)
            except Exception:
                pass

    # Fallback badge
    try:
        img = Image.new('RGB', (100, 100), color='#FFF3E0')
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 99, 99], outline='#D36B5F', width=4)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""

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
    
    # Target stem (e.g. 'clara')
    target = baker_name.lower().strip()
    
    # Scan assets directory
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
    "Clara": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-clara/"
    },
    "Connie": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-connie/"
    },
    "Danni": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-danni/"
    },
    "Gabe": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-gabe/"
    },
    "Gary": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-gary/"
    },
    "Mo": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-mo/"
    },
    "Molly": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-molly/"
    },
    "Moyin": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-moyin/"
    },
    "Nikki": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-nikki/"
    },
    "Shannon": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-shannon/"
    },
    "Tom": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-tom/"
    },
    "Yannis": {
        "url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-yannis/"
    }
}

# Streamlit Session State Initialization for persistence
if "league_members" not in st.session_state:
    st.session_state.league_members = {
        "You": {
            "avatar": None,
            "weekly_picks": {},  # {week_num: dict}
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}  # {week_num: score}
        },
        "AI Brian": {
            "avatar": "🤖",
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }
    }

# Check for AI Brian's custom profile picture
brian_avatar_img = load_ai_brian_avatar()
if brian_avatar_img is not None:
    st.session_state.league_members["AI Brian"]["avatar"] = brian_avatar_img

if "current_week" not in st.session_state:
    st.session_state.current_week = 2

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}  # {week_num: actuals_dict}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []  # [{week, category, timestamp_evidence, correction, player, status}]

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
    # Week 10 Finals
    if week == 10:
        champion = random.choice(active_bakers)
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "show_champion": champion,
            "tech_rank": tech_rank
        }
    # Week 9 Semifinals
    elif week == 9:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            if len(elim_pool) >= 2:
                eliminated = random.sample(elim_pool, 2)
            else:
                eliminated = random.sample(active_bakers, min(2, len(active_bakers)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {
            "star_baker": star_baker,
            "eliminated": eliminated,
            "tech_rank": tech_rank
        }
    # Week 8 Quarterfinals (5 Bakers)
    elif week == 8:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            if len(elim_pool) >= 2:
                eliminated = random.sample(elim_pool, 2)
            else:
                eliminated = random.sample(active_bakers, min(2, len(active_bakers)))
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
    # Standard Weeks 2-7
    else:
        star_baker = random.choice(active_bakers)
        if is_double_elim:
            elim_pool = [b for b in active_bakers if b != star_baker]
            if len(elim_pool) >= 2:
                eliminated = random.sample(elim_pool, 2)
            else:
                eliminated = random.sample(active_bakers, min(2, len(active_bakers)))
        else:
            eliminated = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        
        # Tech challenges (Top 3 and Bottom 3)
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

# Generate AI Brian's long-term picks if empty
if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- 5. APP INTERFACE LAYOUT ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
st.markdown("### Powered by the Balanced 2026 Competition Rules Engine")

# --- SIDEBAR: USER ACCOUNT, AVATAR UPLOAD & PERSISTENT POINTS REMINDER ---
with st.sidebar:
    st.header("👤 Your Profile")
    uploaded_file = st.file_uploader("Upload an Avatar Photo", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        # Resize image for circular presentation
        image = image.resize((150, 150))
        st.session_state.league_members["You"]["avatar"] = image
        st.image(image, caption="Your Active Avatar", width=150)
    else:
        if st.session_state.league_members["You"]["avatar"] is not None:
            st.image(st.session_state.league_members["You"]["avatar"], caption="Your Active Avatar", width=150)
        else:
            st.info("No avatar uploaded yet. Using default.")
            st.markdown("<h1 style='font-size: 70px; margin: 0;'>🍪</h1>", unsafe_allow_html=True)
            
    st.markdown("---")
    st.header("⚙️ Game Controls")
    selected_week = st.slider("Select App Active Week", min_value=2, max_value=10, value=st.session_state.current_week)
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
    st.header("🔍 Individual Player Scorecards & Transparent Point Audit")
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
                    
                    # Compute raw total
                    raw_pts = sum(item["Points"] for item in scorecard_items)
                    
                    # Check for Weekly Star Bonus
                    # Determine high raw score for this week
                    all_raw = {m: calculate_weekly_score(st.session_state.league_members[m]["weekly_picks"].get(w_num, {}), act_w, w_num) for m in st.session_state.league_members}
                    max_raw = max(all_raw.values()) if all_raw else 0
                    has_star_bonus = (raw_pts == max_raw and raw_pts > 0)
                    
                    st.dataframe(df_sc, use_container_width=True, hide_index=True)
                    
                    st.markdown(f"**Episodic Raw Score:** `{raw_pts} pts`" + (f" | 🌟 **Star League Member Bonus:** `+5 pts` *(Highest weekly scorer!)*" if has_star_bonus else ""))
                    st.markdown(f"**Week {w_num} Total Awarded:** `{p_data['weekly_breakdown'].get(w_num, raw_pts + (5 if has_star_bonus else 0))} pts`")

    # Show Season-Long Projections Audit if Season Results exist
    if st.session_state.season_results or p_data.get("season_picks"):
        st.markdown("#### 🌟 Season-Long Projections Audit")
        with st.expander("🏆 Season-Long Projections Breakdown", expanded=False):
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
    # 1. VISUAL BAKER CHEAT SHEET (With photos, emojis, bios)
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("If you downloaded the official contestant images, save them in an 'assets/' folder as 'clara.jpg', 'connie.jpg', etc. inside your local directory to load them dynamically. Otherwise, click on the link to view their official photograph page on the show website.")
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

    st.markdown("---")
    st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
    st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
    
    # Dynamic active bakers list
    eliminated_bakers_by_week = {
        2: ["Yannis"],
        3: ["Yannis", "Nikki"],
        4: ["Yannis", "Nikki", "Connie"],
        5: ["Yannis", "Nikki", "Connie", "Gary"],
        6: ["Yannis", "Nikki", "Connie", "Gary", "Moyin"],
        7: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara"],
        8: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon"],
        9: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly"], # Semifinals: 4 bakers left
        10: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly", "Danni"] # Finals: 3 bakers left
    }
    
    current_eliminated = eliminated_bakers_by_week.get(st.session_state.current_week, [])
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    
    # Sickness / Grace Week Auto-Detection
    prev_week_num = st.session_state.current_week - 1
    prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
    prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
    
    st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
    
    # Toggle for Double Elimination Week predictions
    is_double_elim = False
    if st.session_state.current_week < 10:
        is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, help="Automatically checked if the previous week was a sickness grace week with no elimination!")
    
    # 1. Season long entry if week is 2
    if st.session_state.current_week == 2:
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
                    st.session_state.league_members["You"]["season_picks"] = {
                        "winner": user_winner,
                        "semifinalists": user_semis,
                        "handshakes": user_handshakes,
                        "crying": user_crying,
                        "innuendos": user_innuendos
                    }
                    st.success("Season long predictions saved successfully!")

    # 2. Weekly Form based on active week
    st.markdown("### Weekly Ballot")
    with st.form("weekly_predictions_form"):
        weekly_picks = {}
        
        if st.session_state.current_week == 10:
            # Grand Finale: Predict Show Champion and Tech Rank 1-2-3
            weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", active_bakers)
            st.write("Predict Technical Challenge Final Rank [Perfect 3-for-3 Sweep = flat 15 pts; otherwise exact matches: 1st=3pts, 2nd/3rd=2pts]:")
            tech_1st = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0)
            tech_2nd = st.selectbox("Technical 2nd Place [2 pts]", [b for b in active_bakers if b != tech_1st], index=0)
            tech_3rd = st.selectbox("Technical 3rd Place [2 pts]", [b for b in active_bakers if b not in [tech_1st, tech_2nd]], index=0)
            weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]
            
        elif st.session_state.current_week == 9:
            # Semifinal: Star Baker, Eliminated, and Tech Rank 1-2-3-4
            weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", active_bakers)
            if is_double_elim:
                elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", [b for b in active_bakers if b != weekly_picks.get("star_baker")], key="pred_elim_1_w9")
                elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", [b for b in active_bakers if b not in [weekly_picks.get("star_baker"), elim_1]], key="pred_elim_2_w9")
                weekly_picks["eliminated"] = [elim_1, elim_2]
            else:
                weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
            
            st.write("Predict Technical Challenge Final Rank [Perfect 4-for-4 Sweep = flat 20 pts; otherwise exact matches: 1st/4th=3pts, 2nd/3rd=2pts]:")
            t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0)
            t2 = st.selectbox("Technical 2nd Place [2 pts]", [b for b in active_bakers if b != t1], index=0)
            t3 = st.selectbox("Technical 3rd Place [2 pts]", [b for b in active_bakers if b not in [t1, t2]], index=0)
            t4 = st.selectbox("Technical 4th Place [3 pts]", [b for b in active_bakers if b not in [t1, t2, t3]], index=0)
            weekly_picks["tech_rank"] = [t1, t2, t3, t4]

        elif st.session_state.current_week == 8:
            # Quarterfinal (5 bakers remaining): Star Baker, Eliminated, Consolations, and Tech Rank 1-2-3-4-5
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
            
            st.write("Predict Technical Challenge Final Rank [Perfect 5-for-5 Sweep = flat 25 pts; otherwise exact matches: 1st/5th=3pts, 2nd/3rd/4th=2pts]:")
            t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0, key="t1_w8")
            t2 = st.selectbox("Technical 2nd Place [2 pts]", [b for b in active_bakers if b != t1], index=0, key="t2_w8")
            t3 = st.selectbox("Technical 3rd Place [2 pts]", [b for b in active_bakers if b not in [t1, t2]], index=0, key="t3_w8")
            t4 = st.selectbox("Technical 4th Place [2 pts]", [b for b in active_bakers if b not in [t1, t2, t3]], index=0, key="t4_w8")
            t5 = st.selectbox("Technical 5th Place [3 pts]", [b for b in active_bakers if b not in [t1, t2, t3, t4]], index=0, key="t5_w8")
            weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
            
        else:
            # Standard Weeks 2-7
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
            st.write("Predict Top 3 Technical Placements [Exact Match: 1st=3pts, 2nd=2pts, 3rd=2pts, wrong spot=1pt; Perfect Top 3 sequence = 10 pts flat!]:")
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                t1 = st.selectbox("1st Place [3 pts]", active_bakers, index=0, key="std_t1")
            with col_t2:
                t2_opts = [b for b in active_bakers if b != t1]
                t2 = st.selectbox("2nd Place [2 pts]", t2_opts, index=0 if t2_opts else 0, key="std_t2")
            with col_t3:
                t3_opts = [b for b in active_bakers if b not in [t1, t2]]
                t3 = st.selectbox("3rd Place [2 pts]", t3_opts, index=0 if t3_opts else 0, key="std_t3")
            
            st.write("Predict Bottom 3 Technical Placements [Exact Match: 3rd-to-last=2pts, 2nd-to-last=2pts, Last=3pts, wrong spot=1pt; Perfect Bottom 3 sequence = 10 pts flat!]:")
            col_b1, col_b2, col_b3 = st.columns(3)
            avail_bottom = [b for b in active_bakers if b not in [t1, t2, t3]]
            with col_b1:
                b_3rd_last = st.selectbox("3rd-to-last Place [2 pts]", avail_bottom, index=0 if avail_bottom else 0, key="std_b3")
            with col_b2:
                b_2nd_opts = [b for b in avail_bottom if b != b_3rd_last]
                b_2nd_last = st.selectbox("2nd-to-last Place [2 pts]", b_2nd_opts, index=0 if b_2nd_opts else 0, key="std_b2")
            with col_b3:
                b_last_opts = [b for b in avail_bottom if b not in [b_3rd_last, b_2nd_last]]
                b_last = st.selectbox("Last Place [3 pts]", b_last_opts, index=0 if b_last_opts else 0, key="std_b1")
            
            weekly_picks["tech_top_3"] = [t1, t2, t3]
            weekly_picks["tech_bottom_3"] = [b_3rd_last, b_2nd_last, b_last]
            
        submitted = st.form_submit_button("Submit Predictions")
        if submitted:
            # Save User Picks
            st.session_state.league_members["You"]["weekly_picks"][st.session_state.current_week] = weekly_picks
            
            # Automatically trigger AI Brian to submit his random predictions
            ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
            st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
            
            st.success(f"Predictions submitted for Week {st.session_state.current_week}! AI Brian has also submitted his randomized picks.")

# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Use this tab to input the actual results from the broadcast. Submitting actual results will score the predictions and update the leaderboard!")
    
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
                # Admin enters all mentioned nominees as requested by league manager
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
            
        # If Week 10, also let admin input overall season outcomes
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
                
            # TRIGGER RECALCULATION
            # Reset scores and build from logs to ensure clean database states
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
                    
                # Weekly Star Member Bonus (+5 points) to the weekly high scorer (using episodic points only)
                if weekly_raw:
                    max_raw = max(weekly_raw.values())
                    for m_name, raw_s in weekly_raw.items():
                        if raw_s == max_raw:
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
                
            st.success("Leaderboard updated! All predictions scored and verified against the 2026 rule constraints.")
