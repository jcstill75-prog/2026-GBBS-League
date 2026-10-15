import os
import json
import base64
import random
import datetime
import smtplib
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo
from PIL import Image
import pandas as pd
import streamlit as st

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
                    for wk_k, wk_v in data.get("weekly_results", {}).items():
                        try:
                            w_res[int(wk_k)] = wk_v
                        except Exception:
                            w_res[wk_k] = wk_v
                    data["weekly_results"] = w_res
                    
                    for m_name, m_data in data.get("league_members", {}).items():
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
        now = datetime.datetime.now(ZoneInfo("America/Chicago"))
    except Exception:
        now = datetime.datetime.now()
    weekday = now.weekday()
    if weekday == 1 and now.hour >= 14:
        return True
    return False

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
            breakdown.append((f"Bottom 3 - Exact ({pred_bot3[i]})", pts))
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

def is_week_published(w_num, weekly_results_map):
    w_key_int = int(w_num)
    w_key_str = str(w_num)
    res = weekly_results_map.get(w_key_int, weekly_results_map.get(w_key_str))
    return bool(res and isinstance(res, dict) and len(res) > 0)

def get_week_results(w_num, weekly_results_map):
    return weekly_results_map.get(int(w_num), weekly_results_map.get(str(w_num), {}))

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
    st.session_state.disputes = saved_state.get("disputes", []) if saved_state else []
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "admin_verification_msg" not in st.session_state:
    st.session_state.admin_verification_msg = ""
if "admin_deadline_override" not in st.session_state:
    st.session_state.admin_deadline_override = saved_state.get("admin_deadline_override", False) if saved_state else False
if "week_publication_timestamps" not in st.session_state:
    st.session_state.week_publication_timestamps = saved_state.get("week_publication_timestamps", {}) if saved_state else {}

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
        "winner": act_winner, "semifinalists": act_semis,
        "handshakes": total_hs_all, "crying": total_cry_all, "innuendos": total_inn_all
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

recalculate_all_scores()

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
        * **Season Winner:** 40 pts *(+15 pts Finalist Consolation)*
        * **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        * **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        * **Crying Incidents:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        * **Sexual Innuendos:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Weeks 2–7 Scoring", expanded=False):
        st.markdown("""
        * **Star Baker:** 5 pts
        * **Eliminated Baker:** 5 pts
        * **In Line Nominee:** 2 pts
        * **In Trouble Nominee:** 2 pts
        * **Technical Challenge (Top 3 & Bottom 3):**
          * Top 3 / Bottom 3 Sweep: 10 pts each
          * Exact 1st / Last Place: 3 pts
          * Exact 2nd & 3rd / 2nd-to-Last & 3rd-to-Last: 2 pts each
          * Correct Baker in Wrong Slot: 1 pt
        * **Star Member Bonus:** +5 pts to weekly high scorer
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
        """)

# --- 6. MAIN NAVIGATION TABS ---
st.title("🧁 Great British Baking Show Fantasy League 2026")
tab_lead, tab_submit, tab_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📺 Show Results", 
    "👑 Admin Panel"
])

