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

def is_week_published(w_num, results_map):
    try:
        w_int = int(w_num)
    except Exception:
        w_int = w_num
    if w_int in results_map: return True
    if str(w_int) in results_map: return True
    return False

def get_week_results(w_num, results_map):
    try:
        w_int = int(w_num)
    except Exception:
        w_int = w_num
    if w_int in results_map: return results_map[w_int]
    if str(w_int) in results_map: return results_map[str(w_int)]
    return {}

def calculate_season_score(predictions, actuals):
    if not is_week_published(10, st.session_state.get("weekly_results", {})):
        return 0

    score = 0
    if not predictions or not actuals:
        return score
    
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and act_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and act_finalists and pred_winner in act_finalists:
        score += 15
        
    for baker in predictions.get("semifinalists", []):
        if act_semis and baker in act_semis and baker != pred_winner:
            score += 10
            
    for key, exact_pts, buffer_pts, buf in [("handshakes", 20, 10, 1), ("crying", 20, 10, 5), ("innuendos", 20, 10, 5)]:
        p_val = predictions.get(key)
        a_val = actuals.get(key)
        if p_val is not None and a_val is not None:
            if p_val == a_val: score += exact_pts
            elif abs(p_val - a_val) <= buf: score += buffer_pts
            
    return score

def get_detailed_season_score_breakdown(predictions, actuals):
    breakdown = []
    if not predictions:
        return breakdown
        
    season_published = is_week_published(10, st.session_state.get("weekly_results", {}))
    
    w_pred = predictions.get("winner")
    w_act = actuals.get("winner") if season_published else None
    w_pts = 0
    max_w = 40
    if season_published and w_pred and w_act and w_pred == w_act:
        w_pts = 40
    elif season_published and w_pred and actuals.get("finalists") and w_pred in actuals.get("finalists"):
        w_pts = 15
        max_w = 15
    breakdown.append(("Season Winner", w_pred, w_act if (season_published and w_act) else "Pending W10", w_pts if season_published else 0, max_w))
    
    semis_pred = predictions.get("semifinalists", [])
    semis_act = actuals.get("semifinalists", []) if season_published else []
    semis_pts = 0
    if season_published:
        for b in semis_pred:
            if semis_act and b in semis_act and b != w_pred:
                semis_pts += 10
    breakdown.append(("Semifinalists", ", ".join(semis_pred) if semis_pred else "None", ", ".join(semis_act) if (season_published and semis_act) else "Pending W10", semis_pts if season_published else 0, 30))
    
    hs_pred = predictions.get("handshakes")
    hs_act = actuals.get("handshakes") if season_published else None
    hs_pts = 0
    if season_published and hs_pred is not None and hs_act is not None:
        if hs_pred == hs_act: hs_pts = 20
        elif abs(hs_pred - hs_act) <= 1: hs_pts = 10
    breakdown.append(("Hollywood Handshakes", hs_pred, hs_act if season_published else "Pending W10", hs_pts if season_published else 0, 20))
    
    cry_pred = predictions.get("crying")
    cry_act = actuals.get("crying") if season_published else None
    cry_pts = 0
    if season_published and cry_pred is not None and cry_act is not None:
        if cry_pred == cry_act: cry_pts = 20
        elif abs(cry_pred - cry_act) <= 5: cry_pts = 10
    breakdown.append(("Crying Incidents", cry_pred, cry_act if season_published else "Pending W10", cry_pts if season_published else 0, 20))
    
    inn_pred = predictions.get("innuendos")
    inn_act = actuals.get("innuendos") if season_published else None
    inn_pts = 0
    if season_published and inn_pred is not None and inn_act is not None:
        if inn_pred == inn_act: inn_pts = 20
        elif abs(inn_pred - inn_act) <= 5: inn_pts = 10
    breakdown.append(("Sexual Innuendos", inn_pred, inn_act if season_published else "Pending W10", inn_pts if season_published else 0, 20))
    
    return breakdown

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
if "admin_pin_reset_msg" not in st.session_state:
    st.session_state.admin_pin_reset_msg = ""
if "admin_deadline_override" not in st.session_state:
    st.session_state.admin_deadline_override = saved_state.get("admin_deadline_override", False) if saved_state else False
if "week_publication_timestamps" not in st.session_state:
    st.session_state.week_publication_timestamps = saved_state.get("week_publication_timestamps", {}) if saved_state else {}

def get_eliminated_bakers_by_week():
    elim_map = {}
    elim_list = []
    for w in sorted(st.session_state.weekly_results.keys(), key=lambda x: int(x)):
        res = st.session_state.weekly_results[w]
