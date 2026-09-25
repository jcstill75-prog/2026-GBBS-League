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
    .leaderboard-table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
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
            try:
                return Image.open(p)
            except Exception:
                pass
    return None

# --- 3. CORE BAKERS LIST & DATABASE INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

DEFAULT_ROSTER = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
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

def get_tech_options(active_bakers, current_key, default_val=None, placeholder="-- Select --"):
    opts = [placeholder] + active_bakers
    curr_val = st.session_state.get(current_key, default_val)
    idx = opts.index(curr_val) if curr_val in opts else 0
    return opts, idx

def render_player_avatar(avatar_val, width=50, caption=None):
    if isinstance(avatar_val, str) and os.path.exists(avatar_val):
        try:
            img = Image.open(avatar_val)
            st.image(img, width=width, caption=caption)
            return
        except Exception:
            pass
    if isinstance(avatar_val, str) and avatar_val.startswith("data:image"):
        st.markdown(f'<img src="{avatar_val}" style="width:{width}px; height:{width}px; border-radius:50%; object-fit:cover;">', unsafe_allow_html=True)
        if caption:
            st.caption(caption)
    elif isinstance(avatar_val, Image.Image):
        st.image(avatar_val, width=width, caption=caption)
    elif avatar_val == "🤖":
        b_img = load_ai_brian_avatar()
        if b_img:
            st.image(b_img, width=width, caption=caption)
        else:
            st.markdown("<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)

# --- 4. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions:
        return 0
    
    # Star Baker / Champion
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
            
    # Technical Challenge
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
                        score += 3 if idx in [0, 4] else 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx in [0, 3] else 2
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
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

    # Consolations
    if week < 9:
        act_inl = actuals.get("in_line_sb", [])
        if isinstance(act_inl, str): act_inl = [act_inl]
        pred_inl = predictions.get("in_line_sb")
        if pred_inl and pred_inl in act_inl and pred_inl != actuals.get("star_baker"):
            score += 2
            
        act_trbl = actuals.get("in_trouble", [])
        if isinstance(act_trbl, str): act_trbl = [act_trbl]
        pred_trbl = predictions.get("in_trouble")
        if pred_trbl and pred_trbl in act_trbl:
            score += 2
            
    return score

def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and pred_winner in act_finalists:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    pred_hs = predictions.get("handshakes")
    act_hs = actuals.get("handshakes")
    if pred_hs is not None and act_hs is not None:
        if pred_hs == act_hs: score += 20
        elif abs(pred_hs - act_hs) <= 1: score += 10
            
    pred_cry = predictions.get("crying")
    act_cry = actuals.get("crying")
    if pred_cry is not None and act_cry is not None:
        if pred_cry == act_cry: score += 20
        elif abs(pred_cry - act_cry) <= 5: score += 10
            
    pred_inn = predictions.get("innuendos")
    act_inn = actuals.get("innuendos")
    if pred_inn is not None and act_inn is not None:
        if pred_inn == act_inn: score += 20
        elif abs(pred_inn - act_inn) <= 5: score += 10
            
    return score

def get_weekly_itemized_breakdown(pred, act, week):
    rows = []
    if week == 10:
        p_ch = pred.get("show_champion", "None")
        a_ch = act.get("show_champion", "None")
        pts_ch = 15 if (p_ch != "None" and p_ch == a_ch) else 0
        rows.append({
            "Category": "🏆 Show Champion",
            "Your Prediction": p_ch,
            "Actual Broadcast Result": a_ch,
            "Points Awarded": f"{pts_ch} pts",
            "Details & Explanations": "Correctly predicted Show Champion (+15 pts)" if pts_ch == 15 else "Incorrect prediction (0 pts)"
        })
    else:
        p_sb = pred.get("star_baker", "None")
        a_sb = act.get("star_baker", "None")
        pts_sb = 5 if (p_sb != "None" and p_sb == a_sb) else 0
        rows.append({
            "Category": "🌟 Star Baker",
            "Your Prediction": p_sb,
            "Actual Broadcast Result": a_sb,
            "Points Awarded": f"{pts_sb} pts",
            "Details & Explanations": "Correct Star Baker prediction (+5 pts)" if pts_sb == 5 else "Incorrect Star Baker prediction (0 pts)"
        })

        p_el = pred.get("eliminated")
        a_el = act.get("eliminated")
        pts_el = 0
        p_el_str = ", ".join(p_el) if isinstance(p_el, list) else str(p_el)
        a_el_str = ", ".join(a_el) if isinstance(a_el, list) else str(a_el)
        
        if isinstance(a_el, list):
            if isinstance(p_el, list):
                for p in p_el:
                    if p in a_el: pts_el += 5
            elif p_el in a_el: pts_el += 5
        elif a_el != "None":
            if isinstance(p_el, list):
                if a_el in p_el: pts_el += 5
            elif p_el == a_el: pts_el += 5
            
        rows.append({
            "Category": "❌ Eliminated Baker",
            "Your Prediction": p_el_str if p_el_str else "None",
            "Actual Broadcast Result": a_el_str if a_el_str else "None",
            "Points Awarded": f"{pts_el} pts",
            "Details & Explanations": f"Correct elimination prediction (+{pts_el} pts)" if pts_el > 0 else "Incorrect elimination prediction (0 pts)"
        })

    if week >= 8:
        p_rk = pred.get("tech_rank", [])
        a_rk = act.get("tech_rank", [])
        pts_tk = 0
        if week == 8 and len(p_rk) == 5 and len(a_rk) == 5:
            if p_rk == a_rk: pts_tk = 25
            else:
                for idx, b in enumerate(p_rk):
                    if a_rk[idx] == b: pts_tk += 3 if idx in [0, 4] else 2
        elif week == 9 and len(p_rk) == 4 and len(a_rk) == 4:
            if p_rk == a_rk: pts_tk = 20
            else:
                for idx, b in enumerate(p_rk):
                    if a_rk[idx] == b: pts_tk += 3 if idx in [0, 3] else 2
        elif week == 10 and len(p_rk) == 3 and len(a_rk) == 3:
            if p_rk == a_rk: pts_tk = 15
            else:
                for idx, b in enumerate(p_rk):
                    if a_rk[idx] == b: pts_tk += 3 if idx == 0 else 2
        rows.append({
            "Category": "🍰 Technical Challenge Ranking",
            "Your Prediction": ", ".join(p_rk) if p_rk else "None",
            "Actual Broadcast Result": ", ".join(a_rk) if a_rk else "None",
            "Points Awarded": f"{pts_tk} pts",
            "Details & Explanations": f"Technical placement points (+{pts_tk} pts)" if pts_tk > 0 else "No exact rank matches (0 pts)"
        })
    else:
        p_t3 = pred.get("tech_top_3", [])
        a_t3 = act.get("tech_top_3", [])
        pts_t3 = 0
        if len(p_t3) == 3 and len(a_t3) == 3:
            if p_t3 == a_t3: pts_t3 = 10
            else:
                if p_t3[0] == a_t3[0]: pts_t3 += 3
                if p_t3[1] == a_t3[1]: pts_t3 += 2
                if p_t3[2] == a_t3[2]: pts_t3 += 2
                for idx, b in enumerate(p_t3):
                    if b in a_t3 and b != a_t3[idx]: pts_t3 += 1
        rows.append({
            "Category": "🥇 Technical Top 3",
            "Your Prediction": ", ".join(p_t3) if p_t3 else "None",
            "Actual Broadcast Result": ", ".join(a_t3) if a_t3 else "None",
            "Points Awarded": f"{pts_t3} pts",
            "Details & Explanations": f"Technical Top 3 points (+{pts_t3} pts)" if pts_t3 > 0 else "Top 3 prediction not awarded (0 pts)"
        })

        p_b3 = pred.get("tech_bottom_3", [])
        a_b3 = act.get("tech_bottom_3", [])
        pts_b3 = 0
        if len(p_b3) == 3 and len(a_b3) == 3:
            if p_b3 == a_b3: pts_b3 = 10
            else:
                if p_b3[0] == a_b3[0]: pts_b3 += 2
                if p_b3[1] == a_b3[1]: pts_b3 += 2
                if p_b3[2] == a_b3[2]: pts_b3 += 3
                for idx, b in enumerate(p_b3):
                    if b in a_b3 and b != a_b3[idx]: pts_b3 += 1
        rows.append({
            "Category": "🥉 Technical Bottom 3",
            "Your Prediction": ", ".join(p_b3) if p_b3 else "None",
            "Actual Broadcast Result": ", ".join(a_b3) if a_b3 else "None",
            "Points Awarded": f"{pts_b3} pts",
            "Details & Explanations": f"Technical Bottom 3 points (+{pts_b3} pts)" if pts_b3 > 0 else "Bottom 3 prediction not awarded (0 pts)"
        })

    if week < 9:
        p_inl = pred.get("in_line_sb", "None")
        a_inl = act.get("in_line_sb", [])
        if isinstance(a_inl, str): a_inl = [a_inl]
        pts_inl = 2 if (p_inl != "None" and p_inl in a_inl and p_inl != act.get("star_baker")) else 0
        rows.append({
            "Category": "📈 In Line Nominee Consolation",
            "Your Prediction": p_inl,
            "Actual Broadcast Result": ", ".join(a_inl) if a_inl else "None",
            "Points Awarded": f"{pts_inl} pts",
            "Details & Explanations": f"Picked 'In Line' nominee {p_inl} (+2 pts)" if pts_inl == 2 else "Nominee pick not awarded (0 pts)"
        })

        p_trb = pred.get("in_trouble", "None")
        a_trb = act.get("in_trouble", [])
        if isinstance(a_trb, str): a_trb = [a_trb]
        pts_trb = 2 if (p_trb != "None" and p_trb in a_trb) else 0
        rows.append({
            "Category": "⚠️ In Trouble Nominee Consolation",
            "Your Prediction": p_trb,
            "Actual Broadcast Result": ", ".join(a_trb) if a_trb else "None",
            "Points Awarded": f"{pts_trb} pts",
            "Details & Explanations": f"Picked 'In Trouble' nominee {p_trb} (+2 pts)" if pts_trb == 2 else "Nominee pick not awarded (0 pts)"
        })

    return rows

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    picks = {}
    if not active_bakers:
        return picks
    if week == 10:
        picks["show_champion"] = random.choice(active_bakers)
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_rank"] = shuffled[:3]
    elif week == 9:
        picks["star_baker"] = random.choice(active_bakers)
        rem = [b for b in active_bakers if b != picks["star_baker"]]
        if is_double_elim and len(rem) >= 2:
            picks["eliminated"] = random.sample(rem, 2)
        elif rem:
            picks["eliminated"] = random.choice(rem)
        else:
            picks["eliminated"] = "None"
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_rank"] = shuffled[:4]
    elif week == 8:
        picks["star_baker"] = random.choice(active_bakers)
        rem_inl = [b for b in active_bakers if b != picks["star_baker"]]
        picks["in_line_sb"] = random.choice(rem_inl) if rem_inl else picks["star_baker"]
        rem_trb = [b for b in active_bakers if b != picks["star_baker"] and b != picks["in_line_sb"]]
        picks["in_trouble"] = random.choice(rem_trb) if rem_trb else picks["star_baker"]
        rem_el = [b for b in active_bakers if b != picks["star_baker"] and b != picks["in_line_sb"] and b != picks["in_trouble"]]
        if is_double_elim and len(rem_el) >= 2:
            picks["eliminated"] = random.sample(rem_el, 2)
        elif rem_el:
            picks["eliminated"] = random.choice(rem_el)
        else:
            picks["eliminated"] = "None"
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_rank"] = shuffled[:5]
    else:
        # Standard Weeks 2-7
        picks["star_baker"] = random.choice(active_bakers)
        rem_inl = [b for b in active_bakers if b != picks["star_baker"]]
        picks["in_line_sb"] = random.choice(rem_inl) if rem_inl else picks["star_baker"]
        rem_trb = [b for b in active_bakers if b != picks["star_baker"] and b != picks["in_line_sb"]]
        picks["in_trouble"] = random.choice(rem_trb) if rem_trb else picks["star_baker"]
        rem_el = [b for b in active_bakers if b != picks["star_baker"] and b != picks["in_line_sb"] and b != picks["in_trouble"]]
        if is_double_elim and len(rem_el) >= 2:
            picks["eliminated"] = random.sample(rem_el, 2)
        elif rem_el:
            picks["eliminated"] = random.choice(rem_el)
        else:
            picks["eliminated"] = "None"
            
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_top_3"] = shuffled[:3]
        rem_bot = [b for b in active_bakers if b not in picks["tech_top_3"]]
        random.shuffle(rem_bot)
        picks["tech_bottom_3"] = rem_bot[:3]
        
    return picks

# --- 5. INITIALIZE SESSION STATE & AUTO-MIGRATE ROSTER ---
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

# Auto-migrate roster to remove legacy test profiles and add missing members
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

for old_key in ["Steve", "Craig", "You"]:
    if old_key in st.session_state.league_members:
        del st.session_state.league_members[old_key]

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_weekly if saved_weekly is not None else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_season if saved_season is not None else {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

# Helper function to get current eliminated bakers up to week
def get_current_eliminated_bakers(week_num):
    elim = []
    for w in range(1, week_num):
        res = st.session_state.weekly_results.get(w, {})
        act_el = res.get("eliminated")
        if act_el:
            if isinstance(act_el, list):
                for b in act_el:
                    if b and b != "None" and b not in elim: elim.append(b)
            elif isinstance(act_el, str) and act_el and act_el != "None":
                if act_el not in elim: elim.append(act_el)
    return elim

def get_sorted_weekly_result_weeks():
    w_keys = []
    for k in st.session_state.weekly_results.keys():
        try:
            w_keys.append(int(k))
        except (ValueError, TypeError):
            pass
    return sorted(w_keys)

def get_weekly_result(w_num):
    return st.session_state.weekly_results.get(w_num, st.session_state.weekly_results.get(str(w_num), {}))

# --- 6. HEADER ---
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
        col_logo, col_title = st.columns([1, 6])
        with col_logo:
            st.image(norman_path, width=80)
        with col_title:
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
            st.info("Unlock your profile in the **📝 Submit Predictions** tab using your 4-digit PIN to upload an avatar!")
        else:
            uploaded_file = st.file_uploader(f"Choose Photo for {sb_player}", type=["png", "jpg", "jpeg"], key=f"uploader_{sb_player}")
            if uploaded_file is not None:
                try:
                    img = Image.open(uploaded_file)
                    img = img.convert("RGB")
                    img = img.resize((250, 200))
                    
                    # Convert to Base64 data URL
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                    data_url = f"data:image/png;base64,{b64_str}"
                    
                    st.session_state.league_members[sb_player]["avatar"] = data_url
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Avatar saved permanently for {sb_player}!")
                except Exception as e:
                    st.error(f"Error saving avatar image: {e}")
            
            cur_av = st.session_state.league_members[sb_player].get("avatar")
            if cur_av:
                render_player_avatar(cur_av, width=150, caption=f"{sb_player}'s Avatar")

    st.markdown("---")
    st.subheader("🗓️ Active Competition Week")
    st.session_state.current_week = st.slider("Select Episode Week:", 1, 10, st.session_state.current_week)

# --- 8. MAIN TABS ---
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
        rank_badge = f"🥇 #{rank}" if rank == 1 else (f"🥈 #{rank}" if rank == 2 else (f"🥉 #{rank}" if rank == 3 else f"#{rank}"))
        col_r, col_a, col_p, col_s = st.columns([1, 1.2, 5, 2])
        with col_r:
            st.markdown(f"<div style='padding-top:12px;'><h3>{rank_badge}</h3></div>", unsafe_allow_html=True)
        with col_a:
            render_player_avatar(data.get("avatar"), width=50)
        with col_p:
            st.markdown(f"<div style='padding-top:12px;'><h3><strong>{member_name}</strong></h3></div>", unsafe_allow_html=True)
        with col_s:
            st.markdown(f"<div style='padding-top:12px;'><h3><strong>{data['total_score']} pts</strong></h3></div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    st.markdown("---")
    st.header("🎭 Broadcast Chaos Metrics")
    st.caption("Track cumulative broadcast totals across published episodes to evaluate your season-long projections:")
    
    all_res_weeks = get_sorted_weekly_result_weeks()
    
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    
    weekly_chaos_rows = []
    
    for w_k in all_res_weeks:
        w_data = get_weekly_result(w_k)
        hs_bakers = w_data.get("handshake_bakers", [])
        if isinstance(hs_bakers, list):
            hs_cnt = len(hs_bakers)
            hs_str = ", ".join(hs_bakers) if hs_bakers else "None"
        else:
            hs_cnt = 0
            hs_str = "None"
            
        cry_cnt = w_data.get("crying_count", 0)
        try:
            cry_cnt = int(cry_cnt)
        except (ValueError, TypeError):
            cry_cnt = 0
            
        inn_cnt = w_data.get("innuendo_count", 0)
        try:
            inn_cnt = int(inn_cnt)
        except (ValueError, TypeError):
            inn_cnt = 0
            
        tot_hs += hs_cnt
        tot_cry += cry_cnt
        tot_inn += inn_cnt
        
        weekly_chaos_rows.append({
            "Episode Week": f"Week {w_k}",
            "🤝 Hollywood Handshakes": f"{hs_cnt} ({hs_str})",
            "😢 Crying Incidents": f"{cry_cnt}",
            "💬 Sexual Innuendos": f"{inn_cnt}"
        })

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("🤝 Total Hollywood Handshakes", f"{tot_hs}")
    with col_m2:
        st.metric("😢 Total Crying Incidents", f"{tot_cry}")
    with col_m3:
        st.metric("💬 Total Sexual Innuendos", f"{tot_inn}")
        
    if weekly_chaos_rows:
        with st.expander("📊 Episode-by-Episode Chaos Breakdown", expanded=False):
            st.dataframe(pd.DataFrame(weekly_chaos_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Broadcast chaos counts will populate here automatically as episode actuals are published by the admin.")

    st.markdown("---")
    st.header("🔍 Individual Player Scorecards")
    player_names = list(st.session_state.league_members.keys())
    selected_player = st.selectbox("Choose Player Scorecard to View:", player_names)
    p_data = st.session_state.league_members[selected_player]
    
    col_sc1, col_sc2 = st.columns([1, 4])
    with col_sc1:
        render_player_avatar(p_data.get("avatar"), width=120, caption=f"{selected_player}'s Avatar")
    with col_sc2:
        st.subheader(f"📊 Detailed Point Matrix: {selected_player}")
        st.markdown(f"**Total Combined Score:** `{p_data['total_score']} pts`")
        
        all_weeks = [w for w in get_sorted_weekly_result_weeks() if w != 1]
        if not all_weeks:
            st.info("No episode broadcast results published yet. Weekly line-item calculations will appear here after Episode 1!")
        else:
            st.markdown("#### 📅 Weekly Episodic Scorecards")
            for w_num in all_weeks:
                res = get_weekly_result(w_num)
                pred_w = p_data["weekly_picks"].get(w_num, {})
                with st.expander(f"Week {w_num} Breakdown (Episode Results)", expanded=False):
                    raw_pts = calculate_weekly_score(pred_w, res, w_num)
                    weekly_scores_all = {m: calculate_weekly_score(m_data["weekly_picks"].get(w_num, {}), res, w_num) for m, m_data in st.session_state.league_members.items()}
                    max_score_w = max(weekly_scores_all.values()) if weekly_scores_all else 0
                    has_star_bonus = (raw_pts == max_score_w and raw_pts > 0)
                    
                    hs_stamps = res.get("handshake_timestamps")
                    cry_stamps = res.get("crying_timestamps")
                    if hs_stamps or cry_stamps:
                        st.info("ℹ️ **Broadcast Context & Video Timestamps:**")
                        if hs_stamps:
                            st.write(f"🤝 **Handshake Timestamps & Notes:** {hs_stamps}")
                        if cry_stamps:
                            st.write(f"😢 **Crying Incident Timestamps & Notes:** {cry_stamps}")
                            
                    itemized_rows = get_weekly_itemized_breakdown(pred_w, res, w_num)
                    if has_star_bonus:
                        itemized_rows.append({
                            "Category": "🌟 Star League Member Bonus",
                            "Your Prediction": "Highest Weekly Scorer",
                            "Actual Broadcast Result": f"Highest Score ({raw_pts} pts)",
                            "Points Awarded": "+5 pts",
                            "Details & Explanations": "Awarded +5 bonus pts for top weekly performance!"
                        })
                    st.dataframe(pd.DataFrame(itemized_rows), use_container_width=True, hide_index=True)
                    st.markdown(f"**Week {w_num} Total Awarded:** `{p_data['weekly_breakdown'].get(w_num, raw_pts + (5 if has_star_bonus else 0))} pts`")

            if st.session_state.season_results:
                st.markdown("#### 🌟 Season-Long Predictions")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Player Prediction Portal")
    roster_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    active_sub_player = st.selectbox("Select Your Player Profile to Submit Picks:", ["-- Select Your Name --"] + roster_players)
    
    if active_sub_player != "-- Select Your Name --":
        p_pin = st.session_state.league_members[active_sub_player].get("pin")
        is_authed = st.session_state.authenticated_players.get(active_sub_player, False)
        
        if p_pin is not None and not is_authed:
            st.subheader(f"🔒 Enter PIN for {active_sub_player}")
            entered_pin = st.text_input("4-Digit PIN:", type="password", key=f"pin_entry_{active_sub_player}")
            if st.button("Unlock Ballot", key=f"unlock_btn_{active_sub_player}"):
                if entered_pin == p_pin:
                    st.session_state.authenticated_players[active_sub_player] = True
                    st.success("Unlocked! Proceed to submit your predictions below.")
                    st.rerun()
                else:
                    st.error("Incorrect PIN.")
        else:
            if p_pin is None:
                st.info("ℹ️ Optional: Set a 4-digit PIN below to lock your profile and prevent accidental edits by other players!")
                new_pin = st.text_input("Create 4-Digit PIN:", type="password", key=f"create_pin_{active_sub_player}")
                if st.button("Set PIN", key=f"btn_set_pin_{active_sub_player}"):
                    if len(new_pin) == 4 and new_pin.isdigit():
                        st.session_state.league_members[active_sub_player]["pin"] = new_pin
                        st.session_state.authenticated_players[active_sub_player] = True
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success("PIN set successfully! Profile locked.")
                        st.rerun()
                    else:
                        st.error("PIN must be exactly 4 numeric digits.")
            
            st.markdown("---")
            st.subheader(f"🌟 Season-Long Projections (Locks in Week 2)")
            existing_s = st.session_state.league_members[active_sub_player].get("season_picks", {})
            
            if st.session_state.current_week > 2:
                st.warning("🔒 Season-long predictions are locked for the season!")
            else:
                def_w = existing_s.get("winner")
                opts_w, idx_w = get_tech_options(ALL_BAKERS, f"{active_sub_player}_w_sel", def_w, "-- Select Winner --")
                user_winner = st.selectbox("Predict Overall Season Champion [40 pts or 15 pts finalist consolation]", opts_w, index=idx_w, key=f"{active_sub_player}_w_sel")
                
                def_semis = existing_s.get("semifinalists", [])
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", [b for b in ALL_BAKERS if b != user_winner], default=def_semis, key=f"{active_sub_player}_semis_sel")
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=existing_s.get("handshakes", 0), key=f"{active_sub_player}_hs_pick")
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=existing_s.get("crying", 0), key=f"{active_sub_player}_cry_pick")
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=existing_s.get("innuendos", 0), key=f"{active_sub_player}_inn_pick")
                
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

            # WEEKLY BALLOT FORM
            st.markdown("---")
            st.subheader(f"📅 Submit Weekly Predictions: Week {st.session_state.current_week}")
            
            if st.session_state.current_week == 1:
                st.info("🔍 **Week 1 Scouting Period:** Episode 1 serves as the official scouting phase to evaluate the bakers. No predictions can be submitted during Week 1. Season-long projections and Week 2 prediction ballots will open in **Week 2**!")
            else:
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
                cur_w = st.session_state.current_week
                
                with st.form(f"weekly_predictions_form_{active_sub_player}_w{cur_w}"):
                    weekly_picks = {}
                    
                    if cur_w == 10:
                        def_champ = existing_w.get("show_champion")
                        opts_champ, champ_idx = get_tech_options(active_bakers, f"{active_sub_player}_w10_champ", def_champ, "-- Select Show Champion --")
                        champ_sel = st.selectbox("Predict Show Champion [15 pts at stake]", opts_champ, index=champ_idx, key=f"{active_sub_player}_w10_champ")
                        weekly_picks["show_champion"] = champ_sel if not champ_sel.startswith("-- Select") else "None"
                        
                        st.write("Predict Technical Challenge Final Rank:")
                        def_trk = existing_w.get("tech_rank", [None, None, None])
                        opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w10_t1", def_trk[0] if len(def_trk)>0 else None, "-- Select 1st Place --")
                        t1 = st.selectbox("Technical 1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w10_t1")
                        opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w10_t2", def_trk[1] if len(def_trk)>1 else None, "-- Select 2nd Place --")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w10_t2")
                        opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w10_t3", def_trk[2] if len(def_trk)>2 else None, "-- Select 3rd Place --")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w10_t3")
                        weekly_picks["tech_rank"] = [t1, t2, t3]
                        
                    elif cur_w == 9:
                        def_sb = existing_w.get("star_baker")
                        opts_sb, sb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w9_sb", def_sb, "-- Select Star Baker --")
                        sb_sel = st.selectbox("Predict Star Baker [5 pts at stake]", opts_sb, index=sb_idx, key=f"{active_sub_player}_w9_sb")
                        weekly_picks["star_baker"] = sb_sel if not sb_sel.startswith("-- Select") else "None"
                        
                        def_el = existing_w.get("eliminated")
                        if is_double_elim:
                            el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                            el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                            opts_el1, el1_i = get_tech_options(active_bakers, f"{active_sub_player}_w9_el1", el1, "-- Select Eliminated Baker #1 --")
                            opts_el2, el2_i = get_tech_options(active_bakers, f"{active_sub_player}_w9_el2", el2, "-- Select Eliminated Baker #2 --")
                            elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", opts_el1, index=el1_i, key=f"{active_sub_player}_w9_el1")
                            elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", opts_el2, index=el2_i, key=f"{active_sub_player}_w9_el2")
                            weekly_picks["eliminated"] = [b for b in [elim_1, elim_2] if not b.startswith("-- Select")]
                        else:
                            opts_el, el_idx = get_tech_options(active_bakers, f"{active_sub_player}_w9_el", def_el, "-- Select Eliminated Baker --")
                            el_sel = st.selectbox("Predict Eliminated Baker [5 pts at stake]", opts_el, index=el_idx, key=f"{active_sub_player}_w9_el")
                            weekly_picks["eliminated"] = el_sel if not el_sel.startswith("-- Select") else "None"
                        
                        st.write("Predict Technical Challenge Final Rank:")
                        def_trk = existing_w.get("tech_rank", [None, None, None, None])
                        opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t1", def_trk[0] if len(def_trk)>0 else None, "-- Select 1st Place --")
                        t1 = st.selectbox("Technical 1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w9_t1")
                        opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t2", def_trk[1] if len(def_trk)>1 else None, "-- Select 2nd Place --")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w9_t2")
                        opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t3", def_trk[2] if len(def_trk)>2 else None, "-- Select 3rd Place --")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w9_t3")
                        opts4, idx4 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t4", def_trk[3] if len(def_trk)>3 else None, "-- Select 4th Place --")
                        t4 = st.selectbox("Technical 4th Place [3 pts]", opts4, index=idx4, key=f"{active_sub_player}_w9_t4")
                        weekly_picks["tech_rank"] = [t1, t2, t3, t4]

                    elif cur_w == 8:
                        col1, col2 = st.columns(2)
                        with col1:
                            def_sb = existing_w.get("star_baker")
                            opts_sb, sb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_sb", def_sb, "-- Select Star Baker --")
                            sb_sel = st.selectbox("Predict Star Baker [5 pts at stake]", opts_sb, index=sb_idx, key=f"{active_sub_player}_w8_sb")
                            weekly_picks["star_baker"] = sb_sel if not sb_sel.startswith("-- Select") else "None"
                            
                            def_inl = existing_w.get("in_line_sb")
                            opts_inl, inl_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_inl", def_inl, "-- Select In Line Baker --")
                            inl_sel = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", opts_inl, index=inl_idx, key=f"{active_sub_player}_w8_inl")
                            weekly_picks["in_line_sb"] = inl_sel if not inl_sel.startswith("-- Select") else "None"
                        with col2:
                            def_el = existing_w.get("eliminated")
                            def_trb = existing_w.get("in_trouble")
                            opts_trb, trb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_trb", def_trb, "-- Select In Trouble Baker --")
                            trb_sel = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", opts_trb, index=trb_idx, key=f"{active_sub_player}_w8_trb")
                            weekly_picks["in_trouble"] = trb_sel if not trb_sel.startswith("-- Select") else "None"
                            
                            if is_double_elim:
                                el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                                el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                                opts_el1, el1_i = get_tech_options(active_bakers, f"{active_sub_player}_w8_el1", el1, "-- Select Eliminated Baker #1 --")
                                opts_el2, el2_i = get_tech_options(active_bakers, f"{active_sub_player}_w8_el2", el2, "-- Select Eliminated Baker #2 --")
                                elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", opts_el1, index=el1_i, key=f"{active_sub_player}_w8_el1")
                                elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", opts_el2, index=el2_i, key=f"{active_sub_player}_w8_el2")
                                weekly_picks["eliminated"] = [b for b in [elim_1, elim_2] if not b.startswith("-- Select")]
                            else:
                                opts_el, el_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_el", def_el, "-- Select Eliminated Baker --")
                                el_sel = st.selectbox("Predict Eliminated Baker [5 pts at stake]", opts_el, index=el_idx, key=f"{active_sub_player}_w8_el")
                                weekly_picks["eliminated"] = el_sel if not el_sel.startswith("-- Select") else "None"
                        
                        st.write("Predict Technical Challenge Final Rank:")
                        def_trk = existing_w.get("tech_rank", [None, None, None, None, None])
                        opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t1", def_trk[0] if len(def_trk)>0 else None, "-- Select 1st Place --")
                        t1 = st.selectbox("Technical 1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w8_t1")
                        opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t2", def_trk[1] if len(def_trk)>1 else None, "-- Select 2nd Place --")
                        t2 = st.selectbox("Technical 2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w8_t2")
                        opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t3", def_trk[2] if len(def_trk)>2 else None, "-- Select 3rd Place --")
                        t3 = st.selectbox("Technical 3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w8_t3")
                        opts4, idx4 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t4", def_trk[3] if len(def_trk)>3 else None, "-- Select 4th Place --")
                        t4 = st.selectbox("Technical 4th Place [2 pts]", opts4, index=idx4, key=f"{active_sub_player}_w8_t4")
                        opts5, idx5 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t5", def_trk[4] if len(def_trk)>4 else None, "-- Select 5th Place --")
                        t5 = st.selectbox("Technical 5th Place [3 pts]", opts5, index=idx5, key=f"{active_sub_player}_w8_t5")
                        weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                        
                    else:
                        # Standard Weeks 2-7
                        col1, col2 = st.columns(2)
                        with col1:
                            def_sb = existing_w.get("star_baker")
                            opts_sb, sb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_sb", def_sb, "-- Select Star Baker --")
                            sb_sel = st.selectbox("Predict Star Baker [5 pts at stake]", opts_sb, index=sb_idx, key=f"{active_sub_player}_w{cur_w}_std_sb")
                            weekly_picks["star_baker"] = sb_sel if not sb_sel.startswith("-- Select") else "None"
                            
                            def_inl = existing_w.get("in_line_sb")
                            opts_inl, inl_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_inl", def_inl, "-- Select In Line Baker --")
                            inl_sel = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", opts_inl, index=inl_idx, key=f"{active_sub_player}_w{cur_w}_std_inl")
                            weekly_picks["in_line_sb"] = inl_sel if not inl_sel.startswith("-- Select") else "None"
                        with col2:
                            def_el = existing_w.get("eliminated")
                            def_trb = existing_w.get("in_trouble")
                            opts_trb, trb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_trb", def_trb, "-- Select In Trouble Baker --")
                            trb_sel = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", opts_trb, index=trb_idx, key=f"{active_sub_player}_w{cur_w}_std_trb")
                            weekly_picks["in_trouble"] = trb_sel if not trb_sel.startswith("-- Select") else "None"
                            
                            if is_double_elim:
                                el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                                el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                                opts_el1, el1_i = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el1", el1, "-- Select Eliminated Baker #1 --")
                                opts_el2, el2_i = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el2", el2, "-- Select Eliminated Baker #2 --")
                                elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", opts_el1, index=el1_i, key=f"{active_sub_player}_w{cur_w}_std_el1")
                                elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", opts_el2, index=el2_i, key=f"{active_sub_player}_w{cur_w}_std_el2")
                                weekly_picks["eliminated"] = [b for b in [elim_1, elim_2] if not b.startswith("-- Select")]
                            else:
                                opts_el, el_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el", def_el, "-- Select Eliminated Baker --")
                                el_sel = st.selectbox("Predict Eliminated Baker [5 pts at stake]", opts_el, index=el_idx, key=f"{active_sub_player}_w{cur_w}_std_el")
                                weekly_picks["eliminated"] = el_sel if not el_sel.startswith("-- Select") else "None"
                            
                        st.markdown("---")
                        st.write("Predict Technical Challenge Placements:")
                        col_t_top, col_t_bot = st.columns(2)
                        
                        def_top3 = existing_w.get("tech_top_3", [None, None, None])
                        def_bot3 = existing_w.get("tech_bottom_3", [None, None, None])
                        
                        with col_t_top:
                            opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t1", def_top3[0] if len(def_top3)>0 else None, "-- Select 1st Place --")
                            t1 = st.selectbox("1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w{cur_w}_std_t1")
                            opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t2", def_top3[1] if len(def_top3)>1 else None, "-- Select 2nd Place --")
                            t2 = st.selectbox("2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w{cur_w}_std_t2")
                            opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t3", def_top3[2] if len(def_top3)>2 else None, "-- Select 3rd Place --")
                            t3 = st.selectbox("3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w{cur_w}_std_t3")
                            weekly_picks["tech_top_3"] = [t1, t2, t3]
                            
                        with col_t_bot:
                            opts_b3, idx_b3 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b3", def_bot3[0] if len(def_bot3)>0 else None, "-- Select 3rd-to-last Place --")
                            b_3rd_last = st.selectbox("3rd-to-last Place [2 pts]", opts_b3, index=idx_b3, key=f"{active_sub_player}_w{cur_w}_std_b3")
                            opts_b2, idx_b2 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b2", def_bot3[1] if len(def_bot3)>1 else None, "-- Select 2nd-to-last Place --")
                            b_2nd_last = st.selectbox("2nd-to-last Place [2 pts]", opts_b2, index=idx_b2, key=f"{active_sub_player}_w{cur_w}_std_b2")
                            opts_b1, idx_b1 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b1", def_bot3[2] if len(def_bot3)>2 else None, "-- Select Last Place --")
                            b_last = st.selectbox("Last Place [3 pts]", opts_b1, index=idx_b1, key=f"{active_sub_player}_w{cur_w}_std_b1")
                            weekly_picks["tech_bottom_3"] = [b_3rd_last, b_2nd_last, b_last]

                    submitted = st.form_submit_button("Submit Predictions")
                    if submitted:
                        import collections
                        
                        # 1. Main Categories Check
                        main_bakers = []
                        for k in ["star_baker", "in_line_sb", "in_trouble", "show_champion"]:
                            v = weekly_picks.get(k)
                            if v and isinstance(v, str) and not v.startswith("-- Select") and v != "None":
                                main_bakers.append(v)
                        el = weekly_picks.get("eliminated")
                        if isinstance(el, list):
                            for b in el:
                                if b and not b.startswith("-- Select") and b != "None":
                                    main_bakers.append(b)
                        elif isinstance(el, str) and not el.startswith("-- Select") and el != "None":
                            main_bakers.append(el)
                        
                        main_dups = [b for b, cnt in collections.Counter(main_bakers).items() if cnt > 1]

                        # 2. Technical Placements Check
                        tech_bakers = []
                        for tk in ["tech_top_3", "tech_bottom_3", "tech_rank"]:
                            tv = weekly_picks.get(tk)
                            if isinstance(tv, list):
                                for b in tv:
                                    if b and not b.startswith("-- Select") and b != "None":
                                        tech_bakers.append(b)

                        tech_dups = [b for b, cnt in collections.Counter(tech_bakers).items() if cnt > 1]

                        if main_dups or tech_dups:
                            err_msgs = []
                            if main_dups:
                                err_msgs.append("• **Main Categories:** **" + ", ".join(sorted(list(set(main_dups)))) + "** cannot be chosen for multiple main picks (Star Baker, Eliminated, In Line, In Trouble).")
                            if tech_dups:
                                err_msgs.append("• **Technical Placements:** **" + ", ".join(sorted(list(set(tech_dups)))) + "** cannot be chosen for multiple Technical positions.")
                            
                            st.error("⚠️ **Duplicate Selection Error:**\n\n" + "\n".join(err_msgs) + "\n\nPlease ensure each section uses unique bakers, then submit again.")
                        else:
                            st.session_state.league_members[active_sub_player]["weekly_picks"][cur_w] = weekly_picks
                            ai_picks = generate_ai_brian_weekly_picks(cur_w, active_bakers, is_double_elim=is_double_elim)
                            st.session_state.league_members["AI Brian"]["weekly_picks"][cur_w] = ai_picks
                            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                            st.success(f"Predictions saved for {active_sub_player}!")

