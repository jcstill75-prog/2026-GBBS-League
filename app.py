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
    """Smart case-insensitive and multi-extension baker portrait loader."""
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
    """Renders player avatars reliably using Streamlit native components."""
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

# --- 3. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    
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
        # Award +2 points if predicted baker was nominated In Trouble (whether saved or sent home)
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

# --- 4. CORE BAKERS LIST & ROSTER INITIALIZATION ---
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
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

def generate_ai_brian_picks(active_bakers, week=2):
    random.seed(week * 100)
    picks = {}
    if week == 10:
        picks["show_champion"] = random.choice(active_bakers)
    else:
        picks["star_baker"] = random.choice(active_bakers)
        rem = [b for b in active_bakers if b != picks["star_baker"]]
        picks["eliminated"] = random.choice(rem) if rem else picks["star_baker"]
        rem2 = [b for b in rem if b != picks["eliminated"]]
        picks["in_line_sb"] = random.choice(rem2) if rem2 else picks["star_baker"]
        rem3 = [b for b in rem2 if b != picks["in_line_sb"]]
        picks["in_trouble"] = random.choice(rem3) if rem3 else picks["eliminated"]
        
    shuffled = active_bakers.copy()
    random.shuffle(shuffled)
    if week >= 8:
        picks["tech_rank"] = shuffled
    else:
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
    else:
        # Auto-recover image from disk if session state avatar is missing
        cur_p_av = st.session_state.league_members[p].get("avatar")
        if not cur_p_av:
            for check_path in [f"assets/avatars/{p}.png", f"assets/avatars/{p}.jpg", f"assets/{p}.png", f"assets/{p}.jpg"]:
                if os.path.exists(check_path):
                    st.session_state.league_members[p]["avatar"] = check_path
                    break

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
    st.markdown("### 🏆 Standings Summary")
    summary_data = []
    for member, data in st.session_state.league_members.items():
        summary_data.append({
            "Player": member,
            "Total Score": data.get("total_score", 0)
        })
    df_summary = pd.DataFrame(summary_data).sort_values(by="Total Score", ascending=False)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

# --- 8. MAIN TABS NAVIGATION ---
tab_lead, tab_pred, tab_analytics, tab_rules, tab_admin = st.tabs([
    "📊 Leaderboard & Standings",
    "📝 Submit Predictions",
    "📈 Contestant Analytics",
    "📜 Rules & Scoring",
    "👑 Admin Panel"
])

