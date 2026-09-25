import streamlit as st
import pandas as pd
import random
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
    player_names = [
        "Jasmine", "Ana", "Brian", "Cassie", "Emma", "Gisselle", 
        "Jennifer", "Mark", "Becca", "Sam", "Stacie W.", "Stacy C.", 
        "Taliah", "Tressa"
    ]
    st.session_state.league_members = {}
    for p_name in player_names:
        st.session_state.league_members[p_name] = {
            "avatar": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }
    st.session_state.league_members["AI Brian"] = {
        "avatar": "🤖",
        "weekly_picks": {},
        "season_picks": {},
        "total_score": 0,
        "weekly_breakdown": {}
    }

# Check for AI Brian's custom profile picture
import os
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
    
    # Compile scoring
    rows = []
    for member_name, data in st.session_state.league_members.items():
        avatar_display = "🍪"
        if member_name == "AI Brian":
            if isinstance(data["avatar"], Image.Image):
                avatar_display = "📸 AI Brian Photo"
            else:
                avatar_display = "🤖"
        elif data["avatar"] is not None:
            avatar_display = "📸 Custom Avatar"
            
        rows.append({
            "Avatar": avatar_display,
            "Player": member_name,
            "Total Score": data["total_score"],
            "Winner Prediction": data["season_picks"].get("winner", "None"),
            "Handshakes Predict": data["season_picks"].get("handshakes", 0),
            "Crying Predict": data["season_picks"].get("crying", 0),
            "Innuendos Predict": data["season_picks"].get("innuendos", 0)
        })
        
    df_lead = pd.DataFrame(rows).sort_values(by="Total Score", ascending=False)
    st.dataframe(df_lead, use_container_width=True)
    
    st.subheader("🍪 AI Brian's Automated Profile")
    brian_avatar = st.session_state.league_members["AI Brian"]["avatar"]
    if isinstance(brian_avatar, Image.Image):
        st.image(brian_avatar, caption="AI Brian", width=150)
    else:
        st.markdown("<h1 style='font-size: 70px; margin: 0;'>🤖</h1>", unsafe_allow_html=True)
    st.write("AI Brian is an automated simulator. His weekly and season-long picks are auto-generated randomly according to the 2026 rule constraints.")
    
    col_brian1, col_brian2 = st.columns(2)
    with col_brian1:
        st.markdown("**AI Brian's Locked Season Projections:**")
        st.json(st.session_state.league_members["AI Brian"]["season_picks"])
    with col_brian2:
        st.markdown("**AI Brian's Weekly Predictions Log:**")
        st.write(st.session_state.league_members["AI Brian"]["weekly_picks"])

    st.markdown("---")
    st.header("📺 Broadcast Audit & Video Timestamps (Verify Counts)")
    st.write("Contestants can review the administrator's episode logging, including video timestamps for Hollywood Handshakes and Crying incidents, to verify accuracy.")

    if not st.session_state.weekly_results:
        st.info("No weekly broadcast results published yet. Results will appear here after Episode 2!")
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

            tot_hs += len(w_act.get("handshake_bakers", []))
            if w_act.get("crying_timestamps"):
                # count commas + 1 or items
                tot_cry += len([s for s in w_act.get("crying_timestamps").split(",") if s.strip()])
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

        import pandas as pd
        df_audit = pd.DataFrame(audit_rows)
        st.dataframe(df_audit, use_container_width=True)

        st.markdown(f"**Cumulative Broadcast Totals Across Logged Weeks:** 🤝 Handshakes: `{tot_hs}` | 😢 Crying Incidents: `{tot_cry}` | 💬 Innuendos: `{tot_inn}`")

    st.markdown("---")
    st.header("🚩 Contest / Dispute a Result")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", sorted(list(st.session_state.league_members.keys())))
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(st.session_state.weekly_results.keys())] if st.session_state.weekly_results else ["Week 2"])
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
            st.write("Predict Technical Challenge Placements [Exact Match: 1st=3pts, 2nd/3rd=2pts, wrong spot=1pt; Perfect Top 3 sequence = 10 pts flat!]:")
            tech_top_3 = st.multiselect("Top 3 Technical (Order: 1st, 2nd, 3rd - Max 3) [Up to 10 pts total]", active_bakers, max_selections=3)
            
            st.write("Predict Bottom Technical Placements [Exact Match: 9th=2pts, 10th=2pts, 11th=3pts, wrong spot=1pt; Perfect Bottom 3 sequence = 10 pts flat!]:")
            tech_bottom_3 = st.multiselect("Bottom 3 Technical (Order: 3rd-to-last, 2nd-to-last, Last - Max 3) [Up to 10 pts total]", [b for b in active_bakers if b not in tech_top_3], max_selections=3)
            
            weekly_picks["tech_top_3"] = tech_top_3
            weekly_picks["tech_bottom_3"] = tech_bottom_3
            
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
                
            st.write("Actual Technical Challenge Rankings:")
            act_top_3 = st.multiselect("Actual Top 3 (1st, 2nd, 3rd)", active_bakers, max_selections=3)
            act_bottom_3 = st.multiselect("Actual Bottom 3 (3rd-to-last, 2nd-to-last, Last)", [b for b in active_bakers if b not in act_top_3], max_selections=3)
            actuals["tech_top_3"] = act_top_3
            actuals["tech_bottom_3"] = act_bottom_3
            
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
