import streamlit as st
import pandas as pd
import random
import os
import json
import base64
import datetime
from zoneinfo import ZoneInfo
from PIL import Image
import smtplib
from email.mime.text import MIMEText

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for cozy baking theme & rectangular profile card containers
st.markdown("""
<style>
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
    .baker-profile-card {
        border: 2px solid #8D6E63;
        border-radius: 10px;
        padding: 10px;
        background-color: #FFF9F5;
        box-shadow: 0 3px 6px rgba(93, 64, 55, 0.1);
        margin-bottom: 12px;
    }
    .card-title {
        background-color: #5D4037;
        color: white;
        padding: 5px 8px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 8px;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENCE ENGINE & EMAIL BACKUP ---
DATA_FILE = "league_data.json"

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    w_res = {}
                    for k, v in data.get("weekly_results", {}).items():
                        try:
                            w_res[int(k)] = v
                        except Exception:
                            w_res[k] = v
                    data["weekly_results"] = w_res
                    return data
        except Exception:
            pass
    return {}

def save_league_data():
    try:
        payload = {
            "league_members": st.session_state.get("league_members", {}),
            "weekly_results": st.session_state.get("weekly_results", {}),
            "season_results": st.session_state.get("season_results", {}),
            "disputes": st.session_state.get("disputes", [])
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

def send_admin_email(player_name, week_num, predictions):
    """Sends an email backup of a player's ballot to the admin inbox via Gmail SMTP secrets."""
    try:
        config = st.secrets["email"]
        sender_email = config["sender_email"]
        sender_password = config["sender_password"]
        admin_email = config["admin_email"]
        
        msg_body = f"New ballot submitted by {player_name} for Week {week_num}:\n\n{json.dumps(predictions, indent=2)}"
        msg = MIMEText(msg_body)
        msg['Subject'] = f"[GBBS League] New Ballot: {player_name} (Week {week_num})"
        msg['From'] = sender_email
        msg['To'] = admin_email
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, admin_email, msg.as_string())
    except Exception as e:
        print(f"Email notification failed: {e}")

# --- 3. DEADLINE & SCORING ENGINE ---
def is_weekly_voting_closed():
    """Returns True ONLY on Tuesday at or after 2:00 PM Houston time."""
    try:
        now = datetime.datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        now = datetime.datetime.now()
        
    weekday = now.weekday()  # 0:Mon, 1:Tue, 2:Wed, 3:Thu, 4:Fri, 5:Sat, 6:Sun
    if weekday == 1 and now.hour >= 14:
        return True
    return False

def score_top_3_technical(pred_top3, act_top3):
    if not isinstance(pred_top3, list) or len(pred_top3) != 3:
        return 0, []
    if not isinstance(act_top3, list) or len(act_top3) != 3:
        return 0, []
    
    if pred_top3 == act_top3:
        return 10, [("Perfect Top 3 Sweep", 10)]
    
    score = 0
    breakdown = []
    matched_actuals = set()
    matched_preds = set()
    
    for i in range(3):
        if pred_top3[i] == act_top3[i] and pred_top3[i] != "--Select Baker--":
            pts = 3 if i == 0 else 2
            score += pts
            breakdown.append((f"Top 3 - Exact #{i+1} ({pred_top3[i]})", pts))
            matched_actuals.add(i)
            matched_preds.add(i)
            
    for p_idx in range(3):
        if p_idx in matched_preds:
            continue
        p_baker = pred_top3[p_idx]
        if p_baker == "--Select Baker--" or not p_baker:
            continue
        for a_idx in range(3):
            if a_idx in matched_actuals:
                continue
            if act_top3[a_idx] == p_baker:
                score += 1
                breakdown.append((f"Top 3 - Wrong Spot ({p_baker})", 1))
                matched_actuals.add(a_idx)
                matched_preds.add(p_idx)
                break
                
    return score, breakdown

