import streamlit as st
import pandas as pd
import random
import os
import base64
from PIL import Image
import io

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
    .metric-card {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #D36B5F;
    }
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

# --- 2. THE 2026 OFFICIAL SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return 0
        
    # --- A. Main Episode Results ---
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
            elif isinstance(pred_elim, str):
                if pred_elim in act_elim:
                    score += 5
        elif act_elim == "None" or act_elim is None:
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
        if not act_top3 and "tech_rank" in actuals:
            act_top3 = actuals["tech_rank"][:3]
            
        if len(pred_top3) == 3 and len(act_top3) >= 3:
            if pred_top3 == act_top3[:3]:
                score += 10
            else:
                if pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] == act_top3[2]: score += 2
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3[:3] and baker != act_top3[idx]:
                        score += 1
                        
        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        if not act_bottom3 and "tech_rank" in actuals:
            act_bottom3 = actuals["tech_rank"][-3:]
            
        if len(pred_bottom3) == 3 and len(act_bottom3) >= 3:
            if pred_bottom3 == act_bottom3[-3:]:
                score += 10
            else:
                if pred_bottom3[0] == act_bottom3[0]: score += 2
                if pred_bottom3[1] == act_bottom3[1]: score += 2
                if pred_bottom3[2] == act_bottom3[2]: score += 3
                for idx, baker in enumerate(pred_bottom3):
                    if baker in act_bottom3[-3:] and baker != act_bottom3[idx]:
                        score += 1

    # --- C. Consolations ---
    if week < 9:
        act_inline = actuals.get("in_line_sb", [])
        if isinstance(act_inline, str): act_inline = [act_inline]
        if predictions.get("in_line_sb") and (predictions.get("in_line_sb") in act_inline) and (predictions.get("in_line_sb") != actuals.get("star_baker")):
            score += 2
            
        act_trouble = actuals.get("in_trouble", [])
        if isinstance(act_trouble, str): act_trouble = [act_trouble]
        # REFINED SCORING RULE: As long as predicted in_trouble matches any actual in_trouble nominee, award +2 pts regardless of elimination!
        if predictions.get("in_trouble") and (predictions.get("in_trouble") in act_trouble):
            score += 2
            
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
    if pred_winner and act_winner and pred_winner == act_winner:
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


def load_baker_image(baker_name):
    """Smart case-insensitive and multi-extension image loader."""
    if not os.path.exists("assets"):
        return None
    
    target = baker_name.lower().strip()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        filename = f"{target}{ext}"
        filepath = os.path.join("assets", filename)
        if os.path.exists(filepath):
            try:
                return Image.open(filepath)
            except Exception:
                pass
    try:
        for f in os.listdir("assets"):
            if f.lower().startswith(target) and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                return Image.open(os.path.join("assets", f))
    except Exception:
        pass
    return None

def render_player_avatar(avatar_val, width=120, caption="Profile"):
    if isinstance(avatar_val, Image.Image):
        st.image(avatar_val, width=width, caption=caption)
    elif isinstance(avatar_val, str) and avatar_val.startswith("data:image"):
        st.markdown(f'<img src="{avatar_val}" style="width:{width}px; height:{width}px; border-radius:50%; object-fit:cover;">', unsafe_allow_html=True)
    elif isinstance(avatar_val, str) and os.path.exists(avatar_val):
        st.image(avatar_val, width=width, caption=caption)
    elif avatar_val == "🤖":
        st.markdown(f"<h1 style='font-size: {width//2}px; margin: 0;'>🤖</h1>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 style='font-size: {width//2}px; margin: 0;'>🍪</h1>", unsafe_allow_html=True)


# --- 3. CORE BAKERS LIST & ROSTER INITIALIZATION ---
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

ROSTER_ALPHABETICAL = [
    "AI Brian", "Ana", "Becca", "Brian", "Cassie", "Emma", 
    "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", 
    "Stacie W.", "Stacy C.", "Taliah", "Tressa"
]

ROSTER_HUMANS = [m for m in ROSTER_ALPHABETICAL if m != "AI Brian"]

