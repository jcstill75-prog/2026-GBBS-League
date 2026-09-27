import streamlit as st
import pandas as pd
import random
from PIL import Image
import io
import os
import json

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for high contrast and cozy baking theme
st.markdown("""
<style>
    .reportview-container {
        background: #FFF9F2;
    }
    .stButton>button {
        background-color: #D36B5F;
        color: white !important;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #B54E43;
        color: white !important;
    }
    h1, h2, h3 {
        color: #5D4037;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ENGINE ---
DATA_FILE = "league_data.json"

def save_league_data():
    data_to_save = {
        "league_members": st.session_state.get("league_members", {}),
        "weekly_results": st.session_state.get("weekly_results", {}),
        "season_results": st.session_state.get("season_results", {}),
        "disputes": st.session_state.get("disputes", []),
        "player_pins": st.session_state.get("player_pins", {})
    }
    try:
        clean_members = {}
        for name, mdata in data_to_save["league_members"].items():
            clean_members[name] = {
                "weekly_picks": mdata.get("weekly_picks", {}),
                "season_picks": mdata.get("season_picks", {}),
                "total_score": mdata.get("total_score", 0),
                "weekly_breakdown": mdata.get("weekly_breakdown", {})
            }
        data_to_save["league_members"] = clean_members
        
        # Normalize weekly_results keys to string
        clean_weekly = {}
        for w, act in data_to_save["weekly_results"].items():
            clean_weekly[str(w)] = act
        data_to_save["weekly_results"] = clean_weekly
        
        with open(DATA_FILE, "w") as f:
            json.dump(data_to_save, f, indent=4)
    except Exception:
        pass

def load_league_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data
        except Exception:
            return None
    return None

saved_data = load_league_data()

# --- 3. ROSTERS & INITIALIZATION ---
ALL_BAKERS = [
    "Clara", "Connie", "Danni", "Gabe", "Gary", "Mo", 
    "Molly", "Moyin", "Nikki", "Shannon", "Tom", "Yannis"
]

BAKER_INFO = {
    "Clara": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-clara/"},
    "Connie": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-connie/"},
    "Danni": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-danni/"},
    "Gabe": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-gabe/"},
    "Gary": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-gary/"},
    "Mo": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-mo/"},
    "Molly": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-molly/"},
    "Moyin": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-moyin/"},
    "Nikki": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-nikki/"},
    "Shannon": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-shannon/"},
    "Tom": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-tom/"},
    "Yannis": {"url": "https://thegreatbritishbakeoff.co.uk/bakers/series-17-yannis/"}
}

HUMAN_PLAYERS = [
    "Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", 
    "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", 
    "Taliah", "Tressa"
]

ALL_HUMANS_AND_AI = sorted(HUMAN_PLAYERS) + ["AI Brian"]

def normalize_dict_keys(d):
    clean = {}
    if isinstance(d, dict):
        for k, v in d.items():
            try:
                clean[int(k)] = v
            except (ValueError, TypeError):
                clean[k] = v
    return clean

if "league_members" not in st.session_state:
    if saved_data and "league_members" in saved_data:
        st.session_state.league_members = saved_data["league_members"]
    else:
        st.session_state.league_members = {}
        for name in ALL_HUMANS_AND_AI:
            st.session_state.league_members[name] = {
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {}
            }

for name in ALL_HUMANS_AND_AI:
    if name not in st.session_state.league_members:
        st.session_state.league_members[name] = {
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {}
        }
    m = st.session_state.league_members[name]
    m["weekly_picks"] = normalize_dict_keys(m.get("weekly_picks", {}))
    m["weekly_breakdown"] = normalize_dict_keys(m.get("weekly_breakdown", {}))

if "weekly_results" not in st.session_state:
    raw_w = saved_data.get("weekly_results", {}) if saved_data else {}
    st.session_state.weekly_results = normalize_dict_keys(raw_w)
else:
    st.session_state.weekly_results = normalize_dict_keys(st.session_state.weekly_results)

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_data.get("season_results", {}) if saved_data else {}

if "disputes" not in st.session_state:
    st.session_state.disputes = saved_data.get("disputes", []) if saved_data else []

if "player_pins" not in st.session_state:
    st.session_state.player_pins = saved_data.get("player_pins", {}) if saved_data else {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

# Automatic week determination
scored_weeks = sorted([w for w in st.session_state.weekly_results.keys() if isinstance(w, int)])
active_week = max(scored_weeks) + 1 if scored_weeks else 1
if active_week > 10: active_week = 10
st.session_state.current_week = active_week

# --- 4. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=1):
    score = 0
    if not predictions or not actuals:
        return 0
        
    if week == 10:
        pred_champion = predictions.get("show_champion")
        act_champion = actuals.get("show_champion")
        if pred_champion and act_champion and pred_champion == act_champion:
            score += 15
    else:
        if predictions.get("star_baker") == actuals.get("star_baker") and predictions.get("star_baker") is not None:
            score += 5
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim:
                        score += 5
            elif isinstance(pred_elim, str):
                if pred_elim in act_elim:
                    score += 5
        elif act_elim == "None":
            pass
        else:
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim == act_elim and pred_elim is not None:
                score += 5
                
    # Technical scoring
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            if pred_rank == act_rank:
                score += 25
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 4]: score += 3
                        else: score += 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            if pred_rank == act_rank:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx in [0, 3]: score += 3
                        else: score += 2
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            if pred_rank == act_rank:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        if idx == 0: score += 3
                        else: score += 2
    else:
        pred_top3 = predictions.get("tech_top_3", [])
        act_top3 = actuals.get("tech_top_3", [])
        if len(pred_top3) == 3 and len(act_top3) == 3:
            if pred_top3 == act_top3:
                score += 10
            else:
                if pred_top3[0] == act_top3[0]: score += 3
                if pred_top3[1] == act_top3[1]: score += 2
                if pred_top3[2] == act_top3[2]: score += 2
                for idx, b in enumerate(pred_top3):
                    if b in act_top3 and b != act_top3[idx]: score += 1
                    
        pred_bot3 = predictions.get("tech_bottom_3", [])
        act_bot3 = actuals.get("tech_bottom_3", [])
        if len(pred_bot3) == 3 and len(act_bot3) == 3:
            if pred_bot3 == act_bot3:
                score += 10
            else:
                if pred_bot3[0] == act_bot3[0]: score += 2
                if pred_bot3[1] == act_bot3[1]: score += 2
                if pred_bot3[2] == act_bot3[2]: score += 3
                for idx, b in enumerate(pred_bot3):
                    if b in act_bot3 and b != act_bot3[idx]: score += 1

    if week < 9:
        if predictions.get("in_line_sb") and predictions.get("in_line_sb") in actuals.get("in_line_sb", []) and predictions.get("in_line_sb") != actuals.get("star_baker"):
            score += 2
        if predictions.get("in_trouble") and predictions.get("in_trouble") in actuals.get("in_trouble", []) and predictions.get("in_trouble") != actuals.get("eliminated"):
            score += 2

    return score

def calculate_season_score(predictions, actuals):
    score = 0
    if not predictions or not actuals:
        return 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner == act_winner and pred_winner:
        score += 40
    elif pred_winner in act_finalists and pred_winner:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    for b in pred_semis:
        if b in act_semis and b != pred_winner:
            score += 10
            
    p_hs = predictions.get("handshakes")
    a_hs = actuals.get("handshakes")
    if p_hs is not None and a_hs is not None:
        if p_hs == a_hs: score += 20
        elif abs(p_hs - a_hs) <= 1: score += 10
        
    p_cry = predictions.get("crying")
    a_cry = actuals.get("crying")
    if p_cry is not None and a_cry is not None:
        if p_cry == a_cry: score += 20
        elif abs(p_cry - a_cry) <= 5: score += 10
        
    p_inn = predictions.get("innuendos")
    a_inn = actuals.get("innuendos")
    if p_inn is not None and a_inn is not None:
        if p_inn == a_inn: score += 20
        elif abs(p_inn - a_inn) <= 5: score += 10
        
    return score

def load_baker_image(baker_name):
    if not os.path.exists("assets"):
        return None
    target = baker_name.lower().strip()
    try:
        for filename in os.listdir("assets"):
            stem, ext = os.path.splitext(filename)
            if stem.lower().strip() == target and ext.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                return Image.open(os.path.join("assets", filename))
    except Exception:
        pass
    return None

def get_current_eliminated_bakers(target_week):
    elim = []
    for w in sorted([k for k in st.session_state.weekly_results.keys() if isinstance(k, int)]):
        if w <= target_week:
            act = st.session_state.weekly_results[w]
            e_val = act.get("eliminated")
            if isinstance(e_val, list):
                for b in e_val:
                    if b and b != "None" and b not in elim: elim.append(b)
            elif isinstance(e_val, str) and e_val and e_val != "None":
                if e_val not in elim: elim.append(e_val)
    return elim

def generate_ai_brian_season_picks():
    winner = random.choice(ALL_BAKERS)
    semis = random.sample([b for b in ALL_BAKERS if b != winner], 3)
    return {
        "winner": winner,
        "semifinalists": semis,
        "handshakes": random.randint(1, 10),
        "crying": random.randint(5, 25),
        "innuendos": random.randint(20, 65)
    }

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    if week == 10:
        return {
            "show_champion": random.choice(active_bakers),
            "tech_rank": random.sample(active_bakers, len(active_bakers))
        }
    elif week == 9:
        sb = random.choice(active_bakers)
        pool = [b for b in active_bakers if b != sb]
        el = random.sample(pool, min(2, len(pool))) if is_double_elim else (random.choice(pool) if pool else active_bakers[0])
        return {"star_baker": sb, "eliminated": el, "tech_rank": random.sample(active_bakers, len(active_bakers))}
    elif week == 8:
        sb = random.choice(active_bakers)
        pool = [b for b in active_bakers if b != sb]
        el = random.sample(pool, min(2, len(pool))) if is_double_elim else (random.choice(pool) if pool else active_bakers[0])
        inl = random.choice(pool) if pool else active_bakers[0]
        trb_pool = [b for b in active_bakers if b not in (el if isinstance(el, list) else [el])]
        trb = random.choice(trb_pool) if trb_pool else active_bakers[0]
        return {"star_baker": sb, "eliminated": el, "tech_rank": random.sample(active_bakers, len(active_bakers)), "in_line_sb": inl, "in_trouble": trb}
    else:
        sb = random.choice(active_bakers)
        pool = [b for b in active_bakers if b != sb]
        el = random.sample(pool, min(2, len(pool))) if is_double_elim else (random.choice(pool) if pool else active_bakers[0])
        t3 = random.sample(active_bakers, min(3, len(active_bakers)))
        b3_pool = [b for b in active_bakers if b not in t3]
        b3 = random.sample(b3_pool, min(3, len(b3_pool))) if len(b3_pool) >= 3 else t3
        inl = random.choice(pool) if pool else active_bakers[0]
        trb_pool = [b for b in active_bakers if b not in (el if isinstance(el, list) else [el])]
        trb = random.choice(trb_pool) if trb_pool else active_bakers[0]
        return {"star_baker": sb, "eliminated": el, "tech_top_3": t3, "tech_bottom_3": b3, "in_line_sb": inl, "in_trouble": trb}

if not st.session_state.league_members["AI Brian"]["season_picks"]:
    st.session_state.league_members["AI Brian"]["season_picks"] = generate_ai_brian_season_picks()

# --- SIDEBAR: POINTS REFERENCE GUIDE ONLY ---
with st.sidebar:
    st.header("🎯 Points Reference Guide")
    st.write("A persistent reminder of what points are at stake for each prediction!")
    st.warning("⏰ **Weekly voting window ends on Tuesdays right before the show airs in the UK.**")
    
    with st.expander("🌟 Season-Long Projections", expanded=False):
        st.markdown("""
        *   **Season Winner:** 40 pts
        *   **Finalist Consolation:** 15 pts *(if picked winner makes Top 3 but loses)*
        *   **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        *   **Handshakes Count:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        *   **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        *   **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Standard Weeks (Weeks 1-7)", expanded=False):
        st.markdown("""
        *   **Star Baker:** 5 pts
        *   **Eliminated Baker:** 5 pts
        *   **In Line (Star Baker consolation):** 2 pts
        *   **In Trouble (Elimination consolation):** 2 pts
        *   **Top 3 Technical Challenge:**
            *   *Exact:* 3 pts for 1st, 2 pts for 2nd/3rd
            *   *Wrong Spot:* 1 pt for any correct Top 3 baker
            *   *Combo Sweep:* **10 pts** *(flat)*
        *   **Bottom 3 Technical Challenge:**
            *   *Exact:* 2 pts for 9th/10th, 3 pts for 11th
            *   *Wrong Spot:* 1 pt for any correct Bottom 3 baker
            *   *Combo Sweep:* **10 pts** *(flat)*
        *   **Star League Member:** +5 pts *(weekly high scorer)*
        """)
        
    with st.expander("🏁 Weeks 8, 9 & 10 (Dynamic Scaling)", expanded=False):
        st.markdown("""
        *   **Week 8 (Quarterfinal episodic - 5 bakers):**
            *   *Star Baker:* 5 pts | *Eliminated:* 5 pts | *Technical:* 1st/5th (3 pts), 2nd/3rd/4th (2 pts) | *Perfect Sweep:* **25 pts**
        *   **Week 9 (Semifinal episodic - 4 bakers):**
            *   *Star Baker:* 5 pts | *Eliminated:* 5 pts | *Technical:* 1st/4th (3 pts), 2nd/3rd (2 pts) | *Perfect Sweep:* **20 pts**
        *   **Week 10 (Grand Finale episodic - 3 bakers):**
            *   *Show Champion:* 15 pts | *Technical:* 1st (3 pts), 2nd/3rd (2 pts) | *Perfect Sweep:* **15 pts**
        """)

# --- MAIN TABS ---
tab_lead, tab_submit, tab_show_results, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📺 Show Results",
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    
    sorted_members = sorted(
        st.session_state.league_members.items(),
        key=lambda item: item[1].get("total_score", 0),
        reverse=True
    )
    
    lb_rows = []
    for idx, (name, data) in enumerate(sorted_members, start=1):
        rank_badge = "🥇 #1" if idx == 1 else ("🥈 #2" if idx == 2 else ("🥉 #3" if idx == 3 else f"#{idx}"))
        tot_pts = data.get("total_score", 0)
        lb_rows.append({
            "Rank": rank_badge,
            "League Member": name,
            "Total Points": f"{tot_pts} pts"
        })
        
    df_lb = pd.DataFrame(lb_rows)
    st.dataframe(df_lb, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📋 Individual Player Scorecards & Projections")
    
    selected_sc_player = st.selectbox("Select Player Scorecard to View:", ALL_HUMANS_AND_AI, key="sc_player_select")
    p_data = st.session_state.league_members.get(selected_sc_player, {})
    p_pts = p_data.get("total_score", 0)
    p_season = p_data.get("season_picks", {})
    p_weekly = p_data.get("weekly_picks", {})
    
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        st.markdown(f"### **{selected_sc_player}'s Season Projections**")
        win_pick = p_season.get("winner", "Not submitted yet")
        semis_pick = ", ".join(p_season.get("semifinalists", [])) if p_season.get("semifinalists") else "Not submitted yet"
        hs_pick = p_season.get("handshakes", "N/A")
        cry_pick = p_season.get("crying", "N/A")
        inn_pick = p_season.get("innuendos", "N/A")
        
        st.write(f"🏆 **Predicted Winner:** {win_pick}")
        st.write(f"🏅 **Predicted Semifinalists:** {semis_pick}")
        st.write(f"🤝 **Predicted Handshakes:** {hs_pick} | 😢 **Crying:** {cry_pick} | 💬 **Innuendos:** {inn_pick}")
        
    with col_sc2:
        st.markdown(f"### **{selected_sc_player}'s Weekly Predictions Log**")
        if p_weekly:
            w_rows = []
            for w_num in sorted(p_weekly.keys()):
                w_picks = p_weekly[w_num]
                sb = w_picks.get("star_baker", w_picks.get("show_champion", "N/A"))
                el = w_picks.get("eliminated", "N/A")
                if isinstance(el, list): el = ", ".join(el)
                t_rank = w_picks.get("tech_rank", [])
                if t_rank:
                    t_str = ", ".join(t_rank)
                else:
                    t_top = ", ".join(w_picks.get("tech_top_3", [])) if w_picks.get("tech_top_3") else "N/A"
                    t_bot = ", ".join(w_picks.get("tech_bottom_3", [])) if w_picks.get("tech_bottom_3") else "N/A"
                    t_str = f"Top 3: [{t_top}] | Bottom 3: [{t_bot}]"
                
                w_rows.append({
                    "Week": f"Week {w_num}",
                    "Star Baker Pick": sb,
                    "Eliminated Pick": el,
                    "Technical Pick": t_str
                })
            st.dataframe(pd.DataFrame(w_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No weekly prediction ballots submitted yet.")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Predictions")
    
    with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
        current_elim_gallery = get_current_eliminated_bakers(st.session_state.current_week)
        active_gallery_bakers = [b for b in ALL_BAKERS if b not in current_elim_gallery]
        cols = st.columns(4)
        for idx, baker in enumerate(active_gallery_bakers):
            info = BAKER_INFO.get(baker, {"url": "#"})
            with cols[idx % 4]:
                img = load_baker_image(baker)
                if img is not None:
                    st.image(img, use_container_width=True)
                    st.markdown(f"**{baker}**")
                else:
                    st.markdown(f"**{baker}**")
                    st.markdown(f"[🔗 View Photo Page]({info['url']})")

    st.markdown("---")
    sel_player = st.selectbox("Select Your Name / Player Profile:", ["-- Select Your Name --"] + HUMAN_PLAYERS)
    
    if sel_player != "-- Select Your Name --":
        saved_pin = st.session_state.player_pins.get(sel_player)
        authenticated = st.session_state.authenticated_players.get(sel_player, False)
        
        if not authenticated:
            if not saved_pin:
                st.info(f"🔒 First-time setup for **{sel_player}**: Please create a 4-digit security PIN to protect your predictions!")
                p1 = st.text_input("Create 4-Digit PIN:", type="password", key=f"create_pin_{sel_player}")
                p2 = st.text_input("Confirm 4-Digit PIN:", type="password", key=f"confirm_pin_{sel_player}")
                if st.button("Set PIN & Unlock Ballot"):
                    if len(p1) == 4 and p1.isdigit() and p1 == p2:
                        st.session_state.player_pins[sel_player] = p1
                        st.session_state.authenticated_players[sel_player] = True
                        save_league_data()
                        st.success("4-digit PIN set successfully!")
                        st.rerun()
                    else:
                        st.error("PINs must be exactly 4 digits and match!")
            else:
                entered_pin = st.text_input(f"Enter 4-Digit PIN for **{sel_player}**:", type="password", key=f"login_pin_{sel_player}")
                if st.button("Unlock Prediction Ballot"):
                    if entered_pin == saved_pin:
                        st.session_state.authenticated_players[sel_player] = True
                        st.success(f"🔓 Authenticated as **{sel_player}**!")
                        st.rerun()
                    else:
                        st.error("Incorrect 4-digit PIN!")
        else:
            st.success(f"🔓 Authenticated as **{sel_player}**!")
            if st.button("🔒 Lock Ballot / Log Out Profile"):
                st.session_state.authenticated_players[sel_player] = False
                st.rerun()
                
            st.markdown("---")
            
            # Post-Week 1 / Scouting Phase Season-Long Predictions Form
            if st.session_state.current_week == 1 or st.session_state.current_week == 2:
                with st.expander("🌟 Submit Post-Week 1 Season-Long Predictions (Locks Post-Week 1! | 130 pts total)", expanded=True):
                    existing_s = st.session_state.league_members[sel_player].get("season_picks", {})
                    s_win = st.selectbox("Predict Season Winner [40 pts]", ["--Select Baker--"] + ALL_BAKERS, index=["--Select Baker--"] + ALL_BAKERS.index(existing_s.get("winner")) if existing_s.get("winner") in ALL_BAKERS else 0, key=f"s_win_{sel_player}")
                    s_semis = st.multiselect("Predict Other 3 Semifinalists [10 pts each]", [b for b in ALL_BAKERS if b != s_win], default=[b for b in existing_s.get("semifinalists", []) if b in ALL_BAKERS and b != s_win], max_selections=3, key=f"s_semis_{sel_player}")
                    s_hs = st.number_input("Predict Seasonal Handshakes [20 pts spot-on]", min_value=0, value=existing_s.get("handshakes", 5), key=f"s_hs_{sel_player}")
                    s_cry = st.number_input("Predict Seasonal Crying Incidents [20 pts spot-on]", min_value=0, value=existing_s.get("crying", 12), key=f"s_cry_{sel_player}")
                    s_inn = st.number_input("Predict Seasonal Innuendos [20 pts spot-on]", min_value=0, value=existing_s.get("innuendos", 40), key=f"s_inn_{sel_player}")
                    
                    if st.button("Lock Season-Long Predictions"):
                        if s_win == "--Select Baker--" or len(s_semis) != 3:
                            st.error("Please select a valid Season Winner and exactly 3 other semifinalists!")
                        else:
                            st.session_state.league_members[sel_player]["season_picks"] = {
                                "winner": s_win,
                                "semifinalists": s_semis,
                                "handshakes": s_hs,
                                "crying": s_cry,
                                "innuendos": s_inn
                            }
                            save_league_data()
                            st.success("Season-long projections saved successfully!")

            st.markdown(f"### 📅 Submit Episodic Predictions: Week {st.session_state.current_week}")
            current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            baker_opts = ["--Select Baker--"] + active_bakers
            
            is_double_elim = st.checkbox("📢 Double-Elimination Week?", value=False, key=f"chk_dbl_elim_w{st.session_state.current_week}_{sel_player}")
            
            with st.form(f"weekly_ballot_w{st.session_state.current_week}_{sel_player}"):
                p_picks = {}
                if st.session_state.current_week == 10:
                    p_picks["show_champion"] = st.selectbox("Predict Show Champion [15 pts]", baker_opts, key=f"p_champ_w10_{sel_player}")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key=f"p_t1_w10_{sel_player}")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key=f"p_t2_w10_{sel_player}")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key=f"p_t3_w10_{sel_player}")
                    p_picks["tech_rank"] = [t1, t2, t3]
                elif st.session_state.current_week == 9:
                    p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts, key=f"p_sb_w9_{sel_player}")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key=f"p_e1_w9_{sel_player}")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key=f"p_e2_w9_{sel_player}")
                        p_picks["eliminated"] = [e1, e2]
                    else:
                        p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, key=f"p_e_w9_{sel_player}")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key=f"p_t1_w9_{sel_player}")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key=f"p_t2_w9_{sel_player}")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key=f"p_t3_w9_{sel_player}")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", baker_opts, key=f"p_t4_w9_{sel_player}")
                    p_picks["tech_rank"] = [t1, t2, t3, t4]
                elif st.session_state.current_week == 8:
                    p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts, key=f"p_sb_w8_{sel_player}")
                    p_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts, key=f"p_inline_w8_{sel_player}")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key=f"p_e1_w8_{sel_player}")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key=f"p_e2_w8_{sel_player}")
                        p_picks["eliminated"] = [e1, e2]
                    else:
                        p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, key=f"p_e_w8_{sel_player}")
                    p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_opts, key=f"p_tr_w8_{sel_player}")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key=f"p_t1_w8_{sel_player}")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key=f"p_t2_w8_{sel_player}")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key=f"p_t3_w8_{sel_player}")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", baker_opts, key=f"p_t4_w8_{sel_player}")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", baker_opts, key=f"p_t5_w8_{sel_player}")
                    p_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                else:
                    p_picks["star_baker"] = st.selectbox("Predict Star Baker [5 pts]", baker_opts, key=f"p_sb_std_{sel_player}")
                    p_picks["in_line_sb"] = st.selectbox("Predict In Line for Star Baker [2 pts]", baker_opts, key=f"p_inline_std_{sel_player}")
                    if is_double_elim:
                        e1 = st.selectbox("Predict Eliminated Baker #1 [5 pts]", baker_opts, key=f"p_e1_std_{sel_player}")
                        e2 = st.selectbox("Predict Eliminated Baker #2 [5 pts]", baker_opts, key=f"p_e2_std_{sel_player}")
                        p_picks["eliminated"] = [e1, e2]
                    else:
                        p_picks["eliminated"] = st.selectbox("Predict Eliminated Baker [5 pts]", baker_opts, key=f"p_e_std_{sel_player}")
                    p_picks["in_trouble"] = st.selectbox("Predict In Trouble [2 pts]", baker_opts, key=f"p_tr_std_{sel_player}")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", baker_opts, key=f"p_t1_std_{sel_player}")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", baker_opts, key=f"p_t2_std_{sel_player}")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", baker_opts, key=f"p_t3_std_{sel_player}")
                    tb1 = st.selectbox("Technical 3rd-to-Last Place [2 pts]", baker_opts, key=f"p_tb1_std_{sel_player}")
                    tb2 = st.selectbox("Technical 2nd-to-Last Place [2 pts]", baker_opts, key=f"p_tb2_std_{sel_player}")
                    tb3 = st.selectbox("Technical Last Place [3 pts]", baker_opts, key=f"p_tb3_std_{sel_player}")
                    p_picks["tech_top_3"] = [t1, t2, t3]
                    p_picks["tech_bottom_3"] = [tb1, tb2, tb3]
                    
                sub_ballot = st.form_submit_button("Submit Prediction Ballot")
                if sub_ballot:
                    m_selections = []
                    for k in ["star_baker", "in_line_sb", "in_trouble", "show_champion"]:
                        if k in p_picks and p_picks[k] != "--Select Baker--": m_selections.append(p_picks[k])
                    if "eliminated" in p_picks:
                        ev = p_picks["eliminated"]
                        if isinstance(ev, list):
                            for item in ev:
                                if item != "--Select Baker--": m_selections.append(item)
                        elif ev != "--Select Baker--": m_selections.append(ev)
                        
                    t_selections = [t for t in p_picks.get("tech_rank", []) if t != "--Select Baker--"] + [t for t in p_picks.get("tech_top_3", []) + p_picks.get("tech_bottom_3", []) if t != "--Select Baker--"]
                    
                    if "--Select Baker--" in (m_selections + t_selections):
                        st.error("⚠️ Please select a valid baker for all prediction fields!")
                    elif len(m_selections) != len(set(m_selections)):
                        st.error("❌ Duplicate Selection Error: You may not select the same baker more than once across Star Baker, In Line, In Trouble, and Eliminated!")
                    elif len(t_selections) != len(set(t_selections)):
                        st.error("❌ Duplicate Selection Error: A baker may not be selected more than once across your Technical Challenge predictions!")
                    else:
                        st.session_state.league_members[sel_player]["weekly_picks"][st.session_state.current_week] = p_picks
                        ai_picks = generate_ai_brian_weekly_picks(st.session_state.current_week, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][st.session_state.current_week] = ai_picks
                        save_league_data()
                        st.success(f"Predictions submitted successfully for {sel_player} (Week {st.session_state.current_week})! AI Brian also submitted his picks.")

