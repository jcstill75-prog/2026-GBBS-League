import streamlit as st
import pandas as pd
import random
import os
import json
import base64
import datetime
from zoneinfo import ZoneInfo
from PIL import Image
import io
import smtplib
from email.mime.text import MIMEText

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for cozy baking theme & uniform card typography
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
</style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENCE & NORMALIZATION ENGINE ---
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
                    
                    for m_name, m_data in data.get("league_members", {}).items():
                        if isinstance(m_data, dict):
                            if "weekly_picks" in m_data:
                                norm_picks = {}
                                for wk_k, wk_v in m_data["weekly_picks"].items():
                                    try:
                                        norm_picks[int(wk_k)] = wk_v
                                    except Exception:
                                        norm_picks[wk_k] = wk_v
                                m_data["weekly_picks"] = norm_picks
                            else:
                                m_data["weekly_picks"] = {}
                            
                            m_data.setdefault("season_picks", {})
                            m_data.setdefault("pin", None)
                            m_data.setdefault("season_score", 0)
                            
                    return data
        except Exception:
            pass
    return {}

def save_league_data():
    try:
        clean_members = st.session_state.get("league_members", {})
        for m_name, m_data in clean_members.items():
            if isinstance(m_data, dict):
                norm_picks = {}
                for wk_k, wk_v in m_data.get("weekly_picks", {}).items():
                    try:
                        norm_picks[int(wk_k)] = wk_v
                    except Exception:
                        norm_picks[wk_k] = wk_v
                m_data["weekly_picks"] = norm_picks
                m_data.setdefault("season_picks", {})
                m_data.setdefault("pin", None)

        clean_w_res = {}
        for wk_k, wk_v in st.session_state.get("weekly_results", {}).items():
            try:
                clean_w_res[int(wk_k)] = wk_v
            except Exception:
                clean_w_res[wk_k] = wk_v

        payload = {
            "league_members": clean_members,
            "weekly_results": clean_w_res,
            "season_results": st.session_state.get("season_results", {}),
            "disputes": st.session_state.get("disputes", []),
            "admin_deadline_override": st.session_state.get("admin_deadline_override", False),
            "week_publication_timestamps": st.session_state.get("week_publication_timestamps", {})
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

# --- ADMIN EMAIL NOTIFICATION ENGINE ---
def send_admin_email(player_name, week_num, predictions):
    """Sends an email backup to the admin when a player submits a ballot."""
    try:
        if "email" not in st.secrets:
            return
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
def is_weekly_voting_closed(active_week):
    if st.session_state.get("admin_deadline_override", False):
        return False

    pub_timestamps = st.session_state.get("week_publication_timestamps", {})
    prev_week = int(active_week) - 1
    
    if prev_week not in pub_timestamps and str(prev_week) not in pub_timestamps:
        return False

    try:
        pub_str = pub_timestamps.get(prev_week, pub_timestamps.get(str(prev_week)))
        pub_time = datetime.datetime.fromisoformat(pub_str)
        if pub_time.tzinfo is None:
            pub_time = pub_time.replace(tzinfo=ZoneInfo("America/Chicago"))
    except Exception:
        return False

    try:
        now = datetime.datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        now = datetime.datetime.now().replace(tzinfo=ZoneInfo("America/Chicago"))

    days_until_tuesday = (1 - pub_time.weekday()) % 7
    if days_until_tuesday == 0 and now > pub_time:
        days_until_tuesday = 7
    
    next_tuesday = pub_time + datetime.timedelta(days=days_until_tuesday)
    next_tuesday = next_tuesday.replace(hour=14, minute=0, second=0, microsecond=0)

    if next_tuesday.tzinfo is None:
        next_tuesday = next_tuesday.replace(tzinfo=ZoneInfo("America/Chicago"))

    return now >= next_tuesday

def format_baker_list_display(val):
    if isinstance(val, list):
        return ", ".join([str(b) for b in val if b and b != "--Select Baker--"])
    return str(val) if val and val != "--Select Baker--" else "None"

def calculate_weekly_score(predictions, actuals, week=2):
    try:
        week = int(week)
    except Exception:
        week = 2

    score = 0
    if not predictions or not actuals:
        return score
    
    if week == 10:
        if predictions.get("show_champion") and predictions.get("show_champion") == actuals.get("show_champion"):
            score += 15
        pred_rank = predictions.get("tech_rank", [])
        act_tech_rank = actuals.get("tech_rank", [])
        if isinstance(pred_rank, list) and isinstance(act_tech_rank, list) and pred_rank and act_tech_rank:
            if pred_rank == act_tech_rank:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if idx < len(act_tech_rank) and act_tech_rank[idx] == b and b != "--Select Baker--":
                        score += 3 if idx == 0 else 2
    else:
        if predictions.get("star_baker") and predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
        
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

        inl_pred = predictions.get("in_line_sb")
        inl_act = actuals.get("in_line_sb", [])
        if not isinstance(inl_act, list): inl_act = [inl_act]
        if inl_pred and inl_pred in inl_act:
            score += 2

        trb_pred = predictions.get("in_trouble")
        trb_act = actuals.get("in_trouble", [])
        if not isinstance(trb_act, list): trb_act = [trb_act]
        if trb_pred and trb_pred in trb_act:
            score += 2

        act_tech_rank = actuals.get("tech_rank", [])
        if not isinstance(act_tech_rank, list): act_tech_rank = []

        if week >= 8:
            pred_rank = predictions.get("tech_rank", [])
            if not isinstance(pred_rank, list): pred_rank = []
            if pred_rank and act_tech_rank:
                if pred_rank == act_tech_rank:
                    score += 25 if week == 8 else 20
                else:
                    for idx, b in enumerate(pred_rank):
                        if idx < len(act_tech_rank) and act_tech_rank[idx] == b and b != "--Select Baker--":
                            if week == 8:
                                score += 3 if idx in [0, 4] else 2
                            elif week == 9:
                                score += 3 if idx in [0, 3] else 2
        else:
            act_top3 = act_tech_rank[:3] if len(act_tech_rank) >= 3 else act_tech_rank
            act_bot3 = act_tech_rank[-3:] if len(act_tech_rank) >= 3 else act_tech_rank
            
            pred_top3 = predictions.get("tech_top_3", [])
            if not isinstance(pred_top3, list): pred_top3 = []
            if len(pred_top3) == 3 and len(act_top3) == 3:
                if pred_top3 == act_top3:
                    score += 10
                else:
                    for t_idx, actual_baker in enumerate(act_top3):
                        pred_at_pos = pred_top3[t_idx] if t_idx < len(pred_top3) else "--Select Baker--"
                        if pred_at_pos == actual_baker and pred_at_pos != "--Select Baker--":
                            score += 3 if t_idx == 0 else 2
                        elif pred_at_pos in act_top3 and pred_at_pos != "--Select Baker--":
                            score += 1
                            
            pred_bot3 = predictions.get("tech_bottom_3", [])
            if not isinstance(pred_bot3, list): pred_bot3 = []
            if len(pred_bot3) == 3 and len(act_bot3) == 3:
                if pred_bot3 == act_bot3:
                    score += 10
                else:
                    for b_idx, actual_baker in enumerate(act_bot3):
                        pred_at_pos = pred_bot3[b_idx] if b_idx < len(pred_bot3) else "--Select Baker--"
                        if pred_at_pos == actual_baker and pred_at_pos != "--Select Baker--":
                            score += 3 if b_idx == 2 else 2
                        elif pred_at_pos in act_bot3 and pred_at_pos != "--Select Baker--":
                            score += 1

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
    st.session_state.league_members = saved_state.get("league_members", {}) if saved_state else {}

for m in ROSTER_ALPHABETICAL:
    if m not in st.session_state.league_members:
        st.session_state.league_members[m] = {
            "weekly_picks": {}, "season_picks": {}, "total_score": 0,
            "weekly_breakdown": {}, "pin": None, "season_score": 0
        }
    else:
        st.session_state.league_members[m].setdefault("pin", None)
        st.session_state.league_members[m].setdefault("season_score", 0)
        st.session_state.league_members[m].setdefault("weekly_picks", {})
        st.session_state.league_members[m].setdefault("season_picks", {})

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_state.get("weekly_results", {}) if saved_state else {}
if "season_results" not in st.session_state:
    st.session_state.season_results = saved_state.get("season_results", {}) if saved_state else {}
if "disputes" not in st.session_state:
    st.session_state.disputes = saved_state.get("disputes", []) if saved_state else {}
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "admin_verification_msg" not in st.session_state:
    st.session_state.admin_verification_msg = ""
if "admin_deadline_override" not in st.session_state:
    st.session_state.admin_deadline_override = saved_state.get("admin_deadline_override", False) if saved_state else False
if "week_publication_timestamps" not in st.session_state:
    st.session_state.week_publication_timestamps = saved_state.get("week_publication_timestamps", {}) if saved_state else {}

def get_eliminated_bakers_by_week():
    elim_map = {}
    elim_list = []
    for w in sorted(st.session_state.weekly_results.keys(), key=lambda x: int(x)):
        res = st.session_state.weekly_results[w]
        act_el = res.get("eliminated")
        if isinstance(act_el, list):
            for b in act_el:
                if b and b != "None" and b not in elim_list: elim_list.append(b)
        elif isinstance(act_el, str) and act_el and act_el != "None":
            if act_el not in elim_list: elim_list.append(act_el)
        elim_map[int(w) + 1] = list(elim_list)
    return elim_map

eliminated_bakers_by_week = get_eliminated_bakers_by_week()
all_scored_weeks = sorted([int(k) for k in st.session_state.weekly_results.keys()])
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
        latest_w = max([int(k) for k in st.session_state.weekly_results.keys()])
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
st.title("🧁 Great British Baking Show Fantasy League 2026")
tab_lead, tab_submit, tab_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📺 Show Results", 
    "👑 Admin Panel"
])