# Eliminated Bakers Dictionary by Week
eliminated_bakers_by_week = {
    1: [],  # Week 1: All 12 bakers active in the tent!
    2: ["Yannis"],
    3: ["Yannis", "Nikki"],
    4: ["Yannis", "Nikki", "Connie"],
    5: ["Yannis", "Nikki", "Connie", "Gary"],
    6: ["Yannis", "Nikki", "Connie", "Gary", "Moyin"],
    7: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara"],
    8: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon"],
    9: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly"],
    10: ["Yannis", "Nikki", "Connie", "Gary", "Moyin", "Clara", "Shannon", "Molly", "Danni"]
}

# Streamlit Session State Initialization for persistence
if "league_members" not in st.session_state:
    st.session_state.league_members = {}

for member_name in ROSTER_ALPHABETICAL:
    if member_name not in st.session_state.league_members:
        st.session_state.league_members[member_name] = {
            "avatar": "🤖" if member_name == "AI Brian" else None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None
        }

# Check for AI Brian's custom profile picture
brian_avatar_img = None
for brian_path in ["ai_brian.jpg", "AI Brian.jpg", "assets/ai_brian.jpg", "assets/AI_Brian.jpg", "assets/ai_brian.png", "assets/AI_Brian.png"]:
    if os.path.exists(brian_path):
        try:
            brian_avatar_img = Image.open(brian_path)
            break
        except Exception:
            pass

if brian_avatar_img is not None:
    st.session_state.league_members["AI Brian"]["avatar"] = brian_avatar_img

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = {}

if "season_results" not in st.session_state:
    st.session_state.season_results = {}