# ==============================================================================
# TAB 1: LEADERBOARD & STANDINGS
# ==============================================================================
with tab_lead:
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
        "winner": act_winner_g, "semifinalists": act_semis_g,
        "handshakes": total_hs_g, "crying": total_cry_g, "innuendos": total_inn_g
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
            weekly_results_map = st.session_state.get("weekly_results", {})
            for w_num in sorted([int(k) for k in p_weekly.keys()]):
                w_picks = p_weekly.get(w_num, p_weekly.get(str(w_num), {}))
                w_pts = p_data.get("weekly_breakdown", {}).get(w_num, p_data.get("weekly_breakdown", {}).get(str(w_num), 0))
                with st.expander(f"Week {w_num} Ballot (Earned: {w_pts} pts)"):
                    has_published = is_week_published(w_num, weekly_results_map)
                    if not has_published:
                        st.info("💡 Actual outcomes and scoring will appear here once official broadcast results are published.")
                        sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                        inl = w_picks.get("in_line_sb", "N/A")
                        elim = format_baker_list_display(w_picks.get("eliminated", "N/A"))
                        trb = w_picks.get("in_trouble", "N/A")
                        st.write(f"🌟 **Star Baker / Champion:** {sb}")
                        st.write(f"⭐ **In Line Nominee:** {inl}")
                        st.write(f"🚪 **Eliminated:** {elim}")
                        st.write(f"⚠️ **In Trouble Nominee:** {trb}")
                    else:
                        act_w = get_week_results(w_num, weekly_results_map)
                        w_int_num = int(w_num)
                        
                        st.markdown("🔍 **Core Predictions:**")
                        if w_int_num == 10:
                            sb_pred = w_picks.get("show_champion")
                            sb_act = act_w.get("show_champion")
                            sb_pts = 15 if (sb_pred and sb_act and sb_pred == sb_act) else 0
                            pts_color = "green" if sb_pts > 0 else "gray"
                            st.markdown(f'* **Show Champion:** <span style="color: #1E88E5; font-weight: bold;">{sb_pred}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{sb_act}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{sb_pts} pts</span>', unsafe_allow_html=True)
                        else:
                            sb_pred = w_picks.get("star_baker")
                            sb_act = act_w.get("star_baker")
                            sb_pts = 5 if (sb_pred and sb_act and sb_pred == sb_act) else 0
                            pts_color = "green" if sb_pts > 0 else "gray"
                            st.markdown(f'* **Star Baker:** <span style="color: #1E88E5; font-weight: bold;">{sb_pred}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{sb_act}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{sb_pts} pts</span>', unsafe_allow_html=True)
                            
                            inl_pred = w_picks.get("in_line_sb")
                            inl_act = act_w.get("in_line_sb", [])
                            if not isinstance(inl_act, list): inl_act = [inl_act]
                            inl_pts = 2 if inl_pred in inl_act else 0
                            pts_color = "green" if inl_pts > 0 else "gray"
                            st.markdown(f'* **In Line SB:** <span style="color: #1E88E5; font-weight: bold;">{inl_pred}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{", ".join(inl_act)}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{inl_pts} pts</span>', unsafe_allow_html=True)
                            
                            act_elim = act_w.get("eliminated")
                            pred_elim = w_picks.get("eliminated")
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
                            pts_color = "green" if elim_pts > 0 else "gray"
                            st.markdown(f'* **Eliminated:** <span style="color: #1E88E5; font-weight: bold;">{format_baker_list_display(pred_elim)}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{format_baker_list_display(act_elim)}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {pts_color}; font-weight: bold;">+{elim_pts} pts</span>', unsafe_allow_html=True)
                            
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
                        if w_int_num >= 8:
                            tech_rank = w_picks.get("tech_rank", [])
                            if not isinstance(tech_rank, list): tech_rank = []
                            for idx, pred_b in enumerate(tech_rank):
                                actual_baker = act_tech_rank[idx] if idx < len(act_tech_rank) else "N/A"
                                is_match = (pred_b == actual_baker and pred_b != "--Select Baker--")
                                t_pts = 3 if (is_match and (idx == 0 or idx == len(act_tech_rank)-1)) else (2 if is_match else 0)
                                t_color = "green" if t_pts > 0 else "gray"
                                rank_str = "1st" if idx==0 else ("2nd" if idx==1 else ("3rd" if idx==2 else f"{idx+1}th"))
                                st.markdown(f'* {rank_str} Place: <span style="color: #1E88E5; font-weight: bold;">{pred_b}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {t_color}; font-weight: bold;">+{t_pts} pts</span>', unsafe_allow_html=True)
                        else:
                            act_top3 = act_tech_rank[:3] if len(act_tech_rank) >= 3 else act_tech_rank
                            act_bot3 = act_tech_rank[-3:] if len(act_tech_rank) >= 3 else act_tech_rank
                            pred_top = w_picks.get("tech_top_3", [])
                            pred_bot = w_picks.get("tech_bottom_3", [])
                            
                            st.markdown("**Top 3 Technical Challenge:**")
                            for t_idx, pred_b in enumerate(pred_top):
                                actual_baker = act_top3[t_idx] if t_idx < len(act_top3) else "N/A"
                                r_label = "1st" if t_idx==0 else ("2nd" if t_idx==1 else "3rd")
                                is_match = (pred_b == actual_baker and pred_b != "--Select Baker--")
                                t_pts = 3 if (is_match and t_idx==0) else (2 if is_match else (1 if pred_b in act_top3 else 0))
                                t_color = "green" if t_pts > 0 else "gray"
                                st.markdown(f'* {r_label} Place: <span style="color: #1E88E5; font-weight: bold;">{pred_b}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {t_color}; font-weight: bold;">+{t_pts} pts</span>', unsafe_allow_html=True)
                                
                            st.markdown("**Bottom 3 Technical Challenge:**")
                            for b_idx, pred_b in enumerate(pred_bot):
                                actual_baker = act_bot3[b_idx] if b_idx < len(act_bot3) else "N/A"
                                r_label = "3rd-to-Last" if b_idx==0 else ("2nd-to-Last" if b_idx==1 else "Last")
                                is_match = (pred_b == actual_baker and pred_b != "--Select Baker--")
                                t_pts = 3 if (is_match and b_idx==2) else (2 if is_match else (1 if pred_b in act_bot3 else 0))
                                t_color = "green" if t_pts > 0 else "gray"
                                st.markdown(f'* {r_label} Place: <span style="color: #1E88E5; font-weight: bold;">{pred_b}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{actual_baker}</span> &nbsp;&nbsp;|&nbsp;&nbsp; <span style="color: {t_color}; font-weight: bold;">+{t_pts} pts</span>', unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown(f"🏆 **Total Points Earned for Week {w_num}:** <span style='color: green; font-weight: bold; font-size: 1.1rem;'>{w_pts} pts</span>", unsafe_allow_html=True)
        else:
            st.info("No weekly prediction ballots submitted yet.")

        st.markdown("---")
        st.markdown(f"### **{selected_card_player}'s Season Projections & Results**")
        season_published = is_week_published(10, st.session_state.get("weekly_results", {}))
        
        if not season_published:
            st.markdown("🔍 **Season-Wide Projections:**")
            w_pred = p_season.get("winner", "None")
            semis_pred = format_baker_list_display(p_season.get("semifinalists", []))
            hs_pred = p_season.get("handshakes", 0)
            cry_pred = p_season.get("crying", 0)
            inn_pred = p_season.get("innuendos", 0)
            
            st.markdown(f'* **Season Winner:** <span style="color: #1E88E5; font-weight: bold;">{w_pred}</span>', unsafe_allow_html=True)
            st.markdown(f'* **Semifinalists:** <span style="color: #1E88E5; font-weight: bold;">{semis_pred}</span>', unsafe_allow_html=True)
            st.markdown(f'* **Hollywood Handshakes:** <span style="color: #1E88E5; font-weight: bold;">{hs_pred}</span>', unsafe_allow_html=True)
            st.markdown(f'* **Crying Incidents:** <span style="color: #1E88E5; font-weight: bold;">{cry_pred}</span>', unsafe_allow_html=True)
            st.markdown(f'* **Sexual Innuendos:** <span style="color: #1E88E5; font-weight: bold;">{inn_pred}</span>', unsafe_allow_html=True)
            st.info("💡 Actual outcomes and scoring will appear here once Week 10 grand finale results are published.")
        else:
            season_score_val = calculate_season_score(p_season, current_season_actuals)
            st.markdown(f"🏆 **Total Season Projection Points Earned:** <span style='color: green; font-weight: bold; font-size: 1.1rem;'>{season_score_val} pts</span>", unsafe_allow_html=True)

# ==============================================================================
# TAB 2: SUBMIT PREDICTIONS
# ==============================================================================
with tab_submit:
    st.header("📝 Submit Predictions")
    pred_player = st.selectbox("Select Your Player Profile:", ROSTER_HUMANS, key="pred_player_login_sel")
    p_info = st.session_state.league_members[pred_player]
    
    auth_key = f"auth_verified_{pred_player}"
    notice_key = f"sub_notice_{pred_player}"
    
    if notice_key in st.session_state and not st.session_state.get(auth_key, False):
        st.success(st.session_state[notice_key])
        if st.button("Dismiss Notice & Log In", key="dismiss_notice_btn"):
            del st.session_state[notice_key]
            st.rerun()

    auth_success = False
    admin_proxy_active = st.session_state.get("admin_authenticated", False)
    if admin_proxy_active:
        st.info(f"👑 **Admin Proxy Mode Available:** As the administrator, you can open and edit **{pred_player}'s** ballot directly without entering their personal PIN.")
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
            saved_weekly = p_info.get("weekly_picks", {}).get(active_prediction_week, p_info.get("weekly_picks", {}).get(str(active_prediction_week), {}))
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
                        edit_conf = st.checkbox("⚠️ Check this box to confirm you want to edit your previously submitted Week 2 Ballot & Season Projections.")

                    sub_w2 = st.form_submit_button("Submit Week 2 Ballot & Season Projections")
                    if sub_w2:
                        errors = []
                        if has_submitted and not edit_conf:
                            errors.append("❌ Please check the confirmation box to edit your previously submitted ballot.")
                        if s_win == "--Select Baker--":
                            errors.append("Please select a valid Season Winner.")
                        
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
                            send_admin_email(pred_player, 2, {"season_projections": p_info["season_picks"], "weekly_picks": weekly_picks})
                            st.session_state[notice_key] = f"✅ Success! Your Week 2 Ballot and Season Projections have been successfully submitted, emailed to admin, and locked in."
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
                            send_admin_email(pred_player, active_prediction_week, weekly_picks)
                            st.session_state[notice_key] = f"✅ Success! Your Week {active_prediction_week} Ballot has been successfully submitted, emailed to admin, and locked in."
                            st.session_state[auth_key] = False
                            st.rerun()

# ==============================================================================
# TAB 3: SHOW RESULTS
# ==============================================================================
with tab_results:
    st.header("📺 Official Broadcast Results & Visual Baker Gallery")
    
    with st.expander(f"📸 Visual Baker Profiles & Season Statistics", expanded=False):
        cols = st.columns(2)
        for idx, baker in enumerate(ALL_BAKERS):
            with cols[idx % 2]:
                st.markdown(f"""
                <div style="border: 2px solid #8D6E63; border-radius: 10px; padding: 10px; background-color: #FFF9F5; margin-bottom: 12px;">
                    <div style="background-color: #5D4037; color: white; padding: 5px 8px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 8px;">{baker}</div>
                """, unsafe_allow_html=True)
                card_col1, card_col2 = st.columns([1, 1.5])
                with card_col1:
                    b_img = load_baker_image(baker)
                    if b_img is not None:
                        st.image(b_img, use_container_width=True)
                    else:
                        st.markdown("🧁 *[Portrait]*")
                with card_col2:
                    st.markdown(f"""
                    <div style="font-size: 0.9rem; color: #3E2723; line-height: 1.5;">
                    • Star Baker Wins: <b>0</b><br>
                    • In Line Mentions: <b>0</b><br>
                    • In Trouble Mentions: <b>0</b><br>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    weekly_res_map = st.session_state.get("weekly_results", {})
    if weekly_res_map:
        st.subheader("📋 Published Weekly Results")
        sel_res_week = st.selectbox("Select Week to View Results:", sorted([int(k) for k in weekly_res_map.keys()]), key="show_res_week_sel")
        if sel_res_week:
            w_act = weekly_res_map.get(sel_res_week, weekly_res_map.get(str(sel_res_week), {}))
            st.markdown(f"### 🧁 Episode Week {sel_res_week} Results")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                if sel_res_week == 10:
                    st.write(f"🏆 **Show Champion:** {w_act.get('show_champion', 'N/A')}")
                else:
                    st.write(f"🌟 **Star Baker:** {w_act.get('star_baker', 'N/A')}")
                    inline_val = w_act.get('in_line_sb', 'N/A')
                    inline_str = ", ".join([str(b) for b in inline_val if b]) if isinstance(inline_val, list) else str(inline_val)
                    st.write(f"⭐ **'In Line' for Star Baker:** {inline_str}")
                    elim_val = w_act.get('eliminated', 'N/A')
                    elim_str = ", ".join([str(b) for b in elim_val if b]) if isinstance(elim_val, list) else str(elim_val)
                    st.write(f"🚪 **Eliminated:** {elim_str}")
                    trouble_val = w_act.get('in_trouble', 'N/A')
                    trouble_str = ", ".join([str(b) for b in trouble_val if b]) if isinstance(trouble_val, list) else str(trouble_val)
                    st.write(f"⚠️ **'In Trouble':** {trouble_str}")
            with col_res2:
                hs_bakers = w_act.get('handshake_bakers', [])
                hs_str = ", ".join([str(b) for b in hs_bakers if b]) if hs_bakers else "None"
                st.write(f"🤝 **Hollywood Handshakes:** {hs_str}")
                st.write(f"😢 **Crying Incidents ({w_act.get('crying_count', 0)}):** {w_act.get('crying_timestamps', 'None recorded')}")
                st.write(f"💬 **Sexual Innuendos ({w_act.get('innuendo_count', 0)}):** {w_act.get('innuendo_timestamps', 'None recorded')}")
            
            tech_r = w_act.get('tech_rank', [])
            if tech_r:
                st.markdown("**Technical Challenge Standings:**")
                st.write(" -> ".join([f"**#{i+1}** {b}" for i, b in enumerate(tech_r)]))
    else:
        st.info("No official broadcast results published yet by the administrator.")

    st.markdown("---")
    st.subheader("🔥 Cumulative Season Chaos Counters")
    tot_hs, tot_cry, tot_inn = 0, 0, 0
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
                st.success("Dispute submitted successfully for league review!")

    if st.session_state.get("disputes"):
        st.markdown("---")
        st.subheader("🗳️ Logged League Disputes & Status")
        for idx, d in enumerate(st.session_state.disputes):
            st.markdown(f"""
            <div style="border: 1px solid #B0BEC5; border-radius: 8px; padding: 12px; background-color: #FAFAFA; margin-bottom: 10px;">
                <b>Player:</b> {d.get('Player')} | <b>Week:</b> {d.get('Week')} | <b>Status:</b> {d.get('Status')}<br>
                <b>Evidence:</b> {d.get('Evidence')}<br>
                <b>Requested Correction:</b> {d.get('Correction')}
            </div>
            """, unsafe_allow_html=True)

# ==============================================================================
# TAB 4: ADMIN PANEL
# ==============================================================================
with tab_admin:
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
            
        admin_selected_week = st.selectbox("Select Episode Week:", list(range(1, 11)), key="adm_w_sel")
        saved_w = st.session_state.weekly_results.get(admin_selected_week, st.session_state.weekly_results.get(str(admin_selected_week), {}))
        is_published = bool(saved_w)
        
        edit_allowed = True
        if is_published:
            st.warning(f"⚠️ Week {admin_selected_week} results are already published.")
            col_unpub1, col_unpub2 = st.columns(2)
            with col_unpub1:
                edit_allowed = st.checkbox(f"Unlock Week {admin_selected_week} to edit published results", value=False, key=f"unlock_w{admin_selected_week}")
            with col_unpub2:
                if st.button(f"🗑️ Unpublish Week {admin_selected_week}", type="secondary"):
                    if admin_selected_week in st.session_state.weekly_results:
                        del st.session_state.weekly_results[admin_selected_week]
                    if str(admin_selected_week) in st.session_state.weekly_results:
                        del st.session_state.weekly_results[str(admin_selected_week)]
                    if admin_selected_week in st.session_state.week_publication_timestamps:
                        del st.session_state.week_publication_timestamps[admin_selected_week]
                    recalculate_all_scores()
                    save_league_data()
                    st.session_state.admin_verification_msg = f"✅ Week {admin_selected_week} successfully unpublished! All standings recalculated."
                    st.rerun()
            if not edit_allowed:
                st.info("Form fields are locked to protect existing historical scoring. Check the box above to enable editing.")
        
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
            
            actuals["crying_count"] = st.number_input("Number of Crying Occurrences", min_value=0, value=int(saved_w.get("crying_count", 0)), key=f"adm_cry_count_{admin_selected_week}")
            actuals["crying_timestamps"] = st.text_input("Description of Crying Occurrence", value=saved_w.get("crying_timestamps", ""), placeholder="e.g. Molly @ 14:00", key=f"adm_cry_desc_{admin_selected_week}")
            
            actuals["innuendo_count"] = st.number_input("Number of Innuendo Occurrences", min_value=0, value=int(saved_w.get("innuendo_count", 0)), key=f"adm_inn_count_{admin_selected_week}")
            actuals["innuendo_timestamps"] = st.text_input("Description of Innuendos", value=saved_w.get("innuendo_timestamps", ""), placeholder="e.g. Soggy bottom @ 18:45", key=f"adm_inn_desc_{admin_selected_week}")
            
            pub_btn = st.form_submit_button("Publish Results & Recalculate Standings")
            if pub_btn:
                if is_published and not edit_allowed:
                    st.error("❌ Week results are locked. Please check the 'Unlock to Edit' box above before publishing changes.")
                else:
                    st.session_state.weekly_results[admin_selected_week] = actuals
                    st.session_state.week_publication_timestamps[admin_selected_week] = datetime.datetime.now().isoformat()
                    recalculate_all_scores()
                    save_league_data()
                    st.session_state.admin_verification_msg = f"✅ Week {admin_selected_week} results successfully published! All scores recalculated."
                    st.rerun()

        st.markdown("---")
        st.subheader("⚖️ Resolve League Disputes")
        if st.session_state.disputes:
            for d_idx, d_item in enumerate(st.session_state.disputes):
                col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
                with col_d1:
                    st.write(f"**{d_item.get('Player')}** ({d_item.get('Week')}): {d_item.get('Correction')}")
                with col_d2:
                    r_choice = st.radio("Ruling:", ["Pending Review 🗳️", "Accepted ✅", "Rejected ❌"], index=0 if "Pending" in d_item.get('Status', '') else (1 if "Accepted" in d_item.get('Status', '') else 2), key=f"dispute_ruling_{d_idx}", horizontal=True)
                    st.session_state.disputes[d_idx]['Status'] = r_choice
                with col_d3:
                    if st.button("Save Ruling", key=f"save_ruling_{d_idx}"):
                        save_league_data()
                        st.success("Ruling saved!")
                        st.rerun()
        else:
            st.info("No active disputes logged.")

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
        st.subheader("🔑 Reset Forgotten Player Security PIN")
        human_players = [m for m in sorted(st.session_state.league_members.keys()) if m != "AI Brian"]
        reset_sel_player = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + human_players, key="admin_pin_reset_dropdown")
        if reset_sel_player != "-- Select Player --":
            if st.button(f"Reset PIN for {reset_sel_player}"):
                st.session_state.league_members[reset_sel_player]["pin"] = None
                save_league_data()
                st.success(f"Security PIN for {reset_sel_player} has been cleared!")
                st.rerun()

        st.markdown("---")
        st.subheader("📥 Download League Data Backup")
        st.write("Download a complete JSON file containing all league members, weekly results, season picks, and disputes.")
        data_payload = {
            "league_members": st.session_state.get("league_members", {}),
            "weekly_results": st.session_state.get("weekly_results", {}),
            "season_results": st.session_state.get("season_results", {}),
            "disputes": st.session_state.get("disputes", []),
            "admin_deadline_override": st.session_state.get("admin_deadline_override", False),
            "week_publication_timestamps": st.session_state.get("week_publication_timestamps", {})
        }
        json_backup_str = json.dumps(data_payload, indent=2)
        st.download_button(
            label="📥 Download Full League JSON Backup",
            data=json_backup_str,
            file_name="gbbs_league_backup.json",
            mime="application/json",
        )

        st.markdown("---")
        st.subheader("📤 Upload & Restore League JSON Backup")
        st.write("Upload a previously saved `gbbs_league_backup.json` file to restore all player predictions and league results.")
        uploaded_backup = st.file_uploader("Upload JSON Backup File", type=["json"], key="backup_json_uploader")
        if uploaded_backup is not None:
            if st.button("Confirm & Restore Uploaded Data", type="primary"):
                try:
                    imported_data = json.load(uploaded_backup)
                    if isinstance(imported_data, dict):
                        if "league_members" in imported_data:
                            st.session_state.league_members = imported_data["league_members"]
                        if "weekly_results" in imported_data:
                            w_res = {}
                            for k, v in imported_data["weekly_results"].items():
                                try:
                                    w_res[int(k)] = v
                                except Exception:
                                    w_res[k] = v
                            st.session_state.weekly_results = w_res
                        if "season_results" in imported_data:
                            st.session_state.season_results = imported_data["season_results"]
                        if "disputes" in imported_data:
                            st.session_state.disputes = imported_data["disputes"]
                        if "admin_deadline_override" in imported_data:
                            st.session_state.admin_deadline_override = imported_data["admin_deadline_override"]
                        if "week_publication_timestamps" in imported_data:
                            st.session_state.week_publication_timestamps = imported_data["week_publication_timestamps"]
                        save_league_data()
                        recalculate_all_scores()
                        st.success("✅ League data successfully restored from uploaded JSON backup!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid JSON format: Root element must be a dictionary.")
                except Exception as e:
                    st.error(f"❌ Failed to parse JSON file: {e}")

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
