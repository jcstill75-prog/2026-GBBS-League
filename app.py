import os
import io
import base64
import random
import json
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from PIL import Image

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

saved_state = load_league_data()

if "league_members" not in st.session_state:
    st.session_state.league_members = saved_state.get("league_members", {})
if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_state.get("weekly_results", {})
if "season_results" not in st.session_state:
    st.session_state.season_results = saved_state.get("season_results", {})
if "disputes" not in st.session_state:
    st.session_state.disputes = saved_state.get("disputes", [])
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "admin_deadline_override" not in st.session_state:
    st.session_state.admin_deadline_override = saved_state.get("admin_deadline_override", False)
if "week_publication_timestamps" not in st.session_state:
    st.session_state.week_publication_timestamps = saved_state.get("week_publication_timestamps", {})

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
                    if len(pred_top3) > 1 and len(act_top3) > 1 and pred_top3[1] == act_top3[1] and pred_top3[1] != "--Select Baker--": score += 2
                    if len(pred_top3) > 2 and len(act_top3) > 2 and pred_top3[2] == act_top3[2] and pred_top3[2] != "--Select Baker--": score += 2
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
                    if len(pred_bot3) > 1 and len(act_bot3) > 1 and pred_bot3[1] == act_bot3[1] and pred_bot3[1] != "--Select Baker--": score += 2
                    if len(pred_bot3) > 0 and len(act_bot3) > 0 and pred_bot3[0] == act_bot3[0] and pred_bot3[0] != "--Select Baker--": score += 2
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
    elim_list = []
    for w in sorted(st.session_state.get("weekly_results", {}).keys(), key=lambda x: int(x)):
        res = st.session_state.weekly_results[w]
        act_el = res.get("eliminated")
        if isinstance(act_el, list):
            for b in act_el:
                if b and b != "None" and b not in elim_list: elim_list.append(b)
        elif isinstance(act_el, str) and act_el and act_el != "None":
            if act_el not in elim_list: elim_list.append(act_el)
        elim_map[int(w) + 1] = list(elim_list)
    return elim_map

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

def recalculate_all_scores():
    all_w_res = st.session_state.get("weekly_results", {})
    total_hs_all = sum(len(w_dat.get("handshake_bakers", [])) for w_dat in all_w_res.values())
    total_cry_all = sum(int(w_dat.get("crying_count", 0)) for w_dat in all_w_res.values())
    total_inn_all = sum(int(w_dat.get("innuendo_count", 0)) for w_dat in all_w_res.values())
    w10_res = get_week_results(10, all_w_res)
    act_winner = w10_res.get("show_champion") if w10_res else None
    
    elim_by_week = get_eliminated_bakers_by_week()
    w8_elim = elim_by_week.get(9, [])
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

        for w in all_weeks_scored:
            w_scores = [calculate_weekly_score(m_dat["weekly_picks"].get(w, m_dat["weekly_picks"].get(str(w), {})), get_week_results(w, all_w_res), w) for m_dat in st.session_state.league_members.values()]
            max_w_score = max(w_scores) if w_scores else 0
            base_score = m_data["weekly_breakdown"].get(w, 0)
            if w_scores and base_score == max_w_score and base_score > 0:
                m_data["weekly_breakdown"][w] = base_score + 5

        # Only evaluate season scores after Week 10 grand finale is published
        if is_week_published(10, all_w_res):
            season_score = calculate_season_score(m_data.get("season_picks", {}), computed_season_actuals)
            m_data["season_score"] = season_score
        else:
            m_data["season_score"] = 0
            
        weekly_total = sum(m_data["weekly_breakdown"].values())
        m_data["total_score"] = weekly_total + m_data["season_score"]

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
        st.session_state.league_members[m].setdefault("weekly_picks", {})
        st.session_state.league_members[m].setdefault("season_picks", {})

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

eliminated_bakers_by_week = get_eliminated_bakers_by_week()
all_scored_weeks = sorted([int(k) for k in st.session_state.weekly_results.keys()])
active_prediction_week = max(all_scored_weeks) + 1 if all_scored_weeks else 1
if active_prediction_week > 10: active_prediction_week = 10

recalculate_all_scores()