# --- TAB 3: BAKER ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Career Performance Matrix")
    current_eliminated_latest = get_current_eliminated_bakers(st.session_state.current_week)
    
    baker_stats = {}
    for baker in ALL_BAKERS:
        baker_stats[baker] = {
            "star_baker_cnt": 0,
            "in_line_cnt": 0,
            "in_trouble_cnt": 0,
            "handshake_cnt": 0,
            "tech_ranks": [],
            "tech_rank_pcts": []
        }
        
    for w in get_sorted_weekly_result_weeks():
        res = get_weekly_result(w)
        sb = res.get("star_baker")
        if sb and sb in baker_stats:
            baker_stats[sb]["star_baker_cnt"] += 1
            
        for inl in res.get("in_line_sb", []):
            if inl in baker_stats: baker_stats[inl]["in_line_cnt"] += 1
            
        for trb in res.get("in_trouble", []):
            if trb in baker_stats: baker_stats[trb]["in_trouble_cnt"] += 1
            
        for hs in res.get("handshake_bakers", []):
            if hs in baker_stats: baker_stats[hs]["handshake_cnt"] += 1
            
        if w >= 8:
            tr = res.get("tech_rank", [])
            tot = len(tr)
            for idx, b in enumerate(tr):
                if b in baker_stats:
                    baker_stats[b]["tech_ranks"].append(idx + 1)
                    if tot > 1: baker_stats[b]["tech_rank_pcts"].append(idx / (tot - 1))
        else:
            t3 = res.get("tech_top_3", [])
            b3 = res.get("tech_bottom_3", [])
            for idx, b in enumerate(t3):
                if b in baker_stats: baker_stats[b]["tech_ranks"].append(idx + 1)
            for idx, b in enumerate(b3):
                if b in baker_stats: baker_stats[b]["tech_ranks"].append(10 - idx)

    st.subheader("📊 Individual Contestant Deep Dive")
    sel_baker = st.selectbox("Select Baker to Inspect:", ALL_BAKERS)
    s = baker_stats[sel_baker]
    is_eliminated = sel_baker in current_eliminated_latest
    
    col_img, col_metrics = st.columns([1, 2])
    with col_img:
        b_img = load_baker_image(sel_baker)
        if b_img:
            st.image(b_img, width=200, caption=f"{sel_baker} ('Class of 2026')")
        else:
            st.markdown(f"### 🧁 {sel_baker}")
            st.write("*(No portrait uploaded)*")
            
        b_url = BAKER_INFO.get(sel_baker, {}).get("url")
        if b_url:
            st.markdown(f"👉 [Read Official Bio on Bake Off Website]({b_url})")
            
    with col_metrics:
        status_text = "❌ Eliminated" if is_eliminated else "🟢 Active in the Tent"
        st.markdown(f"### Status: **{status_text}**")
        
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Star Baker Wins", f"{s['star_baker_cnt']} 🌟")
        with m2: st.metric("In Line Nominee", f"{s['in_line_cnt']} 📈")
        with m3: st.metric("In Trouble", f"{s['in_trouble_cnt']} ⚠️")
        with m4: st.metric("Hollywood Handshakes", f"{s['handshake_cnt']} 🤝")
        
        st.markdown("---")
        avg_rank = (sum(s["tech_ranks"]) / len(s["tech_ranks"])) if s["tech_ranks"] else "N/A"
        if isinstance(avg_rank, float): avg_rank = f"{avg_rank:.1f}"
        st.write(f"**Average Technical Rank:** `{avg_rank}`")

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 Admin Portal")
    admin_pw = st.text_input("Enter Admin Password:", type="password", key="admin_pw_entry")
    if admin_pw == "gbbs2026":
        st.session_state.admin_authenticated = True
        st.success("Admin Authenticated!")
    elif admin_pw != "":
        st.error("Incorrect Admin Password.")
        
    if st.session_state.admin_authenticated:
        st.subheader("📢 Publish Official Episode Results")
        cur_w = st.session_state.current_week
        
        current_eliminated = get_current_eliminated_bakers(cur_w)
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        existing_res = get_weekly_result(cur_w)
        
        with st.form(f"admin_results_form_w{cur_w}"):
            st.markdown(f"### 📺 Episode {cur_w} Official Broadcast Results")
            actuals = {}
            
            if cur_w == 10:
                def_ch = existing_res.get("show_champion")
                opts_ch, idx_ch = get_tech_options(active_bakers, f"admin_champ_w10", def_ch, "-- Select Show Champion --")
                actuals["show_champion"] = st.selectbox("Official Show Champion", opts_ch, index=idx_ch, key=f"admin_champ_w10")
                
                st.markdown("### Technical Challenge Official Ranks (Top 3)")
                def_rk = existing_res.get("tech_rank", [None, None, None])
                opts1, idx1 = get_tech_options(active_bakers, f"admin_w10_t1", def_rk[0] if len(def_rk)>0 else None, "-- Select 1st Place --")
                t1 = st.selectbox("1st Place", opts1, index=idx1, key=f"admin_w10_t1")
                opts2, idx2 = get_tech_options(active_bakers, f"admin_w10_t2", def_rk[1] if len(def_rk)>1 else None, "-- Select 2nd Place --")
                t2 = st.selectbox("2nd Place", opts2, index=idx2, key=f"admin_w10_t2")
                opts3, idx3 = get_tech_options(active_bakers, f"admin_w10_t3", def_rk[2] if len(def_rk)>2 else None, "-- Select 3rd Place --")
                t3 = st.selectbox("3rd Place", opts3, index=idx3, key=f"admin_w10_t3")
                actuals["tech_rank"] = [t1, t2, t3]
            else:
                def_sb = existing_res.get("star_baker")
                opts_sb, idx_sb = get_tech_options(active_bakers, f"admin_sb_w{cur_w}", def_sb, "-- Select Star Baker --")
                actuals["star_baker"] = st.selectbox("Official Star Baker", opts_sb, index=idx_sb, key=f"admin_sb_w{cur_w}")
                
                def_inl = existing_res.get("in_line_sb", [])
                def_trb = existing_res.get("in_trouble", [])
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line for Star Baker' Nominees", active_bakers, default=def_inl, key=f"admin_in_line_w{cur_w}")
                actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=def_trb, key=f"admin_in_trouble_w{cur_w}")
                
                def_el = existing_res.get("eliminated", [])
                if isinstance(def_el, str): def_el = [def_el] if def_el != "None" else []
                actuals["eliminated"] = st.multiselect("Actual Eliminated Baker(s)", active_bakers, default=def_el, key=f"admin_elim_w{cur_w}")
                
                if cur_w >= 8:
                    st.markdown("### Technical Challenge Official Ranks")
                    def_rk = existing_res.get("tech_rank", [])
                    if cur_w == 8:
                        r_keys = [f"admin_w8_t{r}" for r in range(1, 6)]
                        r_picks = []
                        for idx, rk in enumerate(r_keys):
                            def_val = def_rk[idx] if len(def_rk) > idx else None
                            opts, i_val = get_tech_options(active_bakers, rk, def_val, f"-- Select {idx+1} Place --")
                            r_picks.append(st.selectbox(f"Place #{idx+1}", opts, index=i_val, key=rk))
                        actuals["tech_rank"] = r_picks
                    elif cur_w == 9:
                        r_keys = [f"admin_w9_t{r}" for r in range(1, 5)]
                        r_picks = []
                        for idx, rk in enumerate(r_keys):
                            def_val = def_rk[idx] if len(def_rk) > idx else None
                            opts, i_val = get_tech_options(active_bakers, rk, def_val, f"-- Select {idx+1} Place --")
                            r_picks.append(st.selectbox(f"Place #{idx+1}", opts, index=i_val, key=rk))
                        actuals["tech_rank"] = r_picks
                else:
                    st.markdown("### Technical Challenge Official Placements")
                    def_t3 = existing_res.get("tech_top_3", [None, None, None])
                    def_b3 = existing_res.get("tech_bottom_3", [None, None, None])
                    
                    opts1, i1 = get_tech_options(active_bakers, f"admin_std_t1_w{cur_w}", def_t3[0], "-- Select 1st Place --")
                    t1 = st.selectbox("1st Place", opts1, index=i1, key=f"admin_std_t1_w{cur_w}")
                    opts2, i2 = get_tech_options(active_bakers, f"admin_std_t2_w{cur_w}", def_t3[1], "-- Select 2nd Place --")
                    t2 = st.selectbox("2nd Place", opts2, index=i2, key=f"admin_std_t2_w{cur_w}")
                    opts3, i3 = get_tech_options(active_bakers, f"admin_std_t3_w{cur_w}", def_t3[2], "-- Select 3rd Place --")
                    t3 = st.selectbox("3rd Place", opts3, index=i3, key=f"admin_std_t3_w{cur_w}")
                    actuals["tech_top_3"] = [t1, t2, t3]
                    
                    opts_b3, ib3 = get_tech_options(active_bakers, f"admin_std_b3_w{cur_w}", def_b3[0], "-- Select 3rd-to-last Place --")
                    b3 = st.selectbox("3rd-to-last Place", opts_b3, index=ib3, key=f"admin_std_b3_w{cur_w}")
                    opts_b2, ib2 = get_tech_options(active_bakers, f"admin_std_b2_w{cur_w}", def_b3[1], "-- Select 2nd-to-last Place --")
                    b2 = st.selectbox("2nd-to-last Place", opts_b2, index=ib2, key=f"admin_std_b2_w{cur_w}")
                    opts_b1, ib1 = get_tech_options(active_bakers, f"admin_std_b1_w{cur_w}", def_b3[2], "-- Select Last Place --")
                    b1 = st.selectbox("Last Place", opts_b1, index=ib1, key=f"admin_std_b1_w{cur_w}")
                    actuals["tech_bottom_3"] = [b3, b2, b1]

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            def_hs_b = existing_res.get("handshake_bakers", [])
            act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, default=def_hs_b, key=f"handshake_bakers_w{cur_w}")
            def_hs_t = existing_res.get("handshake_timestamps", "")
            act_handshake_stamps = st.text_input("Handshake Video Timestamps & Context", value=def_hs_t, key=f"handshake_stamps_w{cur_w}")

            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            def_cry_c = existing_res.get("crying_count", 0)
            act_crying_cnt = st.number_input("Crying Scenes Count in Episode", min_value=0, value=int(def_cry_c), key=f"crying_cnt_w{cur_w}")
            def_cry_t = existing_res.get("crying_timestamps", "")
            act_crying_stamps = st.text_input("Crying Scene Video Timestamps & Context", value=def_cry_t, key=f"crying_stamps_w{cur_w}")

            st.markdown("### 💬 Weekly Sexual Innuendos Count")
            def_inn_c = existing_res.get("innuendo_count", 0)
            act_innuendo_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=int(def_inn_c), key=f"innuendo_cnt_w{cur_w}")

            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt

            if cur_w == 10:
                st.markdown("---")
                st.markdown("### 🏆 Season-Long Final Actual Broadcast Results")
                existing_season = st.session_state.season_results or {}
                actuals_season = {}
                def_w = existing_season.get("winner")
                opts_w, i_w = get_tech_options(ALL_BAKERS, "admin_season_w", def_w, "-- Select Winner --")
                actuals_season["winner"] = st.selectbox("Official Overall Season Champion", opts_w, index=i_w, key="admin_season_w")
                
                def_s = existing_season.get("semifinalists", [])
                actuals_season["semifinalists"] = st.multiselect("Official 3 Other Semifinalists", ALL_BAKERS, default=def_s, key="admin_season_semis")
                
                def_f = existing_season.get("finalists", [])
                actuals_season["finalists"] = st.multiselect("Official 3 Finalists", ALL_BAKERS, default=def_f, key="admin_season_finalists")
                
                actuals_season["handshakes"] = st.number_input("Total Season Handshakes Count", min_value=0, value=existing_season.get("handshakes", 0), key="admin_season_hs")
                actuals_season["crying"] = st.number_input("Total Season Crying Count", min_value=0, value=existing_season.get("crying", 0), key="admin_season_cry")
                actuals_season["innuendos"] = st.number_input("Total Season Innuendos Count", min_value=0, value=existing_season.get("innuendos", 0), key="admin_season_inn")

            admin_submitted = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if admin_submitted:
                st.session_state.weekly_results[cur_w] = actuals
                if cur_w == 10:
                    st.session_state.season_results = actuals_season
                    
                # Recalculate standings
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
                        season_pred = m_data.get("season_picks", {})
                        season_score = calculate_season_score(season_pred, st.session_state.season_results)
                        m_data["season_score"] = season_score
                        
                for m_name, m_data in st.session_state.league_members.items():
                    weekly_total = sum(m_data["weekly_breakdown"].values())
                    season_total = m_data.get("season_score", 0)
                    m_data["total_score"] = weekly_total + season_total
                    
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success("Leaderboard updated! All player predictions scored and verified.")
