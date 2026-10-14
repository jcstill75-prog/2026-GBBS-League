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
        act_tech_rank = actuals.get("tech_rank",
