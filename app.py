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

def load_baker_image(baker_name):
    """Smart case-insensitive and multi-extension baker portrait image loader."""
    if not baker_name:
        return None
    target = str(baker_name).lower().strip()
    search_dirs = [".", "assets", "assets/bakers"]
    valid_exts = [".jpg", ".jpeg", ".png", ".webp"]
    
    for s_dir in search_dirs:
        if os.path.exists(s_dir):
            try:
                for filename in os.listdir(s_dir):
                    stem, ext = os.path.splitext(filename)
                    if stem.lower().strip() == target and ext.lower() in valid_exts:
                        full_p = os.path.join(s_dir, filename)
                        try:
                            return Image.open(full_p)
                        except Exception:
                            pass
            except Exception:
                pass
    return None

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
            st.markdown(f"<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)

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
                        score += (3 if idx in [0, 4] else 2)
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 4:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += (3 if idx in [0, 3] else 2)
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            exact_count = sum(1 for idx, b in enumerate(pred_rank) if act_rank[idx] == b)
            if exact_count == 3:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += (3 if idx == 0 else 2)
    else:
        # Weeks 2-7
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

def get_weekly_itemized_breakdown(pred, act, week):
    rows = []
    if not pred or not act:
        return rows
        
    if week == 10:
        p_champ = pred.get("show_champion", "None")
        a_champ = act.get("show_champion", "None")
        pts_champ = 15 if (p_champ == a_champ and p_champ != "None") else 0
        rows.append({
            "Category": "🏆 Show Champion",
            "Your Prediction": p_champ,
            "Actual Broadcast Result": a_champ,
            "Points Awarded": f"{pts_champ} pts",
            "Details & Explanations": f"Correctly predicted Season Champion {p_champ} (+15 pts)" if pts_champ == 15 else "Incorrect prediction (0 pts)"
        })
    else:
        p_sb = pred.get("star_baker", "None")
        a_sb = act.get("star_baker", "None")
        pts_sb = 5 if (p_sb == a_sb and p_sb != "None") else 0
        rows.append({
            "Category": "🌟 Star Baker",
            "Your Prediction": p_sb,
            "Actual Broadcast Result": a_sb,
            "Points Awarded": f"{pts_sb} pts",
            "Details & Explanations": f"Correctly predicted Star Baker {p_sb} (+5 pts)" if pts_sb == 5 else "Incorrect prediction (0 pts)"
        })

        p_el = pred.get("eliminated", "None")
        a_el = act.get("eliminated", "None")
        a_el_str = ", ".join(a_el) if isinstance(a_el, list) else str(a_el)
        p_el_str = ", ".join(p_el) if isinstance(p_el, list) else str(p_el)
        
        pts_el = 0
        if isinstance(a_el, list):
            if isinstance(p_el, list):
                pts_el = sum(5 for p in p_el if p in a_el)
            elif p_el in a_el:
                pts_el = 5
        elif a_el != "None":
            if isinstance(p_el, list) and a_el in p_el:
                pts_el = 5
            elif p_el == a_el:
                pts_el = 5
                
        rows.append({
            "Category": "❌ Eliminated Baker",
            "Your Prediction": p_el_str,
            "Actual Broadcast Result": a_el_str,
            "Points Awarded": f"{pts_el} pts",
            "Details & Explanations": f"Correctly predicted elimination (+{pts_el} pts)" if pts_el > 0 else "Incorrect elimination prediction (0 pts)"
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

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    picks = {}
    if not active_bakers:
        return picks
    if week == 10:
        picks["show_champion"] = random.choice(active_bakers)
    else:
        picks["star_baker"] = random.choice(active_bakers)
        rem = [b for b in active_bakers if b != picks["star_baker"]]
        if is_double_elim and len(rem) >= 2:
            picks["eliminated"] = random.sample(rem, 2)
        elif rem:
            picks["eliminated"] = random.choice(rem)
        else:
            picks["eliminated"] = "None"
            
        rem_inl = [b for b in active_bakers if b != picks["star_baker"]]
        picks["in_line_sb"] = random.choice(rem_inl) if rem_inl else picks["star_baker"]
        rem_trb = [b for b in active_bakers if b != picks["star_baker"]]
        picks["in_trouble"] = random.choice(rem_trb) if rem_trb else picks["star_baker"]
        
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_top_3"] = shuffled[:3]
        rem_bot = [b for b in active_bakers if b not in picks["tech_top_3"]]
        random.shuffle(rem_bot)
        picks["tech_bottom_3"] = rem_bot[:3]
        
    return picks

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

# --- 8. NAVIGATION TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Contestant Analytics", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    leaderboard_data = []
    for name, data in st.session_state.league_members.items():
        w_score = 0
        for w in range(1, st.session_state.current_week + 1):
            w_act = get_weekly_result(w)
            w_pred = data.get("weekly_picks", {}).get(w, {})
            w_score += calculate_weekly_score(w_pred, w_act, week=w)
            
        s_score = calculate_season_score(data.get("season_picks", {}), st.session_state.season_results)
        tot = w_score + s_score
        
        leaderboard_data.append({
            "player": name,
            "avatar": data.get("avatar"),
            "weekly_pts": w_score,
            "season_pts": s_score,
            "total_pts": tot
        })
        
    leaderboard_data = sorted(leaderboard_data, key=lambda x: x["total_pts"], reverse=True)
    
    for rank, row in enumerate(leaderboard_data, 1):
        col_rank, col_av, col_name, col_w, col_s, col_tot = st.columns([0.5, 0.8, 3, 1.5, 1.5, 1.5])
        with col_rank:
            st.markdown(f"### #{rank}")
        with col_av:
            render_player_avatar(row["avatar"], width=50)
        with col_name:
            st.markdown(f"### {row['player']}")
        with col_w:
            st.metric("Weekly Pts", f"{row['weekly_pts']} pts")
        with col_s:
            st.metric("Season Pts", f"{row['season_pts']} pts")
        with col_tot:
            st.metric("Total Score", f"{row['total_pts']} pts")
        st.markdown("<hr style='margin: 8px 0; border: 0.5px solid #eee;'>", unsafe_allow_html=True)

    st.markdown("---")
    st.header("🎭 Broadcast Chaos Metrics")
    st.caption("Track cumulative broadcast totals across published episodes to evaluate your season-long projections:")
    
    all_res_weeks = get_sorted_weekly_result_weeks()
    tot_hs, tot_cry, tot_inn = 0, 0, 0
    weekly_chaos_rows = []
    
    for w_k in all_res_weeks:
        w_data = get_weekly_result(w_k)
        hs_bakers = w_data.get("handshake_bakers", [])
        if isinstance(hs_bakers, list):
            hs_cnt = len(hs_bakers)
            hs_str = ", ".join(hs_bakers) if hs_bakers else "None"
        else:
            hs_cnt, hs_str = 0, "None"
            
        cry_cnt = int(w_data.get("crying_count", 0)) if str(w_data.get("crying_count", 0)).isdigit() else 0
        inn_cnt = int(w_data.get("innuendo_count", 0)) if str(w_data.get("innuendo_count", 0)).isdigit() else 0
        
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
    with col_m1: st.metric("🤝 Total Hollywood Handshakes", f"{tot_hs}")
    with col_m2: st.metric("😢 Total Crying Incidents", f"{tot_cry}")
    with col_m3: st.metric("💬 Total Sexual Innuendos", f"{tot_inn}")
        
    if weekly_chaos_rows:
        with st.expander("📊 Episode-by-Episode Chaos Breakdown", expanded=False):
            st.dataframe(pd.DataFrame(weekly_chaos_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Broadcast chaos counts will populate here automatically as episode actuals are published by the admin.")

    st.markdown("---")
    st.header("🔍 Individual Player Scorecards")
    
    roster_sc = sorted(list(st.session_state.league_members.keys()))
    selected_player = st.selectbox("Select Player Scorecard:", roster_sc)
    
    if selected_player:
        p_data = st.session_state.league_members[selected_player]
        col_sc_av, col_sc_info = st.columns([1, 4])
        with col_sc_av:
            render_player_avatar(p_data.get("avatar"), width=120, caption=f"{selected_player}'s Avatar")
        with col_sc_info:
            p_w = sum(calculate_weekly_score(p_data.get("weekly_picks", {}).get(w, {}), get_weekly_result(w), week=w) for w in range(1, st.session_state.current_week + 1))
            p_s = calculate_season_score(p_data.get("season_picks", {}), st.session_state.season_results)
            st.markdown(f"## {selected_player}'s Scorecard")
            st.write(f"**Weekly Total:** {p_w} pts | **Season Projections Total:** {p_s} pts | **Grand Total:** {p_w + p_s} pts")

        st.markdown("### 🗓️ Episode Breakdown")
        for w in range(2, st.session_state.current_week + 1):
            with st.expander(f"Week {w} Breakdown (Episode Results)", expanded=False):
                w_pred = p_data.get("weekly_picks", {}).get(w, {})
                w_act = get_weekly_result(w)
                
                hs_stamps = w_act.get("handshake_timestamps")
                cry_stamps = w_act.get("crying_timestamps")
                if hs_stamps or cry_stamps:
                    st.info("ℹ️ **Broadcast Context & Video Timestamps:**")
                    if hs_stamps: st.write(f"🤝 **Handshake Timestamps & Notes:** {hs_stamps}")
                    if cry_stamps: st.write(f"😢 **Crying Incident Timestamps & Notes:** {cry_stamps}")
                
                breakdown_rows = get_weekly_itemized_breakdown(w_pred, w_act, week=w)
                if breakdown_rows:
                    st.dataframe(pd.DataFrame(breakdown_rows), use_container_width=True, hide_index=True)
                else:
                    st.write("No predictions submitted or actuals published for this week yet.")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    all_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    active_sub_player = st.selectbox("Select Player Name:", ["-- Select Your Name --"] + all_players, key="submit_player_select")
    
    if active_sub_player != "-- Select Your Name --":
        saved_pin = st.session_state.league_members[active_sub_player].get("pin")
        
        if saved_pin is None:
            st.info(f"👋 Welcome {active_sub_player}! Create a 4-digit PIN to lock your profile and secure your predictions.")
            new_pin = st.text_input("Create 4-Digit PIN:", type="password", max_chars=4, key="create_pin_input")
            confirm_pin = st.text_input("Confirm 4-Digit PIN:", type="password", max_chars=4, key="confirm_pin_input")
            if st.button("Set PIN & Lock Profile"):
                if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                    st.session_state.league_members[active_sub_player]["pin"] = new_pin
                    st.session_state.authenticated_players[active_sub_player] = True
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success("PIN created successfully! Your profile is now authenticated.")
                    st.rerun()
                else:
                    st.error("PINs must be 4 digits long and match!")
        else:
            if not st.session_state.authenticated_players.get(active_sub_player, False):
                st.warning(f"🔒 Profile locked for {active_sub_player}.")
                input_pin = st.text_input("Enter 4-Digit PIN to Unlock:", type="password", max_chars=4, key=f"unlock_pin_{active_sub_player}")
                if st.button("Unlock Profile"):
                    if input_pin == saved_pin:
                        st.session_state.authenticated_players[active_sub_player] = True
                        st.success("Profile unlocked!")
                        st.rerun()
                    else:
                        st.error("Incorrect PIN!")

        if st.session_state.authenticated_players.get(active_sub_player, False):
            st.success(f"🔓 Authenticated as **{active_sub_player}**")
            
            cur_w = st.session_state.current_week
            st.subheader(f"🗓️ Week {cur_w} Prediction Form")
            
            if cur_w == 1:
                st.info("🔍 **Week 1 is a Scouting & Preview Period!** No prediction ballots or season projections are submitted in Week 1. Official predictions open in **Week 2**.")
            else:
                active_bakers = [b for b in ALL_BAKERS if b not in get_current_eliminated_bakers(cur_w)]
                existing_w = st.session_state.league_members[active_sub_player].get("weekly_picks", {}).get(cur_w, {})
                is_double_elim = cur_w in [5, 9]
                
                with st.form(f"weekly_form_w{cur_w}_{active_sub_player}"):
                    weekly_picks = {}
                    main_raw = []
                    tech_raw = []
                    
                    def get_tech_options(bakers, key, def_val, placeholder):
                        opts = [placeholder] + bakers
                        curr_val = st.session_state.get(key, def_val)
                        idx = opts.index(curr_val) if curr_val in opts else 0
                        return opts, idx

                    col1, col2 = st.columns(2)
                    with col1:
                        def_sb = existing_w.get("star_baker")
                        opts_sb, sb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_sb", def_sb, "-- Select Star Baker --")
                        sb_sel = st.selectbox("Predict Star Baker [5 pts]", opts_sb, index=sb_idx, key=f"{active_sub_player}_w{cur_w}_std_sb")
                        weekly_picks["star_baker"] = sb_sel if not sb_sel.startswith("-- Select") else "None"
                        main_raw.append(weekly_picks["star_baker"])
                        
                        def_inl = existing_w.get("in_line_sb")
                        opts_inl, inl_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_inl", def_inl, "-- Select In Line Baker --")
                        inl_sel = st.selectbox("Predict In Line for Star Baker [2 pts if nominated]", opts_inl, index=inl_idx, key=f"{active_sub_player}_w{cur_w}_std_inl")
                        weekly_picks["in_line_sb"] = inl_sel if not inl_sel.startswith("-- Select") else "None"
                        main_raw.append(weekly_picks["in_line_sb"])
                    
                    with col2:
                        def_el = existing_w.get("eliminated")
                        def_trb = existing_w.get("in_trouble")
                        opts_trb, trb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_trb", def_trb, "-- Select In Trouble Baker --")
                        trb_sel = st.selectbox("Predict In Trouble of Elimination [2 pts if nominated]", opts_trb, index=trb_idx, key=f"{active_sub_player}_w{cur_w}_std_trb")
                        weekly_picks["in_trouble"] = trb_sel if not trb_sel.startswith("-- Select") else "None"
                        main_raw.append(weekly_picks["in_trouble"])
                        
                        if is_double_elim:
                            el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                            el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                            opts_el1, el1_i = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el1", el1, "-- Select Eliminated Baker #1 --")
                            opts_el2, el2_i = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el2", el2, "-- Select Eliminated Baker #2 --")
                            elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", opts_el1, index=el1_i, key=f"{active_sub_player}_w{cur_w}_std_el1")
                            elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", opts_el2, index=el2_i, key=f"{active_sub_player}_w{cur_w}_std_el2")
                            weekly_picks["eliminated"] = [b for b in [elim_1, elim_2] if not b.startswith("-- Select")]
                            main_raw.extend(weekly_picks["eliminated"])
                        else:
                            opts_el, el_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el", def_el, "-- Select Eliminated Baker --")
                            el_sel = st.selectbox("Predict Eliminated Baker [5 pts]", opts_el, index=el_idx, key=f"{active_sub_player}_w{cur_w}_std_el")
                            weekly_picks["eliminated"] = el_sel if not el_sel.startswith("-- Select") else "None"
                            main_raw.append(weekly_picks["eliminated"])
                        
                    st.markdown("---")
                    st.write("Predict Technical Challenge Placements:")
                    col_t_top, col_t_bot = st.columns(2)
                    
                    def_top3 = existing_w.get("tech_top_3", [])
                    def_bot3 = existing_w.get("tech_bottom_3", [])
                    def_t1 = def_top3[0] if len(def_top3) > 0 else None
                    def_t2 = def_top3[1] if len(def_top3) > 1 else None
                    def_t3 = def_top3[2] if len(def_top3) > 2 else None
                    def_b3 = def_bot3[0] if len(def_bot3) > 0 else None
                    def_b2 = def_bot3[1] if len(def_bot3) > 1 else None
                    def_b1 = def_bot3[2] if len(def_bot3) > 2 else None
                    
                    with col_t_top:
                        opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t1", def_t1, "-- Select 1st Place --")
                        t1 = st.selectbox("1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w{cur_w}_std_t1")
                        opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t2", def_t2, "-- Select 2nd Place --")
                        t2 = st.selectbox("2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w{cur_w}_std_t2")
                        opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t3", def_t3, "-- Select 3rd Place --")
                        t3 = st.selectbox("3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w{cur_w}_std_t3")
                        weekly_picks["tech_top_3"] = [t1, t2, t3]
                        tech_raw.extend(weekly_picks["tech_top_3"])
                        
                    with col_t_bot:
                        opts_b3, idx_b3 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b3", def_b3, "-- Select 3rd-to-last Place --")
                        b_3rd_last = st.selectbox("3rd-to-last Place [2 pts]", opts_b3, index=idx_b3, key=f"{active_sub_player}_w{cur_w}_std_b3")
                        opts_b2, idx_b2 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b2", def_b2, "-- Select 2nd-to-last Place --")
                        b_2nd_last = st.selectbox("2nd-to-last Place [2 pts]", opts_b2, index=idx_b2, key=f"{active_sub_player}_w{cur_w}_std_b2")
                        opts_b1, idx_b1 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b1", def_b1, "-- Select Last Place --")
                        b_last = st.selectbox("Last Place [3 pts]", opts_b1, index=idx_b1, key=f"{active_sub_player}_w{cur_w}_std_b1")
                        weekly_picks["tech_bottom_3"] = [b_3rd_last, b_2nd_last, b_last]
                        tech_raw.extend(weekly_picks["tech_bottom_3"])

                    submitted = st.form_submit_button("Submit Predictions")
                    if submitted:
                        clean_main = [b for b in main_raw if b in active_bakers and not str(b).startswith("-- Select") and b != "None"]
                        clean_tech = [b for b in tech_raw if b in active_bakers and not str(b).startswith("-- Select") and b != "None"]
                        
                        dups_main = sorted(list(set([b for b in clean_main if clean_main.count(b) > 1])))
                        dups_tech = sorted(list(set([b for b in clean_tech if clean_tech.count(b) > 1])))
                        
                        if dups_main or dups_tech:
                            err_msgs = []
                            if dups_main:
                                err_msgs.append(f"• **Main Categories:** **{', '.join(dups_main)}** cannot be selected multiple times among Star Baker, Eliminated, In Line, and In Trouble.")
                            if dups_tech:
                                err_msgs.append(f"• **Technical Placements:** **{', '.join(dups_tech)}** cannot be selected multiple times within Technical rankings.")
                            
                            st.error("⚠️ **Duplicate Selection Error:**\n\n" + "\n\n".join(err_msgs) + "\n\nPlease fix the duplicates and submit again.")
                        else:
                            if "weekly_picks" not in st.session_state.league_members[active_sub_player]:
                                st.session_state.league_members[active_sub_player]["weekly_picks"] = {}
                            st.session_state.league_members[active_sub_player]["weekly_picks"][cur_w] = weekly_picks
                            
                            ai_picks = generate_ai_brian_weekly_picks(cur_w, active_bakers, is_double_elim=is_double_elim)
                            if "weekly_picks" not in st.session_state.league_members["AI Brian"]:
                                st.session_state.league_members["AI Brian"]["weekly_picks"] = {}
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

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 Admin Command Center")
    admin_pwd = st.text_input("Enter Admin Security Password:", type="password", key="admin_password_input")
    
    if admin_pwd == "gbbs2026":
        st.success("🔓 Admin Access Granted!")
        
        st.subheader("📺 Publish Broadcast Episode Actuals")
        cur_w = st.session_state.current_week
        st.write(f"Editing actual broadcast results for **Episode Week {cur_w}**")
        
        active_bakers = [b for b in ALL_BAKERS if b not in get_current_eliminated_bakers(cur_w)]
        existing_act = get_weekly_result(cur_w)
        
        with st.form(f"admin_form_w{cur_w}"):
            actuals = {}
            if cur_w == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", ["-- Select Champion --"] + active_bakers)
            else:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", ["-- Select Star Baker --"] + active_bakers)
                
                if cur_w in [5, 9]:
                    actuals["eliminated"] = st.multiselect("Actual Eliminated Bakers (Double Elimination)", active_bakers)
                else:
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", ["None"] + active_bakers)
                    
                actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers)
                actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                
            st.markdown("---")
            st.write("Technical Challenge Results:")
            col_a_t1, col_a_t2 = st.columns(2)
            with col_a_t1:
                t1 = st.selectbox("1st Place", ["-- Select --"] + active_bakers, key=f"admin_t1_w{cur_w}")
                t2 = st.selectbox("2nd Place", ["-- Select --"] + active_bakers, key=f"admin_t2_w{cur_w}")
                t3 = st.selectbox("3rd Place", ["-- Select --"] + active_bakers, key=f"admin_t3_w{cur_w}")
                actuals["tech_top_3"] = [t1, t2, t3]
            with col_a_t2:
                b3 = st.selectbox("3rd-to-last Place", ["-- Select --"] + active_bakers, key=f"admin_b3_w{cur_w}")
                b2 = st.selectbox("2nd-to-last Place", ["-- Select --"] + active_bakers, key=f"admin_b2_w{cur_w}")
                b1 = st.selectbox("Last Place", ["-- Select --"] + active_bakers, key=f"admin_b1_w{cur_w}")
                actuals["tech_bottom_3"] = [b3, b2, b1]

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            actuals["handshake_bakers"] = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"admin_handshake_bakers_w{cur_w}")
            actuals["handshake_timestamps"] = st.text_input("Handshake Video Timestamps & Context", value="", key=f"admin_handshake_stamps_w{cur_w}")

            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            actuals["crying_count"] = st.number_input("Crying Scenes Count in Episode", min_value=0, value=0, key=f"admin_crying_cnt_w{cur_w}")
            actuals["crying_timestamps"] = st.text_input("Crying Scene Video Timestamps & Context", value="", key=f"admin_crying_stamps_w{cur_w}")

            st.markdown("### 💬 Weekly Sexual Innuendos Count")
            actuals["innuendo_count"] = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=0, key=f"admin_innuendo_cnt_w{cur_w}")

            if st.form_submit_button("Publish Actual Results & Recalculate Standings"):
                st.session_state.weekly_results[cur_w] = actuals
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Week {cur_w} actual broadcast results published and saved!")
    elif admin_pwd != "":
        st.error("Incorrect Admin Password!")
