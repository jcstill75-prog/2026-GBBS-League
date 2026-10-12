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

        season_score = calculate_season_score(m_data.get("season_picks", {}), computed_season_actuals)
        m_data["season_score"] = season_score
        weekly_total = sum(m_data["weekly_breakdown"].values())
        m_data["total_score"] = weekly_total + season_score

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
        st.session_state.league_members[m].setdefault("weekly_picks", {})
        st.session_state.league_members[m].setdefault("season_picks", {})

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
          * Top 3 / Bottom 3 Sweep: 10 pts each
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
            star_badge = f"  <span style='font-size: 0.85rem;' title='Star Member High Scorer Wins'>⭐ x{star_wins}</span>" if star_wins > 0 else ""
            html_rows.append(f"<tr><td><b>{badge}</b></td><td><span class='lb-name'>{row['member']}</span>{star_badge}</td><td style='text-align: right;'><b>{row['points']} pts</b></td></tr>")
            
        st.markdown(f"""
        <table style="width: 100%; border-collapse: collapse;">
            <thead><tr><th style="width: 100px;">Rank</th><th>League Member</th><th style="text-align: right;">Total Points</th></tr></thead>
            <tbody>{''.join(html_rows)}</tbody>
        </table>
        """, unsafe_allow_html=True)

### ==============================================================================
### TAB 3: SHOW RESULTS (Visual Baker Profiles with Handshakes)
### ==============================================================================
if tab_results:
    st.header("📺 Official Broadcast Results & Visual Baker Gallery")
    
    curr_elim_all_res = eliminated_bakers_by_week.get(active_prediction_week, [])
    remaining_gallery_bakers_res = [b for b in ALL_BAKERS if b not in curr_elim_all_res]
    
    with st.expander(f"📸 Visual Baker Profiles & Season Statistics (Active Bakers - Week {active_prediction_week})", expanded=True):
        card_cols = st.columns(2)
        for idx, baker in enumerate(remaining_gallery_bakers_res):
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
                    mime="application/json"
                )
            except Exception:
                pass
        with col_bk2:
            uploaded_backup = st.file_uploader("📤 Upload / Restore League JSON Backup", type=["json"])
            if uploaded_backup is not None:
                if st.button("📥 Confirm & Restore Backup"):
                    try:
                        restored_data = json.load(uploaded_backup)
                        if isinstance(restored_data, dict):
                            st.session_state.league_members = restored_data.get("league_members", restored_data.get("league_members", {}))
                            st.session_state.weekly_results = restored_data.get("weekly_results", {})
                            st.session_state.season_results = restored_data.get("season_results", {})
                            st.session_state.disputes = restored_data.get("disputes", [])
                            save_league_data()
                            st.success("✅ League backup successfully restored!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to parse backup file: {e}")