if "disputes" not in st.session_state:
    st.session_state.disputes = []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False


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
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim and len(elim_pool) >= 2:
            eliminated = random.sample(elim_pool, 2)
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        return {"star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank}
    elif week == 8:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim and len(elim_pool) >= 2:
            eliminated = random.sample(elim_pool, 2)
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        tech_rank = random.sample(active_bakers, len(active_bakers))
        in_line_sb = random.choice([b for b in active_bakers if b != star_baker]) if len(active_bakers) > 1 else active_bakers[0]
        in_trouble_pool = [b for b in active_bakers if b not in (eliminated if isinstance(eliminated, list) else [eliminated])]
        in_trouble = random.choice(in_trouble_pool) if in_trouble_pool else active_bakers[0]
        return {
            "star_baker": star_baker, "eliminated": eliminated, "tech_rank": tech_rank,
            "in_line_sb": in_line_sb, "in_trouble": in_trouble
        }
    else:
        star_baker = random.choice(active_bakers)
        elim_pool = [b for b in active_bakers if b != star_baker]
        if is_double_elim and len(elim_pool) >= 2:
            eliminated = random.sample(elim_pool, 2)
        else:
            eliminated = random.choice(elim_pool) if elim_pool else active_bakers[0]
        
        tech_top_3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bottom = [b for b in active_bakers if b not in tech_top_3]
        tech_bottom_3 = random.sample(rem_bottom, min(3, len(rem_bottom))) if rem_bottom else random.sample(active_bakers, min(3, len(active_bakers)))
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

# --- 5. APP INTERFACE LAYOUT ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("normanbeaver.jpg"):
        st.image("normanbeaver.jpg", width=90)
    elif os.path.exists("assets/normanbeaver.jpg"):
        st.image("assets/normanbeaver.jpg", width=90)
    else:
        st.write("🦫")

with col_title:
    st.title("🧁 Great British Baking Show Fantasy League 2026")
    st.markdown("### Powered by the Balanced 2026 Competition Rules Engine")

# --- SIDEBAR: PLAYER AVATAR UPLOAD & POINTS REFERENCE GUIDE ---
with st.sidebar:
    st.header("👤 Player Avatar Uploader")
    avatar_player_sel = st.selectbox("Select Player Profile:", ROSTER_HUMANS, key="avatar_player_sel")
    uploaded_file = st.file_uploader(f"Upload Avatar Photo for {avatar_player_sel}", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        image = image.resize((150, 150))
        st.session_state.league_members[avatar_player_sel]["avatar"] = image
        st.image(image, caption=f"{avatar_player_sel}'s Avatar", width=120)
    else:
        curr_av = st.session_state.league_members[avatar_player_sel].get("avatar")
        render_player_avatar(curr_av, width=120, caption=f"{avatar_player_sel}'s Avatar")

    # Determine competition progress automatically from published results
    all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
    latest_scored_week = max(all_scored_weeks) if all_scored_weeks else 0
    active_comp_week = latest_scored_week + 1 if latest_scored_week < 10 else 10

    st.markdown("---")
    st.header("📌 Competition Progress")
    if latest_scored_week == 0:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\n*Week 2 predictions will unlock automatically once Week 1 results are published in the Admin Panel.*")
    else:
        st.success(f"🟢 **Active Status: Week {active_comp_week} Predictions Open**\n\n*Broadcast results published through Week {latest_scored_week}.*")

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

    with st.expander("📅 Weekly Episodic Predictions", expanded=False):
        st.markdown("""
        *   **Star Baker:** 5 pts
        *   **In Line for Star Baker:** 2 pts *(consolation)*
        *   **Eliminated Baker:** 5 pts
        *   **In Trouble of Elimination:** 2 pts *(consolation)*
        *   **Technical Top 3 Sequence:** Up to 10 pts flat sweep *(3pts 1st, 2pts 2nd/3rd, 1pt wrong spot)*
        *   **Technical Bottom 3 Sequence:** Up to 10 pts flat sweep *(2pts 9th/10th, 3pts 11th, 1pt wrong spot)*
        *   **Week 8 Quarterfinal (5 bakers):** Perfect 5-for-5 sweep = 25 pts flat!
        *   **Week 9 Semifinal (4 bakers):** Perfect 4-for-4 sweep = 20 pts flat!
        *   **Week 10 Finale (3 bakers):** Perfect 3-for-3 sweep = 15 pts flat!
        *   **Weekly Star Bonus:** +5 pts to the weekly top scorer!
        """)


# --- MAIN TABS (ADMIN PANEL ON FAR RIGHT) ---
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
    for name in ROSTER_ALPHABETICAL:
        data = st.session_state.league_members.get(name, {})
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
                    <th style="text-align: right; width: 120px;">Total Points</th>
                </tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    scorecard_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="scorecard_player_sel")
    p_data = st.session_state.league_members.get(scorecard_player, {})
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})
    
    col_av, col_details = st.columns([1, 3])
    with col_av:
        render_player_avatar(p_data.get("avatar"), width=120, caption=f"{scorecard_player}'s Profile")
    with col_details:
        st.markdown(f"### **{scorecard_player}'s Season Projections (Total Score: {p_pts} pts)**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
        
    if p_weekly:
        st.markdown("#### **Weekly Predictions Log:**")
        w_rows = []
        for w_num in sorted(p_weekly.keys()):
            w_picks = p_weekly[w_num]
            sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
            el = w_picks.get("eliminated", "N/A")
            if isinstance(el, list): el = ", ".join(el)
            t3 = ", ".join(w_picks.get("tech_top_3", [])) if w_picks.get("tech_top_3") else "N/A"
            
            w_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker Pick": sb,
                "Eliminated Pick": el,
                "Technical Top 3": t3
            })
        st.dataframe(pd.DataFrame(w_rows), use_container_width=True)

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps (Verify Counts)")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 1!")
    else:
        audit_rows = []
        tot_hs = 0
        tot_cry = 0
        tot_inn = 0

        for w_num in sorted(st.session_state.weekly_results.keys()):
            w_act = st.session_state.weekly_results[w_num]
            hs_bakers = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
            hs_stamps = w_act.get("handshake_timestamps", "N/A") or "N/A"
            cry_stamps = w_act.get("crying_timestamps", "N/A") or "N/A"
            inn_cnt = w_act.get("innuendo_count", 0)

            tot_hs += w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
            tot_cry += w_act.get("crying_count", 0)
            tot_inn += inn_cnt

            audit_rows.append({
                "Week": f"Week {w_num}",
                "Star Baker": w_act.get("star_baker", w_act.get("show_champion", "N/A")),
                "Eliminated": ", ".join(w_act["eliminated"]) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "N/A"),
                "Handshake Bakers": hs_bakers,
                "Handshake Timestamps": hs_stamps,
                "Crying Timestamps": cry_stamps,
                "Innuendos": inn_cnt
            })

        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True)
        st.markdown(f"**Cumulative Broadcast Totals Across Logged Weeks:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", ROSTER_HUMANS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 1"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Video Evidence (e.g., 'At 28:14 in Episode 3, Paul clearly shakes Tom's hand during Showstopper judging')")
            disp_correction = st.text_input("Requested Correction (e.g., 'Add +1 Handshake for Tom in Week 3')")
            
            sub_disp = st.form_submit_button("Submit Dispute for League Vote")
            if sub_disp:
                st.session_state.disputes.append({
                    "Player": disp_player,
                    "Week": disp_week,
                    "Category": disp_cat,
                    "Evidence": disp_evidence,
                    "Correction": disp_correction,
                    "Status": "Pending GroupMe Vote 🗳️"
                })
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        df_disp = pd.DataFrame(st.session_state.disputes)
        st.dataframe(df_disp, use_container_width=True)


# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=True):
        st.write("Browse official photographs and bios for the Class of 2026:")
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
    st.subheader("🔒 Player Login & Prediction Ballot")
    
    selected_player = st.selectbox("Select Your Player Name:", ROSTER_HUMANS, key="pred_player_sel")
    player_info = st.session_state.league_members[selected_player]
    
    # 4-Digit Password Security System
    authenticated = False
    player_pin = player_info.get("pin")
    
    if player_pin is None:
        st.info(f"Welcome, **{selected_player}**! Create a 4-digit PIN to secure your prediction ballot.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            new_pin = st.text_input("Create 4-Digit PIN:", type="password", max_chars=4, key="create_pin_input")
        with col_p2:
            conf_pin = st.text_input("Confirm 4-Digit PIN:", type="password", max_chars=4, key="confirm_pin_input")
            
        if st.button("Set 4-Digit PIN & Proceed"):
            if len(new_pin) == 4 and new_pin.isdigit():
                if new_pin == conf_pin:
                    player_info["pin"] = new_pin
                    st.success(f"PIN created successfully for {selected_player}! You are now logged in.")
                    st.rerun()
                else:
                    st.error("PINs do not match! Please verify both input boxes.")
            else:
                st.error("PIN must be exactly 4 numeric digits!")
    else:
        entered_pin = st.text_input(f"Enter 4-Digit PIN for {selected_player}:", type="password", max_chars=4, key="login_pin_input")
        if entered_pin == player_pin:
            authenticated = True
            st.success(f"🔓 Authenticated as **{selected_player}**")
        elif entered_pin != "":
            st.error("Incorrect PIN! Please try again or ask the Administrator to reset your PIN.")

    if authenticated:
        st.markdown("---")
        
        # 1. Post-Week 1 Season-Long Predictions Form
        with st.expander("🌟 Season-Long Projections (Locks Post-Week 1! | 130 pts total at stake)", expanded=True):
            s_picks = player_info.get("season_picks", {})
            st.write("Submit your long-term season projections (Winner, Semifinalists, and Chaos Counts):")
            
            win_opts = ["--Select Baker--"] + ALL_BAKERS
            cur_win = s_picks.get("winner", "--Select Baker--")
            win_idx = win_opts.index(cur_win) if cur_win in win_opts else 0
            user_winner = st.selectbox("Predict Season Winner [40 pts if winner, 15 pts if runner-up consolation]", win_opts, index=win_idx, key="user_win_pick_sub")
            
            user_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each | 30 pts max]", ALL_BAKERS, default=s_picks.get("semifinalists", []), max_selections=3)
            user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=s_picks.get("handshakes", 5))
            user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=s_picks.get("crying", 10))
            user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=s_picks.get("innuendos", 40))
            
            if st.button("Lock Season-Long Predictions"):
                if user_winner == "--Select Baker--":
                    st.error("Please select a valid Season Winner!")
                elif len(user_semis) != 3:
                    st.error("Please select exactly 3 other semifinalists.")
                elif user_winner in user_semis:
                    st.error("Season Winner cannot also be selected as an 'other' semifinalist!")
                else:
                    player_info["season_picks"] = {
                        "winner": user_winner,
                        "semifinalists": user_semis,
                        "handshakes": user_handshakes,
                        "crying": user_crying,
                        "innuendos": user_innuendos
                    }
                    st.success("Season long predictions saved successfully!")

        st.markdown("---")
        
        # 2. Dynamic Weekly Ballot based on competition progress
        all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
        latest_scored_week = max(all_scored_weeks) if all_scored_weeks else 0
        active_comp_week = latest_scored_week + 1 if latest_scored_week < 10 else 10
        
        st.subheader(f"📅 Submit Weekly Predictions: Week {active_comp_week}")
        st.warning("⏰ **Weekly Voting Window Notice:** All prediction ballots must be locked in prior to the Great British Baking Show broadcast on **Tuesdays right before the episode airs in the UK**.")
        
        # Active bakers in the tent for active_comp_week
        current_eliminated = eliminated_bakers_by_week.get(active_comp_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_select_options = ["--Select Baker--"] + active_bakers
        
        st.info(f"Active Bakers in the Tent for Week {active_comp_week}: " + ", ".join(active_bakers))
        
        prev_week_results = st.session_state.weekly_results.get(active_comp_week - 1, {})
        prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
        
        is_double_elim = False
        if active_comp_week < 10:
            is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace)

        with st.form("weekly_predictions_form"):
            weekly_picks = {}
            
            if active_comp_week == 10:
                weekly_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts at stake]", baker_select_options, index=0)
                st.write("Predict Technical Challenge Final Rank [1st=3pts, 2nd/3rd=2pts; Perfect Sweep = 15 pts flat]:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_select_options, index=0)
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_select_options, index=0)
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_select_options, index=0)
                weekly_picks["tech_rank"] = [t1, t2, t3]
                
            elif active_comp_week == 9:
                weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_select_options, index=0)
                if is_double_elim:
                    e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_select_options, index=0, key="pred_e1_w9")
                    e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_select_options, index=0, key="pred_e2_w9")
                    weekly_picks["eliminated"] = [e1, e2]
                else:
                    weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_select_options, index=0)
                
                st.write("Predict Technical Challenge Final Rank [1st/4th=3pts, 2nd/3rd=2pts; Perfect Sweep = 20 pts flat]:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_select_options, index=0)
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_select_options, index=0)
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_select_options, index=0)
                t4 = st.selectbox("Technical 4th Place [3 pts]", baker_select_options, index=0)
                weekly_picks["tech_rank"] = [t1, t2, t3, t4]

            elif active_comp_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_select_options, index=0)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", baker_select_options, index=0)
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_select_options, index=0, key="pred_e1_w8")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_select_options, index=0, key="pred_e2_w8")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_select_options, index=0)
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated]", baker_select_options, index=0)
                
                st.write("Predict Technical Challenge Final Rank [1st/5th=3pts, 2nd/3rd/4th=2pts; Perfect Sweep = 25 pts flat]:")
                t1 = st.selectbox("Technical 1st Place [3 pts]", baker_select_options, index=0, key="t1_w8")
                t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_select_options, index=0, key="t2_w8")
                t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_select_options, index=0, key="t3_w8")
                t4 = st.selectbox("Technical 4th Place [2 pts]", baker_select_options, index=0, key="t4_w8")
                t5 = st.selectbox("Technical 5th Place [3 pts]", baker_select_options, index=0, key="t5_w8")
                weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                
            else:
                # Standard Weeks 1-7
                col1, col2 = st.columns(2)
                with col1:
                    weekly_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts at stake]", baker_select_options, index=0)
                    weekly_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", baker_select_options, index=0)
                with col2:
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", baker_select_options, index=0, key="pred_e1_std")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", baker_select_options, index=0, key="pred_e2_std")
                        weekly_picks["eliminated"] = [e1, e2]
                    else:
                        weekly_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts at stake]", baker_select_options, index=0)
                    weekly_picks["in_trouble"] = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated]", baker_select_options, index=0)
                    
                st.markdown("---")
                st.write("Predict Technical Challenge Placements:")
                t_1st = st.selectbox("Technical 1st Place [3 pts]", baker_select_options, index=0)
                t_2nd = st.selectbox("Technical 2nd Place [2 pts]", baker_select_options, index=0)
                t_3rd = st.selectbox("Technical 3rd Place [2 pts]", baker_select_options, index=0)
                t_3rd_last = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_select_options, index=0)
                t_2nd_last = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_select_options, index=0)
                t_last = st.selectbox("Technical Last Place [3 pts]", baker_select_options, index=0)
                
                weekly_picks["tech_top_3"] = [t_1st, t_2nd, t_3rd]
                weekly_picks["tech_bottom_3"] = [t_3rd_last, t_2nd_last, t_last]
                
            submitted = st.form_submit_button("Submit Predictions")
            if submitted:
                # 1. Unselected placeholder check
                has_unselected = False
                all_picks_flat = []
                for k, v in weekly_picks.items():
                    if isinstance(v, list):
                        all_picks_flat.extend(v)
                    else:
                        all_picks_flat.append(v)
                        
                if "--Select Baker--" in all_picks_flat:
                    st.error("⚠️ Please select a valid baker for all prediction fields!")
                else:
                    # 2. Strict Duplicate Validation
                    if active_comp_week in [8, 9, 10]:
                        main_picks = [weekly_picks.get("star_baker"), weekly_picks.get("in_line_sb"), weekly_picks.get("in_trouble")]
                        elim_val = weekly_picks.get("eliminated")
                        if isinstance(elim_val, list): main_picks.extend(elim_val)
                        else: main_picks.append(elim_val)
                        main_picks = [p for p in main_picks if p]
                        
                        tech_picks = weekly_picks.get("tech_rank", [])
                    else:
                        main_picks = [weekly_picks.get("star_baker"), weekly_picks.get("in_line_sb"), weekly_picks.get("in_trouble")]
                        elim_val = weekly_picks.get("eliminated")
                        if isinstance(elim_val, list): main_picks.extend(elim_val)
                        else: main_picks.append(elim_val)
                        main_picks = [p for p in main_picks if p]
                        
                        tech_picks = weekly_picks.get("tech_top_3", []) + weekly_picks.get("tech_bottom_3", [])
                        
                    if len(main_picks) != len(set(main_picks)):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    elif len(tech_picks) != len(set(tech_picks)):
                        st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                    else:
                        player_info["weekly_picks"][active_comp_week] = weekly_picks
                        ai_picks = generate_ai_brian_weekly_picks(active_comp_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][active_comp_week] = ai_picks
                        st.success(f"Predictions successfully locked for Week {active_comp_week}! AI Brian has also logged his picks.")