def score_bottom_3_technical(pred_bot3, act_bot3):
    if not isinstance(pred_bot3, list) or len(pred_bot3) != 3:
        return 0, []
    if not isinstance(act_bot3, list) or len(act_bot3) != 3:
        return 0, []
        
    if pred_bot3 == act_bot3:
        return 10, [("Perfect Bottom 3 Sweep", 10)]
        
    score = 0
    breakdown = []
    matched_actuals = set()
    matched_preds = set()
    
    for i in range(3):
        if pred_bot3[i] == act_bot3[i] and pred_bot3[i] != "--Select Baker--":
            pts = 3 if i == 2 else 2
            score += pts
            breakdown.append((f"Bottom 3 - Exact #{'Last' if i==2 else ('2nd-to-Last' if i==1 else '3rd-to-Last')} ({pred_bot3[i]})", pts))
            matched_actuals.add(i)
            matched_preds.add(i)
            
    for p_idx in range(3):
        if p_idx in matched_preds:
            continue
        p_baker = pred_bot3[p_idx]
        if p_baker == "--Select Baker--" or not p_baker:
            continue
        for a_idx in range(3):
            if a_idx in matched_actuals:
                continue
            if act_bot3[a_idx] == p_baker:
                score += 1
                breakdown.append((f"Bottom 3 - Wrong Spot ({p_baker})", 1))
                matched_actuals.add(a_idx)
                matched_preds.add(p_idx)
                break
                
    return score, breakdown

def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions or not actuals:
        return score
    
    if week == 10:
        if predictions.get("show_champion") and predictions.get("show_champion") == actuals.get("show_champion"):
            score += 15
    else:
        if predictions.get("star_baker") and predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
            
        if predictions.get("in_line_sb") and predictions.get("in_line_sb") == actuals.get("in_line_sb"):
            score += 2
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim: score += 5
            elif isinstance(pred_elim, str) and pred_elim in act_elim:
                score += 5
        elif act_elim == "None":
            pass
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: score += 5
            elif pred_elim == act_elim:
                score += 5

        if predictions.get("in_trouble") and predictions.get("in_trouble") == actuals.get("in_trouble"):
            score += 2

        act_tech_rank = actuals.get("tech_rank", [])
        if week >= 8:
            pred_rank = predictions.get("tech_rank", [])
            if pred_rank and act_tech_rank:
                if pred_rank == act_tech_rank:
                    score += 25 if week == 8 else (20 if week == 9 else 15)
                else:
                    for idx, b in enumerate(pred_rank):
                        if idx < len(act_tech_rank) and act_tech_rank[idx] == b and b != "--Select Baker--":
                            score += 3 if idx in [0, len(act_tech_rank)-1] else 2
        else:
            act_top3 = act_tech_rank[:3] if len(act_tech_rank) >= 3 else act_tech_rank
            act_bot3 = act_tech_rank[-3:] if len(act_tech_rank) >= 3 else act_tech_rank
            
            pred_top3 = predictions.get("tech_top_3", [])
            t_score, _ = score_top_3_technical(pred_top3, act_top3)
            score += t_score
            
            pred_bot3 = predictions.get("tech_bottom_3", [])
            b_score, _ = score_bottom_3_technical(pred_bot3, act_bot3)
            score += b_score

    return score

def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return score
    
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner == act_winner:
        score += 40
    elif pred_winner in act_finalists:
        score += 15
        
    for baker in predictions.get("semifinalists", []):
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    for key, exact_pts, buffer_pts, buf in [("handshakes", 20, 10, 1), ("crying", 20, 10, 5), ("innuendos", 20, 10, 5)]:
        p_val = predictions.get(key)
        a_val = actuals.get(key)
        if p_val is not None and a_val is not None:
            if p_val == a_val: score += exact_pts
            elif abs(p_val - a_val) <= buf: score += buffer_pts
            
    return score

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

