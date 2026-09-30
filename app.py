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
                        if isinstance(m_data, dict) and "weekly_picks" in m_data:
                            norm_picks = {}
                            for wk_k, wk_v in m_data["weekly_picks"].items():
                                try:
                                    norm_picks[int(wk_k)] = wk_v
                                except Exception:
                                    norm_picks[wk_k] = wk_v
                            m_data["weekly_picks"] = norm_picks
                            
                    return data
        except Exception:
            pass
    return {}

def save_league_data():
    try:
        clean_members = st.session_state.get("league_members", {})
        for m_name, m_data in clean_members.items():
            if isinstance(m_data, dict) and "weekly_picks" in m_data:
                norm_picks = {}
                for wk_k, wk_v in m_data["weekly_picks"].items():
                    try:
                        norm_picks[int(wk_k)] = wk_v
                    except Exception:
                        norm_picks[wk_k] = wk_v
                m_data["weekly_picks"] = norm_picks

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
            "disputes": st.session_state.get("disputes", [])
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

# --- 3. DEADLINE & SCORING ENGINE ---
def is_weekly_voting_closed():
    """Returns True if past Tuesday at 2:00 PM Houston time (Wed-Sun or Tue >= 14:00), unless Admin override is active."""
    if st.session_state.get("admin_deadline_override", False):
        return False

    try:
        now = datetime.datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        now = datetime.datetime.now()
        
    weekday = now.weekday()  # 0:Mon, 1:Tue, 2:Wed, 3:Thu, 4:Fri, 5:Sat, 6:Sun
    if weekday > 1 or (weekday == 1 and now.hour >= 14):
        return True
    return False

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

        # In Line SB (2 pts)
        inl_pred = predictions.get("in_line_sb")
        inl_act = actuals.get("in_line_sb", [])
        if not isinstance(inl_act, list): inl_act = [inl_act]
        if inl_pred and inl_pred in inl_act:
            score += 2

        # In Trouble (2 pts)
        trb_pred = predictions.get("in_trouble")
        trb_act = actuals.get("in_trouble", [])
        if not isinstance(trb_act, list): trb_act = [trb_act]
        if trb_pred and trb_pred in trb_act:
            score += 2

        # Technical challenge scoring
        act_tech_rank = actuals.get("tech_rank", [])
        if not isinstance(act_tech_rank, list): act_tech_rank = []

        if week >= 8:
            pred_rank = predictions.get("tech_rank", [])
            if not isinstance(pred_rank, list): pred_rank = []
            if pred_rank and act_tech_rank:
                if pred_rank == act_tech_rank:
                    score += 25 if week == 8 else 20  # Flawless sweep bonus (25 pts for W8, 20 pts for W9)
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
                    score += 10  # Perfect Top 3 Sweep flat bonus
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
                    score += 10  # Perfect Bottom 3 Sweep flat bonus
                else:
                    for b_idx, actual_baker in enumerate(act_bot3):
                        pred_at_pos = pred_bot3[b_idx] if b_idx < len(pred_bot3) else "--Select Baker--"
                        if pred_at_pos == actual_baker and pred_at_pos != "--Select Baker--":
                            score += 3 if b_idx == 2 else 2
                        elif pred_at_pos in act_bot3 and pred_at_pos != "--Select Baker--":
                            score += 1

    return score

def get_detailed_weekly_score_breakdown(predictions, actuals, week):
    try:
        week = int(week)
    except Exception:
        week = 2

    breakdown = []
    if not predictions or not actuals:
        return breakdown
    
    if week == 10:
        champ_pred = predictions.get("show_champion")
        champ_act = actuals.get("show_champion")
        pts = 15 if (champ_pred and champ_act and champ_pred == champ_act) else 0
        breakdown.append(("Show Champion", champ_pred, champ_act, pts, 15))
    else:
        sb_pred = predictions.get("star_baker")
        sb_act = actuals.get("star_baker")
        sb_pts = 5 if (sb_pred and sb_act and sb_pred == sb_act) else 0
        breakdown.append(("Star Baker", sb_pred, sb_act, sb_pts, 5))
            
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        elim_pts = 0
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim: elim_pts += 5
            elif isinstance(pred_elim, str) and pred_elim in act_elim:
                elim_pts += 5
        elif act_elim != "None":
            if isinstance(pred_elim, list):
                if act_elim in pred_elim: elim_pts += 5
            elif pred_elim == act_elim:
                elim_pts += 5
        max_elim_pts = 10 if isinstance(pred_elim, list) else 5
        breakdown.append(("Eliminated", pred_elim, act_elim, elim_pts, max_elim_pts))

        inl_pred = predictions.get("in_line_sb")
        inl_act = actuals.get("in_line_sb", [])
        if not isinstance(inl_act, list): inl_act = [inl_act]
        inl_pts = 0
        if inl_pred in inl_act:
            inl_pts += 2
        breakdown.append(("In Line SB", inl_pred, inl_act, inl_pts, 2))

        trb_pred = predictions.get("in_trouble")
        trb_act = actuals.get("in_trouble", [])
        if not isinstance(trb_act, list): trb_act = [trb_act]
        trb_pts = 0
        if trb_pred in trb_act:
            trb_pts += 2
        breakdown.append(("In Trouble", trb_pred, trb_act, trb_pts, 2))

    return breakdown

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
if "admin_pin_reset_msg" not in st.session_state:
    st.session_state.admin_pin_reset_msg = ""
if "admin_deadline_override" not in st.session_state:
    st.session_state.admin_deadline_override = False

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

# Force dynamic recalculation of scores on load to prevent stale legacy test scores
def recalculate_all_scores():
    all_w_res = st.session_state.get("weekly_results", {})
    total_hs_all = sum(len(w_dat.get("handshake_bakers", [])) for w_dat in all_w_res.values())
    total_cry_all = sum(int(w_dat.get("crying_count", 0)) for w_dat in all_w_res.values())
    total_inn_all = sum(int(w_dat.get("innuendo_count", 0)) for w_dat in all_w_res.values())
    w10_res = get_week_results(10, all_w_res)
    act_winner = w10_res.get("show_champion") if w10_res else None
    
    w8_elim = eliminated_bakers_by_week.get(9, [])
    act_semis = [b for b in ALL_BAKERS if b not in w8_elim]

    computed_season_actuals = {
        "winner": act_winner,
        "semifinalists": act_semis,
        "handshakes": total_hs_all,
        "crying": total_cry_all,
        "innuendos": total_inn_all
    }

    all_weeks_scored = sorted([int(k) for k in all_w_res.keys()])

    for m_name, m_data in st.session_state.league_members.items():
        m_data["total_score"] = 0
        m_data["weekly_breakdown"] = {}
        
        for w in all_weeks_scored:
            act_w = get_week_results(w, all_w_res)
            pred_w = m_data["weekly_picks"].get(w, m_data["weekly_picks"].get(str(w), {}))
            raw_score = calculate_weekly_score(pred_w, act_w, w)
            m_data["weekly_breakdown"][w] = raw_score

        # High scorer bonus calculation per week
        for w in all_weeks_scored:
            w_scores = [calculate_weekly_score(m_dat["weekly_picks"].get(w, m_dat["weekly_picks"].get(str(w), {})), get_week_results(w, all_w_res), w) for m_dat in st.session_state.league_members.values()]
            max_w_score = max(w_scores) if w_scores else 0
            base_score = m_data["weekly_breakdown"].get(w, 0)
            if w_scores and base_score == max_w_score and base_score > 0:
                m_data["weekly_breakdown"][w] = base_score + 5

        season_score = calculate_season_score(m_data.get("season_picks", {}), computed_season_actuals)
        m_data["season_score"] = season_score
        weekly_total = sum(m_data["weekly_breakdown"].values())
        m_data["total_score"] = weekly_total + season_score

recalculate_all_scores()

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

def generate_ai_brian_weekly_picks(active_bakers, is_grace_week_catchup, week):
    if week == 1:
        return {}

    pool = list(active_bakers)
    random.shuffle(pool)
    
    if week == 10:
        return {
            "show_champion": random.choice(active_bakers),
            "tech_rank": random.sample(active_bakers, len(active_bakers))
        }
        
    needed_main = 3 if is_grace_week_catchup else 4
    sampled_main = random.sample(active_bakers, min(len(active_bakers), max(needed_main, len(active_bakers))))
    
    sb = sampled_main[0]
    if is_grace_week_catchup:
        elim = [sampled_main[1], sampled_main[2]]
        inl = sampled_main[3] if len(sampled_main) > 3 else sampled_main[0]
        trb = sampled_main[4] if len(sampled_main) > 4 else sampled_main[0]
    else:
        elim = sampled_main[1]
        inl = sampled_main[2]
        trb = sampled_main[3] if len(sampled_main) > 3 else sampled_main[0]
        
    picks = {
        "star_baker": sb,
        "eliminated": elim,
        "in_line_sb": inl,
        "in_trouble": trb
    }
    
    if week >= 8:
        picks["tech_rank"] = random.sample(active_bakers, len(active_bakers))
    else:
        top3 = random.sample(active_bakers, min(3, len(active_bakers)))
        rem_bot = [b for b in active_bakers if b not in top3]
        if len(rem_bot) < 3:
            rem_bot = list(active_bakers)
        bot3 = random.sample(rem_bot, min(3, len(rem_bot)))
        picks["tech_top_3"] = top3
        picks["tech_bottom_3"] = bot3
        
    return picks

