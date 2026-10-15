import streamlit as st
import pandas as pd
import random
import os
import json
import base64
import datetime
import smtplib
from email.mime.text import MIMEText
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
                breakdown.
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
                            st.markdown(f'* **In Line SB:** <span style="color: #1E88E5; font-weight: bold;">{inl_pred}</span> | Actual: <span style="color: #B54E43; font-weight: bold;">{",