def get_baker_stats(baker_name, current_week=1):
    sb_count = 0
    inline_count = 0
    trouble_count = 0
    tech_placements = {}
    tech_ranks_list = []
    
    weekly_res = st.session_state.get("weekly_results", {})
    for w_num, w_res in weekly_res.items():
        if w_res.get("star_baker") == baker_name:
            sb_count += 1
            
        inl = w_res.get("in_line_sb", [])
        if isinstance(inl, list) and baker_name in inl:
            inline_count += 1
        elif isinstance(inl, str) and inl == baker_name:
            inline_count += 1
            
        trb = w_res.get("in_trouble", [])
        if isinstance(trb, list) and baker_name in trb:
            trouble_count += 1
        elif isinstance(trb, str) and trb == baker_name:
            trouble_count += 1
            
        tech_r = w_res.get("tech_rank", [])
        if isinstance(tech_r, list) and baker_name in tech_r:
            rank = tech_r.index(baker_name) + 1
            tech_placements[w_num] = rank
            tech_ranks_list.append(rank)
        else:
            t_top = w_res.get("tech_top_3", [])
            t_bot = w_res.get("tech_bottom_3", [])
            if baker_name in t_top:
                rank = t_top.index(baker_name) + 1
                tech_placements[w_num] = rank
                tech_ranks_list.append(rank)
                
    if current_week <= 5:
        tech_display = tech_placements if tech_placements else "None yet"
    else:
        tech_display = round(sum(tech_ranks_list) / len(tech_ranks_list), 1) if tech_ranks_list else "N/A"
        
    return sb_count, inline_count, trouble_count, tech_display

# --- 4. ROSTER & STATE INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", 
    "Stacy C.", "Taliah", "Tressa"
]

ROSTER_ALPHABETICAL = sorted(["AI Brian"] + ROSTER_HUMANS)

saved_state = load_league_data()

if "league_members" not in st.session_state:
    st.session_state.league_members = saved_state.get("league_members", {})

for m in ROSTER_ALPHABETICAL:
    if m not in st.session_state.league_members:
        st.session_state.league_members[m] = {
            "weekly_picks": {}, "season_picks": {}, "total_score": 0,
            "weekly_breakdown": {}, "pin": None, "season_score": 0
        }
    else:
        st.session_state.league_members[m].setdefault("pin", None)
        st.session_state.league_members[m].setdefault("season_score", 0)

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_state.get("weekly_results", {})
if "season_results" not in st.session_state:
    st.session_state.season_results = saved_state.get("season_results", {})
if "disputes" not in st.session_state:
    st.session_state.disputes = saved_state.get("disputes", [])
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "admin_verification_msg" not in st.session_state:
    st.session_state.admin_verification_msg = ""

def generate_ai_brian_season_picks():
    winner = random.choice(ALL_BAKERS)
    remaining_pool = [b for b in ALL_BAKERS if b != winner]
    semis = random.sample(remaining_pool, 3)
    return {
        "winner": winner, "semifinalists": semis,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

def get_eliminated_bakers_by_week():
    elim_map = {}
    elim_list = []
    for w in sorted(st.session_state.weekly_results.keys()):
        res = st.session_state.weekly_results[w]
        act_el = res.get("eliminated")
        if isinstance(act_el, list):
            for b in act_el:
                if b and b != "None" and b not in elim_list: elim_list.append(b)
        elif isinstance(act_el, str) and act_el and act_el != "None":
            if act_el not in elim_list: elim_list.append(act_el)
        elim_map[w + 1] = list(elim_list)
    return elim_map

eliminated_bakers_by_week = get_eliminated_bakers_by_week()
all_scored_weeks = sorted(list(st.session_state.weekly_results.keys()))
active_prediction_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_prediction_week > 10: active_prediction_week = 10

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🧁 GBBS League")
    st.markdown("---")
    st.subheader("📌 Competition Progress")
    if not st.session_state.weekly_results:
        st.info("🟢 **Active Status: Week 1 Scouting Phase**\n\nSeason-wide predictions & Week 2 ballots unlock together once Week 1 results are posted!")
    else:
        latest_w = max(st.session_state.weekly_results.keys())
        st.success(f"🟢 **Active Competition Week: Week {latest_w + 1}**\n\n(Week {latest_w} Results Published)")
    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.warning("⏰ **Weekly voting window ends on Tuesdays at 2:00 PM Houston time.**")
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(Top 3)*
        * **Other 3 Semifinalists:** 10 pts each
        * **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        * **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        * **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
    with st.expander("📅 Weekly Predictions", expanded=False):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts
        * **In Line / In Trouble:** 2 pts each
        * **Technical Exact Positions:** 3 pts (1st/Last), 2 pts (middle)
        * **Star Member Bonus:** +5 pts to weekly high scorer
        """)

# --- 6. MAIN NAVIGATION TABS ---
st.title
