import streamlit as st
import pandas as pd
import random
from PIL import Image, ImageDraw
import io
import base64
import os
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
    .leaderboard-table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENCE ENGINE (JSON & AVATAR FILESYSTEM) ---
DATA_FILE = "league_data.json"
AVATAR_DIR = os.path.join("assets", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

DEFAULT_ROSTER = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C", "Taliah", "Tressa"
]

def save_league_data():
    serializable_members = {}
    for m_name, m_data in st.session_state.league_members.items():
        av = m_data.get("avatar")
        av_path = None
        if isinstance(av, Image.Image):
            clean_filename = "".join([c for c in m_name if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_') + ".png"
            full_av_path = os.path.join(AVATAR_DIR, clean_filename)
            try:
                av.save(full_av_path, format="PNG")
                av_path = full_av_path
            except Exception:
                pass
        elif isinstance(av, str):
            av_path = av

        serializable_members[m_name] = {
            "avatar_path": av_path,
            "weekly_picks": m_data.get("weekly_picks", {}),
            "season_picks": m_data.get("season_picks", {}),
            "total_score": m_data.get("total_score", 0),
            "weekly_breakdown": m_data.get("weekly_breakdown", {}),
            "season_score": m_data.get("season_score", 0)
        }
    
    payload = {
        "league_members": serializable_members,
        "weekly_results": st.session_state.get("weekly_results", {}),
        "season_results": st.session_state.get("season_results", {}),
        "disputes": st.session_state.get("disputes", [])
    }
    
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                payload = json.load(f)
                
            loaded_members = payload.get("league_members", {})
            for m_name, m_data in loaded_members.items():
                av_path = m_data.get("avatar_path")
                av_obj = None
                if av_path and os.path.exists(str(av_path)):
                    try:
                        av_obj = Image.open(av_path)
                    except Exception:
                        av_obj = av_path
                elif m_name == "AI Brian":
                    av_obj = load_ai_brian_avatar() or "🤖"
                else:
                    av_obj = av_path

                st.session_state.league_members[m_name] = {
                    "avatar": av_obj,
                    "weekly_picks": {int(k) if str(k).isdigit() else k: v for k, v in m_data.get("weekly_picks", {}).items()},
                    "season_picks": m_data.get("season_picks", {}),
                    "total_score": m_data.get("total_score", 0),
                    "weekly_breakdown": {int(k) if str(k).isdigit() else k: v for k, v in m_data.get("weekly_breakdown", {}).items()},
                    "season_score": m_data.get("season_score", 0)
                }
            
            if "weekly_results" in payload:
                st.session_state.weekly_results = {int(k) if str(k).isdigit() else k: v for k, v in payload["weekly_results"].items()}
            if "season_results" in payload:
                st.session_state.season_results = payload["season_results"]
            if "disputes" in payload:
                st.session_state.disputes = payload["disputes"]
        except Exception:
            pass

# --- 3. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions:
        return 0
    
    # --- A. Main Episode Results ---
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
            
    # --- B. Technical Challenge ---
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


def get_weekly_scorecard_details(predictions, actuals, week=2):
    items = []
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

# --- 4. DATABASE & PRE-LOADED ROSTER INITIALIZATION ---
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

if "league_members" not in st.session_state:
    st.session_state.league_members = {
        "AI Brian": {
            "avatar": load_ai_brian_avatar() or "🤖",
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }
    }
    # Pre-populate 14 League Members
    for p_name in DEFAULT_ROSTER:
        st.session_state.league_members[p_name] = {
            "avatar": None,
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

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# Load persistent data if exists
load_league_data()

# --- 5. AI BRIAN PICK GENERATOR ---
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
        if is_double_elim:
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim:
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank, "in_line_sb": in_line_sb, "in_trouble": in_trouble}
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim:
            eliminated = random.sample(elim_pool, min(2, len(elim_pool)))
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        remaining_for_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(remaining_for_bottom, min(3, len(remaining_for_bottom))) if len(remaining_for_bottom) >= 3 else random.sample(active_bakers, min(3, len(active_bakers)))
            
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

# --- 6. APP INTERFACE LAYOUT ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
st.markdown("### Powered by the Balanced 2026 Competition Rules Engine")

# --- SIDEBAR: PLAYER PROFILE, AVATAR UPLOAD & CONTROLS ---
with st.sidebar:
    st.header("📸 Upload Avatar Photo")
    st.write("Select your name below to upload or update your profile picture!")
    
    roster_list = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sidebar_player_choice = st.selectbox(
        "Select Your Player Name:",
        ["-- Select your name --"] + roster_list + ["➕ Register New Name"]
    )
    
    active_sidebar_name = None
    if sidebar_player_choice == "➕ Register New Name":
        custom_name = st.text_input("Enter New Player Name:").strip()
        if custom_name:
            active_sidebar_name = custom_name
            if custom_name not in st.session_state.league_members:
                st.session_state.league_members[custom_name] = {
                    "avatar": None, "weekly_picks": {}, "season_picks": {},
                    "total_score": 0, "weekly_breakdown": {}
                }
                save_league_data()
    elif sidebar_player_choice != "-- Select your name --":
        active_sidebar_name = sidebar_player_choice
        
    if active_sidebar_name:
        uploaded_file = st.file_uploader(f"Choose Photo for {active_sidebar_name}", type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file).resize((150, 150))
            st.session_state.league_members[active_sidebar_name]["avatar"] = image
            save_league_data()
            st.success(f"Avatar saved for {active_sidebar_name}!")
            st.image(image, caption=f"{active_sidebar_name}'s Active Avatar", width=150)
        else:
            cur_av = st.session_state.league_members[active_sidebar_name].get("avatar")
            if isinstance(cur_av, Image.Image):
                st.image(cur_av, caption=f"{active_sidebar_name}'s Active Avatar", width=150)
            else:
                st.info("No photo uploaded yet.")
                st.markdown("<h1 style='font-size: 60px; margin: 0;'>🍪</h1>", unsafe_allow_html=True)
    else:
        st.info("Select your name above to upload a custom avatar photo!")

    st.markdown("---")
    st.header("⚙️ Game Controls")
    selected_week = st.slider("Select App Active Week", min_value=2, max_value=10, value=st.session_state.current_week)
    st.session_state.current_week = selected_week

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
        *   **Top 3 Technical:** Exact 1st=3pt, 2nd/3rd=2pt, Wrong spot=1pt. Perfect sweep = **10 pts flat!**
        *   **Bottom 3 Technical:** Exact 9th/10th=2pt, 11th=3pt, Wrong spot=1pt. Perfect sweep = **10 pts flat!**
        *   **Star League Member:** +5 pts *(weekly high scorer)*
        """)

# --- MAIN TABS ---
tab_lead, tab_submit, tab_admin = st.tabs(["📊 Leaderboard & Standings", "📝 Submit Predictions", "👑 Admin Panel"])

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
    with col_hs: st.markdown("**Total Combined Score**")
    st.markdown("<hr style='margin: 4px 0 12px 0; border-top: 2px solid #D36B5F;'>", unsafe_allow_html=True)

    for idx, (member_name, data) in enumerate(sorted_members):
        rank_num = idx + 1
        rank_badge = f"🥇 #{rank_num}" if rank_num == 1 else (f"🥈 #{rank_num}" if rank_num == 2 else (f"🥉 #{rank_num}" if rank_num == 3 else f"#{rank_num}"))
        
        avatar_img = data.get("avatar")
        if member_name == "AI Brian" and not isinstance(avatar_img, Image.Image):
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

    player_names = sorted(list(st.session_state.league_members.keys()))
    selected_player = st.selectbox("Choose Player Scorecard to View:", player_names)
    
    p_data = st.session_state.league_members[selected_player]
    p_avatar = p_data.get("avatar")
    
    col_sc1, col_sc2 = st.columns([1, 4])
    with col_sc1:
        if isinstance(p_avatar, Image.Image):
            st.image(p_avatar, caption=f"{selected_player}'s Avatar", width=120)
        elif selected_player == "AI Brian":
            b_img = load_ai_brian_avatar()
            if b_img: st.image(b_img, caption="AI Brian", width=120)
            else: st.markdown("<h1 style='font-size: 60px; margin: 0;'>🤖</h1>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='font-size: 60px; margin: 0;'>🍪</h1>", unsafe_allow_html=True)
            
    with col_sc2:
        st.subheader(f"📊 {selected_player}'s Score Summary")
        st.markdown(f"**Total Combined Score:** `{p_data['total_score']} pts`")
        if selected_player == "AI Brian":
            st.info("🤖 **AI Brian Note:** Automated participant generating random predictions following official 2026 rule constraints.")

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

    if st.session_state.season_results or p_data.get("season_picks"):
        st.markdown("#### 🌟 Season-Long Projections Audit")
        with st.expander("🏆 Season-Long Projections Breakdown", expanded=False):
            sp = p_data.get("season_picks", {})
            sr = st.session_state.season_results
            if not sp:
                st.info("No season-long prediction locked.")
            else:
                s_rows = [
                    {"Category": "Season Winner [40 pts]", "Player Pick": str(sp.get("winner", "N/A")), "Actual Result": str(sr.get("winner", "Pending Season Finale")), "Points Earned": 40 if (sr and sp.get("winner") == sr.get("winner")) else (15 if (sr and sp.get("winner") in sr.get("finalists", [])) else 0), "Notes": "40 pts if exact winner; 15 pts if runner-up finalist"},
                    {"Category": "Other 3 Semifinalists [10 pts each]", "Player Pick": ", ".join(sp.get("semifinalists", [])) if sp.get("semifinalists") else "N/A", "Actual Result": ", ".join(sr.get("semifinalists", [])) if sr.get("semifinalists") else "Pending Semifinals", "Points Earned": sum(10 for b in sp.get("semifinalists", []) if sr and b in sr.get("semifinalists", []) and b != sp.get("winner")), "Notes": "10 pts per correct pick (max 30 pts)"},
                    {"Category": "Hollywood Handshakes Count", "Player Pick": str(sp.get("handshakes", "N/A")), "Actual Result": str(sr.get("handshakes", "Pending Cumulative Log")) if sr else "Pending", "Points Earned": 20 if (sr and sp.get("handshakes") == sr.get("handshakes")) else (10 if (sr and sp.get("handshakes") is not None and sr.get("handshakes") is not None and abs(sp.get("handshakes") - sr.get("handshakes")) <= 1) else 0), "Notes": "20 pts spot-on; 10 pts within +/- 1"},
                    {"Category": "Crying Incidents Count", "Player Pick": str(sp.get("crying", "N/A")), "Actual Result": str(sr.get("crying", "Pending Cumulative Log")) if sr else "Pending", "Points Earned": 20 if (sr and sp.get("crying") == sr.get("crying")) else (10 if (sr and sp.get("crying") is not None and sr.get("crying") is not None and abs(sp.get("crying") - sr.get("crying")) <= 5) else 0), "Notes": "20 pts spot-on; 10 pts within +/- 5"},
                    {"Category": "Sexual Innuendos Count", "Player Pick": str(sp.get("innuendos", "N/A")), "Actual Result": str(sr.get("innuendos", "Pending Cumulative Log")) if sr else "Pending", "Points Earned": 20 if (sr and sp.get("innuendos") == sr.get("innuendos")) else (10 if (sr and sp.get("innuendos") is not None and sr.get("innuendos") is not None and abs(sp.get("innuendos") - sr.get("innuendos")) <= 5) else 0), "Notes": "20 pts spot-on; 10 pts within +/- 5"}
                ]
                df_s_audit = pd.DataFrame(s_rows)
                st.dataframe(df_s_audit, use_container_width=True, hide_index=True)
                st.markdown(f"**Season Projections Total Points Earned:** `{p_data.get('season_score', 0)} pts`")


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("Browse the Series 17 contestant photo gallery below:")
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
    st.subheader(f"📅 Submit Predictions: Week {st.session_state.current_week}")
    st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
    
    player_options_list = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sub_player_choice = st.selectbox(
        "Select Your Player Name to Submit Predictions:",
        ["-- Select your name --"] + player_options_list + ["➕ Register New Player"]
    )
    
    active_sub_player = None
    if sub_player_choice == "➕ Register New Player":
        new_name_val = st.text_input("Enter New Player Name:").strip()
        if new_name_val: active_sub_player = new_name_val
    elif sub_player_choice != "-- Select your name --":
        active_sub_player = sub_player_choice
        
    if not active_sub_player:
        st.info("👈 **Please select your name from the drop-down menu above to open your prediction ballot!**")
    else:
        if active_sub_player not in st.session_state.league_members:
            st.session_state.league_members[active_sub_player] = {
                "avatar": None, "weekly_picks": {}, "season_picks": {},
                "total_score": 0, "weekly_breakdown": {}
            }
            save_league_data()
            
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
        
        prev_week_num = st.session_state.current_week - 1
        prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        st.success(f"Logging predictions for: **{active_sub_player}**")
        st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
        
        is_double_elim = False
        if st.session_state.current_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)
        
        if st.session_state.current_week == 2:
            with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Now! | 130 pts total at stake)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts]", active_bakers, key=f"win_{active_sub_player}")
                remaining_for_semis = [b for b in active_bakers if b != user_winner]
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", remaining_for_semis, max_selections=3, key=f"semis_{active_sub_player}")
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes", min_value=0, value=5, key=f"hs_{active_sub_player}")
                user_crying = st.number_input("Predict Seasonal Crying", min_value=0, value=10, key=f"cry_{active_sub_player}")
                user_innuendos = st.number_input("Predict Seasonal Innuendos", min_value=0, value=40, key=f"inn_{active_sub_player}")
                
                if st.button("Lock Season-Long Predictions"):
                    if len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members[active_sub_player]["season_picks"] = {
                            "winner": user_winner, "semifinalists": user_semis,
                            "handshakes": user_handshakes, "crying": user_crying, "innuendos": user_innuendos
                        }
                        save_league_data()
                        st.success(f"Season long predictions saved for {active_sub_player}!")

        st.markdown("### Weekly Ballot")
        with st.form("weekly_predictions_form"):
            weekly_picks = {}
            
            if st.session_state.current_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", active_bakers)
                tech_1st = st.selectbox("Technical 1st Place", active_bakers, index=0)
                tech_2nd = st.selectbox("Technical 2nd Place", [b for b in active_bakers if b != tech_1st], index=0)
                tech_3rd = st.selectbox("Technical 3rd Place", [b for b in active_bakers if b not in [tech_1st, tech_2nd]], index=0)
                weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]
                
            elif st.session_state.current_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                if is_double_elim:
                    elim_1 = st.selectbox("Predict Eliminated Baker #1", [b for b in active_bakers if b != weekly_picks.get("star_baker")], key="pred_elim_1_w9")
                    elim_2 = st.selectbox("Predict Eliminated Baker #2", [b for b in active_bakers if b not in [weekly_picks.get("star_baker"), elim_1]], key="pred_elim_2_w9")
                    weekly_picks["eliminated"] = [elim_1, elim_2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker", [b for b in active_bakers if b != weekly_picks.get("star_baker")])
                
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
                        elim_1 = st.selectbox("Predict Eliminated Baker #1", active_bakers, key="pred_elim_1_w8")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2", [b for b in active_bakers if b != elim_1], key="pred_elim_2_w8")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b not in weekly_picks["eliminated"]])
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b != weekly_picks.get("eliminated")])
                
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
                        elim_1 = st.selectbox("Predict Eliminated Baker #1", active_bakers, key="pred_elim_1_std")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2", [b for b in active_bakers if b != elim_1], key="pred_elim_2_std")
                        weekly_picks["eliminated"] = [elim_1, elim_2]
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b not in weekly_picks["eliminated"]])
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers)
                        weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts]", [b for b in active_bakers if b != weekly_picks.get("eliminated")])
                    
                st.markdown("---")
                st.write("Predict Top 3 Technical Placements:")
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1: t1 = st.selectbox("1st Place [3 pts]", active_bakers, index=0, key="std_t1")
                with col_t2:
                    t2_opts = [b for b in active_bakers if b != t1]
                    t2 = st.selectbox("2nd Place [2 pts]", t2_opts, index=0 if t2_opts else 0, key="std_t2")
                with col_t3:
                    t3_opts = [b for b in active_bakers if b not in [t1, t2]]
                    t3 = st.selectbox("3rd Place [2 pts]", t3_opts, index=0 if t3_opts else 0, key="std_t3")
                
                st.write("Predict Bottom 3 Technical Placements:")
                col_b1, col_b2, col_b3 = st.columns(3)
                avail_bottom = [b for b in active_bakers if b not in [t1, t2, t3]]
                with col_b1: b_3rd_last = st.selectbox("3rd-to-last Place [2 pts]", avail_bottom, index=0 if avail_bottom else 0, key="std_b3")
                with col_b2:
                    b_2nd_opts = [b for b in avail_bottom if b != b_3rd_last]
                    b_2nd_last = st.selectbox("2nd-to-last Place [2 pts]", b_2nd_opts, index=0 if b_2nd_opts else 0, key="std_b2")
                with col_b3:
                    b_last_opts = [b for b in avail_bottom if b not in [b_3rd_last, b_2nd_last]]
                    b_last = st.selectbox("Last Place [3 pts]", b_last_opts, index=0 if b_last_opts else 0, key="std_b1")
                
                weekly_picks["tech_top_3"] = [t1, t2, t3]
                weekly_picks["tech_bottom_3"] = [b_3rd_last, b_2nd_last, b_last]
                
            submitted = st.form_submit_button(f"Submit Predictions for {active_sub_player}")
            if submitted:
                st.session_state.league_members[active_sub_player]["weekly_picks"][st.session_state.current_week] = weekly_picks
                
                ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                
                save_league_data()
                st.success(f"Predictions locked for {active_sub_player} (Week {st.session_state.current_week})! AI Brian also submitted picks.")

# --- TAB 3: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        st.markdown("### 🔒 Administrator Lock Screen")
        st.write("This tab is restricted to the League Administrator. Enter your Admin PIN below to unlock console controls.")
        
        pin_input = st.text_input("Enter Admin PIN", type="password", key="admin_pin_input")
        if st.button("Unlock Admin Panel"):
            if pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect PIN. Access Denied.")
    else:
        col_adm1, col_adm2 = st.columns([4, 1])
        with col_adm1:
            st.success("🔓 Admin Authenticated (PIN 6284)")
        with col_adm2:
            if st.button("🔒 Lock Console"):
                st.session_state.admin_authenticated = False
                st.rerun()
                
        st.write("Input actual broadcast results below to score prediction ballots and update standings!")
        
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
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
            actuals = {}
            
            if st.session_state.current_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", active_bakers)
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
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_w8")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_w8")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])
                    
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
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    else:
                        act_elim_1 = st.selectbox("Actual Eliminated Baker #1", active_bakers, key="admin_act_elim_1_std")
                        act_elim_2 = st.selectbox("Actual Eliminated Baker #2", [b for b in active_bakers if b != act_elim_1], key="admin_act_elim_2_std")
                        actuals["eliminated"] = [act_elim_1, act_elim_2]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", [b for b in active_bakers if b not in actuals["eliminated"]])
                    
                st.write("Actual Top 3 Technical Rankings:")
                col_act_t1, col_act_t2, col_act_t3 = st.columns(3)
                with col_act_t1: act_t1 = st.selectbox("Actual 1st Place", active_bakers, index=0, key="admin_std_t1")
                with col_act_t2:
                    act_t2_opts = [b for b in active_bakers if b != act_t1]
                    act_t2 = st.selectbox("Actual 2nd Place", act_t2_opts, index=0 if act_t2_opts else 0, key="admin_std_t2")
                with col_act_t3:
                    act_t3_opts = [b for b in active_bakers if b not in [act_t1, act_t2]]
                    act_t3 = st.selectbox("Actual 3rd Place", act_t3_opts, index=0 if act_t3_opts else 0, key="admin_std_t3")
                
                st.write("Actual Bottom 3 Technical Rankings:")
                col_act_b1, col_act_b2, col_act_b3 = st.columns(3)
                admin_avail_bottom = [b for b in active_bakers if b not in [act_t1, act_t2, act_t3]]
                with col_act_b1: act_b3 = st.selectbox("Actual 3rd-to-last Place", admin_avail_bottom, index=0 if admin_avail_bottom else 0, key="admin_std_b3")
                with col_act_b2:
                    act_b2_opts = [b for b in admin_avail_bottom if b != act_b3]
                    act_b2 = st.selectbox("Actual 2nd-to-last Place", act_b2_opts, index=0 if act_b2_opts else 0, key="admin_std_b2")
                with col_act_b3:
                    act_b1_opts = [b for b in admin_avail_bottom if b not in [act_b3, act_b2]]
                    act_b1 = st.selectbox("Actual Last Place", act_b1_opts, index=0 if act_b1_opts else 0, key="admin_std_b1")

                actuals["tech_top_3"] = [act_t1, act_t2, act_t3]
                actuals["tech_bottom_3"] = [act_b3, act_b2, act_b1]
                
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"handshake_bakers_w{st.session_state.current_week}")
            act_handshake_stamps = st.text_input("Handshake Video Timestamps & Context", value="", key=f"handshake_stamps_w{st.session_state.current_week}")

            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            act_crying_stamps = st.text_input("Crying Scene Video Timestamps & Context", value="", key=f"crying_stamps_w{st.session_state.current_week}")

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
                    "winner": act_winner, "semifinalists": act_semis, "finalists": act_finalists,
                    "handshakes": act_handshakes, "crying": act_crying, "innuendos": act_innuendos
                }
                
            submit_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if submit_actuals:
                st.session_state.weekly_results[st.session_state.current_week] = actuals
                if st.session_state.current_week == 10:
                    st.session_state.season_results = actuals_season
                    
                for member_name in st.session_state.league_members:
                    st.session_state.league_members[member_name]["total_score"] = 0
                    st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                    
                all_weeks_scored = sorted(list(st.session_state.weekly_results.keys()))
                
                for w in all_weeks_scored:
                    act_w = st.session_state.weekly_results[w]
                    weekly_raw = {}
                    for m_name, m_data in st.session_state.league_members.items():
                        pred_w = m_data["weekly_picks"].get(w, {})
                        raw_score = calculate_weekly_score(pred_w, act_w, w)
                        weekly_raw[m_name] = raw_score
                        m_data["weekly_breakdown"][w] = raw_score
                        
                    if weekly_raw:
                        max_raw = max(weekly_raw.values())
                        for m_name, raw_s in weekly_raw.items():
                            if raw_s == max_raw:
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
                    
                save_league_data()
                st.success("Leaderboard updated and saved permanently! All predictions scored and verified.")