### --- 5. SIDEBAR (3-Section Scoring Guide) ---
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
    
    with st.expander("🌟 Season-Wide Predictions", expanded=False):
        st.markdown("""
        * **Season Winner:** 40 pts
        * **Finalist Consolation:** 15 pts *(Top 3)*
        * **Other 3 Semifinalists:** 10 pts each
        * **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        * **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        * **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Weeks 2–7 Scoring", expanded=False):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts
        * **In Line / In Trouble Nominees:** 2 pts each
        * **Technical Challenge (Top 3 & Bottom 3):**
          * Top 3 / Bottom 3 Sweep: 10 pts each[cite: 1, 3]
          * Exact 1st / Last Place: 3 pts[cite: 1, 3]
          * Exact 2nd & 3rd / 2nd-to-Last & 3rd-to-Last: 2 pts each[cite: 1, 3]
          * Correct Baker in Wrong Slot: 1 pt[cite: 1, 3]
        """)
        
    with st.expander("🏆 Weeks 8–10 Scoring", expanded=False):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts
        * **In Line / In Trouble (Weeks 8–9):** 2 pts each
        * **Week 8 (Quarterfinals - 5 Bakers):** 
          * Full Ranking: 3 pts (1st/5th), 2 pts (2nd/3rd/4th)
          * Flawless 5-for-5 Sweep: 25 pts
        * **Week 9 (Semifinals - 4 Bakers):** 
          * Full Ranking: 3 pts (1st/4th), 2 pts (2nd/3rd)
          * Flawless 4-for-4 Sweep: 20 pts
        * **Week 10 (Grand Finale - 3 Bakers):** 
          * Full Ranking: 3 pts (1st), 2 pts (2nd/3rd)
          * Flawless 3-for-3 Sweep: 15 pts
          * Correct Show Champion Prediction: 15 pts
        * **Star Member Weekly Bonus:** +5 pts
        """)

### --- NAVIGATION TABS ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
tab_lead, tab_submit, tab_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings",
    "📝 Submit Predictions",
    "📺 Show Results",
    "👑 Admin Panel"
])

### ==============================================================================
### TAB 1: LEADERBOARD & STANDINGS
### ==============================================================================
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
        if is_week_published(10, all_w_res_global):
            s_score = calculate_season_score(data.get("season_picks", {}), current_season_actuals)
            data["season_score"] = s_score
        else:
            data["season_score"] = 0
            
        weekly_total = sum(data.get("weekly_breakdown", {}).values())
        data["total_score"] = weekly_total + data["season_score"]
        
        lb_data.append({"member": name, "points": data.get("total_score", 0), "data": data})
        
    df_lb = pd.DataFrame(lb_data)
    if not df_lb.empty:
        df_lb = df_lb.sort_values(by="points", ascending=False).reset_index(drop=True)
        df_lb.index = df_lb.index + 1
        
        html_rows = []
        for idx, row in df_lb.iterrows():
            badge = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"#{idx}"))
            star_wins = get_star_member_wins_count(row['member'])
            star_badge = f"  <span style='font-size: 0.85rem;' title='Star Member High Scorer Wins'>⭐ x{star_wins}</span>" if star_wins > 0 else ""
            html_rows.append(f"<tr><td><b>{badge}</b></td><td><span class='lb-name'>{row['member']}</span>{star_badge}</td><td style='text-align: right;'><b>{row['points']} pts</b></td></tr>")
            
        st.markdown(f"""
        <table style="width: 100%; border-collapse: collapse;">
            <thead><tr><th style="width: 100px;">Rank</th><th>League Member</th><th style="text-align: right;">Total Points</th></tr></thead>
            <tbody>{''.join(html_rows)}</tbody>
        </table>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    selected_card_player = st.selectbox("Select Player to View Scorecard:", ROSTER_ALPHABETICAL, key="lb_player_card_sel")
    if selected_card_player in st.session_state.league_members:
        p_data = st.session_state.league_members[selected_card_player]
        p_season = p_data.get("season_picks", {})
        p_weekly = p_data.get("weekly_picks", {})
        
        if selected_card_player == "AI Brian":
            avatar = load_ai_brian_avatar()
            col_av, col_desc = st.columns([1, 6])
            with col_av:
                if avatar:
                    st.image(avatar, width=70)
                else:
                    st.markdown("### 🤖")
            with col_desc:
                st.write("AI Brian is an automated simulator. His picks are auto-generated according to league rules.")

        st.markdown(f"### **{selected_card_player}'s Weekly Predictions Log**")
        if p_weekly:
            sorted_weeks = sorted(p_weekly.keys(), key=lambda x: int(x))
            for w_num in sorted_weeks:
                w_picks = p_weekly[w_num]
                w_pts = p_data.get("weekly_breakdown", {}).get(w_num, 0)
                w_pts_str = f"{w_pts} pts"
                
                with st.expander(f"Week {w_num} Ballot (Earned: {w_pts_str})"):
                    has_pub = is_week_published(w_num, weekly_res_map)
                    act_w = get_week_results(w_num, weekly_res_map)
                    
                    if has_pub:
                        sb_pred = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                        sb_act = act_w.get("star_baker", act_w.get("show_champion", "N/A"))
                        sb_ok = (sb_pred == sb_act)
                        sb_color = "green" if sb_ok else "gray"
                        sb_pts = "+5 pts" if sb_ok else "+0 pts"
                        st.markdown(f"* **Star Baker / Champion:** <span style='color: #1E88E5; font-weight: bold;'>{sb_pred}</span> | Actual: <span style='color: #B54E43; font-weight: bold;'>{sb_act}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color: {sb_color}; font-weight: bold;'>{sb_pts}</span>", unsafe_allow_html=True)
                        
                        inl_pred = w_picks.get("in_line_sb", "N/A")
                        inl_act = act_w.get("in_line_sb", "N/A")
                        if isinstance(inl_act, list):
                            inl_ok = (inl_pred in inl_act)
                        else:
                            inl_ok = (inl_pred == inl_act)
                        inl_color = "green" if inl_ok else "gray"
                        inl_pts = "+2 pts" if inl_ok else "+0 pts"
                        inl_act_str = ", ".join(inl_act) if isinstance(inl_act, list) else str(inl_act)
                        st.markdown(f"* **In Line SB:** <span style='color: #1E88E5; font-weight: bold;'>{inl_pred}</span> | Actual: <span style='color: #B54E43; font-weight: bold;'>{inl_act_str}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color: {inl_color}; font-weight: bold;'>{inl_pts}</span>", unsafe_allow_html=True)
                        
                        elim_pred = w_picks.get("eliminated", "N/A")
                        elim_act = act_w.get("eliminated", "N/A")
                        
                        if isinstance(elim_pred, list):
                            pred_str = ", ".join([str(b) for b in elim_pred if b])
                        else:
                            pred_str = str(elim_pred)
                            
                        if isinstance(elim_act, list):
                            act_str = ", ".join([str(b) for b in elim_act if b])
                            if isinstance(elim_pred, list):
                                elim_ok = any(p in elim_act for p in elim_pred)
                            else:
                                elim_ok = (elim_pred in elim_act)
                        else:
                            act_str = str(elim_act)
                            if isinstance(elim_pred, list):
                                elim_ok = (act_str in elim_pred)
                            else:
                                elim_ok = (pred_str == act_str)
                                
                        elim_color = "green" if elim_ok else "gray"
                        elim_pts = "+5 pts" if elim_ok else "+0 pts"
                        st.markdown(f"* **Eliminated:** <span style='color: #1E88E5; font-weight: bold;'>{pred_str}</span> | Actual: <span style='color: #B54E43; font-weight: bold;'>{act_str}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color: {elim_color}; font-weight: bold;'>{elim_pts}</span>", unsafe_allow_html=True)
                        
                        trb_pred = w_picks.get("in_trouble", "N/A")
                        trb_act = act_w.get("in_trouble", "N/A")
                        if isinstance(trb_act, list):
                            trb_ok = (trb_pred in trb_act)
                        else:
                            trb_ok = (trb_pred == trb_act)
                        trb_color = "green" if trb_ok else "gray"
                        trb_pts = "+2 pts" if trb_ok else "+0 pts"
                        trb_act_str = ", ".join(trb_act) if isinstance(trb_act, list) else str(trb_act)
                        st.markdown(f"* **In Trouble:** <span style='color: #1E88E5; font-weight: bold;'>{trb_pred}</span> | Actual: <span style='color: #B54E43; font-weight: bold;'>{trb_act_str}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color: {trb_color}; font-weight: bold;'>{trb_pts}</span>", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown("**Technical Challenge Breakdown:**")
                        
                        if w_num >= 8:
                            pred_r = w_picks.get("tech_rank", [])
                            act_r = act_w.get("tech_rank", [])
                            for idx, pred_b in enumerate(pred_r):
                                actual_baker = act_r[idx] if idx < len(act_r) else "N/A"
                                is_exact = (pred_b == actual_baker)
                                t_color = "green" if is_exact else "gray"
                                t_pts = "3 pts" if is_exact else "0 pts"
                                st.markdown(f"* #{idx+1} Place: <span style='color: #1E88E5; font-weight: bold;'>{pred_b}</span> | Actual: <span style='color: #B54E43; font-weight: bold;'>{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color: {t_color}; font-weight: bold;'>{t_pts}</span>", unsafe_allow_html=True)
                        else:
                            pred_top3 = w_picks.get("tech_top_3", [])
                            act_top3 = act_w.get("tech_top_3", [])
                            if not act_top3 and act_w.get("tech_rank"):
                                act_top3 = act_w.get("tech_rank")[:3]
                                
                            pred_bot3 = w_picks.get("tech_bottom_3", [])
                            act_bot3 = act_w.get("tech_bottom_3", [])
                            if not act_bot3 and act_w.get("tech_rank"):
                                act_bot3 = act_w.get("tech_rank")[-3:]
                                
                            is_top3_sweep = (len(pred_top3) == 3 and len(act_top3) == 3 and pred_top3 == act_top3)
                            
                            st.markdown("*(Top 3 Technical)*")
                            for t_idx, pred_b in enumerate(pred_top3):
                                r_label = "1st" if t_idx == 0 else ("2nd" if t_idx == 1 else "3rd")
                                actual_baker = act_top3[t_idx] if t_idx < len(act_top3) else "N/A"
                                
                                if is_top3_sweep:
                                    t_color = "green"
                                    t_pts = "+10 pts (Sweep)"
                                else:
                                    if pred_b == actual_baker:
                                        t_color = "green"
                                        t_pts = "+3 pts" if t_idx == 0 else "+2 pts"
                                    elif pred_b in act_top3:
                                        t_color = "orange"
                                        t_pts = "+1 pt (Wrong Slot)"
                                    else:
                                        t_color = "gray"
                                        t_pts = "+0 pts"
                                        
                                st.markdown(f"* {r_label} Place: <span style='color: #1E88E5; font-weight: bold;'>{pred_b}</span> | Actual: <span style='color: #B54E43; font-weight: bold;'>{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color: {t_color}; font-weight: bold;'>{t_pts}</span>", unsafe_allow_html=True)
                                
                            is_bot3_sweep = (len(pred_bot3) == 3 and len(act_bot3) == 3 and pred_bot3 == act_bot3)
                            st.markdown("*(Bottom 3 Technical)*")
                            for b_idx, pred_b in enumerate(pred_bot3):
                                r_label = "3rd-to-Last" if b_idx == 0 else ("2nd-to-Last" if b_idx == 1 else "Last")
                                actual_baker = act_bot3[b_idx] if b_idx < len(act_bot3) else "N/A"
                                
                                if is_bot3_sweep:
                                    t_color = "green"
                                    t_pts = "+10 pts (Sweep)"
                                else:
                                    if pred_b == actual_baker:
                                        t_color = "green"
                                        t_pts = "+3 pts" if b_idx == 2 else "+2 pts"
                                    elif pred_b in act_bot3:
                                        t_color = "orange"
                                        t_pts = "+1 pt (Wrong Slot)"
                                    else:
                                        t_color = "gray"
                                        t_pts = "+0 pts"
                                        
                                st.markdown(f"* {r_label} Place: <span style='color: #1E88E5; font-weight: bold;'>{pred_b}</span> | Actual: <span style='color: #B54E43; font-weight: bold;'>{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color: {t_color}; font-weight: bold;'>{t_pts}</span>", unsafe_allow_html=True)
                    else:
                        st.info("Transparent scoring comparison and actual outcomes will appear here once official broadcast results are published.")
                        
                    st.markdown("---")
                    st.markdown(f"**Total Points Earned This Week:** `{w_pts} pts`")
        else:
            st.info("No weekly prediction ballots submitted yet.")

        st.markdown("---")
        st.markdown(f"### **{selected_card_player}'s Season Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_list = p_season.get("semifinalists", [])
        semis_pick = ", ".join(semis_list) if semis_list else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick}")
        st.write(f"😢 **Predicted Crying Incidents:** {cry_pick}")
        st.write(f"💬 **Predicted Sexual Innuendos:** {inn_pick}")

### ==============================================================================
### TAB 2: SUBMIT PREDICTIONS
### ==============================================================================
if tab_submit:
    st.header("📝 Submit Predictions")
    pred_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="pred_player_login_sel")
    p_info = st.session_state.league_members[pred_player]
    
    auth_success = False
    
    if p_info.get("pin") is None:
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
        auth_key = f"auth_verified_{pred_player}"
        if st.session_state.get(auth_key, False):
            auth_success = True
            st.success(f"🔓 Authenticated as {pred_player}!")
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
        if not st.session_state.weekly_results and active_prediction_week == 1:
            st.warning("🔒 **Week 1 Scouting Phase:** No weekly ballots are submitted for Week 1. Season-wide projections and Week 2 ballots unlock together once Week 1 results are published by the Admin!")
        elif is_weekly_voting_closed(active_prediction_week):
            st.error("⏰ **Weekly Voting Closed:** The weekly voting deadline (Tuesdays at 2:00 PM Houston time) has passed. Ballot submissions and edits are locked.")
        else:
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
                
                success_key_w2 = f"ballot_submitted_msg_w2_{pred_player}"
                if st.session_state.get(success_key_w2, False):
                    st.success("🎉 Your Week 2 ballot and season projections have been successfully locked in! You may log back in anytime with your 4-digit PIN to view or update your choices.")
                    if st.button("Make Further Edits", key="reset_w2_sub_btn"):
                        st.session_state[success_key_w2] = False
                        st.rerun()
                else:
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
                            weekly_picks["in_line_sb"] = st.selectbox("'In Line SB' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=inl_idx)
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
                            edit_conf = st.checkbox("⚠️ Check this box to confirm you want to edit your previously submitted Week 2 Ballot & Season Projections.")

                        sub_w2 = st.form_submit_button("Submit Week 2 Ballot & Season Projections")
                        if sub_w2:
                            errors = []
                            if has_submitted and not edit_conf:
                                errors.append("❌ Please check the confirmation box to edit your previously submitted ballot.")
                            if s_win == "--Select Baker--":
                                errors.append("Please select a valid Season Winner.")
                            
                            main_picks = [weekly_picks.get("star_baker"), weekly_picks.get("in_line_sb"), weekly_picks.get("in_trouble")]
                            elim_val = weekly_picks.get("eliminated")
                            if isinstance(elim_val, list):
                                main_picks.extend(elim_val)
                            else:
                                main_picks.append(elim_val)
                                
                            valid_main = [p for p in main_picks if p and p != "--Select Baker--"]
                            if len(valid_main) != len(set(valid_main)):
                                errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line SB, In Trouble, and Eliminated!")
                                
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
                                    st.session_state.league_members["AI Brian"]["weekly_picks"][2] = {
                                        "star_baker": random.choice(active_bakers),
                                        "eliminated": random.choice(active_bakers),
                                        "tech_top_3": random.sample(active_bakers, min(3, len(active_bakers))),
                                        "tech_bottom_3": random.sample(active_bakers, min(3, len(active_bakers)))
                                    }
                                save_league_data()
                                st.session_state[success_key_w2] = True
                                st.rerun()

            else:
                st.markdown(f"### 📅 Week {active_prediction_week} Prediction Ballot")
                success_key_wk = f"ballot_submitted_msg_w{active_prediction_week}_{pred_player}"
                
                if st.session_state.get(success_key_wk, False):
                    st.success(f"🎉 Your Week {active_prediction_week} ballot has been successfully locked in! You may log back in anytime with your 4-digit PIN to view or update your choices.")
                    if st.button("Make Further Edits", key=f"reset_w{active_prediction_week}_sub_btn"):
                        st.session_state[success_key_wk] = False
                        st.rerun()
                else:
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
                                weekly_picks["in_line_sb"] = st.selectbox("'In Line SB' Nominee (2 pts):", ["--Select Baker--"] + active_bakers, index=inl_idx)
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
                                main_picks = []
                                sb = weekly_picks.get("star_baker")
                                if sb and sb != "--Select Baker--": main_pins.append(sb) if 'main_pins' in locals() else main_picks.append(sb)
                                
                                inl = weekly_picks.get("in_line_sb")
                                if inl and inl != "--Select Baker--": main_picks.append(inl)
                                
                                elim = weekly_picks.get("eliminated")
                                if isinstance(elim, list):
                                    for e in elim:
                                        if e and e != "--Select Baker--": main_picks.append(e)
                                elif elim and elim != "--Select Baker--":
                                    main_picks.append(elim)
                                    
                                trb = weekly_picks.get("in_trouble")
                                if trb and trb != "--Select Baker--": main_picks.append(trb)
                                
                                if len(main_picks) != len(set(main_picks)):
                                    errors.append("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line SB, In Trouble, and Eliminated!")
                                    
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
                                    st.session_state.league_members["AI Brian"]["weekly_picks"][active_prediction_week] = {
                                        "star_baker": random.choice(active_bakers),
                                        "eliminated": random.sample(active_bakers, 2) if is_grace_week_catchup else random.choice(active_bakers),
                                        "tech_top_3": random.sample(active_bakers, min(3, len(active_bakers))),
                                        "tech_bottom_3": random.sample(active_bakers, min(3, len(active_bakers)))
                                    }
                                save_league_data()
                                st.session_state[success_key_wk] = True
                                st.rerun()

### ==============================================================================
### TAB 3: SHOW RESULTS (Including Visual Baker Profiles with Handshakes)
### ==============================================================================
if tab_results:
    st.header("📺 Official Broadcast Results & Visual Baker Gallery")
    
    weekly_res_map = st.session_state.get("weekly_results", {})
    
    if weekly_res_map:
        st.subheader("📋 Published Weekly Results")
        sel_res_week = st.selectbox("Select Week to View Results:", sorted(weekly_res_map.keys(), key=lambda x: int(x)), key="show_res_week_sel")
        if sel_res_week:
            w_act = weekly_res_map[sel_res_week]
            
            st.markdown(f"### 🧁 Episode Week {sel_res_week} Results")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                if int(sel_res_week) == 10:
                    st.write(f"🏆 **Show Champion:** {w_act.get('show_champion', 'N/A')}")
                else:
                    st.write(f"🌟 **Star Baker:** {w_act.get('star_baker', 'N/A')}")
                    
                    inline_val = w_act.get('in_line_sb', 'N/A')
                    if isinstance(inline_val, list):
                        inline_str = ", ".join([str(b) for b in inline_val if b])
                    else:
                        inline_str = str(inline_val)
                    st.write(f"⭐ **'In Line SB':** {inline_str}")
                    
                    elim_val = w_act.get('eliminated', 'N/A')
                    if isinstance(elim_val, list):
                        elim_str = ", ".join([str(b) for b in elim_val if b])
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
    curr_elim_all = eliminated_bakers_by_week.get(active_prediction_week, [])
    remaining_gallery_bakers = [b for b in ALL_BAKERS if b not in curr_elim_all]
    
    with st.expander(f"📸 Visual Baker Profiles & Season Statistics (Active Bakers - Week {active_prediction_week})", expanded=True):
        card_cols = st.columns(2)
        for idx, baker in enumerate(remaining_gallery_bakers):
            sb_c, inl_c, trb_c, hs_c, tech_stat = get_baker_stats(baker, active_prediction_week)
            
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
                        <div style="color: #2D1B18; margin-bottom: 3px;">Handshakes: <b style="color: #5D4037;">{hs_c}</b></div>
                        <div style="color: #2D1B18;">{tech_line}</div>
                    </div>
                </div>
            </div>
            """
            with card_cols[idx % 2]:
                st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚖️ Result Dispute & Timestamp Correction")
    
    dispute_player_choice = st.selectbox("Select Your Name to Log a Dispute:", ["-- Select Name --"] + ROSTER_HUMANS, key="dispute_player_dropdown")
    
    if dispute_player_choice != "-- Select Name --":
        sub_key = f"dispute_sent_{dispute_player_choice}"
        if st.session_state.get(sub_key, False):
            st.success(f"✅ Dispute successfully logged for **{dispute_player_choice}**. It is pending review by the league.")
            if st.button("Submit Another Dispute", key="reset_disp_btn"):
                st.session_state[sub_key] = False
                st.rerun()
        else:
            st.success(f"Logging dispute as **{dispute_player_choice}**")
            with st.form("dispute_form"):
                disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted(weekly_res_map.keys(), key=lambda x: int(x))] if weekly_res_map else ["Week 1"])
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

### ==============================================================================
### TAB 4: ADMIN PANEL
### ==============================================================================
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
        
        # --- DATABASE BACKUP & RESTORE UTILITIES ---
        st.subheader("💾 Database Backup & Restore")
        col_bk1, col_bk2 = st.columns(2)
        with col_bk1:
            try:
                current_payload = {
                    "league_members": st.session_state.get("league_members", {}),
                    "weekly_results": st.session_state.get("weekly_results", {}),
                    "season_results": st.session_state.get("season_results", {}),
                    "disputes": st.session_state.get("disputes", [])
                }
                json_bytes = json.dumps(current_payload, indent=2).encode('utf-8')
                st.download_button(
                    label="📥 Download League JSON Backup",
                    data=json_bytes,
                    file_name="gbbs_league_backup.json",
                    mime="application/json",
                    help="Download a backup file of all league data to protect against server resets."
                )
            except Exception:
                st.info("Backup download unavailable.")
        with col_bk2:
            uploaded_backup = st.file_uploader("📤 Upload / Restore League JSON Backup", type=["json"], key="backup_uploader")
            if uploaded_backup is not None:
                if st.button("📥 Confirm & Restore Backup", key="confirm_restore_btn"):
                    try:
                        restored_data = json.load(uploaded_backup)
                        if isinstance(restored_data, dict):
                            st.session_state.league_members = restored_data.get("league_members", st.session_state.league_members)
                            w_res_raw = restored_data.get("weekly_results", {})
                            w_res = {}
                            for k, v in w_res_raw.items():
                                try:
                                    w_res[int(k)] = v
                                except Exception:
                                    w_res[k] = v
                            st.session_state.weekly_results = w_res
                            st.session_state.season_results = restored_data.get("season_results", {})
                            st.session_state.disputes = restored_data.get("disputes", [])
                            save_league_data()
                            st.success("✅ League backup successfully restored! Refreshing app...")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to parse backup file: {e}")

        st.markdown("---")
        
        if st.session_state.get("admin_verification_msg"):
            st.success(st.session_state["admin_verification_msg"])
            
        admin_selected_week = st.selectbox("Select Episode Week:", list(range(1, 11)), key="adm_w_sel")
        
        saved_w = st.session_state.weekly_results.get(admin_selected_week, st.session_state.weekly_results.get(str(admin_selected_week), {}))
        is_published = bool(saved_w)
        
        edit_allowed = True
        if is_published:
            st.warning(f"⚠️ Week {admin_selected_week} results are already published.")
            edit_allowed = st.checkbox(f"Unlock Week {admin_selected_week} to edit published results and modify historical scoring", value=False, key=f"unlock_w{admin_selected_week}")
            if not edit_allowed:
                st.info("Form fields are locked to protect existing historical scoring. Check the box above to enable editing.")
        
        elim_type = st.radio("Elimination Format:", ["Single Elimination", "No Elimination (Grace Week)", "Double Elimination"], horizontal=True, key=f"adm_elim_type_w{admin_selected_week}")
        
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
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line SB' Nominees", active_bakers, default=def_inline_defaults, key=f"adm_inline_w{admin_selected_week}")
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
            
            if admin_selected_week == 10:
                st.markdown("---")
                st.subheader("Final Seasonal Broadcast Totals")
                act_winner = st.selectbox("Actual Season Winner", baker_opts, key=f"adm_season_winner_w{admin_selected_week}")
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, max_selections=4, key=f"adm_season_semis_w{admin_selected_week}")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, max_selections=3, key=f"adm_season_fin_w{admin_selected_week}")
                act_handshakes = st.number_input("Actual Season Total Handshakes", min_value=0, value=5, key=f"adm_season_hs_w{admin_selected_week}")
                act_crying = st.number_input("Actual Season Total Crying Incidents", min_value=0, value=12, key=f"adm_season_cry_w{admin_selected_week}")
                act_innuendos = st.number_input("Actual Season Total Sexual Innuendos", min_value=0, value=48, key=f"adm_season_inn_w{admin_selected_week}")

                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }

            pub_btn = st.form_submit_button("Publish Results & Recalculate Standings")
            if pub_btn:
                if is_published and not edit_allowed:
                    st.error("❌ Week results are locked. Please check the 'Unlock to Edit' box above before publishing changes.")
                else:
                    st.session_state.weekly_results[admin_selected_week] = actuals
                    st.session_state.week_publication_timestamps[admin_selected_week] = datetime.datetime.now(ZoneInfo("America/Chicago")).isoformat()
                    
                    if admin_selected_week == 10:
                        st.session_state.season_results = actuals_season

                    recalculate_all_scores()
                    save_league_data()
                    
                    action_type = "republished and updated" if is_published else "published"
                    st.session_state["admin_verification_msg"] = f"✅ **Verification Confirmed:** Week {admin_selected_week} results successfully {action_type}! All player scores, standings, and scorecards have been successfully recalculated."
                    st.rerun()

        st.markdown("---")
        
        # --- UNPUBLISH WEEK UTILITY ---
        st.subheader(f"↩️ Unpublish Week Results")
        published_weeks_list = sorted([int(k) for k in st.session_state.weekly_results.keys()])
        if published_weeks_list:
            unpub_week_sel = st.selectbox("Select Week to Unpublish (Roll Back):", published_weeks_list, key="unpub_week_dropdown")
            if st.button(f"↩️ Roll Back / Unpublish Week {unpub_week_sel}", key="unpub_btn_exec"):
                if unpub_week_sel in st.session_state.weekly_results:
                    del st.session_state.weekly_results[unpub_week_sel]
                if unpub_week_sel in st.session_state.week_publication_timestamps:
                    del st.session_state.week_publication_timestamps[unpub_week_sel]
                recalculate_all_scores()
                save_league_data()
                st.success(f"Successfully unpublished Week {unpub_week_sel} and recalculated standings!")
                st.rerun()
        else:
            st.info("No published weeks available to roll back.")

        st.markdown("---")
        st.subheader("🗳️ Resolve League Disputes")
        st.write("Review active disputes submitted by players, vote in GroupMe, and record the final ruling below:")
        pending_disputes = [d for d in st.session_state.get("disputes", []) if d.get("Status") == "Pending Review 🗳️"]
        if pending_disputes:
            for idx, disp in enumerate(st.session_state.get("disputes", [])):
                if disp.get("Status") == "Pending Review 🗳️":
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
            st.info("No active disputes awaiting review.")

        st.markdown("---")
        st.subheader("🔑 Reset Forgotten Player Security PIN")
        human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
        reset_sel_player = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + human_players, key="admin_pin_reset_dropdown")
        if reset_sel_player != "-- Select Player --":
            if st.button(f"Reset PIN for {reset_sel_player}"):
                st.session_state.league_members[reset_sel_player]["pin"] = None
                save_league_data()
                st.success(f"Security PIN for {reset_sel_player} has been cleared! They can set a new 4-digit PIN upon next login.")
                st.rerun()

        st.markdown("---")
        st.subheader("🔓 Grant Late Ballot Submission Extension")
        override_status = st.toggle("Enable Deadline Override (Allow Late Submissions)", value=st.session_state.get("admin_deadline_override", False), key="deadline_override_toggle")
        if override_status != st.session_state.get("admin_deadline_override", False):
            st.session_state.admin_deadline_override = override_status
            save_league_data()
            st.rerun()

        if st.session_state.get("admin_deadline_override", False):
            st.warning("⚠️ **Deadline Override Active:** The weekly voting deadline is currently bypassed. Players can submit or edit their ballots for the active week.")

        st.markdown("---")
        st.subheader("🚨 Emergency Reset & Delete All App Data")
        confirm_erase = st.checkbox("I understand this will permanently erase all player prediction ballots, PINs, and published broadcast results.", key="confirm_erase_check")
        if st.button("🗑️ Erase All Competition Data", type="primary"):
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
