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

### Custom Styling for cozy baking theme & uniform card typography
st.markdown("""
<style>
.stButton>button {
    background-color: #D36B5F;
    color: white;
    border-radius: 8px;
    border: none;
}
.stButton>button:hover {
    background-color: #B25346;
    color: white;
}
</style>
""", unsafe_allow_html=True)

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
    except Exception:
        now = datetime.datetime.now()

    days_until_tuesday = (1 - pub_time.weekday()) % 7
    if days_until_tuesday == 0 and now > pub_time:
        days_until_tuesday = 7
        
    next_tuesday = pub_time + datetime.timedelta(days=days_until_tuesday)
    next_tuesday = next_tuesday.replace(hour=14, minute=0, second=0, microsecond=0)

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
                score += 15  # Flawless 3-for-3 sweep bonus
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
    return w_num in weekly_res_map or str(w_num) in weekly_res_map

def get_week_results(w_num, weekly_res_map):
    return weekly_res_map.get(w_num, weekly_res_map.get(str(w_num), {}))

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

def get_baker_stats(baker_name, current_week=1):
    sb_count = 0
    inline_count = 0
    trouble_count = 0
    handshake_count = 0
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

        hs_list = w_res.get("handshake_bakers", [])
        if isinstance(hs_list, list) and baker_name in hs_list:
            handshake_count += 1
            
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
        
    return sb_count, inline_count, trouble_count, handshake_count, tech_display

def get_star_member_wins_count(member_name):
    count = 0
    weekly_res_map = st.session_state.get("weekly_results", {})
    if not weekly_res_map:
        return count
        
    all_weeks = sorted([int(k) for k in weekly_res_map.keys()])
    for w in all_weeks:
        act_w = get_week_results(w, weekly_res_map)
        if not act_w:
            continue
            
        scores = {}
        for m_name, m_data in st.session_state.league_members.items():
            pred = m_data["weekly_picks"].get(w, m_data["weekly_picks"].get(str(w), {}))
            scores[m_name] = calculate_weekly_score(pred, act_w, w)
            
        if not scores:
            continue
            
        max_score = max(scores.values())
        if max_score > 0 and scores.get(member_name, 0) == max_score:
            count += 1
            
    return count

### --- 4. ROSTER & STATE INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Dinn", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]
ROSTER_HUMANS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", 
    "Stacy C.", "Taliah", "Tressa"
]
ROSTER_ALPHABETICAL = sorted(["AI Brian"] + ROSTER_HUMANS)

DATA_FILE = "league_data.json"

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_league_data():
    try:
        payload = {
            "league_members": st.session_state.get
