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

def render_player_avatar(avatar_val, width=50, caption=None):
    """Renders avatar image cleanly using native st.image or fallback emojis."""
    if not avatar_val:
        st.markdown("<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)
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
        st.markdown("<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
        return

    st.markdown("<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)

# --- 3. OFFICIAL 2026 SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    # Main Episode Results
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") and predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
            
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim:
                        score += 5
            elif isinstance(pred_elim, str) and pred_elim in act_elim:
                score += 5
        elif act_elim != "None":
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
                for idx, b in enumerate(pred_top3):
                    if b in act_top3 and b != act_top3[idx]:
                        score += 1

        pred_bot3 = predictions.get("tech_bottom_3", [])
        act_bot3 = actuals.get("tech_bottom_3", [])
        if len(pred_bot3) == 3 and len(act_bot3) == 3:
            if pred_bot3 == act_bot3:
                score += 10
            else:
                if pred_bot3[0] == act_bot3[0]: score += 2
                if pred_bot3[1] == act_bot3[1]: score += 2
                if pred_bot3[2] == act_bot3[2]: score += 3
                for idx, b in enumerate(pred_bot3):
                    if b in act_bot3 and b != act_bot3[idx]:
                        score += 1

    # Consolations
    if week < 9:
        act_in_line = actuals.get("in_line_sb", [])
        if not isinstance(act_in_line, list): act_in_line = [act_in_line]
        pred_in_line = predictions.get("in_line_sb")
        if pred_in_line and pred_in_line in act_in_line:
            score += 2

        act_in_trouble = actuals.get("in_trouble", [])
        if not isinstance(act_in_trouble, list): act_in_trouble = [act_in_trouble]
        pred_in_trouble = predictions.get("in_trouble")
        if pred_in_trouble and pred_in_trouble in act_in_trouble:
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

def load_baker_image(baker_name):
    """Smart image loader for contestant portraits."""
    target = baker_name.lower().strip()
    for folder in ["assets", "assets/bakers", "."]:
        if os.path.exists(folder):
            try:
                for fn in os.listdir(folder):
                    stem, ext = os.path.splitext(fn)
                    if stem.lower().strip() == target and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                        return Image.open(os.path.join(folder, fn))
            except Exception:
                pass
    return None

# --- 4. CORE DATA CONSTANTS ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

DEFAULT_ROSTER = [
    "Ana", "Becca", "Clara", "Connie", "Danni", "Gabe", 
    "Gary", "Mo", "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

BAKER_INFO = {b: {"url": f"https://thegreatbritishbakeoff.co.uk/bakers/series-17-{b.lower()}/"} for b in ALL_BAKERS}

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    random.seed(42 + week)
    shuffled = list(active_bakers)
    random.shuffle(shuffled)
    picks = {}
    
    if week == 10:
        picks["show_champion"] = shuffled[0]
        picks["tech_rank"] = shuffled[:3]
    elif week == 9:
        picks["star_baker"] = shuffled[0]
        if is_double_elim and len(shuffled) >= 3:
            picks["eliminated"] = [shuffled[1], shuffled[2]]
        else:
            picks["eliminated"] = shuffled[1]
        picks["tech_rank"] = shuffled[:4]
    elif week == 8:
        picks["star_baker"] = shuffled[0]
        picks["in_line_sb"] = shuffled[1]
        if is_double_elim and len(shuffled) >= 4:
            picks["eliminated"] = [shuffled[2], shuffled[3]]
            picks["in_trouble"] = shuffled[4] if len(shuffled) > 4 else shuffled[0]
        else:
            picks["eliminated"] = shuffled[2]
            picks["in_trouble"] = shuffled[3]
        picks["tech_rank"] = shuffled[:5]
    else:
        picks["star_baker"] = shuffled[0]
        picks["in_line_sb"] = shuffled[1]
        if is_double_elim and len(shuffled) >= 4:
            picks["eliminated"] = [shuffled[2], shuffled[3]]
            picks["in_trouble"] = shuffled[4] if len(shuffled) > 4 else shuffled[0]
        else:
            picks["eliminated"] = shuffled[2]
            picks["in_trouble"] = shuffled[3]
        picks["tech_top_3"] = shuffled[:3]
        rem = [b for b in active_bakers if b not in picks["tech_top_3"]]
        random.shuffle(rem)
        picks["tech_bottom_3"] = rem[:3]
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
    else:
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
    st.session_state.current_week = 2

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

# --- 6. NORMAN BEAVER HEADER ---
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
        with col_logo: st.image(norman_path, width=80)
        with col_title: st.title("Great British Baking Show Fantasy League 2026")
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
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Contestant Analytics",
    "👑 Admin Panel"
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
            "avatar": av_val
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
                margin-bottom: 20px;
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
                av_html = f'<img src="{av_val}" style="width:40px; height:40px; border-radius:50%; object-fit:cover;">'
            elif isinstance(av_val, str) and os.path.exists(av_val):
                try:
                    with open(av_val, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    ext = "png" if av_val.endswith(".png") else "jpeg"
                    av_html = f'<img src="data:image/{ext};base64,{b64}" style="width:40px; height:40px; border-radius:50%; object-fit:cover;">'
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
                    <th style="text-align: right; width: 100px;">Total Points</th>
                </tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

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

    st.markdown("---")
    st.header("🔍 Individual Player Scorecards")
    
    scorecard_players = sorted(list(st.session_state.league_members.keys()))
    sel_sc_player = st.selectbox("Select Player Scorecard to Inspect:", scorecard_players, key="scorecard_select")
    
    if sel_sc_player:
        p_data = st.session_state.league_members[sel_sc_player]
        col_sc1, col_sc2 = st.columns([1, 3])
        with col_sc1:
            render_player_avatar(p_data.get("avatar"), width=120, caption=f"{sel_sc_player}")
        with col_sc2:
            st.subheader(f"Scorecard: **{sel_sc_player}**")
            st.markdown(f"### Total Score: **{p_data.get('total_score', 0)} pts**")
            
        with st.expander("🌟 Locked Season-Long Predictions", expanded=False):
            st.json(p_data.get("season_picks", {}))
            
        w_breakdown = p_data.get("weekly_breakdown", {})
        if w_breakdown:
            st.subheader("📅 Weekly Episode Score Breakdown")
            for w_num in sorted(w_breakdown.keys()):
                w_score = w_breakdown[w_num]
                w_picks = p_data.get("weekly_picks", {}).get(w_num, {})
                res = get_weekly_result(w_num)
                
                with st.expander(f"Week {w_num} Breakdown — Earned **{w_score} pts**", expanded=False):
                    hs_stamps = res.get("handshake_timestamps")
                    cry_stamps = res.get("crying_timestamps")
                    if hs_stamps or cry_stamps:
                        st.info("ℹ️ **Broadcast Context & Video Timestamps:**")
                        if hs_stamps: st.write(f"🤝 **Handshakes Notes:** {hs_stamps}")
                        if cry_stamps: st.write(f"😢 **Crying Notes:** {cry_stamps}")
                        
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.markdown("**Player Predictions Submitted:**")
                        st.json(w_picks)
                    with col_p2:
                        st.markdown("**Actual Episode Results:**")
                        st.json(res)

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions & Ballots")
    
    active_week = st.selectbox("Select Episode Week for Predictions:", list(range(1, 11)), index=st.session_state.current_week - 1)
    st.session_state.current_week = active_week
    
    if active_week == 1:
        st.info("🔎 **Week 1 Scouting Phase Active:** No prediction ballots are submitted in Week 1. Use this episode to evaluate the bakers!")
    else:
        st.warning("⏰ **Weekly Deadline:** Ballots lock prior to the broadcast on Tuesdays!")
        
        eliminated_bakers_latest = get_current_eliminated_bakers(active_week)
        active_bakers = [b for b in ALL_BAKERS if b not in eliminated_bakers_latest]
        st.info(f"Active Bakers in the Tent for Week {active_week}: " + ", ".join(active_bakers))
        
        # 1. Season Long Predictions (Week 2)
        if active_week == 2:
            with st.expander("🌟 Season-Long Projections (Locks Week 2 | 130 pts total at stake)", expanded=True):
                user_winner = st.selectbox("Predict Season Winner [40 pts]", active_bakers, key="season_win_pick")
                rem_semis = [b for b in active_bakers if b != user_winner]
                user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", rem_semis, max_selections=3, key="season_semis_pick")
                
                user_hs = st.number_input("Predict Total Handshakes [20 pts]", min_value=0, value=5, key="season_hs_pick")
                user_cry = st.number_input("Predict Total Crying Incidents [20 pts]", min_value=0, value=10, key="season_cry_pick")
                user_inn = st.number_input("Predict Total Innuendos [20 pts]", min_value=0, value=40, key="season_inn_pick")
                
                if st.button("Lock Season-Long Projections"):
                    if len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members["Ana"]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_hs,
                            "crying": user_cry,
                            "innuendos": user_inn
                        }
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success("Season-long projections locked successfully!")

        # 2. Weekly Ballot
        st.markdown(f"### 📅 Weekly Ballot: Week {active_week}")
        
        is_double_elim = st.checkbox("📢 Is this a Double Elimination Week?", value=False)
        
        with st.form("weekly_ballot_form"):
            w_picks = {}
            main_cat_picks = []
            tech_cat_picks = []
            
            if active_week == 10:
                show_champ = st.selectbox("Predict Show Champion [15 pts]", active_bakers)
                w_picks["show_champion"] = show_champ
                t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0)
                t2 = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=min(1, len(active_bakers)-1))
                t3 = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=min(2, len(active_bakers)-1))
                w_picks["tech_rank"] = [t1, t2, t3]
                tech_cat_picks = [t1, t2, t3]
            elif active_week == 9:
                sb = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                w_picks["star_baker"] = sb
                main_cat_picks.append(sb)
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", active_bakers, index=1)
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", active_bakers, index=min(2, len(active_bakers)-1))
                    w_picks["eliminated"] = [e1, e2]
                    main_cat_picks.extend([e1, e2])
                else:
                    el = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers, index=min(1, len(active_bakers)-1))
                    w_picks["eliminated"] = el
                    main_cat_picks.append(el)
                t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0)
                t2 = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=min(1, len(active_bakers)-1))
                t3 = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=min(2, len(active_bakers)-1))
                t4 = st.selectbox("Technical 4th Place [3 pts]", active_bakers, index=min(3, len(active_bakers)-1))
                w_picks["tech_rank"] = [t1, t2, t3, t4]
                tech_cat_picks = [t1, t2, t3, t4]
            elif active_week == 8:
                sb = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                inline = st.selectbox("Predict In Line for Star Baker [2 pts]", active_bakers, index=min(1, len(active_bakers)-1))
                w_picks["star_baker"] = sb
                w_picks["in_line_sb"] = inline
                main_cat_picks.extend([sb, inline])
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", active_bakers, index=min(2, len(active_bakers)-1))
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", active_bakers, index=min(3, len(active_bakers)-1))
                    tr = st.selectbox("Predict In Trouble [2 pts]", active_bakers, index=min(4, len(active_bakers)-1))
                    w_picks["eliminated"] = [e1, e2]
                    w_picks["in_trouble"] = tr
                    main_cat_picks.extend([e1, e2, tr])
                else:
                    el = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers, index=min(2, len(active_bakers)-1))
                    tr = st.selectbox("Predict In Trouble [2 pts]", active_bakers, index=min(3, len(active_bakers)-1))
                    w_picks["eliminated"] = el
                    w_picks["in_trouble"] = tr
                    main_cat_picks.extend([el, tr])
                t1 = st.selectbox("Technical 1st Place [3 pts]", active_bakers, index=0)
                t2 = st.selectbox("Technical 2nd Place [2 pts]", active_bakers, index=min(1, len(active_bakers)-1))
                t3 = st.selectbox("Technical 3rd Place [2 pts]", active_bakers, index=min(2, len(active_bakers)-1))
                t4 = st.selectbox("Technical 4th Place [2 pts]", active_bakers, index=min(3, len(active_bakers)-1))
                t5 = st.selectbox("Technical 5th Place [3 pts]", active_bakers, index=min(4, len(active_bakers)-1))
                w_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                tech_cat_picks = [t1, t2, t3, t4, t5]
            else:
                # Weeks 2-7
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    sb = st.selectbox("Predict Star Baker [5 pts]", active_bakers, key=f"sb_w{active_week}")
                    inline = st.selectbox("Predict In Line for Star Baker [2 pts]", active_bakers, index=min(1, len(active_bakers)-1), key=f"inline_w{active_week}")
                    w_picks["star_baker"] = sb
                    w_picks["in_line_sb"] = inline
                    main_cat_picks.extend([sb, inline])
                with col_w2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated #1 [5 pts]", active_bakers, index=min(2, len(active_bakers)-1), key=f"e1_w{active_week}")
                        e2 = st.selectbox("Predict Eliminated #2 [5 pts]", active_bakers, index=min(3, len(active_bakers)-1), key=f"e2_w{active_week}")
                        tr = st.selectbox("Predict In Trouble [2 pts]", active_bakers, index=min(4, len(active_bakers)-1), key=f"tr_w{active_week}")
                        w_picks["eliminated"] = [e1, e2]
                        w_picks["in_trouble"] = tr
                        main_cat_picks.extend([e1, e2, tr])
                    else:
                        el = st.selectbox("Predict Eliminated [5 pts]", active_bakers, index=min(2, len(active_bakers)-1), key=f"el_w{active_week}")
                        tr = st.selectbox("Predict In Trouble [2 pts]", active_bakers, index=min(3, len(active_bakers)-1), key=f"tr_w{active_week}")
                        w_picks["eliminated"] = el
                        w_picks["in_trouble"] = tr
                        main_cat_picks.extend([el, tr])
                        
                st.markdown("---")
                tech_top3 = st.multiselect("Top 3 Technical Placements (1st, 2nd, 3rd - Select exactly 3):", active_bakers, max_selections=3, key=f"tt3_w{active_week}")
                tech_bot3 = st.multiselect("Bottom 3 Technical Placements (3rd-from-last, 2nd-from-last, Last - Select exactly 3):", active_bakers, max_selections=3, key=f"tb3_w{active_week}")
                w_picks["tech_top_3"] = tech_top3
                w_picks["tech_bottom_3"] = tech_bot3
                tech_cat_picks.extend(tech_top3 + tech_bot3)
                
            sub_ballot = st.form_submit_button("Submit Prediction Ballot")
            if sub_ballot:
                # Validation
                main_dups = [b for b in set(main_cat_picks) if main_cat_picks.count(b) > 1]
                tech_dups = [b for b in set(tech_cat_picks) if tech_cat_picks.count(b) > 1]
                
                if main_dups:
                    st.error(f"⚠️ **Main Category Duplicate Error:** {', '.join(main_dups)} cannot be selected multiple times among Star Baker, Eliminated, In Line, and In Trouble.")
                elif tech_dups:
                    st.error(f"⚠️ **Technical Placements Duplicate Error:** {', '.join(tech_dups)} cannot be selected multiple times within Technical rankings.")
                else:
                    p_sub = "Ana"
                    st.session_state.league_members[p_sub]["weekly_picks"][active_week] = w_picks
                    ai_p = generate_ai_brian_weekly_picks(active_week, active_bakers, is_double_elim=is_double_elim)
                    st.session_state.league_members["AI Brian"]["weekly_picks"][active_week] = ai_p
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Predictions successfully submitted for {p_sub} in Week {active_week}!")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Performance & Analytics")
    
    current_eliminated_latest = get_current_eliminated_bakers(st.session_state.current_week)
    
    baker_stats = {b: {
        "star_baker_cnt": 0, "eliminated_cnt": 0, "in_line_cnt": 0, "in_trouble_cnt": 0,
        "handshake_cnt": 0, "tech_ranks": [], "tech_rank_pcts": []
    } for b in ALL_BAKERS}
    
    for w, res in st.session_state.weekly_results.items():
        sb = res.get("star_baker", res.get("show_champion"))
        if sb in baker_stats: baker_stats[sb]["star_baker_cnt"] += 1
            
        el = res.get("eliminated")
        if isinstance(el, list):
            for b in el:
                if b in baker_stats: baker_stats[b]["eliminated_cnt"] += 1
        elif el in baker_stats: baker_stats[el]["eliminated_cnt"] += 1
            
        inl = res.get("in_line_sb", [])
        if not isinstance(inl, list): inl = [inl]
        for b in inl:
            if b in baker_stats: baker_stats[b]["in_line_cnt"] += 1
                
        trb = res.get("in_trouble", [])
        if not isinstance(trb, list): trb = [trb]
        for b in trb:
            if b in baker_stats: baker_stats[b]["in_trouble_cnt"] += 1
                
        hs = res.get("handshake_bakers", [])
        if isinstance(hs, list):
            for b in hs:
                if b in baker_stats: baker_stats[b]["handshake_cnt"] += 1

    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
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
                    st.markdown(f"[🔗 Official Bio Page]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
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
    st.header("👑 League Administrator Console")
    
    adm_pass = st.text_input("Enter Admin Password to Unlock Console:", type="password")
    if adm_pass == "gbbs2026":
        st.session_state.admin_authenticated = True
        st.success("Admin Console Unlocked!")
    
    if st.session_state.admin_authenticated:
        adm_week = st.selectbox("Select Episode Week to Publish Results:", list(range(1, 11)), index=st.session_state.current_week - 1)
        
        current_elim_adm = get_current_eliminated_bakers(adm_week)
        active_bakers_adm = [b for b in ALL_BAKERS if b not in current_elim_adm]
        
        st.subheader(f"Publish Broadcast Results: Week {adm_week}")
        
        with st.form("admin_publish_form"):
            act_sb = st.selectbox("Actual Star Baker", active_bakers_adm)
            act_inline = st.multiselect("Actual In Line Nominees", [b for b in active_bakers_adm if b != act_sb])
            act_elim = st.multiselect("Actual Eliminated Bakers", [b for b in active_bakers_adm if b != act_sb])
            act_trouble = st.multiselect("Actual In Trouble Nominees", [b for b in active_bakers_adm if b != act_sb and b not in act_elim])
            
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", active_bakers_adm)
            act_hs_stamps = st.text_input("Handshake Video Timestamps & Context")
            
            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            act_cry_cnt = st.number_input("Crying Scenes Count", min_value=0, value=0)
            act_cry_stamps = st.text_input("Crying Scene Video Timestamps & Context")
            
            st.markdown("### 💬 Weekly Sexual Innuendos Count")
            act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=0)
            
            pub_sub = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if pub_sub:
                actuals = {
                    "star_baker": act_sb,
                    "in_line_sb": act_inline,
                    "eliminated": act_elim if act_elim else "None",
                    "in_trouble": act_trouble,
                    "handshake_bakers": act_hs_bakers,
                    "handshake_timestamps": act_hs_stamps,
                    "crying_count": act_cry_cnt,
                    "crying_timestamps": act_cry_stamps,
                    "innuendo_count": act_inn_cnt
                }
                st.session_state.weekly_results[adm_week] = actuals
                
                # Recalculate all player scores
                for m_name, m_data in st.session_state.league_members.items():
                    tot = 0
                    m_data["weekly_breakdown"] = {}
                    for w_num, w_picks in m_data.get("weekly_picks", {}).items():
                        w_act = get_weekly_result(w_num)
                        if w_act:
                            w_score = calculate_weekly_score(w_picks, w_act, week=w_num)
                            m_data["weekly_breakdown"][w_num] = w_score
                            tot += w_score
                    s_score = calculate_season_score(m_data.get("season_picks", {}), st.session_state.season_results)
                    m_data["total_score"] = tot + s_score
                    
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Broadcast results published and scores recalculated for Week {adm_week}!")