# --- TAB 3: SHOW RESULTS ---
with tab_show_results:
    st.header("📺 Show Results & Broadcast Archive")
    
    # 1. CHAOS CATEGORIES RUNNING TOTALS
    st.subheader("🔥 Chaos Categories Running Totals")
    tot_hs = 0
    tot_cry = 0
    tot_inn = 0
    for w, act in st.session_state.weekly_results.items():
        if isinstance(act, dict):
            tot_hs += act.get("handshake_count", len(act.get("handshake_bakers", [])))
            tot_cry += act.get("crying_count", 0)
            tot_inn += act.get("innuendo_count", 0)
            
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1: st.metric("🤝 Total Hollywood Handshakes", f"{tot_hs}")
    with col_c2: st.metric("😢 Total Crying Incidents", f"{tot_cry}")
    with col_c3: st.metric("💬 Total Sexual Innuendos", f"{tot_inn}")
    
    st.markdown("---")
    # 2. WEEKLY BROADCAST RESULTS BREAKDOWN
    st.subheader("📅 Weekly Broadcast Results Breakdown")
    
    if not st.session_state.weekly_results:
        st.info("No broadcast results published yet. Results will appear here as Episode results are recorded in the Admin Panel!")
    else:
        for w_num in sorted([k for k in st.session_state.weekly_results.keys() if isinstance(k, int)]):
            w_act = st.session_state.weekly_results[w_num]
            with st.expander(f"📺 Episode Results: Week {w_num}", expanded=(w_num == max(st.session_state.weekly_results.keys()))):
                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    sb_val = w_act.get("star_baker", w_act.get("show_champion", "N/A"))
                    st.write(f"🌟 **Star Baker / Champion:** `{sb_val}`")
                    inl_val = ", ".join(w_act.get("in_line_sb", [])) if isinstance(w_act.get("in_line_sb"), list) else w_act.get("in_line_sb", "None")
                    st.write(f"📈 **In Line Nominees:** `{inl_val}`")
                with col_w2:
                    el_val = ", ".join(w_act.get("eliminated")) if isinstance(w_act.get("eliminated"), list) else w_act.get("eliminated", "None")
                    st.write(f"🚪 **Eliminated Baker(s):** `{el_val}`")
                    trb_val = ", ".join(w_act.get("in_trouble", [])) if isinstance(w_act.get("in_trouble"), list) else w_act.get("in_trouble", "None")
                    st.write(f"⚠️ **In Trouble Nominees:** `{trb_val}`")
                    
                st.markdown("#### **📊 Technical Challenge Placements:**")
                t_ranks = w_act.get("tech_rank", [])
                if t_ranks:
                    t_formatted = []
                    for idx_pos, baker_name in enumerate(t_ranks, start=1):
                        badge = "🥇 1st Place" if idx_pos == 1 else ("🥈 2nd Place" if idx_pos == 2 else ("🥉 3rd Place" if idx_pos == 3 else f"{idx_pos}th Place"))
                        t_formatted.append(f"**{badge}:** {baker_name}")
                    st.write(" | ".join(t_formatted))
                else:
                    t_top = ", ".join(w_act.get("tech_top_3", [])) if w_act.get("tech_top_3") else "N/A"
                    t_bot = ", ".join(w_act.get("tech_bottom_3", [])) if w_act.get("tech_bottom_3") else "N/A"
                    st.write(f"**Top 3 Technical:** {t_top} | **Bottom 3 Technical:** {t_bot}")
                    
                st.markdown("#### **🤝 Hollywood Handshakes, Crying & Innuendos Log:**")
                hs_cnt = w_act.get("handshake_count", len(w_act.get("handshake_bakers", [])))
                hs_bk = ", ".join(w_act.get("handshake_bakers", [])) if w_act.get("handshake_bakers") else "None"
                st.write(f"🤝 **Handshakes:** `{hs_cnt}` ({hs_bk}) | **Notes:** {w_act.get('handshake_timestamps', 'N/A')}")
                st.write(f"😢 **Crying Incidents:** `{w_act.get('crying_count', 0)}` | **Notes:** {w_act.get('crying_timestamps', 'N/A')}")
                st.write(f"💬 **Sexual Innuendos:** `{w_act.get('innuendo_count', 0)}` | **Notes:** {w_act.get('innuendo_timestamps', 'N/A')}")

    # 3. RESULT DISPUTES & TIMESTAMP CORRECTIONS
    st.markdown("---")
    st.subheader("⚖️ Broadcast Result Disputes & Timestamp Corrections")
    st.write("If you spot an error, missed handshake, or unrecorded crying scene in an episode, submit a dispute below with video timestamp evidence. Disputes are reviewed democratically by league members on GroupMe via majority vote.")

    with st.expander("📝 Submit a Result Dispute / Timestamp Correction", expanded=False):
        with st.form("dispute_form"):
            disp_player = st.selectbox("Your Name / Player Profile", HUMAN_PLAYERS)
            disp_week = st.selectbox("Week to Contest", [f"Week {w}" for w in sorted([k for k in st.session_state.weekly_results.keys() if isinstance(k, int)])] if st.session_state.weekly_results else ["Week 1"])
            disp_cat = st.selectbox("Category Contested", [
                "Hollywood Handshake Count / Recipient",
                "Crying Scene Timestamp",
                "Sexual Innuendo Count",
                "Technical Challenge Placement",
                "Star Baker / Elimination Selection"
            ])
            disp_evidence = st.text_area("Video Timestamp & Video Evidence")
            disp_correction = st.text_input("Requested Correction")

            sub_disp = st.form_submit_button("Submit Dispute for League Vote")
            if sub_disp:
                st.session_state.disputes.append({
                    "Player": disp_player,
                    "Week": disp_week,
                    "Category": disp_cat,
                    "Evidence": disp_evidence,
                    "Correction": disp_correction,
                    "Status": "Pending GroupMe Vote 🗳️"
                })
                save_league_data()
                st.success("Dispute submitted successfully! It has been logged below for democratic GroupMe review.")

    if st.session_state.disputes:
        st.subheader("📋 Active Contestations & Dispute Log")
        st.dataframe(pd.DataFrame(st.session_state.disputes), hide_index=True, use_container_width=True)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if st.session_state.get("data_erased_confirmation"):
        st.success("✅ **All competition data, predictions, broadcast actuals, disputes, and player PINs have been permanently erased!**")
        st.session_state["data_erased_confirmation"] = False
        
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Console is Password Protected**")
        admin_pin_input = st.text_input("Enter Administrator Security PIN (6284)", type="password", key="admin_pin_field")
        if st.button("Unlock Admin Panel"):
            if admin_pin_input == "6284":
                st.session_state.admin_authenticated = True
                st.success("Administrator Console Unlocked!")
                st.rerun()
            else:
                st.error("Incorrect Admin Security PIN!")
    else:
        st.success("🔓 **Authenticated as League Administrator**")
        if st.button("🔒 Lock Admin Console"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.markdown("---")
        with st.expander("🔑 Player Security PIN Reset Console", expanded=False):
            p_to_reset = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + HUMAN_PLAYERS)
            if p_to_reset != "-- Select Player --":
                cur_status = "Set 🔒" if st.session_state.player_pins.get(p_to_reset) else "Unset 🔓"
                st.write(f"Current PIN status for **{p_to_reset}**: `{cur_status}`")
                if st.button(f"Reset 4-Digit PIN for {p_to_reset}"):
                    st.session_state.player_pins[p_to_reset] = None
                    if p_to_reset in st.session_state.authenticated_players:
                        st.session_state.authenticated_players[p_to_reset] = False
                    save_league_data()
                    st.success(f"Security PIN reset for {p_to_reset}!")
                    st.rerun()

        st.markdown("---")
        st.subheader("📅 Select Competition Week to Input / Update Broadcast Results")
        
        default_admin_week = st.session_state.current_week
        admin_selected_week = st.selectbox(
            "Select Competition Week to Input / Update Broadcast Results:",
            options=list(range(1, 11)),
            index=(default_admin_week - 1) if (1 <= default_admin_week <= 10) else 0,
            format_func=lambda w: f"Week {w} Results" + (" (Already Published)" if w in st.session_state.weekly_results else " (Pending Input)"),
            key="admin_week_selector_dropdown"
        )
        
        current_eliminated = get_current_eliminated_bakers(admin_selected_week)
        admin_active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        baker_opts_admin = ["--Select Baker--"] + admin_active_bakers
        
        saved_w = st.session_state.weekly_results.get(admin_selected_week, {})
        is_published = admin_selected_week in st.session_state.weekly_results
        
        if is_published:
            st.info(f"🟢 **Week {admin_selected_week} Results Recorded & Saved in System.** Fields are locked by default to prevent accidental edits.")
            enable_edit = st.checkbox("🔓 Enable Editing for Published Week", value=False, key=f"chk_edit_w{admin_selected_week}")
        else:
            enable_edit = True
            
        with st.form(f"admin_actuals_form_w{admin_selected_week}"):
            st.subheader(f"Input Official Broadcast Results for Week {admin_selected_week}")
            actuals = {}

            if admin_selected_week == 10:
                def_champ = saved_w.get("show_champion", "--Select Baker--")
                idx_champ = baker_opts_admin.index(def_champ) if def_champ in baker_opts_admin else 0
                actuals["show_champion"] = st.selectbox("Actual Show Champion", baker_opts_admin, index=idx_champ, disabled=not enable_edit)
                
                st.write("Actual Technical Challenge Rankings:")
                saved_tr = saved_w.get("tech_rank", [])
                t1_def = saved_tr[0] if len(saved_tr) > 0 and saved_tr[0] in baker_opts_admin else "--Select Baker--"
                t2_def = saved_tr[1] if len(saved_tr) > 1 and saved_tr[1] in baker_opts_admin else "--Select Baker--"
                t3_def = saved_tr[2] if len(saved_tr) > 2 and saved_tr[2] in baker_opts_admin else "--Select Baker--"
                
                act_t1 = st.selectbox("Technical 1st Place", baker_opts_admin, index=baker_opts_admin.index(t1_def), disabled=not enable_edit, key="adm_t1_w10")
                act_t2 = st.selectbox("Technical 2nd Place", baker_opts_admin, index=baker_opts_admin.index(t2_def), disabled=not enable_edit, key="adm_t2_w10")
                act_t3 = st.selectbox("Technical 3rd Place", baker_opts_admin, index=baker_opts_admin.index(t3_def), disabled=not enable_edit, key="adm_t3_w10")
                actuals["tech_rank"] = [act_t1, act_t2, act_t3]
            else:
                col1, col2 = st.columns(2)
                with col1:
                    def_sb = saved_w.get("star_baker", "--Select Baker--")
                    idx_sb = baker_opts_admin.index(def_sb) if def_sb in baker_opts_admin else 0
                    actuals["star_baker"] = st.selectbox("Actual Star Baker", baker_opts_admin, index=idx_sb, disabled=not enable_edit, key=f"adm_sb_w{admin_selected_week}")
                    
                    def_inl = [b for b in saved_w.get("in_line_sb", []) if b in admin_active_bakers] if isinstance(saved_w.get("in_line_sb"), list) else ([saved_w.get("in_line_sb")] if saved_w.get("in_line_sb") in admin_active_bakers else [])
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", admin_active_bakers, default=def_inl, disabled=not enable_edit, key=f"adm_inline_w{admin_selected_week}")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, disabled=not enable_edit, key=f"adm_elim_type_w{admin_selected_week}")
                    
                    def_elim = saved_w.get("eliminated", "--Select Baker--")
                    if elim_type == "Single Elimination":
                        s_elim = def_elim if isinstance(def_elim, str) and def_elim in baker_opts_admin else "--Select Baker--"
                        actuals["eliminated"] = st.selectbox("Actual Eliminated Baker", baker_opts_admin, index=baker_opts_admin.index(s_elim), disabled=not enable_edit, key=f"adm_elim_s_w{admin_selected_week}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                    else:
                        e1_def = def_elim[0] if isinstance(def_elim, list) and len(def_elim) > 0 and def_elim[0] in baker_opts_admin else "--Select Baker--"
                        e2_def = def_elim[1] if isinstance(def_elim, list) and len(def_elim) > 1 and def_elim[1] in baker_opts_admin else "--Select Baker--"
                        e1 = st.selectbox("Actual Eliminated Baker #1", baker_opts_admin, index=baker_opts_admin.index(e1_def), disabled=not enable_edit, key=f"adm_e1_d_w{admin_selected_week}")
                        e2 = st.selectbox("Actual Eliminated Baker #2", baker_opts_admin, index=baker_opts_admin.index(e2_def), disabled=not enable_edit, key=f"adm_e2_d_w{admin_selected_week}")
                        actuals["eliminated"] = [e1, e2]
                        
                    def_trb = [b for b in saved_w.get("in_trouble", []) if b in admin_active_bakers] if isinstance(saved_w.get("in_trouble"), list) else ([saved_w.get("in_trouble")] if saved_w.get("in_trouble") in admin_active_bakers else [])
                    actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", admin_active_bakers, default=def_trb, disabled=not enable_edit, key=f"adm_tr_w{admin_selected_week}")

                st.markdown("---")
                st.markdown(f"### 📊 Actual Technical Challenge Rankings (All {len(admin_active_bakers)} Bakers)")
                saved_tr = saved_w.get("tech_rank", [])
                tech_rank_inputs = []
                for i_pos in range(len(admin_active_bakers)):
                    pos_label = f"Technical Position #{i_pos + 1}"
                    if i_pos == 0: pos_label += " (1st Place)"
                    elif i_pos == len(admin_active_bakers) - 1: pos_label += f" ({i_pos+1}th / Last Place)"
                    
                    def_pos = saved_tr[i_pos] if i_pos < len(saved_tr) and saved_tr[i_pos] in baker_opts_admin else "--Select Baker--"
                    t_val = st.selectbox(pos_label, baker_opts_admin, index=baker_opts_admin.index(def_pos), disabled=not enable_edit, key=f"adm_tech_pos_{i_pos}_w{admin_selected_week}")
                    tech_rank_inputs.append(t_val)
                actuals["tech_rank"] = tech_rank_inputs
                
                clean_tr = [b for b in tech_rank_inputs if b != "--Select Baker--"]
                actuals["tech_top_3"] = clean_tr[:3]
                actuals["tech_bottom_3"] = clean_tr[-3:] if len(clean_tr) >= 3 else clean_tr

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            def_hs_cnt = saved_w.get("handshake_count", len(saved_w.get("handshake_bakers", [])))
            act_hs_cnt = st.number_input("Handshakes Count", min_value=0, value=def_hs_cnt, disabled=not enable_edit, key=f"adm_hs_cnt_w{admin_selected_week}")
            
            def_hs_bk = [b for b in saved_w.get("handshake_bakers", []) if b in admin_active_bakers]
            act_hs_bakers = st.multiselect("Bakers Receiving Hollywood Handshake(s)", admin_active_bakers, default=def_hs_bk, disabled=not enable_edit, key=f"adm_hs_bk_w{admin_selected_week}")
            
            act_hs_stamps = st.text_input("Handshake Circumstances & Video Timestamps", value=saved_w.get("handshake_timestamps", ""), disabled=not enable_edit, key=f"adm_hs_stamps_w{admin_selected_week}")

            st.markdown("### 😢 Crying Incidents")
            col_cr1, col_cr2 = st.columns(2)
            with col_cr1:
                act_cry_cnt = st.number_input("Crying Incidents Count", min_value=0, value=saved_w.get("crying_count", 0), disabled=not enable_edit, key=f"adm_cry_cnt_w{admin_selected_week}")
            with col_cr2:
                act_cry_stamps = st.text_input("Crying Circumstances & Video Timestamps", value=saved_w.get("crying_timestamps", ""), disabled=not enable_edit, key=f"adm_cry_stamps_w{admin_selected_week}")

            st.markdown("### 💬 Sexual Innuendos")
            col_in1, col_in2 = st.columns(2)
            with col_in1:
                act_inn_cnt = st.number_input("Sexual Innuendos Count", min_value=0, value=saved_w.get("innuendo_count", 0), disabled=not enable_edit, key=f"adm_inn_cnt_w{admin_selected_week}")
            with col_in2:
                act_inn_stamps = st.text_input("Innuendos Circumstances & Video Timestamps", value=saved_w.get("innuendo_timestamps", ""), disabled=not enable_edit, key=f"adm_inn_stamps_w{admin_selected_week}")

            actuals["handshake_count"] = act_hs_cnt
            actuals["handshake_bakers"] = act_hs_bakers
            actuals["handshake_timestamps"] = act_hs_stamps
            actuals["crying_count"] = act_cry_cnt
            actuals["crying_timestamps"] = act_cry_stamps
            actuals["innuendo_count"] = act_inn_cnt
            actuals["innuendo_timestamps"] = act_inn_stamps

            if admin_selected_week == 10:
                st.markdown("---")
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                def_s_win = st.session_state.season_results.get("winner", "--Select Baker--")
                s_winner = st.selectbox("Actual Season Winner", baker_opts_admin, index=baker_opts_admin.index(def_s_win) if def_s_win in baker_opts_admin else 0, disabled=not enable_edit, key="adm_s_winner")
                s_semis = st.multiselect("Actual Semifinalists (4 Bakers)", ALL_BAKERS, default=[b for b in st.session_state.season_results.get("semifinalists", []) if b in ALL_BAKERS], disabled=not enable_edit, key="adm_s_semis")
                s_finalists = st.multiselect("Actual Finalists (3 Bakers)", ALL_BAKERS, default=[b for b in st.session_state.season_results.get("finalists", []) if b in ALL_BAKERS], disabled=not enable_edit, key="adm_s_finalists")
                
                s_hs_tot = st.number_input("Actual Total Season Handshakes", min_value=0, value=st.session_state.season_results.get("handshakes", 5), disabled=not enable_edit, key="adm_s_hs")
                s_cry_tot = st.number_input("Actual Total Season Crying", min_value=0, value=st.session_state.season_results.get("crying", 12), disabled=not enable_edit, key="adm_s_cry")
                s_inn_tot = st.number_input("Actual Total Season Innuendos", min_value=0, value=st.session_state.season_results.get("innuendos", 40), disabled=not enable_edit, key="adm_s_inn")
                
                actuals_season = {
                    "winner": s_winner,
                    "semifinalists": s_semis,
                    "finalists": s_finalists,
                    "handshakes": s_hs_tot,
                    "crying": s_cry_tot,
                    "innuendos": s_inn_tot
                }

            sub_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings", disabled=not enable_edit)
            if sub_actuals:
                st.session_state.weekly_results[admin_selected_week] = actuals
                if admin_selected_week == 10:
                    st.session_state.season_results = actuals_season
                    
                # Recalculate all scores
                for m_name in st.session_state.league_members:
                    st.session_state.league_members[m_name]["total_score"] = 0
                    st.session_state.league_members[m_name]["weekly_breakdown"] = {}
                    
                all_weeks_scored = sorted([k for k in st.session_state.weekly_results.keys() if isinstance(k, int)])
                for w in all_weeks_scored:
                    act_w = st.session_state.weekly_results[w]
                    weekly_raw = {}
                    for m_name, m_data in st.session_state.league_members.items():
                        pred_w = m_data["weekly_picks"].get(w, {})
                        raw_s = calculate_weekly_score(pred_w, act_w, w)
                        weekly_raw[m_name] = raw_s
                        m_data["weekly_breakdown"][w] = raw_s
                        
                    if weekly_raw:
                        max_r = max(weekly_raw.values())
                        if max_r > 0:
                            for m_name, raw_s in weekly_raw.items():
                                if raw_s == max_r:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                    
                if st.session_state.season_results:
                    for m_name, m_data in st.session_state.league_members.items():
                        s_pred = m_data["season_picks"]
                        s_score = calculate_season_score(s_pred, st.session_state.season_results)
                        m_data["season_score"] = s_score
                        
                for m_name, m_data in st.session_state.league_members.items():
                    w_tot = sum(m_data["weekly_breakdown"].values())
                    s_tot = m_data.get("season_score", 0)
                    m_data["total_score"] = w_tot + s_tot
                    
                save_league_data()
                st.success(f"Results published for Week {admin_selected_week}! Leaderboard updated.")
                st.rerun()

        # --- DISPUTE RESOLUTION CONSOLE ---
        st.markdown("---")
        st.subheader("⚖️ Dispute Resolution & Management Console")
        st.write("Review player disputes submitted on the Show Results tab. Select a dispute below to change its status after a GroupMe league vote:")
        
        if not st.session_state.disputes:
            st.info("No active result disputes logged.")
        else:
            disp_options = [f"Dispute #{idx+1}: {d.get('Player')} - {d.get('Week')} ({d.get('Category')})" for idx, d in enumerate(st.session_state.disputes)]
            sel_disp_idx = st.selectbox("Select Dispute to Resolve:", range(len(disp_options)), format_func=lambda i: disp_options[i], key="admin_disp_sel")
            
            target_disp = st.session_state.disputes[sel_disp_idx]
            st.markdown(f"**Submitted by:** `{target_disp.get('Player')}` | **Week:** `{target_disp.get('Week')}`")
            st.markdown(f"**Category:** `{target_disp.get('Category')}`")
            st.markdown(f"**Evidence:** {target_disp.get('Evidence')}")
            st.markdown(f"**Requested Correction:** {target_disp.get('Correction')}")
            st.markdown(f"**Current Status:** `{target_disp.get('Status')}`")
            
            col_ds1, col_ds2 = st.columns(2)
            with col_ds1:
                new_status = st.selectbox("Update Resolution Status:", ["Pending GroupMe Vote 🗳️", "Accepted ✅", "Rejected ❌"], key="admin_disp_status_sel")
                if st.button("Save Resolution Status"):
                    target_disp["Status"] = new_status
                    save_league_data()
                    st.success("Dispute status updated successfully!")
                    st.rerun()
            with col_ds2:
                if st.button("🗑️ Delete Dispute Entry"):
                    st.session_state.disputes.pop(sel_disp_idx)
                    save_league_data()
                    st.success("Dispute deleted from log!")
                    st.rerun()

        # --- RESET ALL COMPETITION DATA ---
        st.markdown("---")
        with st.expander("🗑️ Reset All Competition Data", expanded=False):
            st.warning("⚠️ **Danger Zone:** Clearing competition data will permanently wipe all recorded weekly broadcast results, season results, player prediction ballots, dispute logs, and player PINs!")
            confirm_reset = st.checkbox("I understand that this will erase all competition data across all weeks.", key="confirm_reset_data_check")
            if st.button("🗑️ Erase All Competition Data", type="primary", disabled=not confirm_reset):
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.disputes = []
                st.session_state.player_pins = {}
                st.session_state.authenticated_players = {}
                
                for member_name in st.session_state.league_members:
                    st.session_state.league_members[member_name]["weekly_picks"] = {}
                    st.session_state.league_members[member_name]["season_picks"] = {}
                    st.session_state.league_members[member_name]["total_score"] = 0
                    st.session_state.league_members[member_name]["season_score"] = 0
                    st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                
                if os.path.exists(DATA_FILE):
                    try: os.remove(DATA_FILE)
                    except Exception: pass
                    
                st.session_state["data_erased_confirmation"] = True
                st.rerun()
