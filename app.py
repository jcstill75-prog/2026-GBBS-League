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

# --- 3. THE 2026 OFFICIAL SCORING ENGINE ---
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

# --- 4. CORE BAKERS & OFFICIAL LEAGUE ROSTER ---
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
    "Ana", "Becca", "Craig", "Emma", "Jasmine", "Sam", 
    "Stacie W.", "Stacy C.", "Steve", "Taliah", "Tressa"
]

# --- 5. INITIALIZE SESSION STATE ---
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
    else:
        cur_p_av = st.session_state.league_members[p].get("avatar")
        if not cur_p_av:
            for check_path in [f"assets/avatars/{p}.png", f"assets/avatars/{p}.jpg", f"assets/{p}.png", f"assets/{p}.jpg"]:
                if os.path.exists(check_path):
                    st.session_state.league_members[p]["avatar"] = check_path
                    break

for old_key in ["Steve_old", "You"]:
    if old_key in st.session_state.league_members and old_key not in DEFAULT_ROSTER:
        pass

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

if "disputes" not in st.session_state:
    st.session_state.disputes = []

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
    - **Weekly Ballots:** Due prior to the broadcast each week.
    - **Star Baker:** +5 pts.
    - **Eliminated Baker:** +5 pts.
    - **Technical Placements:** Top 3 / Bottom 3 scoring in Weeks 2-7; Full Rankings in Weeks 8-10.
    - **In Line / In Trouble:** +2 pts each.
    - **Chaos Counts:** Hollywood Handshakes, Crying, and Sexual Innuendos.
    """)

# --- 8. MAIN NAVIGATION TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📊 Contestant Analytics",
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
            "avatar": av_val,
            "data": data
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
    st.subheader("🎭 Broadcast Chaos Metrics Summary")
    
    tot_hs, tot_cry, tot_inn = 0, 0, 0
    breakdown_rows = []
    
    for w_num in get_sorted_weekly_result_weeks():
        w_res = get_weekly_result(w_num)
        hs_list = w_res.get("handshake_bakers", [])
        hs_cnt = len(hs_list)
        
        cry_str = w_res.get("crying_timestamps", "")
        cry_cnt = len([s for s in cry_str.split(",") if s.strip()]) if cry_str else 0
        
        inn_cnt = w_res.get("innuendo_count", 0)
        
        tot_hs += hs_cnt
        tot_cry += cry_cnt
        tot_inn += inn_cnt
        
        breakdown_rows.append({
            "Week": f"Week {w_num}",
            "Hollywood Handshakes": f"{hs_cnt} 🤝 ({', '.join(hs_list) if hs_list else 'None'})",
            "Crying Incidents": f"{cry_cnt} 😢",
            "Sexual Innuendos": f"{inn_cnt} 💬"
        })
        
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Total Hollywood Handshakes", f"{tot_hs} 🤝")
    with m2: st.metric("Total Crying Incidents", f"{tot_cry} 😢")
    with m3: st.metric("Total Sexual Innuendos", f"{tot_inn} 💬")
    
    if breakdown_rows:
        with st.expander("📊 Episode-by-Episode Chaos Breakdown", expanded=False):
            st.dataframe(pd.DataFrame(breakdown_rows), use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards")
    for p_name in sorted(st.session_state.league_members.keys()):
        p_data = st.session_state.league_members[p_name]
        tot = p_data.get("total_score", 0)
        
        with st.expander(f"👤 {p_name} — Total Score: {tot} pts", expanded=False):
            col_av, col_info = st.columns([1, 3])
            with col_av:
                render_player_avatar(p_data.get("avatar"), width=120, caption=f"{p_name}'s Profile")
            with col_info:
                st.markdown("#### Season Projections")
                s_picks = p_data.get("season_picks", {})
                if s_picks:
                    st.write(f"🏆 **Winner Pick:** {s_picks.get('winner', 'None')}")
                    st.write(f"🥈 **Other Semifinalists:** {', '.join(s_picks.get('semifinalists', []))}")
                    st.write(f"🤝 **Handshakes:** {s_picks.get('handshakes', 'N/A')} | 😢 **Crying:** {s_picks.get('crying', 'N/A')} | 💬 **Innuendos:** {s_picks.get('innuendos', 'N/A')}")
                else:
                    st.info("No season projections locked yet.")
                    
            st.markdown("#### Weekly Ballot History")
            w_picks = p_data.get("weekly_picks", {})
            w_breakdown = p_data.get("weekly_breakdown", {})
            if w_picks:
                history_rows = []
                for w_key in sorted(w_picks.keys()):
                    w_num = int(w_key)
                    w_p = w_picks[w_key]
                    w_score = w_breakdown.get(w_num, w_breakdown.get(str(w_num), 0))
                    
                    sb = w_p.get("star_baker", w_p.get("show_champion", "N/A"))
                    el = w_p.get("eliminated", "N/A")
                    if isinstance(el, list): el = ", ".join(el)
                    
                    history_rows.append({
                        "Week": f"Week {w_num}",
                        "Points Earned": f"{w_score} pts",
                        "Star Baker Pick": sb,
                        "Eliminated Pick": el
                    })
                st.dataframe(pd.DataFrame(history_rows), use_container_width=True)
            else:
                st.write("*(No weekly ballots submitted yet)*")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    if st.session_state.current_week == 1:
        st.info("🔎 **Week 1 Scouting Phase Active!** Use this week to evaluate the bakers before locking in your Season Projections in Week 2. Weekly voting opens in Week 2.")
    
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
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
                    st.markdown(f"[🔗 Bio Page]({info['url']})")
                st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"📅 Prediction Ballot — Week {st.session_state.current_week}")
    st.warning("⏰ **Weekly Voting Window:** Ballots lock prior to the broadcast on Tuesdays.")
    
    current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
    active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
    st.info(f"Active Bakers in the Tent: " + ", ".join(active_bakers))
    
    roster_for_auth = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sel_player = st.selectbox("Select Your Player Profile to Submit:", ["-- Select Name --"] + roster_for_auth)
    
    if sel_player != "-- Select Name --":
        p_pin = st.session_state.league_members[sel_player].get("pin")
        is_authed = st.session_state.authenticated_players.get(sel_player, False)
        
        if p_pin is not None and not is_authed:
            st.warning(f"🔒 Profile locked for **{sel_player}**.")
            input_pin = st.text_input(f"Enter 4-Digit PIN for {sel_player}:", type="password", key=f"pin_entry_{sel_player}")
            if st.button("Unlock Profile"):
                if input_pin == str(p_pin):
                    st.session_state.authenticated_players[sel_player] = True
                    st.success("Profile unlocked successfully!")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again.")
        else:
            if p_pin is None:
                with st.expander("🔐 Set Profile 4-Digit PIN (Optional)"):
                    new_pin = st.text_input("Choose 4-Digit PIN:", type="password", key=f"new_pin_{sel_player}")
                    if st.button("Save PIN"):
                        if len(new_pin) == 4 and new_pin.isdigit():
                            st.session_state.league_members[sel_player]["pin"] = new_pin
                            st.session_state.authenticated_players[sel_player] = True
                            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                            st.success("PIN set successfully!")
                            st.rerun()
                        else:
                            st.error("PIN must be exactly 4 digits.")
                            
            if st.session_state.current_week == 2:
                with st.expander("🌟 Season-Long Projections (Locks Week 2 | 130 pts total)", expanded=True):
                    user_winner = st.selectbox("Predict Season Winner [40 pts]", active_bakers, key=f"win_{sel_player}")
                    rem_semis = [b for b in active_bakers if b != user_winner]
                    user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", rem_semis, max_selections=3, key=f"semis_{sel_player}")
                    user_hs = st.number_input("Predict Total Handshakes [20 pts]", min_value=0, value=5, key=f"hs_{sel_player}")
                    user_cry = st.number_input("Predict Total Crying Incidents [20 pts]", min_value=0, value=10, key=f"cry_{sel_player}")
                    user_inn = st.number_input("Predict Total Innuendos [20 pts]", min_value=0, value=40, key=f"inn_{sel_player}")
                    
                    if st.button("Lock Season Projections"):
                        if len(user_semis) != 3:
                            st.error("Please select exactly 3 other semifinalists.")
                        else:
                            st.session_state.league_members[sel_player]["season_picks"] = {
                                "winner": user_winner,
                                "semifinalists": user_semis,
                                "handshakes": user_hs,
                                "crying": user_cry,
                                "innuendos": user_inn
                            }
                            save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                            st.success(f"Season projections saved for {sel_player}!")

            st.markdown(f"### Weekly Ballot — Week {st.session_state.current_week}")
            with st.form(f"ballot_form_{sel_player}"):
                w_picks = {}
                
                if st.session_state.current_week == 10:
                    w_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", active_bakers)
                    t1 = st.selectbox("Technical 1st Place", active_bakers, index=0)
                    t2 = st.selectbox("Technical 2nd Place", [b for b in active_bakers if b != t1], index=0)
                    t3 = st.selectbox("Technical 3rd Place", [b for b in active_bakers if b not in [t1, t2]], index=0)
                    w_picks["tech_rank"] = [t1, t2, t3]
                elif st.session_state.current_week == 9:
                    w_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                    w_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", [b for b in active_bakers if b != w_picks.get("star_baker")])
                    t1 = st.selectbox("Technical 1st Place", active_bakers, index=0)
                    t2 = st.selectbox("Technical 2nd Place", [b for b in active_bakers if b != t1], index=0)
                    t3 = st.selectbox("Technical 3rd Place", [b for b in active_bakers if b not in [t1, t2]], index=0)
                    t4 = st.selectbox("Technical 4th Place", [b for b in active_bakers if b not in [t1, t2, t3]], index=0)
                    w_picks["tech_rank"] = [t1, t2, t3, t4]
                elif st.session_state.current_week == 8:
                    c1, c2 = st.columns(2)
                    with c1:
                        w_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                        w_picks["in_line_sb"] = st.selectbox("Predict In Line SB [2 pts]", [b for b in active_bakers if b != w_picks.get("star_baker")])
                    with c2:
                        w_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers)
                        w_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", [b for b in active_bakers if b != w_picks.get("eliminated")])
                    t1 = st.selectbox("Technical 1st", active_bakers, index=0, key="t1_w8")
                    t2 = st.selectbox("Technical 2nd", [b for b in active_bakers if b != t1], index=0, key="t2_w8")
                    t3 = st.selectbox("Technical 3rd", [b for b in active_bakers if b not in [t1, t2]], index=0, key="t3_w8")
                    t4 = st.selectbox("Technical 4th", [b for b in active_bakers if b not in [t1, t2, t3]], index=0, key="t4_w8")
                    t5 = st.selectbox("Technical 5th", [b for b in active_bakers if b not in [t1, t2, t3, t4]], index=0, key="t5_w8")
                    w_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        w_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", active_bakers)
                        w_picks["in_line_sb"] = st.selectbox("Predict In Line SB [2 pts]", active_bakers)
                    with c2:
                        w_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", active_bakers)
                        w_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", active_bakers)
                        
                    st.markdown("---")
                    t_top = st.multiselect("Top 3 Technical (Order: 1st, 2nd, 3rd - Max 3)", active_bakers, max_selections=3)
                    t_bot = st.multiselect("Bottom 3 Technical (Order: 3rd-last, 2nd-last, Last - Max 3)", [b for b in active_bakers if b not in t_top], max_selections=3)
                    w_picks["tech_top_3"] = t_top
                    w_picks["tech_bottom_3"] = t_bot

                sub_ballot = st.form_submit_button("Submit Prediction Ballot")
                if sub_ballot:
                    # Validate Main Categories
                    main_picks = [w_picks.get("star_baker"), w_picks.get("eliminated"), w_picks.get("in_line_sb"), w_picks.get("in_trouble")]
                    main_picks = [p for p in main_picks if p and p != "None"]
                    if len(main_picks) != len(set(main_picks)):
                        st.error("⚠️ **Duplicate Selection Error in Main Categories:** You cannot select the same baker multiple times among Star Baker, Eliminated, In Line, and In Trouble.")
                    else:
                        st.session_state.league_members[sel_player]["weekly_picks"][st.session_state.current_week] = w_picks
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success(f"Predictions saved for {sel_player}!")

# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📊 Contestant Analytics")
    st.write("Examine individual baker stats, star baker counts, in trouble nominations, and official bios!")
    
    baker_stats = {b: {"star_baker_cnt": 0, "in_line_cnt": 0, "in_trouble_cnt": 0, "eliminated_week": None, "handshake_cnt": 0} for b in ALL_BAKERS}
    
    for w_num in get_sorted_weekly_result_weeks():
        res = get_weekly_result(w_num)
        sb = res.get("star_baker")
        if sb in baker_stats: baker_stats[sb]["star_baker_cnt"] += 1
        
        for il in res.get("in_line_sb", []):
            if il in baker_stats: baker_stats[il]["in_line_cnt"] += 1
            
        for itr in res.get("in_trouble", []):
            if itr in baker_stats: baker_stats[itr]["in_trouble_cnt"] += 1
            
        for hs in res.get("handshake_bakers", []):
            if hs in baker_stats: baker_stats[hs]["handshake_cnt"] += 1

    latest_elim = get_current_eliminated_bakers(10)
    
    sel_baker = st.selectbox("Select Baker to Inspect:", ALL_BAKERS)
    s = baker_stats[sel_baker]
    is_elim = sel_baker in latest_elim
    
    c_img, c_stats = st.columns([1, 2])
    with c_img:
        b_img = load_baker_image(sel_baker)
        if b_img:
            st.image(b_img, width=200, caption=f"{sel_baker} ('Class of 2026')")
        else:
            st.markdown(f"### 🧁 {sel_baker}")
            st.write("*(No portrait uploaded)*")
            
        b_url = BAKER_INFO.get(sel_baker, {}).get("url")
        if b_url:
            st.markdown(f"👉 [Read Official Bio on Bake Off Website]({b_url})")
            
    with c_stats:
        status_str = "❌ Eliminated" if is_elim else "🟢 Active in the Tent"
        st.markdown(f"### Status: **{status_str}**")
        
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Star Baker Wins", f"{s['star_baker_cnt']} 🌟")
        with m2: st.metric("In Line Nominee", f"{s['in_line_cnt']} 📈")
        with m3: st.metric("In Trouble", f"{s['in_trouble_cnt']} ⚠️")
        with m4: st.metric("Hollywood Handshakes", f"{s['handshake_cnt']} 🤝")

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Log broadcast results to score prediction ballots and update the Live Leaderboard!")
    
    admin_pin = "2026"
    if not st.session_state.admin_authenticated:
        a_input = st.text_input("Enter Admin PIN:", type="password", key="admin_pin_input")
        if st.button("Authenticate Admin"):
            if a_input == admin_pin:
                st.session_state.admin_authenticated = True
                st.success("Admin authenticated!")
                st.rerun()
            else:
                st.error("Invalid Admin PIN.")
    else:
        st.success("🔑 Admin Console Authenticated")
        adm_week = st.number_input("Select Week to Log Broadcast Results:", min_value=1, max_value=10, value=st.session_state.current_week)
        
        curr_elim = get_current_eliminated_bakers(adm_week)
        act_bakers = [b for b in ALL_BAKERS if b not in curr_elim]
        
        with st.form("admin_results_form"):
            st.markdown(f"### Broadcast Results Entry — Week {adm_week}")
            
            is_double = st.checkbox("📢 Double-Elimination Week?", value=False)
            
            col_a, col_b = st.columns(2)
            with col_a:
                act_sb = st.selectbox("Actual Star Baker:", act_bakers)
                act_in_line = st.multiselect("Actual In Line for SB (Nominees):", [b for b in act_bakers if b != act_sb])
            with col_b:
                if is_double:
                    act_elim1 = st.selectbox("Actual Eliminated #1:", act_bakers, key="adm_e1")
                    act_elim2 = st.selectbox("Actual Eliminated #2:", [b for b in act_bakers if b != act_elim1], key="adm_e2")
                    act_elim = [act_elim1, act_elim2]
                else:
                    act_elim = st.selectbox("Actual Eliminated Baker:", act_bakers)
                    
                act_trouble = st.multiselect("Actual In Trouble Nominees:", act_bakers)

            st.markdown("---")
            st.markdown("#### Technical Challenge Actual Rankings")
            act_tech = st.multiselect(f"Technical Placement (1st to Last - Select all {len(act_bakers)} active bakers in order):", act_bakers)
            
            st.markdown("---")
            st.markdown("#### Broadcast Chaos Counts")
            act_hs_bakers = st.multiselect("Hollywood Handshake Recipients:", act_bakers)
            act_hs_stamps = st.text_input("Handshake Timestamps (e.g. '14:22 Signature')")
            act_cry_stamps = st.text_input("Crying Scene Timestamps (e.g. '22:15 Tech, 41:02 Showstopper')")
            act_inn_cnt = st.number_input("Sexual Innuendos Count:", min_value=0, value=0)
            
            pub_res = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if pub_res:
                act_dict = {
                    "star_baker": act_sb,
                    "in_line_sb": act_in_line,
                    "eliminated": act_elim,
                    "in_trouble": act_trouble,
                    "tech_rank": act_tech,
                    "handshake_bakers": act_hs_bakers,
                    "handshake_timestamps": act_hs_stamps,
                    "crying_timestamps": act_cry_stamps,
                    "innuendo_count": act_inn_cnt
                }
                st.session_state.weekly_results[adm_week] = act_dict
                
                # Recalculate all player scores
                for m_name in st.session_state.league_members:
                    tot_score = 0
                    m_breakdown = {}
                    m_picks = st.session_state.league_members[m_name].get("weekly_picks", {})
                    
                    for w_k in get_sorted_weekly_result_weeks():
                        w_u_picks = m_picks.get(w_k, m_picks.get(str(w_k), {}))
                        w_actuals = get_weekly_result(w_k)
                        w_pts = calculate_weekly_score(w_u_picks, w_actuals, week=w_k)
                        tot_score += w_pts
                        m_breakdown[w_k] = w_pts
                        
                    st.session_state.league_members[m_name]["total_score"] = tot_score
                    st.session_state.league_members[m_name]["weekly_breakdown"] = m_breakdown
                    
                save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                st.success(f"Week {adm_week} results published and standings recalculated!")
