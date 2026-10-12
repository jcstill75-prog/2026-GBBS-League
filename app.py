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

### --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    background-color: #B25346;
    color: white;
}
h1, h2, h3 {
    color: #5D4037;
}
[data-theme="dark"] .lb-name,
[data-theme="dark"] .lb-rank {
    color: #FFFFFF !important;
}
[data-theme="light"] .lb-name,
[data-theme="light"] .lb-rank {
    color: #2C1810 !important;
}
</style>
""", unsafe_allow_html=True)

### --- 2. PERSISTENCE ENGINE ---
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

### --- 3. DEADLINE & SCORING ENGINE ---
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
    except Exception:
        return False

    try:
        now = datetime.datetime.now(ZoneInfo("America/Chicago"))
        if pub_time.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo("America/Chicago"))
        elif pub_time.tzinfo is None and now.tzinfo is not None:
            pub_time = pub_time.replace(tzinfo=ZoneInfo("America/Chicago"))
    except Exception:
        now = datetime.datetime.now()

    days_until_tuesday = (1 - pub_time.weekday()) % 7
    if days_until_tuesday == 0 and now > pub_time:
        days_until_tuesday = 7
        
    next_tuesday = pub_time + datetime.timedelta(days=days_until_tuesday)
    next_tuesday = next_tuesday.replace(hour=14, minute=0, second=0, microsecond=0)

    return now >= next_tuesday

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

        if week >= 8:
            pred_rank = predictions.get("tech_rank", [])
            act_rank = actuals.get("tech_rank", [])
            if pred_rank and act_rank:
                if pred_rank == act_rank:
                    score += 25 if week == 8 else (20 if week == 9 else 15)
                else:
                    for idx, b in enumerate(pred_rank):
                        if idx < len(act_rank) and act_rank[idx] == b and b != "--Select Baker--":
                            score += 3 if idx in [0, len(act_rank)-1] else 2
        else:
            pred_top3 = predictions.get("tech_top_3", [])
            act_top3 = actuals.get("tech_top_3", [])
            if len(pred_top3) == 3 and len(act_top3) == 3:
                if pred_top3 == act_top3:
                    score += 10
                else:
                    if pred_top3[0] == act_top3[0] and pred_top3[0] != "--Select Baker--": score += 3
                    for idx, baker in enumerate(pred_top3):
                        if baker in act_top3 and baker != "--Select Baker--" and baker != act_top3[idx]:
                            score += 1
                            
            pred_bot3 = predictions.get("tech_bottom_3", [])
            act_bot3 = actuals.get("tech_bottom_3", [])
            if len(pred_bot3) == 3 and len(act_bot3) == 3:
                if pred_bot3 == act_bot3:
                    score += 10
                else:
                    if pred_bot3[2] == act_bot3[2] and pred_bot3[2] != "--Select Baker--": score += 3
                    for idx, baker in enumerate(pred_bot3):
                        if baker in act_bot3 and baker != "--Select Baker--" and baker != act_bot3[idx]:
                            score += 1
    return score

def calculate_season_score(predictions, actuals):
    if not predictions or not actuals:
        return 0
    score = 0
    pred_win = predictions.get("winner")
    act_win = actuals.get("winner")
    if pred_win and act_win and pred_win == act_win:
        score += 40
    elif pred_win and actuals.get("finalists") and pred_win in actuals.get("finalists"):
        score += 15

    pred_semis = predictions.get("semifinalists", [])
    act_semis = actuals.get("semifinalists", [])
    for b in pred_semis:
        if b in act_semis and b != act_win:
            score += 10

    hs_pred = predictions.get("handshakes")
    hs_act = actuals.get("handshakes")
    if hs_pred is not None and hs_act is not None:
        if hs_pred == hs_act: score += 20
        elif abs(hs_pred - hs_act) <= 1: score += 10

    cry_pred = predictions.get("crying")
    cry_act = actuals.get("crying")
    if cry_pred is not None and cry_act is not None:
        if cry_pred == cry_act: score += 20
        elif abs(cry_pred - cry_act) <= 5: score += 10

    inn_pred = predictions.get("innuendos")
    inn_act = actuals.get("innuendos")
    if inn_pred is not None and inn_act is not None:
        if inn_pred == inn_act: score += 20
        elif abs(inn_pred - inn_act) <= 5: score += 10

    return score

def is_week_published(w_num, weekly_res_map):
    return w_num in weekly_res_map or str(w_num) in weekly_res_map or int(w_num) in weekly_res_map

def get_week_results(w_num, weekly_res_map):
    return weekly_res_map.get(w_num, weekly_res_map.get(str(w_num), weekly_res_map.get(int(w_num) if isinstance(w_num, int) else str(w_num), {})))

def image_to_base64(img):
    if img is None:
        return ""
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

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

def load_ai_brian_avatar():
    path = "assets/aibrian.jpg"
    if os.path.exists(path):
        try:
            return Image.open(path)
        except Exception:
            pass
    return None

def get_eliminated_bakers_by_week():
    elim_map = {}