# ==========================================
# TAB 1: LEADERBOARD & STANDINGS
# ==========================================
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    # Recalculate all scores to ensure freshness
    all_res_weeks = get_sorted_weekly_result_weeks()
    for member, data in st.session_state.league_members.items():
        tot = 0
        wb = {}
        for w_k in all_res_weeks:
            res = get_weekly_result(w_k)
            picks = data.get("weekly_picks", {}).get(w_k, data.get("weekly_picks", {}).get(str(w_k), {}))
            if picks:
                s = calculate_weekly_score(picks, res, week=w_k)
                wb[w_k] = s
                tot += s
        
        s_picks = data.get("season_picks", {})
        if s_picks and st.session_state.season_results:
            tot += calculate_season_score(s_picks, st.session_state.season_results)
            
        data["total_score"] = tot
        data["weekly_breakdown"] = wb

    lb_list = []
    for member, data in st.session_state.league_members.items():
        lb_list.append({
            "member": member,
            "avatar": data.get("avatar"),
            "score": data.get("total_score", 0)
        })
    lb_list = sorted(lb_list, key=lambda x: x["score"], reverse=True)

    for idx, entry in enumerate(lb_list, start=1):
        col_rank, col_av, col_name, col_score = st.columns([1, 1.5, 5, 2])
        with col_rank:
            st.markdown(f"<h3 style='margin-top:15px;'>#{idx}</h3>", unsafe_allow_html=True)
        with col_av:
            render_player_avatar(entry["avatar"], width=55)
        with col_name:
            st.markdown(f"<h3 style='margin-top:15px; color:#5D4037;'>{entry['member']}</h3>", unsafe_allow_html=True)
        with col_score:
            st.markdown(f"<h3 style='margin-top:15px; color:#D36B5F;'>{entry['score']} pts</h3>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    # Broadcast Chaos Metrics Section
    st.markdown("---")
    st.header("🎭 Broadcast Chaos Metrics")
    st.caption("Track cumulative broadcast totals across published episodes to evaluate your season-long projections:")
    
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
        try: cry_cnt = int(cry_cnt)
        except (ValueError, TypeError): cry_cnt = 0
            
        inn_cnt = w_data.get("innuendo_count", 0)
        try: inn_cnt = int(inn_cnt)
        except (ValueError, TypeError): inn_cnt = 0
            
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
    sel_card_player = st.selectbox("Select Player to Inspect Scorecard:", sorted(list(st.session_state.league_members.keys())))
    p_data = st.session_state.league_members[sel_card_player]
    
    col_card_av, col_card_info = st.columns([1, 3])
    with col_card_av:
        render_player_avatar(p_data.get("avatar"), width=120, caption=f"{sel_card_player}'s Profile")
    with col_card_info:
        st.markdown(f"### Scorecard for **{sel_card_player}**")
        st.markdown(f"**Total Cumulative Points:** `{p_data.get('total_score', 0)} pts`")
        
    st.markdown("#### Episode Performance Breakdown")
    p_wb = p_data.get("weekly_breakdown", {})
    if not p_wb:
        st.info(f"No episode breakdown available for {sel_card_player} yet.")
    else:
        for w_num in sorted(p_wb.keys()):
            w_score = p_wb[w_num]
            res = get_weekly_result(w_num)
            picks = p_data.get("weekly_picks", {}).get(w_num, p_data.get("weekly_picks", {}).get(str(w_num), {}))
            
            with st.expander(f"Week {w_num} Breakdown ({w_score} pts scored)", expanded=False):
                # Display timestamps callout box if available
                hs_stamps = res.get("handshake_timestamps")
                cry_stamps = res.get("crying_timestamps")
                if hs_stamps or cry_stamps:
                    st.info("ℹ️ **Broadcast Context & Video Timestamps:**")
                    if hs_stamps: st.write(f"🤝 **Handshake Timestamps & Notes:** {hs_stamps}")
                    if cry_stamps: st.write(f"😢 **Crying Incident Timestamps & Notes:** {cry_stamps}")
                    st.markdown("---")
                    
                col_p, col_a = st.columns(2)
                with col_p:
                    st.markdown("##### Your Predictions")
                    if picks:
                        for k, v in picks.items():
                            st.write(f"• **{k.replace('_', ' ').title()}:** {v}")
                    else:
                        st.write("*(No predictions submitted)*")
                with col_a:
                    st.markdown("##### Episode Actuals")
                    if res:
                        for k, v in res.items():
                            if k not in ["handshake_timestamps", "crying_timestamps"]:
                                st.write(f"• **{k.replace('_', ' ').title()}:** {v}")
                    else:
                        st.write("*(Actuals pending)*")

# ==========================================
# TAB 2: SUBMIT PREDICTIONS
# ==========================================
with tab_pred:
    st.header("📝 Submit Weekly & Season Predictions")
    
    sel_player = st.selectbox("Select Your Profile Name:", ["-- Select Your Name --"] + roster_players, key="pred_player_select")
    
    if sel_player != "-- Select Your Name --":
        p_pin = st.session_state.league_members[sel_player].get("pin")
        is_authed = st.session_state.authenticated_players.get(sel_player, False)
        
        if p_pin is not None and not is_authed:
            st.warning(f"🔒 Profile for **{sel_player}** is protected by a 4-digit PIN.")
            input_pin = st.text_input("Enter 4-Digit PIN to Unlock Profile:", type="password", key=f"pin_input_{sel_player}")
            if st.button("Unlock Profile", key=f"unlock_btn_{sel_player}"):
                if input_pin == p_pin:
                    st.session_state.authenticated_players[sel_player] = True
                    st.success(f"Profile unlocked for {sel_player}!")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again.")
        else:
            if p_pin is None:
                st.info("💡 Set a 4-digit PIN to lock your profile from unauthorized edits!")
                new_pin = st.text_input("Create 4-Digit PIN (Optional):", type="password", key=f"new_pin_{sel_player}")
                if st.button("Set PIN", key=f"set_pin_btn_{sel_player}"):
                    if len(new_pin) == 4 and new_pin.isdigit():
                        st.session_state.league_members[sel_player]["pin"] = new_pin
                        st.session_state.authenticated_players[sel_player] = True
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success("PIN set successfully!")
                        st.rerun()
                    else:
                        st.error("PIN must be exactly 4 digits.")
            
            sel_week = st.selectbox("Select Prediction Week:", range(1, 11), index=1)
            
            # --- WEEK 1 SCOUTING LOCKOUT BANNER ---
            if sel_week == 1:
                st.markdown("""
                <div class="status-box">
                    <h3>🔍 Week 1 Scouting Period Active</h3>
                    <p><b>No weekly ballot is required for Week 1!</b> Use this broadcast to evaluate the bakers, their techniques, and personality dynamics.</p>
                    <p><b>Active Voting Opens in Week 2:</b> You will lock in your Season-Long Projections and Week 2 Ballot prior to the Week 2 broadcast.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                eliminated_so_far = get_current_eliminated_bakers(sel_week)
                active_bakers = [b for b in ALL_BAKERS if b not in eliminated_so_far]
                
                st.markdown(f"### 📋 Week {sel_week} Prediction Ballot")
                st.write(f"Active Bakers in the Tent ({len(active_bakers)}): {', '.join(active_bakers)}")
                
                # Season-long projections form if Week 2
                if sel_week == 2:
                    st.markdown("---")
                    st.markdown("### 🏆 Lock Season-Long Projections (Week 2 Requirement)")
                    st.write("These long-term predictions lock prior to Episode 2 and evaluate at season conclusion:")
                    
                    s_winner = st.selectbox("Predicted Season Champion:", active_bakers, key="s_winner_sel")
                    s_semis = st.multiselect("Other 3 Semifinalists (Pick 3):", [b for b in active_bakers if b != s_winner], max_selections=3, key="s_semis_sel")
                    s_handshakes = st.number_input("Predicted Season Hollywood Handshakes Count:", min_value=0, value=3, key="s_hs_sel")
                    s_crying = st.number_input("Predicted Season Crying Scenes Count:", min_value=0, value=15, key="s_cry_sel")
                    s_innuendos = st.number_input("Predicted Season Sexual Innuendos Count:", min_value=0, value=25, key="s_inn_sel")

                st.markdown("---")
                st.markdown("#### Weekly Episode Predictions")
                
                p_sb = st.selectbox("Predicted Star Baker:", active_bakers, key=f"sb_w{sel_week}")
                p_elim = st.selectbox("Predicted Eliminated Baker:", active_bakers, key=f"elim_w{sel_week}")
                p_in_line = st.selectbox("Predicted 'In Line for Star Baker' Nominee:", active_bakers, key=f"inline_w{sel_week}")
                p_in_trouble = st.selectbox("Predicted 'In Trouble' Nominee:", active_bakers, key=f"introuble_w{sel_week}")
                
                st.markdown("#### Technical Challenge Ranking Predictions")
                p_tech_top3 = st.multiselect("Predicted Technical Top 3 (1st, 2nd, 3rd in exact order):", active_bakers, max_selections=3, key=f"top3_w{sel_week}")
                p_tech_bot3 = st.multiselect("Predicted Technical Bottom 3 (10th, 11th, 12th in exact order):", active_bakers, max_selections=3, key=f"bot3_w{sel_week}")

                if st.button(f"Submit Week {sel_week} Predictions", key=f"submit_btn_w{sel_week}"):
                    # Independent Section Validation
                    main_picks = [p_sb, p_elim, p_in_line, p_in_trouble]
                    main_dupes = [b for b in set(main_picks) if main_picks.count(b) > 1]
                    
                    tech_picks = p_tech_top3 + p_tech_bot3
                    tech_dupes = [b for b in set(tech_picks) if tech_picks.count(b) > 1]
                    
                    if main_dupes:
                        st.error(f"⚠️ **Main Categories Duplicate Selection:** You selected **{', '.join(main_dupes)}** multiple times among Star Baker, Eliminated, In Line, and In Trouble. Please choose distinct bakers for each main category.")
                    elif tech_dupes:
                        st.error(f"⚠️ **Technical Challenge Duplicate Selection:** You selected **{', '.join(tech_dupes)}** multiple times within your Technical rankings. Please select 6 distinct bakers across Top 3 and Bottom 3.")
                    elif len(p_tech_top3) < 3 or len(p_tech_bot3) < 3:
                        st.error("⚠️ Please select exactly 3 bakers for Technical Top 3 and 3 bakers for Technical Bottom 3.")
                    else:
                        # Save ballot
                        weekly_picks = {
                            "star_baker": p_sb,
                            "eliminated": p_elim,
                            "in_line_sb": p_in_line,
                            "in_trouble": p_in_trouble,
                            "tech_top_3": p_tech_top3,
                            "tech_bottom_3": p_tech_bot3
                        }
                        
                        if "weekly_picks" not in st.session_state.league_members[sel_player]:
                            st.session_state.league_members[sel_player]["weekly_picks"] = {}
                        st.session_state.league_members[sel_player]["weekly_picks"][sel_week] = weekly_picks
                        
                        if sel_week == 2 and 's_winner' in locals():
                            st.session_state.league_members[sel_player]["season_picks"] = {
                                "winner": s_winner,
                                "semifinalists": s_semis,
                                "handshakes": s_handshakes,
                                "crying": s_crying,
                                "innuendos": s_innuendos
                            }
                            
                        # Generate AI Brian's picks
                        if "AI Brian" in st.session_state.league_members:
                            if "weekly_picks" not in st.session_state.league_members["AI Brian"]:
                                st.session_state.league_members["AI Brian"]["weekly_picks"] = {}
                            st.session_state.league_members["AI Brian"]["weekly_picks"][sel_week] = generate_ai_brian_picks(active_bakers, week=sel_week)
                            
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success(f"Predictions saved for **{sel_player}**!")

# ==========================================
# TAB 3: CONTESTANT ANALYTICS
# ==========================================
with tab_analytics:
    st.header("📈 Contestant Performance & Stats Analytics")
    
    current_eliminated_latest = get_current_eliminated_bakers(11)
    
    baker_stats = {b: {
        "star_baker_cnt": 0,
        "eliminated_cnt": 0,
        "in_line_cnt": 0,
        "in_trouble_cnt": 0,
        "handshake_cnt": 0,
        "tech_ranks": []
    } for b in ALL_BAKERS}
    
    for w_k in get_sorted_weekly_result_weeks():
        res = get_weekly_result(w_k)
        sb = res.get("star_baker")
        if sb in baker_stats: baker_stats[sb]["star_baker_cnt"] += 1
        
        el = res.get("eliminated")
        if isinstance(el, list):
            for b in el:
                if b in baker_stats: baker_stats[b]["eliminated_cnt"] += 1
        elif isinstance(el, str) and el in baker_stats:
            baker_stats[el]["eliminated_cnt"] += 1
            
        inl = res.get("in_line_sb", [])
        if isinstance(inl, list):
            for b in inl:
                if b in baker_stats: baker_stats[b]["in_line_cnt"] += 1
        elif isinstance(inl, str) and inl in baker_stats:
            baker_stats[inl]["in_line_cnt"] += 1
            
        intr = res.get("in_trouble", [])
        if isinstance(intr, list):
            for b in intr:
                if b in baker_stats: baker_stats[b]["in_trouble_cnt"] += 1
        elif isinstance(intr, str) and intr in baker_stats:
            baker_stats[intr]["in_trouble_cnt"] += 1
            
        hs = res.get("handshake_bakers", [])
        if isinstance(hs, list):
            for b in hs:
                if b in baker_stats: baker_stats[b]["handshake_cnt"] += 1

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
        with m3: st.metric("In Trouble Nominee", f"{s['in_trouble_cnt']} ⚠️")
        with m4: st.metric("Hollywood Handshakes", f"{s['handshake_cnt']} 🤝")

# ==========================================
# TAB 4: RULES & SCORING BREAKDOWN
# ==========================================
with tab_rules:
    st.header("📜 2026 Official Fantasy League Rulebook")
    st.markdown("""
    ### 🏆 Overview & Matchup Phases
    • **Week 1 (Scouting Phase):** No predictions or points! Evaluate baker skills and personalities.  
    • **Week 2 (Season Locking):** Lock season-long champion, semifinalists, and chaos counts before Episode 2.  
    • **Weeks 2–10 (Weekly Matchups):** Submit recurring weekly ballots prior to British broadcast.

    ### 💯 Point Scoring Infrastructure
    • **Star Baker:** +5 points  
    • **Eliminated Baker:** +5 points  
    • **In Line for Star Baker (Consolation):** +2 points (if nominated by judges and not Star Baker)  
    • **In Trouble Nominee (Consolation):** +2 points (if nominated by judges and not eliminated)  
    • **Technical Top 3 & Bottom 3:** Combo bonus (+10 pts) or exact/partial placement scoring  
    • **Season Champion:** +40 points (or +15 finalist consolation)  
    • **Season Chaos Counts:** Handshakes, Crying, and Sexual Innuendo accuracy bonuses (+20 exact, +10 within margin)
    """)

# ==========================================
# TAB 5: ADMIN PANEL
# ==========================================
with tab_admin:
    st.header("👑 Admin Command Center")
    
    admin_pass = st.text_input("Enter Admin Password:", type="password", key="admin_pass_input")
    if admin_pass == "bakeoff2026":
        st.session_state.admin_authenticated = True
        st.success("Admin authenticated!")
        
        st.markdown("---")
        st.subheader("⚙️ Publish Episode Actual Results")
        
        adm_week = st.number_input("Episode Week Number:", min_value=1, max_value=10, value=st.session_state.current_week)
        elim_so_far = get_current_eliminated_bakers(adm_week)
        active_bakers = [b for b in ALL_BAKERS if b not in elim_so_far]
        
        act_sb = st.selectbox("Actual Star Baker:", active_bakers, key=f"adm_sb_w{adm_week}")
        act_elim = st.selectbox("Actual Eliminated Baker:", ["None"] + active_bakers, key=f"adm_elim_w{adm_week}")
        act_inline = st.multiselect("Actual 'In Line for Star Baker' Nominees:", active_bakers, key=f"adm_inline_w{adm_week}")
        act_introuble = st.multiselect("Actual 'In Trouble' Nominees:", active_bakers, key=f"adm_introuble_w{adm_week}")
        
        st.markdown("---")
        st.markdown("### 🤝 Hollywood Handshakes & Context Notes")
        act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes:", active_bakers, key=f"adm_hs_bakers_w{adm_week}")
        act_hs_stamps = st.text_input("Handshake Video Timestamps & Context Notes:", value="", key=f"adm_hs_stamps_w{adm_week}")

        st.markdown("### 😢 Crying Incidents & Context Notes")
        act_cry_cnt = st.number_input("Crying Scenes Count in Episode:", min_value=0, value=0, key=f"adm_cry_cnt_w{adm_week}")
        act_cry_stamps = st.text_input("Crying Incident Video Timestamps & Context Notes:", value="", key=f"adm_cry_stamps_w{adm_week}")

        st.markdown("### 💬 Sexual Innuendos Count")
        act_inn_cnt = st.number_input("Sexual Innuendos Count in Episode:", min_value=0, value=0, key=f"adm_inn_cnt_w{adm_week}")

        if st.button("Publish Actual Results & Recalculate Standings"):
            actuals = {
                "star_baker": act_sb,
                "eliminated": act_elim,
                "in_line_sb": act_inline,
                "in_trouble": act_introuble,
                "handshake_bakers": act_hs_bakers,
                "handshake_timestamps": act_hs_stamps,
                "crying_count": act_cry_cnt,
                "crying_timestamps": act_cry_stamps,
                "innuendo_count": act_inn_cnt
            }
            
            st.session_state.weekly_results[adm_week] = actuals
            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
            st.success(f"Week {adm_week} results published and standings recalculated!")
    else:
        if admin_pass != "":
            st.error("Incorrect Admin Password.")