# --- 5. SIDEBAR (Fully Synchronized Points Reference Guide) ---
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
    
    with st.expander("🌟 Season-Long Projections", expanded=True):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(Top 3)*
        * **Other 3 Semifinalists:** 10 pts each
        * **Hollywood Handshakes:** 20 pts *(exact)* / 10 pts *(+/- 1)*
        * **Crying Incidents:** 20 pts *(exact)* / 10 pts *(+/- 5)*
        * **Sexual Innuendos:** 20 pts *(exact)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Weekly Scoring: Weeks 2–7", expanded=True):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts *(10 pts for Double Elim)*
        * **In Line SB Nominee:** 2 pts
        * **In Trouble Nominee:** 2 pts
        * **Top 3 Technical:**
          * Exact 1st Place = 3 pts
          * Exact 2nd & 3rd = 2 pts each
          * Correct Baker, Wrong Spot = 1 pt each
          * Perfect Sweep = 10 pts flat bonus
        * **Bottom 3 Technical:**
          * Exact Last Place = 3 pts
          * Exact 3rd/2nd-to-Last = 2 pts each
          * Correct Baker, Wrong Spot = 1 pt each
          * Perfect Sweep = 10 pts flat bonus
        * **Star Member Bonus:** +5 pts to weekly high scorer
        """)
        
    with st.expander("📅 Weekly Scoring: Weeks 8–10", expanded=True):
        st.markdown("""
        * **Quarterfinals (Week 8 — 5 Bakers):**
          * Exact 1st & 5th = 3 pts each
          * Exact 2nd, 3rd, 4th = 2 pts each
          * Flawless 5-for-5 Sweep = 25 pts flat
        * **Semifinals (Week 9 — 4 Bakers):**
          * Exact 1st & 4th = 3 pts each
          * Exact 2nd & 3rd = 2 pts each
          * Flawless 4-for-4 Sweep = 20 pts flat
        * **Grand Finale (Week 10 — 3 Bakers):**
          * Show Champion = 15 pts
          * Exact 1st Place = 3 pts
          * Exact 2nd & 3rd = 2 pts each
          * Flawless 3-for-3 Sweep = 15 pts flat
        * **Star Member Bonus:** +5 pts to weekly high scorer
        """)

# --- 6. MAIN NAVIGATION TABS ---
st.title("🧁 Great British Baking Show Fantasy League 2026")

tabs_list = [
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📺 Show Results", 
    "👑 Admin Panel"
]

selected_tab = st.radio("Navigation", tabs_list, horizontal=True, label_visibility="collapsed")
st.markdown("---")

tab_lead = (selected_tab == tabs_list[0])
tab_submit = (selected_tab == tabs_list[1])
tab_results = (selected_tab == tabs_list[2])
tab_admin = (selected_tab == tabs_list[3])

# ==============================================================================
# TAB 1: LEADERBOARD & STANDINGS
# ==============================================================================
if tab_lead:
    st.header("🏆 Live Leaderboard & Standings")
    
    all_w_res_global = st.session_state.get("weekly_results", {})
    total_hs_g = sum(len(w_dat.get("handshake_bakers", [])) for w_dat in all_w_res_global.values())
    total_cry_g = sum(int(w_dat.get("crying_count", 0)) for w_dat in all_w_res_global.values())
    total_inn_g = sum(int(w_dat.get("innuendo_count", 0)) for w_dat in all_w_res_global.values())
    w10_g = get_week_results(10, all_w_res_global)
    act_winner_g = w10_g.get("show_champion") if w10_g else None
    
    w8_elim_g = eliminated_bakers_by_week.get(9, [])
    act_semis_g = [b for b in ALL_BAKERS if b not in w8_elim_g]
    
    current_season_actuals = {
        "winner": act_winner_g,
        "semifinalists": act_semis_g,
        "handshakes": total_hs_g,
        "crying": total_cry_g,
        "innuendos": total_inn_g
    }

    lb_data = []
    for name, data in st.session_state.league_members.items():
        s_score = calculate_season_score(data.get("season_picks", {}), current_season_actuals)
        data["season_score"] = s_score
        weekly_total = sum(data.get("weekly_breakdown", {}).values())
        data["total_score"] = weekly_total + s_score
        
        lb_data.append({"member": name, "points": data.get("total_score", 0), "data": data})
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        html_rows = []
        for idx, row in df_lb.iterrows():
            badge = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"#{idx}"))
            star_wins = get_star_member_wins_count(row['member'])
            star_badge = f" &nbsp;<span style='font-size: 0.85rem;' title='Star Member High Scorer Wins'>⭐ x{star_wins}</span>" if star_wins > 0 else ""
            html_rows.append(f"<tr><td><b>{badge}</b></td><td>{row['member']}{star_badge}</td><td style='text-align: right;'><b>{row['points']} pts</b></td></tr>")
            
        st.markdown(f"""
        <table style="width: 100%; border-collapse: collapse;">
            <thead><tr><th style="width: 100px;">Rank</th><th>League Member</th><th style="text-align: right;">Total Points</th></tr></thead>
            <tbody>{''.join(html_rows)}</tbody>
        </table>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Transparent Scoring")
    selected_card_player = st.selectbox("Select Player Scorecard to View:", ROSTER_ALPHABETICAL, key="lb_player_card_sel")
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        st.markdown(f"### **{selected_card_player}'s Weekly Predictions Log & Results**")
        if p_weekly:
            voting_closed = is_weekly_voting_closed()
            weekly_results_map = st.session_state.get("weekly_results", {})
            season_finished = is_week_published(10, weekly_results_map)
            admin_unlocked = st.session_state.get("admin_authenticated", False)
            
            logged_in_human = None
            for hum in ROSTER_HUMANS:
                if st.session_state.get(f"auth_verified_{hum}", False):
                    logged_in_human = hum
                    break

            for w_num in sorted(p_weekly.keys(), key=lambda x: int(x)):
                is_current_active_week = (int(w_num) == active_prediction_week)
                can_view = (selected_card_player == logged_in_human) or (selected_card_player == "AI Brian") or (not is_current_active_week) or voting_closed or season_finished or admin_unlocked
                
                if not can_view:
                    with st.expander(f"Week {w_num} Ballot (Locked 🔒)", expanded=False):
                        st.warning(f"🔒 Week {w_num} prediction logs for other players are locked until the voting deadline passes (Tuesdays at 2:00 PM Houston time).")
                else:
                    w_picks = p_weekly[w_num]
                    has_published = is_week_published(w_num, weekly_results_map)
                    
                    base_w_pts = calculate_weekly_score(w_picks, get_week_results(w_num, weekly_results_map), w_num)
                    all_w_scores = [calculate_weekly_score(m_dat["weekly_picks"].get(w_num, m_dat["weekly_picks"].get(str(w_num), {})), get_week_results(w_num, weekly_results_map), w_num) for m_dat in st.session_state.league_members.values()]
                    is_high_scorer = (all_w_scores and base_w_pts == max(all_w_scores) and base_w_pts > 0)
                    w_pts = base_w_pts + (5 if is_high_scorer else 0)
                    
                    expander_title = f"Week {w_num} Ballot (Earned: {w_pts} pts)" if has_published else f"Week {w_num} Ballot (Pending Results)"
                    with st.expander(expander_title, expanded=False):
                        if has_published:
                            act_w = get_week_results(w_num, weekly_results_map)
                            
                            st.markdown("🔍 **Core Predictions:**")
                            sb_pred = w_picks.get("star_baker")
                            sb_act = act_w.get("star_baker")
                            sb_pts = 5 if (sb_pred and sb_act and sb_pred == sb_act) else 0
                            pts_color = "green" if sb_pts > 0 else "gray"
                            st.markdown(f'* **Star Baker:** <span style="color: #1E88E5; font-weight: bold;">{sb_pred}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{sb_act}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{sb_pts} pts</span>', unsafe_allow_html=True)
                            
                            act_elim = act_w.get("eliminated")
                            pred_elim = w_picks.get("eliminated")
                            elim_pts = 0
                            if isinstance(act_elim, list):
                                if isinstance(pred_elim, list):
                                    for p in pred_elim:
                                        if p in act_elim: elim_pts += 5
                            elif act_elim != "None":
                                if isinstance(pred_elim, list):
                                    if act_elim in pred_elim: elim_pts += 5
                                elif pred_elim == act_elim:
                                    elim_pts += 5
                            pred_elim_str = ", ".join(pred_elim) if isinstance(pred_elim, list) else str(pred_elim)
                            act_elim_str = ", ".join(act_elim) if isinstance(act_elim, list) else str(act_elim)
                            pts_color = "green" if elim_pts > 0 else "gray"
                            st.markdown(f'* **Eliminated:** <span style="color: #1E88E5; font-weight: bold;">{pred_elim_str}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{act_elim_str}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{elim_pts} pts</span>', unsafe_allow_html=True)
                            
                            inl_pred = w_picks.get("in_line_sb")
                            inl_act = act_w.get("in_line_sb", [])
                            if not isinstance(inl_act, list): inl_act = [inl_act]
                            inl_pts = 2 if inl_pred in inl_act else 0
                            pts_color = "green" if inl_pts > 0 else "gray"
                            st.markdown(f'* **In Line SB:** <span style="color: #1E88E5; font-weight: bold;">{inl_pred}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{", ".join(inl_act)}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{inl_pts} pts</span>', unsafe_allow_html=True)
                            
                            trb_pred = w_picks.get("in_trouble")
                            trb_act = act_w.get("in_trouble", [])
                            if not isinstance(trb_act, list): trb_act = [trb_act]
                            trb_pts = 2 if trb_pred in trb_act else 0
                            pts_color = "green" if trb_pts > 0 else "gray"
                            st.markdown(f'* **In Trouble:** <span style="color: #1E88E5; font-weight: bold;">{trb_pred}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{", ".join(trb_act)}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{trb_pts} pts</span>', unsafe_allow_html=True)
                            
                            st.markdown("---")
                            st.markdown("📊 **Technical Challenge Breakdown:**")
                            act_tech_rank = act_w.get("tech_rank", [])
                            if not isinstance(act_tech_rank, list): act_tech_rank = []
                            
                            w_int_num = int(w_num)
                            if w_int_num >= 8:
                                tech_rank = w_picks.get("tech_rank", [])
                                if not isinstance(tech_rank, list): tech_rank = []
                                if act_tech_rank and tech_rank:
                                    is_sweep = (tech_rank == act_tech_rank)
                                    sweep_pts = 25 if w_int_num == 8 else (20 if w_int_num == 9 else 15)
                                    if is_sweep:
                                        st.markdown(f"✨ **Technical Challenge (Flawless Sweep Bonus: <span style='color: green;'>+{sweep_pts} pts</span>):**", unsafe_allow_html=True)
                                        
                                    for t_idx, actual_baker in enumerate(act_tech_rank):
                                        r_label = "1st" if t_idx==0 else ("2nd" if t_idx==1 else ("3rd" if t_idx==2 else f"{t_idx+1}th"))
                                        pred_at_pos = tech_rank[t_idx] if t_idx < len(tech_rank) else "--Select Baker--"
                                        
                                        if is_sweep:
                                            t_pts = sweep_pts if t_idx == 0 else 0
                                        else:
                                            is_match = (pred_at_pos == actual_baker and pred_at_pos != "--Select Baker--")
                                            t_pts = 3 if (is_match and t_idx in [0, len(act_tech_rank)-1]) else (2 if is_match else 0)
                                            
                                        t_color = "green" if t_pts > 0 else "gray"
                                        st.markdown(f'* {r_label} Place: <span style="color: #1E88E5; font-weight: bold;">{pred_at_pos}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {t_color}; font-weight: bold;">+{t_pts} pts</span>', unsafe_allow_html=True)
                            else:
                                act_top3 = act_tech_rank[:3] if len(act_tech_rank) >= 3 else act_tech_rank
                                act_bot3 = act_tech_rank[-3:] if len(act_tech_rank) >= 3 else act_tech_rank
                                
                                pred_top3 = w_picks.get("tech_top_3", [])
                                if not isinstance(pred_top3, list): pred_top3 = []
                                pred_bot3 = w_picks.get("tech_bottom_3", [])
                                if not isinstance(pred_bot3, list): pred_bot3 = []
                                
                                st.markdown("**Top 3 Technical Challenge:**")
                                top3_sweep = (pred_top3 == act_top3 and len(pred_top3) == 3)
                                if top3_sweep:
                                    st.markdown("✨ **Top 3 Flawless Sweep Bonus: <span style='color: green;'>+10 pts</span>**", unsafe_allow_html=True)
                                for t_idx, actual_baker in enumerate(act_top3):
                                    r_label = "1st" if t_idx==0 else ("2nd" if t_idx==1 else "3rd")
                                    pred_b = pred_top3[t_idx] if t_idx < len(pred_top3) else "--Select Baker--"
                                    if top3_sweep:
                                        t_pts = 10 if t_idx == 0 else 0
                                    else:
                                        is_match = (pred_b == actual_baker and pred_b != "--Select Baker--")
                                        t_pts = 3 if (is_match and t_idx==0) else (2 if is_match else (1 if pred_b in act_top3 else 0))
                                    t_color = "green" if t_pts > 0 else "gray"
                                    st.markdown(f'* {r_label} Place: <span style="color: #1E88E5; font-weight: bold;">{pred_b}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {t_color}; font-weight: bold;">+{t_pts} pts</span>', unsafe_allow_html=True)

                                st.markdown("**Bottom 3 Technical Challenge:**")
                                bot3_sweep = (pred_bot3 == act_bot3 and len(pred_bot3) == 3)
                                if bot3_sweep:
                                    st.markdown("✨ **Bottom 3 Flawless Sweep Bonus: <span style='color: green;'>+10 pts</span>**", unsafe_allow_html=True)
                                for b_idx, actual_baker in enumerate(act_bot3):
                                    r_label = "3rd-to-Last" if b_idx==0 else ("2nd-to-Last" if b_idx==1 else "Last")
                                    pred_b = pred_bot3[b_idx] if b_idx < len(pred_bot3) else "--Select Baker--"
                                    if bot3_sweep:
                                        t_pts = 10 if b_idx == 0 else 0
                                    else:
                                        is_match = (pred_b == actual_baker and pred_b != "--Select Baker--")
                                        t_pts = 3 if (is_match and b_idx==2) else (2 if is_match else (1 if pred_b in act_bot3 else 0))
                                    t_color = "green" if t_pts > 0 else "gray"
                                    st.markdown(f'* {r_label} Place: <span style="color: #1E88E5; font-weight: bold;">{pred_b}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {t_color}; font-weight: bold;">+{t_pts} pts</span>', unsafe_allow_html=True)
                                
                            if is_high_scorer:
                                st.markdown("<span style='color: green; font-weight: bold;'>• Star Member High Scorer Bonus: +5 pts</span>", unsafe_allow_html=True)
                        else:
                            sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                            inl = w_picks.get("in_line_sb", "N/A")
                            elim = w_picks.get("eliminated", "N/A")
                            if isinstance(elim, list):
                                elim_str = ", ".join([str(b) for b in elim if b])
                            else:
                                elim_str = str(elim)
                            trb = w_picks.get("in_trouble", "N/A")
                            
                            st.write(f"🌟 **Star Baker / Champion:** {sb}")
                            st.write(f"⭐ **In Line SB:** {inl}")
                            st.write(f"🚪 **Eliminated:** {elim_str}")
                            st.write(f"⚠️ **In Trouble:** {trb}")
                            
                            w_int_num = int(w_num)
                            if w_int_num < 8:
                                tech_top = w_picks.get("tech_top_3", [])
                                tech_bot = w_picks.get("tech_bottom_3", [])
                                if tech_top:
                                    st.markdown("**Top 3 Technical Predictions:**")
                                    for t_idx, b_val in enumerate(tech_top):
                                        r_label = "1st" if t_idx==0 else ("2nd" if t_idx==1 else "3rd")
                                        st.markdown(f"* {r_label} Place: <span style='color: #1E88E5; font-weight: bold;'>{b_val if b_val else 'None'}</span>", unsafe_allow_html=True)
                                if tech_bot:
                                    st.markdown("**Bottom 3 Technical Predictions:**")
                                    for b_idx, b_val in enumerate(tech_bot):
                                        r_label = "3rd-to-Last" if b_idx==0 else ("2nd-to-Last" if b_idx==1 else "Last")
                                        st.markdown(f"* {r_label} Place: <span style='color: #1E88E5; font-weight: bold;'>{b_val if b_val else 'None'}</span>", unsafe_allow_html=True)
                            elif w_int_num >= 8:
                                tech_r = w_picks.get("tech_rank", [])
                                if tech_r:
                                    st.markdown("**Technical Rankings:**")
                                    for t_idx, b_val in enumerate(tech_r):
                                        r_label = "1st" if t_idx==0 else ("2nd" if t_idx==1 else ("3rd" if t_idx==2 else f"{t_idx+1}th"))
                                        st.markdown(f"* {r_label} Place: <span style='color: #1E88E5; font-weight: bold;'>{b_val if b_val else 'None'}</span>", unsafe_allow_html=True)

                            st.info("💡 Transparent scoring comparison and actual outcomes will appear here once official broadcast results are published.")

                        st.markdown("---")
                        st.markdown(f"🏆 **Total Points Earned for Week {w_num}:** <span style='color: green; font-weight: bold; font-size: 1.1rem;'>{w_pts} pts</span>", unsafe_allow_html=True)
        else:
            st.info("No weekly prediction ballots submitted yet.")

        st.markdown("---")
        st.markdown(f"### **{selected_card_player}'s Season Projections & Results**")
        season_breakdown = get_detailed_season_score_breakdown(p_season, current_season_actuals)
        total_season_earned = sum(item[3] for item in season_breakdown)
        
        st.markdown("🔍 **Projection vs. Actual Season Outcome & Points:**")
        for cat_label, pred_val, act_val, pts_earned, max_pts in season_breakdown:
            if isinstance(pred_val, list):
                pred_str = ", ".join([str(x) for x in pred_val if x])
            else:
                pred_str = str(pred_val)
                
            if isinstance(act_val, list):
                act_str = ", ".join([str(x) for x in act_val if x])
            else:
                act_str = str(act_val)
                
            pts_color = "green" if pts_earned > 0 else "gray"
            st.markdown(f"""
            * **{cat_label}:** <span style="color: #1E88E5; font-weight: bold;">{pred_str}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{act_str}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{pts_earned} pts</span>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        st.markdown(f"🏆 **Total Season Projection Points Earned:** <span style='color: green; font-weight: bold; font-size: 1.1rem;'>{total_season_earned} pts</span>", unsafe_allow_html=True)

# ==============================================================================
# TAB 2: SUBMIT PREDICTIONS
# ==============================================================================
if tab_submit:
    st.header("📝 Submit Predictions")
    pred_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="pred_player_login_sel")
    p_info = st.session_state.league_members[pred_player]
    
    auth_key = f"auth_verified_{pred_player}"
    notice_key = f"sub_notice_{pred_player}"
    
    if notice_key in st.session_state and not st.session_state.get(auth_key, False):
        st.success(st.session_state[notice_key])
        if st.button("Dismiss & Log In", key="dismiss_notice_btn"):
            del st.session_state[notice_key]
            st.rerun()

    auth_success = False
    admin_proxy_active = st.session_state.get("admin_authenticated", False)

    if admin_proxy_active:
        st.info(f"👑 **Admin Proxy Mode Available:** As the administrator, you can open and edit **{pred_player}'s** ballot directly without entering their personal PIN.")
        col_prox1, col_prox2 = st.columns(2)
        with col_prox1:
            if st.button(f"🔓 Open Ballot as Admin for {pred_player}", key="admin_proxy_unlock_btn"):
                st.session_state[auth_key] = True
                st.rerun()

    if p_info.get("pin") is None and not st.session_state.get(auth_key, False):
        st.info(f"Welcome {pred_player}! Please create a 4-digit security PIN for your account:")
        with st.form(f"pin_create_form_{pred_player}"):
            p1 = st.text_input("Create 4-Digit Security PIN:", type="password")
            p2 = st.text_input("Confirm 4-Digit Security PIN:", type="password")
            submitted_pin = st.form_submit_button("Save Security PIN & Unlock")
            if submitted_pin:
                if p1 and p1 == p2 and len(p1) == 4 and p1.isdigit():
                    p_info["pin"] = p1
                    save_league_data()
                    st.success("Security PIN saved successfully! Ballot unlocked.")
                    st.rerun()
                else:
                    st.error("PIN must be exactly 4 numeric digits and match in both fields.")
    else:
        if st.session_state.get(auth_key, False):
            auth_success = True
            
            col_l1, col_l2 = st.columns([6, 1])
            with col_l2:
                if st.button("🔒 Log Out"):
                    st.session_state[auth_key] = False
                    st.rerun()
                    
            proxy_badge = " (via Admin Proxy Override)" if admin_proxy_active else ""
            st.success(f"🔓 Authenticated as {pred_player}{proxy_badge}!")
        else:
            with st.form(f"pin_login_form_{pred_player}"):
                entered_pin = st.text_input(f"Enter 4-Digit Security PIN for {pred_player}:", type="password")
                submitted_login = st.form_submit_button("Unlock Ballot")
                if submitted_login:
                    if entered_pin == p_info.get("pin"):
                        st.session_state[auth_key] = True
                        st.success(f"🔓 Authenticated as {pred_player}!")
                        st.rerun()
                    else:
                        st.error("Incorrect PIN. Please try again.")
            if st.session_state.get(auth_key, False):
                auth_success = True

    if auth_success:
        st.markdown("---")
        if not st.session_state.weekly_results:
            st.warning("🔒 **Week 1 Scouting Phase:** Season-wide predictions & Week 2 ballots unlock together once Week 1 results are published by the Admin!")
        elif is_weekly_voting_closed():
            st.error("⏰ **Weekly Voting Closed:** The weekly voting deadline (Tuesdays at 2:00 PM Houston time) has passed. Ballot submissions and edits are locked. *(Note: The Administrator can grant an extension from the Admin Panel if needed.)*")
        else:
            if st.session_state.get("admin_deadline_override", False):
                st.info("🔓 **Admin Extension Active:** Deadline restrictions are temporarily lifted for late submissions.")

            curr_elim = eliminated_bakers_by_week.get(active_prediction_week, [])
            active_bakers = [b for b in ALL_BAKERS if b not in curr_elim]
            
            prev_w = active_prediction_week - 1
            prev_res = st.session_state.weekly_results.get(prev_w, st.session_state.weekly_results.get(str(prev_w), {}))
            is_grace_week_catchup = (prev_res.get("eliminated") == "None")
            
            if is_grace_week_catchup:
                st.warning(f"⚠️ **Grace Week Catch-Up Active:** Because Week {prev_w} had no elimination, Week {active_prediction_week} is a **Double Elimination** week! You must predict **two** eliminated bakers.")

            saved_season = p_info.get("season_picks", {})
            saved_weekly = p_info.get("weekly_picks", {}).get(active_prediction_week, {})
            has_submitted = bool(saved_weekly) or (active_prediction_week == 2 and bool(saved_season and saved_season.get("winner")))

            if active_prediction_week == 2:
                st.subheader("🌟 Week 2 Ballot & Season-Long Projections")
                with st.form("week_2_combined_form"):
                    st.markdown("### 🌟 Season-Long Projections")
                    s_win_def = saved_season.get("winner", "--Select Baker--")
                    s_win_idx = (["--Select Baker--"] + ALL_BAKERS).index(s_win_def) if s_win_def in (["--Select Baker--"] + ALL_BAKERS) else 0
                    s_win = st.selectbox("Season Winner (40 pts):", ["--Select Baker--"] + ALL_BAKERS, index=s_win_idx)
                    
                    s_semis_def = [b for b in saved_season.get("semifinalists", []) if b in ALL_BAKERS]
                    s_semis = st.multiselect("3 Other Semifinalists (10 pts each - Select 3):", ALL_BAKERS, default=s_semis_def, max_selections=3)
                    
                    s_hs = st.number_input("Total Handshakes:", min_value=0, value=int(saved_season.get("handshakes", 0)), placeholder="e.g. 5")
                    s_cry = st.number_input("Total Crying Incidents:", min_value=0, value=int(saved_season.get("crying", 0)), placeholder="e.g. 12")
                    s_inn = st.number_input("Total Sexual Innuendos:", min_value=0, value=int(saved_season.get("innuendos", 0)), placeholder="e.g. 45")
                    
                    st.markdown("---")
                    st.markdown("### 📅 Week 2 Episodic Predictions")
                    weekly_picks = {}
                    col1, col2 = st.columns(2)
                    with col1:
                        sb_def = saved_weekly.get("star_baker", "--Select Baker--")
                        sb_idx = (["--Select Baker--"] + active_bakers).index(sb_def) if sb_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["star_baker"] = st.selectbox("Star Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=sb_idx)
                        
                        inl_def = saved_weekly.get("in_line_sb", "--Select Baker--")
                        inl_idx = (["--Select Baker--"] + active_bakers).index(inl_def) if inl_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["in_line_sb"] = st.selectbox("'In Line' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=inl_idx)
                    with col2:
                        if is_grace_week_catchup:
                            el_def = [b for b in saved_weekly.get("eliminated", []) if b in active_bakers]
                            weekly_picks["eliminated"] = st.multiselect("Predicted 2 Eliminated Bakers (5 pts each - Select 2):", active_bakers, default=el_def, max_selections=2)
                        else:
                            el_def = saved_weekly.get("eliminated", "--Select Baker--")
                            el_idx = (["--Select Baker--"] + active_bakers).index(el_def) if el_def in (["--Select Baker--"] + active_bakers) else 0
                            weekly_picks["eliminated"] = st.selectbox("Eliminated Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=el_idx)
                            
                        trb_def = saved_weekly.get("in_trouble", "--Select Baker--")
                        trb_idx = (["--Select Baker--"] + active_bakers).index(trb_def) if trb_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["in_trouble"] = st.selectbox("'In Trouble' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=trb_idx)
                    
                    st.markdown("#### Technical Challenge Predictions:")
                    col_t1, col_t2 = st.columns(2)
                    saved_top = saved_weekly.get("tech_top_3", [])
                    saved_bot = saved_weekly.get("tech_bottom_3", [])
                    with col_t1:
                        st.write("**Top 3 Technical:**")
                        tp_defaults = [b for b in saved_top if b in active_bakers]
                        tp1 = st.selectbox("1st Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[0]) if len(tp_defaults)>0 and tp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="tp_1")
                        tp2 = st.selectbox("2nd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[1]) if len(tp_defaults)>1 and tp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="tp_2")
                        tp3 = st.selectbox("3rd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[2]) if len(tp_defaults)>2 and tp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="tp_3")
                        weekly_picks["tech_top_3"] = [tp1, tp2, tp3]
                    with col_t2:
                        st.write("**Bottom 3 Technical:**")
                        bp_defaults = [b for b in saved_bot if b in active_bakers]
                        bp1 = st.selectbox("3rd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[0]) if len(bp_defaults)>0 and bp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="bp_1")
                        bp2 = st.selectbox("2nd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[1]) if len(bp_defaults)>1 and bp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="bp_2")
                        bp3 = st.selectbox("Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[2]) if len(bp_defaults)>2 and bp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="bp_3")
                        weekly_picks["tech_bottom_3"] = [bp1, bp2, bp3]
                    
                    edit_conf = True
                    if has_submitted:
                        edit_conf = st.checkbox(f"⚠️ Check this box to confirm you want to edit your previously submitted Week 2 Ballot & Season Projections.")

                    sub_w2 = st.form_submit_button("Submit Week 2 Ballot & Season Projections")
                    if sub_w2:
                        errors = []
                        if has_submitted and not edit_conf:
                            errors.append(f"❌ Please check the confirmation box to edit your previously submitted ballot.")
                        if s_win == "--Select Baker--":
                            errors.append("Please select a valid Season Winner.")
                        
                        main_picks_flat = []
                        for k in ["star_baker", "eliminated", "in_line_sb", "in_trouble"]:
                            val = weekly_picks.get(k)
                            if isinstance(val, list):
                                for item in val:
                                    if item and item != "--Select Baker--":
                                        main_picks_flat.append(item)
                            elif isinstance(val, str) and val and val != "--Select Baker--":
                                main_picks_flat.append(val)

                        if len(main_picks_flat) != len(set(main_picks_flat)):
                            errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                            
                        valid_top = [t for t in weekly_picks.get("tech_top_3", []) if t and t != "--Select Baker--"]
                        valid_bot = [t for t in weekly_picks.get("tech_bottom_3", []) if t and t != "--Select Baker--"]
                        if len(valid_top) != len(set(valid_top)):
                            errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Top 3 Technical picks!")
                        if len(valid_bot) != len(set(valid_bot)):
                            errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Bottom 3 Technical picks!")
                        if any(b in valid_bot for b in valid_top):
                            errors.append("❌ Duplicate Selection Error: A baker cannot appear in both Top 3 and Bottom 3 technical predictions!")
                            
                        if errors:
                            for err in errors:
                                st.error(err)
                        else:
                            p_info["season_picks"] = {"winner": s_win, "semifinalists": s_semis, "handshakes": s_hs, "crying": s_cry, "innuendos": s_inn}
                            p_info["weekly_picks"][2] = weekly_picks
                            if 2 not in st.session_state.league_members["AI Brian"]["weekly_picks"]:
                                st.session_state.league_members["AI Brian"]["weekly_picks"][2] = generate_ai_brian_weekly_picks(active_bakers, is_grace_week_catchup, 2)
                            save_league_data()
                            st.session_state[notice_key] = f"✅ Success! Your Week 2 Ballot and Season Projections have been successfully submitted and locked in. You can log back in with your PIN anytime to review or edit your choices before the deadline."
                            st.session_state[auth_key] = False
                            st.rerun()

            else:
                st.markdown(f"### 📅 Week {active_prediction_week} Prediction Ballot")
                with st.form("weekly_ballot_form"):
                    weekly_picks = {}
                    if active_prediction_week == 10:
                        champ_def = saved_weekly.get("show_champion", "--Select Baker--")
                        champ_idx = (["--Select Baker--"] + active_bakers).index(champ_def) if champ_def in (["--Select Baker--"] + active_bakers) else 0
                        weekly_picks["show_champion"] = st.selectbox("Show Champion (15 pts):", ["--Select Baker--"] + active_bakers, index=champ_idx)
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            sb_def = saved_weekly.get("star_baker", "--Select Baker--")
                            sb_idx = (["--Select Baker--"] + active_bakers).index(sb_def) if sb_def in (["--Select Baker--"] + active_bakers) else 0
                            weekly_picks["star_baker"] = st.selectbox("Star Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=sb_idx)
                            
                            inl_def = saved_weekly.get("in_line_sb", "--Select Baker--")
                            inl_idx = (["--Select Baker--"] + active_bakers).index(inl_def) if inl_def in (["--Select Baker--"] + active_bakers) else 0
                            weekly_picks["in_line_sb"] = st.selectbox("'In Line' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=inl_idx)
                        with col2:
                            if is_grace_week_catchup:
                                el_def = [b for b in saved_weekly.get("eliminated", []) if b in active_bakers]
                                weekly_picks["eliminated"] = st.multiselect("Predicted 2 Eliminated Bakers (5 pts each - Select 2):", active_bakers, default=el_def, max_selections=2)
                            else:
                                el_def = saved_weekly.get("eliminated", "--Select Baker--")
                                el_idx = (["--Select Baker--"] + active_bakers).index(el_def) if el_def in (["--Select Baker--"] + active_bakers) else 0
                                weekly_picks["eliminated"] = st.selectbox("Eliminated Baker (5 pts):", ["--Select Baker--"] + active_bakers, index=el_idx)
                                
                            trb_def = saved_weekly.get("in_trouble", "--Select Baker--")
                            trb_idx = (["--Select Baker--"] + active_bakers).index(trb_def) if trb_def in (["--Select Baker--"] + active_bakers) else 0
                            weekly_picks["in_trouble"] = st.selectbox("'In Trouble' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=trb_idx)
                    
                    st.markdown("#### Technical Challenge Predictions:")
                    if active_prediction_week >= 8:
                        num_b = len(active_bakers)
                        st.write(f"Rank all {num_b} Bakers (1st through {num_b}th):")
                        tech_ranks = []
                        saved_tech = saved_weekly.get("tech_rank", [])
                        for i in range(num_b):
                            t_def = saved_tech[i] if (isinstance(saved_tech, list) and i < len(saved_tech) and saved_tech[i] in active_bakers) else "--Select Baker--"
                            t_idx = (["--Select Baker--"] + active_bakers).index(t_def) if t_def in (["--Select Baker--"] + active_bakers) else 0
                            rank_str = "1st" if i==0 else ("2nd" if i==1 else ("3rd" if i==2 else f"{i+1}th"))
                            sel = st.selectbox(f"Technical {rank_str} Place", ["--Select Baker--"] + active_bakers, index=t_idx, key=f"tech_rank_{i}")
                            tech_ranks.append(sel)
                        weekly_picks["tech_rank"] = tech_ranks
                    else:
                        saved_top = saved_weekly.get("tech_top_3", [])
                        saved_bot = saved_weekly.get("tech_bottom_3", [])
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            st.write("**Top 3 Technical:**")
                            tp_defaults = [b for b in saved_top if b in active_bakers]
                            tp1 = st.selectbox("1st Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[0]) if len(tp_defaults)>0 and tp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="tp_1")
                            tp2 = st.selectbox("2nd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[1]) if len(tp_defaults)>1 and tp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="tp_2")
                            tp3 = st.selectbox("3rd Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(tp_defaults[2]) if len(tp_defaults)>2 and tp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="tp_3")
                            weekly_picks["tech_top_3"] = [tp1, tp2, tp3]
                        with col_t2:
                            st.write("**Bottom 3 Technical:**")
                            bp_defaults = [b for b in saved_bot if b in active_bakers]
                            bp1 = st.selectbox("3rd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[0]) if len(bp_defaults)>0 and bp_defaults[0] in (["--Select Baker--"] + active_bakers) else 0, key="bp_1")
                            bp2 = st.selectbox("2nd-to-Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[1]) if len(bp_defaults)>1 and bp_defaults[1] in (["--Select Baker--"] + active_bakers) else 0, key="bp_2")
                            bp3 = st.selectbox("Last Place", ["--Select Baker--"] + active_bakers, index=(["--Select Baker--"] + active_bakers).index(bp_defaults[2]) if len(bp_defaults)>2 and bp_defaults[2] in (["--Select Baker--"] + active_bakers) else 0, key="bp_3")
                            weekly_picks["tech_bottom_3"] = [bp1, bp2, bp3]
                    
                    edit_conf = True
                    if has_submitted:
                        edit_conf = st.checkbox(f"⚠️ Check this box to confirm you want to edit your previously submitted Week {active_prediction_week} ballot.")

                    sub_weekly = st.form_submit_button(f"Submit Week {active_prediction_week} Ballot")
                    if sub_weekly:
                        errors = []
                        if has_submitted and not edit_conf:
                            errors.append(f"❌ Please check the confirmation box to edit your previously submitted Week {active_prediction_week} ballot.")
                        
                        if active_prediction_week < 10:
                            main_picks_flat = []
                            for k in ["star_baker", "eliminated", "in_line_sb", "in_trouble"]:
                                val = weekly_picks.get(k)
                                if isinstance(val, list):
                                    for item in val:
                                        if item and item != "--Select Baker--":
                                            main_picks_flat.append(item)
                                elif isinstance(val, str) and val and val != "--Select Baker--":
                                    main_picks_flat.append(val)
                            
                            if len(main_picks_flat) != len(set(main_picks_flat)):
                                errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                                
                        if active_prediction_week >= 8:
                            valid_tech = [t for t in weekly_picks.get("tech_rank", []) if t and t != "--Select Baker--"]
                            if len(valid_tech) != len(set(valid_tech)):
                                errors.append("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                        else:
                            valid_top = [t for t in weekly_picks.get("tech_top_3", []) if t and t != "--Select Baker--"]
                            valid_bot = [t for t in weekly_picks.get("tech_bottom_3", []) if t and t != "--Select Baker--"]
                            if len(valid_top) != len(set(valid_top)):
                                errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Top 3 Technical picks!")
                            if len(valid_bot) != len(set(valid_bot)):
                                errors.append("❌ Duplicate Selection Error: A baker may not be duplicated within your Bottom 3 Technical picks!")
                            if any(b in valid_bot for b in valid_top):
                                errors.append("❌ Duplicate Selection Error: A baker cannot appear in both Top 3 and Bottom 3 technical predictions!")
                            
                        if errors:
                            for err in errors:
                                st.error(err)
                        else:
                            p_info["weekly_picks"][active_prediction_week] = weekly_picks
                            if active_prediction_week not in st.session_state.league_members["AI Brian"]["weekly_picks"]:
                                st.session_state.league_members["AI Brian"]["weekly_picks"][active_prediction_week] = generate_ai_brian_weekly_picks(active_bakers, is_grace_week_catchup, active_prediction_week)
                            save_league_data()
                            st.session_state[notice_key] = f"✅ Success! Your Week {active_prediction_week} Ballot has been successfully submitted and locked in. You can log back in with your PIN anytime to review or edit your choices before the deadline."
                            st.session_state[auth_key] = False
                            st.rerun()

# ==============================================================================
# TAB 3: SHOW RESULTS
# ==============================================================================
if tab_results:
    st.header("📺 Official Broadcast Results & Visual Baker Gallery")
    
    curr_elim_all_res = eliminated_bakers_by_week.get(active_prediction_week, [])
    remaining_gallery_bakers_res = [b for b in ALL_BAKERS if b not in curr_elim_all_res]
    
    with st.expander(f"📸 Visual Baker Profiles & Season Statistics (Active Bakers - Week {active_prediction_week})", expanded=True):
        card_cols = st.columns(2)
        for idx, baker in enumerate(remaining_gallery_bakers_res):
            sb_c, inl_c, trb_c, tech_stat = get_baker_stats(baker, active_prediction_week)
            
            b_img = load_baker_image(baker)
            img_b64 = image_to_base64(b_img) if b_img else ""
            
            if img_b64:
                img_tag = f'<img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; max-width: 95px; height: 110px; object-fit: cover; border-radius: 6px; border: 1px solid #8D6E63;">'
            else:
                img_tag = '<div style="width: 100%; max-width: 95px; height: 110px; background-color: #EFEBE9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; color: #5D4037;">[Photo]</div>'
            
            if active_prediction_week <= 5:
                if isinstance(tech_stat, dict) and tech_stat:
                    tech_str = ", ".join([f"W{w}: #{p}" for w, p in sorted(tech_stat.items())])
                else:
                    tech_str = "None yet"
                tech_line = f"Technicals: <b>{tech_str}</b>"
            else:
                tech_line = f"Technicals: <b>{tech_stat}</b>"

            card_html = f"""
            <div style="border: 2px solid #5D4037; border-radius: 10px; padding: 12px; background-color: #FFF9F5; color: #2D1B18; box-shadow: 0 3px 6px rgba(0,0,0,0.1); margin-bottom: 15px;">
                <div style="background-color: #5D4037; color: #FFFFFF; padding: 6px 10px; border-radius: 6px; font-weight: bold; text-align: center; margin-bottom: 10px; font-size: 1.05rem;">
                    {baker}
                </div>
                <div style="display: flex; gap: 12px; align-items: center;">
                    <div style="flex: 0 0 95px; text-align: center;">
                        {img_tag}
                    </div>
                    <div style="flex: 1; font-size: 0.85rem; color: #2D1B18; line-height: 1.5; background-color: #FFFFFF; padding: 8px; border-radius: 6px; border: 1px solid #D7CCC8;">
                        <div style="color: #2D1B18; margin-bottom: 3px;">Star Baker: <b style="color: #5D4037;">{sb_c}</b></div>
                        <div style="color: #2D1B18; margin-bottom: 3px;">In Line SB: <b style="color: #5D4037;">{inl_c}</b></div>
                        <div style="color: #2D1B18; margin-bottom: 3px;">In Trouble: <b style="color: #5D4037;">{trb_c}</b></div>
                        <div style="color: #2D1B18;">{tech_line}</div>
                    </div>
                </div>
            </div>
            """
            with card_cols[idx % 2]:
                st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")
    weekly_res_map = st.session_state.get("weekly_results", {})
    
    if weekly_res_map:
        st.subheader("📋 Published Weekly Results")
        sel_res_week = st.selectbox("Select Week to View Results:", sorted([int(k) for k in weekly_res_map.keys()]), key="show_res_week_sel")
        if sel_res_week:
            w_act = get_week_results(sel_res_week, weekly_res_map)
            
            st.markdown(f"### 🧁 Episode Week {sel_res_week} Results")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                if sel_res_week == 10:
                    st.write(f"🏆 **Show Champion:** {w_act.get('show_champion', 'N/A')}")
                else:
                    st.write(f"🌟 **Star Baker:** {w_act.get('star_baker', 'N/A')}")
                    
                    inline_val = w_act.get('in_line_sb', 'N/A')
                    if isinstance(inline_val, list):
                        inline_str = ", ".join([str(b) for b in inline_val if b])
                    else:
                        inline_str = str(inline_val)
                    st.write(f"⭐ **'In Line' for Star Baker:** {inline_str}")
                    
                    elim_val = w_act.get('eliminated', 'N/A')
                    if isinstance(elim_val, list):
                        elim_str = ", ".join([str(b) for b in elim if b])
                    else:
                        elim_str = str(elim_val)
                    st.write(f"🚪 **Eliminated:** {elim_str}")
                    
                    trouble_val = w_act.get('in_trouble', 'N/A')
                    if isinstance(trouble_val, list):
                        trouble_str = ", ".join([str(b) for b in trouble_val if b])
                    else:
                        trouble_str = str(trouble_val)
                    st.write(f"⚠️ **'In Trouble':** {trouble_str}")
            with col_res2:
                hs_bakers = w_act.get('handshake_bakers', [])
                hs_str = ", ".join([str(b) for b in hs_bakers if b]) if hs_bakers else "None"
                st.write(f"🤝 **Hollywood Handshakes:** {hs_str}")
                st.write(f"😢 **Crying Incidents ({w_act.get('crying_count', 0)}):** {w_act.get('crying_timestamps', 'None recorded')}")
                st.write(f"💬 **Sexual Innuendos ({w_act.get('innuendo_count', 0)}):** {w_act.get('innuendo_timestamps', 'None recorded')}")
            
            tech_r = w_act.get('tech_rank', [])
            tech_top = w_act.get('tech_top_3', [])
            tech_bot = w_act.get('tech_bottom_3', [])
            if tech_r:
                st.markdown("**Technical Challenge Standings:**")
                st.write(" -> ".join([f"**#{i+1}** {b}" for i, b in enumerate(tech_r)]))
            elif tech_top or tech_bot:
                st.markdown("**Technical Challenge Standings:**")
                st.write(f"Top 3: {', '.join(tech_top)} | Bottom 3: {', '.join(tech_bot)}")
    else:
        st.info("No official broadcast results published yet by the administrator.")

    st.markdown("---")
    st.subheader("🔥 Cumulative Season Chaos Counters")
    
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    if weekly_res_map:
        for w_data in weekly_res_map.values():
            tot_hs += len(w_data.get("handshake_bakers", []))
            tot_cry += int(w_data.get("crying_count", 0))
            tot_inn += int(w_data.get("innuendo_count", 0))
            
    c_col1, c_col2, c_col3 = st.columns(3)
    c_col1.metric("🤝 Total Hollywood Handshakes", tot_hs)
    c_col2.metric("😢 Total Crying Incidents", tot_cry)
    c_col3.metric("💬 Total Sexual Innuendos", tot_inn)

    st.markdown("---")
    st.subheader("⚖️ Result Dispute & Timestamp Correction")
    
    dispute_player_choice = st.selectbox("Select Your Name to Log a Dispute:", ["-- Select Name --"] + ROSTER_HUMANS, key="dispute_player_dropdown")
    
    if dispute_player_choice != "-- Select Name --":
        sub_key = f"dispute_sent_{dispute_player_choice}"
        if st.session_state.get(sub_key, False):
            st.success(f"✅ Dispute successfully submitted for {dispute_player_choice}! You can submit another or select a different player above.")
            if st.button("Submit Another Dispute", key="reset_disp_btn"):
                st.session_state[sub_key] = False
                st.rerun()
        else:
            st.success(f"Logging dispute as **{dispute_player_choice}**")
            with st.form("dispute_form"):
                disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted([int(k) for k in weekly_res_map.keys()])] if weekly_res_map else ["Week 1"])
                disp_evidence = st.text_area("Video Timestamp & Evidence Description:")
                disp_correction = st.text_input("Requested Correction:")
                
                if st.form_submit_button("Submit Dispute"):
                    st.session_state.disputes.append({
                        "Player": dispute_player_choice, "Week": disp_week,
                        "Evidence": disp_evidence, "Correction": disp_correction,
                        "Status": "Pending Review 🗳️"
                    })
                    save_league_data()
                    st.session_state[sub_key] = True
                    st.rerun()
    else:
        st.info("👆 Please select your player name from the dropdown above to open the dispute submission form.")

    st.markdown("---")
    st.subheader("📋 Logged Disputes & Status")
    if st.session_state.get("disputes"):
        st.dataframe(pd.DataFrame(st.session_state.disputes), use_container_width=True, hide_index=True)
    else:
        st.info("No disputes submitted yet.")

# ==============================================================================
# TAB 4: ADMIN PANEL
# ==============================================================================
if tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        admin_pin = st.text_input("Enter Administrator PIN:", type="password")
        if st.button("Unlock Admin Panel"):
            if admin_pin == "6284":
                st.session_state.admin_authenticated = True
                st.success("Admin Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin PIN.")
    else:
        st.success("🔓 Authenticated as Administrator")
        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        
        if st.session_state.admin_verification_msg:
            st.success(st.session_state.admin_verification_msg)
            
        if st.session_state.admin_pin_reset_msg:
            c_msg1, c_msg2 = st.columns([5, 1])
            with c_msg1:
                st.success(st.session_state.admin_pin_reset_msg)
            with c_msg2:
                if st.button("Dismiss", key="dismiss_pin_msg_btn"):
                    st.session_state.admin_pin_reset_msg = ""
                    st.rerun()
            
        admin_selected_week = st.selectbox("Select Episode Week:", list(range(1, 11)), key="adm_w_sel")
        
        saved_w = get_week_results(admin_selected_week, st.session_state.weekly_results)
        is_published = bool(saved_w)
        
        edit_allowed = True
        if is_published:
            st.warning(f"⚠️ Week {admin_selected_week} results are already published.")
            col_unpub1, col_unpub2 = st.columns(2)
            with col_unpub1:
                edit_allowed = st.checkbox(f"Unlock Week {admin_selected_week} to edit published results", value=False, key=f"unlock_w{admin_selected_week}")
            with col_unpub2:
                if st.button(f"🗑️ Unpublish Week {admin_selected_week} Results", key=f"unpub_btn_{admin_selected_week}"):
                    if admin_selected_week in st.session_state.weekly_results:
                        del st.session_state.weekly_results[admin_selected_week]
                    if str(admin_selected_week) in st.session_state.weekly_results:
                        del st.session_state.weekly_results[str(admin_selected_week)]
                    if admin_selected_week == 10:
                        st.session_state.season_results = {}
                    
                    for member_name in st.session_state.league_members:
                        st.session_state.league_members[member_name]["total_score"] = 0
                        st.session_state.league_members[member_name]["weekly_breakdown"] = {}

                    all_weeks_scored = sorted([int(k) for k in st.session_state.weekly_results.keys()])
                    for w in all_weeks_scored:
                        act_w = get_week_results(w, st.session_state.weekly_results)
                        weekly_raw = {}
                        for m_name, m_data in st.session_state.league_members.items():
                            pred_w = m_data["weekly_picks"].get(w, m_data["weekly_picks"].get(str(w), {}))
                            raw_score = calculate_weekly_score(pred_w, act_w, w)
                            weekly_raw[m_name] = raw_score
                            m_data["weekly_breakdown"][w] = raw_score

                        if weekly_raw:
                            max_raw = max(weekly_raw.values())
                            for m_name, raw_s in weekly_raw.items():
                                if raw_s == max_raw and raw_s > 0:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5

                    all_w_res_pub2 = st.session_state.get("weekly_results", {})
                    total_hs_all2 = sum(len(w_dat.get("handshake_bakers", [])) for w_dat in all_w_res_pub2.values())
                    total_cry_all2 = sum(int(w_dat.get("crying_count", 0)) for w_dat in all_w_res_pub2.values())
                    total_inn_all2 = sum(int(w_dat.get("innuendo_count", 0)) for w_dat in all_w_res_pub2.values())
                    w10_pub2 = get_week_results(10, all_w_res_pub2)
                    act_winner_pub2 = w10_pub2.get("show_champion") if w10_pub2 else None
                    w8_elim_c2 = eliminated_bakers_by_week.get(9, [])
                    act_semis_c2 = [b for b in ALL_BAKERS if b not in w8_elim_c2]

                    comp_season_act2 = {
                        "winner": act_winner_pub2,
                        "semifinalists": act_semis_c2,
                        "handshakes": total_hs_all2,
                        "crying": total_cry_all2,
                        "innuendos": total_inn_all2
                    }

                    for m_name, m_data in st.session_state.league_members.items():
                        season_pred = m_data["season_picks"]
                        season_score = calculate_season_score(season_pred, comp_season_act2)
                        m_data["season_score"] = season_score
                        weekly_total = sum(m_data["weekly_breakdown"].values())
                        m_data["total_score"] = weekly_total + season_score

                    save_league_data()
                    st.session_state.admin_verification_msg = f"✅ Week {admin_selected_week} successfully unpublished! All standings and active weeks recalculated."
                    st.rerun()

            if not edit_allowed:
                st.info("Form fields are locked. Check the 'Unlock to Edit' box above to modify published results.")
        
        elim_saved = saved_w.get("eliminated")
        default_elim_idx = 0
        if elim_saved == "None":
            default_elim_idx = 1
        elif isinstance(elim_saved, list) and len(elim_saved) == 2:
            default_elim_idx = 2

        elim_type = st.radio("Elimination Format:", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], index=default_elim_idx, horizontal=True, key=f"adm_elim_type_w{admin_selected_week}")
        
        active_bakers = [b for b in ALL_BAKERS if b not in eliminated_bakers_by_week.get(admin_selected_week, [])]
        baker_opts = ["-- Select Baker --"] + active_bakers
        
        with st.form("admin_results_form"):
            st.subheader(f"Input Official Results for Week {admin_selected_week}")
            actuals = {}
            if admin_selected_week == 10:
                def_champ = saved_w.get("show_champion")
                def_champ_i = baker_opts.index(def_champ) if def_champ in baker_opts else 0
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts, index=def_champ_i)
            else:
                st.markdown("#### 🌟 Star Baker & Elimination Group")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    def_sb = saved_w.get("star_baker")
                    def_sb_i = baker_opts.index(def_sb) if def_sb in baker_opts else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts, index=def_sb_i, key=f"adm_sb_w{admin_selected_week}")
                    
                    def_inline = saved_w.get("in_line_sb", [])
                    if isinstance(def_inline, str): def_inline = [def_inline]
                    def_inline_defaults = [b for b in def_inline if b in active_bakers]
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, default=def_inline_defaults, key=f"adm_inline_w{admin_selected_week}")
                with col_g2:
                    if elim_type == "Single Elimination":
                        def_elim = saved_w.get("eliminated")
                        def_elim_i = baker_opts.index(def_elim) if def_elim in baker_opts else 0
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts, index=def_elim_i, key=f"adm_elim_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Grace Week)":
                        actuals["eliminated"] = "None"
                        st.info("Grace week active: No elimination.")
                    else:
                        el_list = saved_w.get("eliminated", [])
                        def_e1 = el_list[0] if isinstance(el_list, list) and len(el_list) > 0 else baker_opts[0]
                        def_e2 = el_list[1] if isinstance(el_list, list) and len(el_list) > 1 else baker_opts[0]
                        e1 = st.selectbox("Eliminated #1", baker_opts, index=baker_opts.index(def_e1) if def_e1 in baker_opts else 0, key=f"adm_elim1_w{admin_selected_week}")
                        e2 = st.selectbox("Eliminated #2", baker_opts, index=baker_opts.index(def_e2) if def_e2 in baker_opts else 0, key=f"adm_elim2_w{admin_selected_week}")
                        actuals["eliminated"] = [e1, e2]
                        
                    def_introuble = saved_w.get("in_trouble", [])
                    if isinstance(def_introuble, str): def_introuble = [def_introuble]
                    def_introuble_defaults = [b for b in def_introuble if b in active_bakers]
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, default=def_introuble_defaults, key=f"adm_introuble_w{admin_selected_week}")
            
            st.markdown(f"#### Technical Challenge Rankings (Enter all {len(active_bakers)} active bakers 1st through {len(active_bakers)}th):")
            act_tech = []
            saved_tech_rank = saved_w.get("tech_rank", [])
            for idx, b in enumerate(active_bakers):
                def_t = saved_tech_rank[idx] if (isinstance(saved_tech_rank, list) and idx < len(saved_tech_rank)) else baker_opts[0]
                def_t_i = baker_opts.index(def_t) if def_t in baker_opts else 0
                rank_str = "1st" if idx==0 else ("2nd" if idx==1 else ("3rd" if idx==2 else f"{idx+1}th"))
                sel = st.selectbox(f"Actual Technical {rank_str} Place", baker_opts, index=def_t_i, key=f"adm_t_{idx}_{admin_selected_week}")
                act_tech.append(sel)
            actuals["tech_rank"] = act_tech
            
            st.markdown("#### Chaos Categories & Timestamps:")
            def_hs_bakers = saved_w.get("handshake_bakers", [])
            actuals["handshake_bakers"] = st.multiselect("Bakers Receiving Handshakes", active_bakers, default=[b for b in def_hs_bakers if b in active_bakers])
            
            st.markdown("##### 😢 Crying Incidents")
            actuals["crying_count"] = st.number_input("Number of Crying Occurrences", min_value=0, value=int(saved_w.get("crying_count", 0)), key=f"adm_cry_count_{admin_selected_week}")
            actuals["crying_timestamps"] = st.text_input("Description of Crying Occurrence", value=saved_w.get("crying_timestamps", ""), placeholder="e.g. Molly @ 14:00", key=f"adm_cry_desc_{admin_selected_week}")
            
            st.markdown("##### 💬 Sexual Innuendos")
            actuals["innuendo_count"] = st.number_input("Number of Innuendo Occurrences", min_value=0, value=int(saved_w.get("innuendo_count", 0)), key=f"adm_inn_count_{admin_selected_week}")
            actuals["innuendo_timestamps"] = st.text_input("Description of Innuendos", value=saved_w.get("innuendo_timestamps", ""), placeholder="e.g. Soggy bottom @ 18:45", key=f"adm_inn_desc_{admin_selected_week}")

            pub_btn = st.form_submit_button("Publish Results & Recalculate Standings")
            if pub_btn:
                if is_published and not edit_allowed:
                    st.error("❌ Week results are locked. Please check the 'Unlock to Edit' box above before publishing changes.")
                else:
                    st.session_state.weekly_results[admin_selected_week] = actuals

                    for member_name in st.session_state.league_members:
                        st.session_state.league_members[member_name]["total_score"] = 0
                        st.session_state.league_members[member_name]["weekly_breakdown"] = {}

                    all_weeks_scored = sorted([int(k) for k in st.session_state.weekly_results.keys()])

                    for w in all_weeks_scored:
                        act_w = get_week_results(w, st.session_state.weekly_results)
                        weekly_raw = {}
                        for m_name, m_data in st.session_state.league_members.items():
                            pred_w = m_data["weekly_picks"].get(w, m_data["weekly_picks"].get(str(w), {}))
                            raw_score = calculate_weekly_score(pred_w, act_w, w)
                            weekly_raw[m_name] = raw_score
                            m_data["weekly_breakdown"][w] = raw_score

                        if weekly_raw:
                            max_raw = max(weekly_raw.values())
                            for m_name, raw_s in weekly_raw.items():
                                if raw_s == max_raw and raw_s > 0:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5

                    all_w_res_pub = st.session_state.get("weekly_results", {})
                    total_hs_all = sum(len(w_dat.get("handshake_bakers", [])) for w_dat in all_w_res_pub.values())
                    total_cry_all = sum(int(w_dat.get("crying_count", 0)) for w_dat in all_w_res_pub.values())
                    total_inn_all = sum(int(w_dat.get("innuendo_count", 0)) for w_dat in all_w_res_pub.values())
                    w10_pub = get_week_results(10, all_w_res_pub)
                    act_winner_pub = w10_pub.get("show_champion") if w10_pub else None
                    w8_elim_pub = eliminated_bakers_by_week.get(9, [])
                    act_semis_pub = [b for b in ALL_BAKERS if b not in w8_elim_pub]

                    computed_season_actuals = {
                        "winner": act_winner_pub,
                        "semifinalists": act_semis_pub,
                        "handshakes": total_hs_all,
                        "crying": total_cry_all,
                        "innuendos": total_inn_all
                    }

                    for m_name, m_data in st.session_state.league_members.items():
                        season_pred = m_data["season_picks"]
                        season_score = calculate_season_score(season_pred, computed_season_actuals)
                        m_data["season_score"] = season_score

                    for m_name, m_data in st.session_state.league_members.items():
                        weekly_total = sum(m_data["weekly_breakdown"].values())
                        season_total = m_data.get("season_score", 0)
                        m_data["total_score"] = weekly_total + season_total

                    save_league_data()
                    
                    action_type = "republished and updated" if is_published else "published"
                    st.session_state.admin_verification_msg = f"✅ **Verification Confirmed:** Week {admin_selected_week} results successfully {action_type}! All player scores, standings, and scorecards have been successfully recalculated."
                    st.rerun()

        st.markdown("---")
        st.subheader("🗳️ Resolve League Disputes")
        
        pending_disputes = [d for d in st.session_state.get("disputes", []) if "Pending Review" in d.get("Status", "")]
        
        if pending_disputes:
            st.write("Review active pending disputes, vote in GroupMe, and record the final ruling below:")
            for idx, disp in enumerate(st.session_state.get("disputes", [])):
                if "Pending Review" not in disp.get("Status", ""):
                    continue
                    
                st.markdown(f"**Dispute #{idx+1}** | Player: **{disp.get('Player')}** | Week: **{disp.get('Week')}** | Status: `{disp.get('Status')}`")
                st.markdown(f"*Evidence:* {disp.get('Evidence')}")
                st.markdown(f"*Correction Requested:* {disp.get('Correction')}")
                
                c_res1, c_res2 = st.columns(2)
                with c_res1:
                    if st.button(f"Accept Dispute #{idx+1}", key=f"accept_disp_{idx}"):
                        st.session_state.disputes[idx]["Status"] = "Accepted ✅"
                        save_league_data()
                        st.success(f"Dispute #{idx+1} marked as Accepted!")
                        st.rerun()
                with c_res2:
                    if st.button(f"Reject Dispute #{idx+1}", key=f"reject_disp_{idx}"):
                        st.session_state.disputes[idx]["Status"] = "Rejected ❌"
                        save_league_data()
                        st.success(f"Dispute #{idx+1} marked as Rejected!")
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No active pending disputes to resolve.")

        st.subheader("🔑 Reset Forgotten Player Security PIN")
        human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
        
        player_options = ["-- Select Player --"] + [f"{p} ({'🔐 PIN Active' if st.session_state.league_members[p].get('pin') else '🔓 PIN Cleared'})" for p in human_players]
        
        reset_sel_selection = st.selectbox("Select Player Profile to Reset PIN:", player_options, key="admin_pin_reset_dropdown")
        
        if reset_sel_selection != "-- Select Player --":
            reset_sel_player = reset_sel_selection.split(" (")[0]
            if st.button(f"Reset PIN for {reset_sel_player}"):
                st.session_state.league_members[reset_sel_player]["pin"] = None
                save_league_data()
                st.session_state.admin_pin_reset_msg = f"✅ Security PIN for **{reset_sel_player}** has been successfully cleared! They can now set a new 4-digit PIN upon next login."
                st.rerun()

        st.markdown("---")
        st.subheader("🔓 Grant Late Ballot Submission Extension")
        override_status = st.toggle("Enable Deadline Override (Allow Late Submissions)", value=st.session_state.get("admin_deadline_override", False), key="deadline_override_toggle")
        if override_status != st.session_state.get("admin_deadline_override", False):
            st.session_state.admin_deadline_override = override_status
            st.rerun()

        if st.session_state.get("admin_deadline_override", False):
            st.warning("⚠️ **Deadline Override Active:** The weekly voting deadline is currently bypassed. players can submit or edit their ballots for the active week.")

        st.markdown("---")
        st.subheader("🚨 Emergency Reset & Delete All App Data")
        confirm_erase = st.checkbox("I understand this will permanently erase all player prediction ballots, PINs, and published broadcast results.", key="confirm_erase_check")
        if st.button("🗑️️ Erase All Competition Data", type="primary"):
            if confirm_erase:
                if os.path.exists(DATA_FILE):
                    try:
                        os.remove(DATA_FILE)
                    except Exception:
                        pass
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("All competition data successfully erased!")
                st.rerun()
            else:
                st.error("Please check the confirmation box above first.")