# --- TAB 3: CONTESTANT ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Baker Cards")
    st.write("Detailed profiles for the Series 17 Bakers:")
    selected_baker = st.selectbox("Select a Baker to Inspect:", ALL_BAKERS)
    
    col_img, col_details = st.columns([1, 2])
    with col_img:
        b_img = load_baker_image(selected_baker)
        if b_img is not None:
            st.image(b_img, caption=selected_baker, use_container_width=True)
        else:
            st.info(f"No image file found for {selected_baker} in assets/.")
    with col_details:
        st.subheader(f"Baker Profile: {selected_baker}")
        b_info = BAKER_INFO.get(selected_baker, {})
        st.markdown(f"[🔗 Official Show Profile Page]({b_info.get('url', '#')})")


# --- TAB 4: ADMIN PANEL (FAR RIGHT) ---
with tab_admin:
    st.header("👑 League Administrator Console")
    st.write("Input official broadcast results to calculate scores and update the leaderboard!")
    
    # Password Protection for Admin Panel (PIN 6284)
    if not st.session_state.admin_authenticated:
        admin_pin = st.text_input("Enter Administrator PIN to Access Console:", type="password", key="admin_pin_access")
        if st.button("Unlock Admin Panel"):
            if admin_pin == "6284":
                st.session_state.admin_authenticated = True
                st.success("🔓 Admin Panel Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Administrator PIN!")
    else:
        if st.button("🔒 Lock Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        st.markdown("### 📅 Select Episode Results to Input")
        
        all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
        default_admin_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
        if default_admin_week > 10: default_admin_week = 10
        
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=default_admin_week - 1,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_choice_sel"
        )
        
        current_eliminated = eliminated_bakers_by_week.get(admin_selected_week, [])
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_opts = ["--Select Baker--"] + active_bakers
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {admin_selected_week}")
            actuals = {}
            
            if admin_selected_week == 10:
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts, index=0)
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st Place", baker_opts, index=0)
                act_t2 = st.selectbox("Actual Technical 2nd Place", baker_opts, index=0)
                act_t3 = st.selectbox("Actual Technical 3rd Place", baker_opts, index=0)
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
                
            elif admin_selected_week == 9:
                actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=0)
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=0)
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts, index=0, key="admin_act_e1_w9")
                    e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts, index=0, key="admin_act_e2_w9")
                    actuals["eliminated"] = [e1, e2]
                
                st.write("Actual Technical Challenge Rankings:")
                act_t1 = st.selectbox("Actual Technical 1st", baker_opts, index=0)
                act_t2 = st.selectbox("Actual Technical 2nd", baker_opts, index=0)
                act_t3 = st.selectbox("Actual Technical 3rd", baker_opts, index=0)
                act_t4 = st.selectbox("Actual Technical 4th", baker_opts, index=0)
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4]

            elif admin_selected_week == 8:
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers)
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w8")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=0)
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts, index=0, key="admin_act_e1_w8")
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts, index=0, key="admin_act_e2_w8")
                        actuals["eliminated"] = [e1, e2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    
                st.write("Actual Technical Challenge Rankings (1st through 5th):")
                act_t1 = st.selectbox("Actual Technical 1st", baker_opts, index=0, key="act_t1_w8")
                act_t2 = st.selectbox("Actual Technical 2nd", baker_opts, index=0, key="act_t2_w8")
                act_t3 = st.selectbox("Actual Technical 3rd", baker_opts, index=0, key="act_t3_w8")
                act_t4 = st.selectbox("Actual Technical 4th", baker_opts, index=0, key="act_t4_w8")
                act_t5 = st.selectbox("Actual Technical 5th", baker_opts, index=0, key="act_t5_w8")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3, act_t4, act_t5]
                
            else:
                # Standard Weeks 1-7
                col1, col2 = st.columns(2)
                with col1:
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=0)
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers)
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_std")
                    if elim_type == "Single Elimination":
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=0)
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                    else:
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts, index=0, key="admin_act_e1_std")
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts, index=0, key="admin_act_e2_std")
                        actuals["eliminated"] = [e1, e2]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers)
                    
                st.write("Actual Technical Challenge Rankings (Enter all positions separately for rich analytics):")
                act_tech_positions = []
                for rank_num in range(1, len(active_bakers) + 1):
                    t_pos = st.selectbox(f"Actual Technical Placement #{rank_num}", baker_opts, index=0, key=f"admin_act_tech_{rank_num}_w{admin_selected_week}")
                    act_tech_positions.append(t_pos)
                    
                actuals["tech_rank"] = act_tech_positions
                actuals["tech_top_3"] = [act_tech_positions[0], act_tech_positions[1], act_tech_positions[2]] if len(act_tech_positions) >= 3 else []
                actuals["tech_bottom_3"] = [act_tech_positions[-3], act_tech_positions[-2], act_tech_positions[-1]] if len(act_tech_positions) >= 3 else []
                
            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes & Video Timestamps")
            act_hs_cnt = st.number_input("Hollywood Handshakes Count in Episode", min_value=0, value=None, placeholder="Enter count (e.g. 2)", key=f"hs_cnt_w{admin_selected_week}")
            act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes", active_bakers, key=f"hs_bakers_w{admin_selected_week}")
            act_hs_stamps = st.text_input("Handshake Video Timestamps & Context (e.g. 'Clara @ 14:22 Signature, Tom @ 42:10 Showstopper')", value="", key=f"hs_stamps_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents & Video Timestamps")
            act_cry_cnt = st.number_input("Crying Scene Incidents Count in Episode", min_value=0, value=None, placeholder="Enter count (e.g. 2)", key=f"cry_cnt_w{admin_selected_week}")
            act_cry_stamps = st.text_input("Crying Scene Video Timestamps & Context (e.g. 'Gabe @ 24:15 Technical, Molly @ 54:02 Elimination')", value="", key=f"cry_stamps_w{admin_selected_week}")

            st.markdown("### 💬 Weekly Sexual Innuendos Count")
            act_inn_cnt = st.number_input("Sexual Innuendos Count in Episode", min_value=0, value=None, placeholder="Enter count (e.g. 5)", key=f"inn_cnt_w{admin_selected_week}")
            act_inn_stamps = st.text_input("Sexual Innuendos Descriptions & Timestamps", value="", key=f"inn_stamps_w{admin_selected_week}")

            actuals["handshake_count"] = act_hs_cnt if act_hs_cnt is not None else 0
            actuals["handshake_bakers"] = act_hs_bakers
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt if act_cry_cnt is not None else 0
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt if act_inn_cnt is not None else 0
            actuals["innuendo_timestamps"] = act_inn_stamps
                
            if admin_selected_week == 10:
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner (Show Champion)", baker_opts, index=0)
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
                
            submit_actuals = st.form_submit_button("Publish Broadcast Results & Recalculate Standings")
            if submit_actuals:
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10 and 'actuals_season' in locals():
                    st.session_state.season_results = actuals_season
                    
                # TRIGGER RECALCULATION
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
                    
                st.success(f"Results published for Week {admin_selected_week}! Leaderboard updated successfully.")

        # --- PLAYER PASSWORD RESET ---
        st.markdown("---")
        st.markdown("### 🔑 Player Password Management")
        st.write("Select a player below to reset their password PIN if forgotten:")
        reset_player = st.selectbox("Select Player to Reset Password:", ROSTER_ALPHABETICAL, key="admin_pwd_reset_sel")
        if st.button(f"Reset Password PIN for {reset_player}"):
            st.session_state.league_members[reset_player]["pin"] = None
            st.success(f"Password PIN for {reset_player} has been cleared! They can now set a new 4-digit PIN on the Submit Predictions tab.")

        # --- ERASE ALL SAVED DATA (RESET APP STATE) AT VERY BOTTOM ---
        st.markdown("---")
        st.markdown("### 🚨 Erase All Saved Data (Reset App State)")
        st.write("Use this feature after testing to wipe all test predictions, weekly broadcast actuals, disputes, and player passwords back to a clean starting state.")
        confirm_erase = st.checkbox("⚠️ I confirm I want to permanently delete all predictions, broadcast actuals, disputes, and player passwords", key="confirm_erase_chk")
        if st.button("Erase All Saved Data & Reset Application", type="primary"):
            if confirm_erase:
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["weekly_picks"] = {}
                    st.session_state.league_members[m_name]["season_picks"] = {}
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    st.session_state.league_members[m_name]["pin"] = None
                    st.session_state.league_members[m_name]["season_score"] = 0
                st.success("All saved data, test predictions, actuals, disputes, and player PINs have been permanently erased!")
                st.rerun()
            else:
                st.warning("Please check the confirmation box above to proceed with erasing all data.")
