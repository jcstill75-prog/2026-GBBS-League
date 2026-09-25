import streamlit as st
import pandas as pd
import random
import json
import base64
from PIL import Image
import io
import os

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(
    page_title="GBBS Fantasy League 2026",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    .status-box {
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FFB74D;
        margin-bottom: 15px;
    }
    .leaderboard-table {
        font-family: Arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
    }
    a.aria-label, a[data-testid="stHeaderAnchor"], .stHeaderAnchor {
        outline: none !important;
        box-shadow: none !important;
        text-decoration: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENCE & DATA STORAGE HANDLERS ---
DATA_FILE = "league_data.json"

def save_league_data(league_members, weekly_results, season_results):
    """Saves league session state data to persistent league_data.json file."""
    try:
        members_copy = {}
        for name, data in league_members.items():
            m_dict = dict(data)
            members_copy[name] = m_dict
            
        payload = {
            "league_members": members_copy,
            "weekly_results": weekly_results,
            "season_results": season_results
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

def load_league_data():
    """Loads saved league session state from league_data.json if present."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                payload = json.load(f)
                members = payload.get("league_members", {})
                raw_weekly = payload.get("weekly_results", {})
                season = payload.get("season_results", {})
                
                weekly = {}
                if isinstance(raw_weekly, dict):
                    for k, v in raw_weekly.items():
                        try:
                            weekly[int(k)] = v
                        except (ValueError, TypeError):
                            weekly[k] = v
                            
                return members, weekly, season
        except Exception:
            pass
    return None, None, None

# --- 3. HELPER FUNCTIONS ---
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

DEFAULT_ROSTER = ["Ana", "Becca", "Brian", "Cassie", "Emma", "Gisselle", "Jasmine", "Jennifer", "Mark", "Sam", "Stacie W.", "Stacy C.", "Taliah", "Tressa"]

def load_baker_image(baker_name):
    filename = f"assets/{baker_name.lower()}.jpg"
    if os.path.exists(filename):
        try:
            return Image.open(filename)
        except Exception:
            pass
    return None

def load_ai_brian_avatar():
    if os.path.exists("assets/aibrian.jpg"):
        try:
            return Image.open("assets/aibrian.jpg")
        except Exception:
            pass
    return None

def get_sorted_weekly_result_weeks():
    weeks = []
    for k in st.session_state.weekly_results.keys():
        try:
            weeks.append(int(k))
        except (ValueError, TypeError):
            pass
    return sorted(list(set(weeks)))

def get_weekly_result(week):
    try:
        w_int = int(week)
    except (ValueError, TypeError):
        w_int = week
    return st.session_state.weekly_results.get(w_int) or st.session_state.weekly_results.get(str(w_int)) or {}

def get_current_eliminated_bakers(week_num):
    elim = []
    try:
        target_week = int(week_num)
    except (ValueError, TypeError):
        target_week = 10
        
    for w_int in get_sorted_weekly_result_weeks():
        if w_int <= target_week:
            res = get_weekly_result(w_int)
            act_el = res.get("eliminated")
            if isinstance(act_el, list):
                for b in act_el:
                    if b and b != "None" and b not in elim:
                        elim.append(b)
            elif isinstance(act_el, str) and act_el and act_el != "None":
                if act_el not in elim:
                    elim.append(act_el)
    return elim

def get_tech_options(active_bakers, current_key, default_val=None, placeholder="-- Select --"):
    """Returns all active bakers for dropdown choices."""
    opts = [placeholder] + active_bakers
    curr_val = st.session_state.get(current_key, default_val)
    idx = opts.index(curr_val) if curr_val in opts else 0
    return opts, idx

def render_player_avatar(avatar_val, width=50, caption=None):
    if not avatar_val:
        st.markdown(f"<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)
        return

    # Base64 string directly stored in JSON
    if isinstance(avatar_val, str) and avatar_val.startswith("data:image"):
        try:
            header, b64_data = avatar_val.split(",", 1)
            img_bytes = base64.b64decode(b64_data)
            img = Image.open(io.BytesIO(img_bytes))
            st.image(img, width=width, caption=caption)
            return
        except Exception:
            pass

    # Disk file fallback
    if isinstance(avatar_val, str) and os.path.exists(avatar_val):
        try:
            img = Image.open(avatar_val)
            st.image(img, width=width, caption=caption)
            return
        except Exception:
            pass

    # PIL Image object
    if isinstance(avatar_val, Image.Image):
        st.image(avatar_val, width=width, caption=caption)
        return

    # Robot avatar or default cookie
    if avatar_val == "🤖":
        b_img = load_ai_brian_avatar()
        if b_img:
            st.image(b_img, width=width, caption=caption)
        else:
            st.markdown(f"<h2 style='margin:0;'>🤖</h2>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='margin:0;'>🍪</h2>", unsafe_allow_html=True)

# --- 4. SCORING ENGINE ---
def calculate_weekly_score(predictions, actuals, week=2):
    score = 0
    if not predictions:
        return 0
    
    # Star Baker / Champion
    if week == 10:
        if predictions.get("show_champion") and predictions.get("show_champion") == actuals.get("show_champion"):
            score += 15
    else:
        if predictions.get("star_baker") == actuals.get("star_baker"):
            score += 5
        
        act_elim = actuals.get("eliminated")
        pred_elim = predictions.get("eliminated")
        if isinstance(act_elim, list):
            if isinstance(pred_elim, list):
                for p in pred_elim:
                    if p in act_elim:
                        score += 5
            elif isinstance(pred_elim, str) and pred_elim in act_elim:
                score += 5
        elif act_elim != "None":
            if isinstance(pred_elim, list):
                if act_elim in pred_elim:
                    score += 5
            elif pred_elim == act_elim:
                score += 5

    # Technical Placements
    if week >= 8:
        pred_rank = predictions.get("tech_rank", [])
        act_rank = actuals.get("tech_rank", [])
        
        if week == 8 and len(pred_rank) == 5 and len(act_rank) == 5:
            if pred_rank == act_rank:
                score += 25
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx in [0, 4] else 2
        elif week == 9 and len(pred_rank) == 4 and len(act_rank) == 4:
            if pred_rank == act_rank:
                score += 20
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx in [0, 3] else 2
        elif week == 10 and len(pred_rank) == 3 and len(act_rank) == 3:
            if pred_rank == act_rank:
                score += 15
            else:
                for idx, b in enumerate(pred_rank):
                    if act_rank[idx] == b:
                        score += 3 if idx == 0 else 2
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
                for idx, baker in enumerate(pred_top3):
                    if baker in act_top3 and baker != act_top3[idx]:
                        score += 1

        pred_bottom3 = predictions.get("tech_bottom_3", [])
        act_bottom3 = actuals.get("tech_bottom_3", [])
        if len(pred_bottom3) == 3 and len(act_bottom3) == 3:
            if pred_bottom3 == act_bottom3:
                score += 10
            else:
                if pred_bottom3[0] == act_bottom3[0]: score += 2
                if pred_bottom3[1] == act_bottom3[1]: score += 2
                if pred_bottom3[2] == act_bottom3[2]: score += 3
                for idx, baker in enumerate(pred_bottom3):
                    if baker in act_bottom3 and baker != act_bottom3[idx]:
                        score += 1

    # Consolations
    if week < 9:
        act_inl = actuals.get("in_line_sb", [])
        if isinstance(act_inl, str): act_inl = [act_inl]
        pred_inl = predictions.get("in_line_sb")
        if pred_inl and pred_inl in act_inl and pred_inl != actuals.get("star_baker"):
            score += 2
            
        act_trbl = actuals.get("in_trouble", [])
        if isinstance(act_trbl, str): act_trbl = [act_trbl]
        pred_trbl = predictions.get("in_trouble")
        act_elim_raw = actuals.get("eliminated", [])
        if isinstance(act_elim_raw, str): act_elim_raw = [act_elim_raw]
        if pred_trbl and pred_trbl in act_trbl and pred_trbl not in act_elim_raw:
            score += 2
            
    return score

def calculate_season_score(predictions, actuals):
    score = 0
    act_winner = actuals.get("winner")
    act_semis = actuals.get("semifinalists", [])
    act_finalists = actuals.get("finalists", act_semis)
    
    pred_winner = predictions.get("winner")
    if pred_winner and pred_winner == act_winner:
        score += 40
    elif pred_winner and pred_winner in act_finalists:
        score += 15
        
    pred_semis = predictions.get("semifinalists", [])
    for baker in pred_semis:
        if baker in act_semis and baker != pred_winner:
            score += 10
            
    pred_hs = predictions.get("handshakes")
    act_hs = actuals.get("handshakes")
    if pred_hs is not None and act_hs is not None:
        if pred_hs == act_hs: score += 20
        elif abs(pred_hs - act_hs) <= 1: score += 10
            
    pred_cry = predictions.get("crying")
    act_cry = actuals.get("crying")
    if pred_cry is not None and act_cry is not None:
        if pred_cry == act_cry: score += 20
        elif abs(pred_cry - act_cry) <= 5: score += 10

    pred_inn = predictions.get("innuendos")
    act_inn = actuals.get("innuendos")
    if pred_inn is not None and act_inn is not None:
        if pred_inn == act_inn: score += 20
        elif abs(pred_inn - act_inn) <= 5: score += 10
            
    return score

def get_weekly_itemized_breakdown(pred, act, week):
    rows = []
    if week == 10:
        p_c = pred.get("show_champion", "None")
        a_c = act.get("show_champion", "None")
        pts_c = 15 if (p_c != "None" and p_c == a_c) else 0
        rows.append({
            "Category": "🏆 Show Champion",
            "Your Prediction": p_c,
            "Actual Broadcast Result": a_c,
            "Points Awarded": f"{pts_c} pts",
            "Details & Explanations": "Correct Show Champion (+15 pts)" if pts_c == 15 else "Incorrect Show Champion prediction (0 pts)"
        })
    else:
        p_sb = pred.get("star_baker", "None")
        a_sb = act.get("star_baker", "None")
        pts_sb = 5 if (p_sb != "None" and p_sb == a_sb) else 0
        rows.append({
            "Category": "🌟 Star Baker",
            "Your Prediction": p_sb,
            "Actual Broadcast Result": a_sb,
            "Points Awarded": f"{pts_sb} pts",
            "Details & Explanations": "Correct Star Baker (+5 pts)" if pts_sb == 5 else "Incorrect Star Baker prediction (0 pts)"
        })

        p_el = pred.get("eliminated", "None")
        a_el = act.get("eliminated", "None")
        pts_el = 0
        desc_el = "Incorrect elimination prediction (0 pts)"
        if a_el == "None":
            desc_el = "Sickness / Grace Week — No elimination (0 pts)"
        else:
            if isinstance(a_el, list):
                matched = [p for p in (p_el if isinstance(p_el, list) else [p_el]) if p in a_el]
                pts_el = len(matched) * 5
                if pts_el > 0:
                    desc_el = f"Correctly predicted eliminated baker(s): {', '.join(matched)} (+{pts_el} pts)"
            else:
                if (isinstance(p_el, list) and a_el in p_el) or p_el == a_el:
                    pts_el = 5
                    desc_el = f"Correctly predicted eliminated baker {a_el} (+5 pts)"
        rows.append({
            "Category": "❌ Eliminated Baker",
            "Your Prediction": ", ".join(p_el) if isinstance(p_el, list) else str(p_el),
            "Actual Broadcast Result": ", ".join(a_el) if isinstance(a_el, list) else str(a_el),
            "Points Awarded": f"{pts_el} pts",
            "Details & Explanations": desc_el
        })

    if week >= 8:
        p_rank = pred.get("tech_rank", [])
        a_rank = act.get("tech_rank", [])
        pts_t = 0
        desc_t = "No technical placement matches (0 pts)"
        if p_rank and a_rank and len(p_rank) == len(a_rank):
            if p_rank == a_rank:
                sweep_pts = {8: 25, 9: 20, 10: 15}
                pts_t = sweep_pts.get(week, 15)
                desc_t = f"🎉 Perfect Technical Challenge Rank Sweep Bonus (+{pts_t} pts)!"
            else:
                details = []
                for idx, b in enumerate(p_rank):
                    if a_rank[idx] == b:
                        p_val = 3 if idx in [0, len(p_rank)-1] else 2
                        pts_t += p_val
                        ord_s = "1st" if idx == 0 else ("Last" if idx == len(p_rank)-1 else f"{idx+1}th")
                        details.append(f"{b} (Exact {ord_s}: +{p_val}pts)")
                if pts_t > 0:
                    desc_t = ", ".join(details)
        rows.append({
            "Category": f"📊 Technical Challenge Placement (Week {week})",
            "Your Prediction": ", ".join(p_rank) if p_rank else "None",
            "Actual Broadcast Result": ", ".join(a_rank) if a_rank else "None",
            "Points Awarded": f"{pts_t} pts",
            "Details & Explanations": desc_t
        })
    else:
        p_t3 = pred.get("tech_top_3", [])
        a_t3 = act.get("tech_top_3", [])
        pts_t3 = 0
        desc_t3 = "No Top 3 technical matches (0 pts)"
        if len(p_t3) == 3 and len(a_t3) == 3:
            if p_t3 == a_t3:
                pts_t3 = 10
                desc_t3 = "🎉 Perfect Top 3 Technical Combo Sweep Bonus (+10 pts)!"
            else:
                det = []
                if p_t3[0] == a_t3[0]: pts_t3 += 3; det.append(f"{p_t3[0]} (Exact 1st: +3pts)")
                if p_t3[1] == a_t3[1]: pts_t3 += 2; det.append(f"{p_t3[1]} (Exact 2nd: +2pts)")
                if p_t3[2] == a_t3[2]: pts_t3 += 2; det.append(f"{p_t3[2]} (Exact 3rd: +2pts)")
                for idx, b in enumerate(p_t3):
                    if b in a_t3 and b != a_t3[idx]:
                        pts_t3 += 1; det.append(f"{b} (In Top 3 wrong spot: +1pt)")
                if pts_t3 > 0: desc_t3 = ", ".join(det)
        rows.append({
            "Category": "🥇 Technical Challenge Top 3",
            "Your Prediction": ", ".join(p_t3) if p_t3 else "None",
            "Actual Broadcast Result": ", ".join(a_t3) if a_t3 else "None",
            "Points Awarded": f"{pts_t3} pts",
            "Details & Explanations": desc_t3
        })

        p_b3 = pred.get("tech_bottom_3", [])
        a_b3 = act.get("tech_bottom_3", [])
        pts_b3 = 0
        desc_b3 = "No Bottom 3 technical matches (0 pts)"
        if len(p_b3) == 3 and len(a_b3) == 3:
            if p_b3 == a_b3:
                pts_b3 = 10
                desc_b3 = "🎉 Perfect Bottom 3 Technical Combo Sweep Bonus (+10 pts)!"
            else:
                det = []
                if p_b3[0] == a_b3[0]: pts_b3 += 2; det.append(f"{p_b3[0]} (Exact 3rd-last: +2pts)")
                if p_b3[1] == a_b3[1]: pts_b3 += 2; det.append(f"{p_b3[1]} (Exact 2nd-last: +2pts)")
                if p_b3[2] == a_b3[2]: pts_b3 += 3; det.append(f"{p_b3[2]} (Exact Last: +3pts)")
                for idx, b in enumerate(p_b3):
                    if b in a_b3 and b != a_b3[idx]:
                        pts_b3 += 1; det.append(f"{b} (In Bottom 3 wrong spot: +1pt)")
                if pts_b3 > 0: desc_b3 = ", ".join(det)
        rows.append({
            "Category": "🔻 Technical Challenge Bottom 3",
            "Your Prediction": ", ".join(p_b3) if p_b3 else "None",
            "Actual Broadcast Result": ", ".join(a_b3) if a_b3 else "None",
            "Points Awarded": f"{pts_b3} pts",
            "Details & Explanations": desc_b3
        })

    if week < 9:
        p_inl = pred.get("in_line_sb", "None")
        a_inl = act.get("in_line_sb", [])
        if isinstance(a_inl, str): a_inl = [a_inl]
        pts_inl = 2 if (p_inl != "None" and p_inl in a_inl and p_inl != act.get("star_baker")) else 0
        rows.append({
            "Category": "📈 In Line Nominee Consolation",
            "Your Prediction": p_inl,
            "Actual Broadcast Result": ", ".join(a_inl) if a_inl else "None",
            "Points Awarded": f"{pts_inl} pts",
            "Details & Explanations": f"Picked 'In Line' nominee {p_inl} (+2 pts)" if pts_inl == 2 else "Nominee pick not awarded (0 pts)"
        })

        p_trb = pred.get("in_trouble", "None")
        a_trb = act.get("in_trouble", [])
        if isinstance(a_trb, str): a_trb = [a_trb]
        a_el_r = act.get("eliminated", [])
        if isinstance(a_el_r, str): a_el_r = [a_el_r]
        pts_trb = 2 if (p_trb != "None" and p_trb in a_trb and p_trb not in a_el_r) else 0
        rows.append({
            "Category": "⚠️ In Trouble Nominee Consolation",
            "Your Prediction": p_trb,
            "Actual Broadcast Result": ", ".join(a_trb) if a_trb else "None",
            "Points Awarded": f"{pts_trb} pts",
            "Details & Explanations": f"Picked 'In Trouble' saved nominee {p_trb} (+2 pts)" if pts_trb == 2 else "Nominee pick not awarded (0 pts)"
        })

    return rows

def generate_ai_brian_weekly_picks(week, active_bakers, is_double_elim=False):
    picks = {}
    if not active_bakers:
        return picks
    if week == 10:
        picks["show_champion"] = random.choice(active_bakers)
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_rank"] = shuffled[:3]
    elif week == 9:
        picks["star_baker"] = random.choice(active_bakers)
        rem = [b for b in active_bakers if b != picks["star_baker"]]
        if is_double_elim and len(rem) >= 2:
            picks["eliminated"] = random.sample(rem, 2)
        elif rem:
            picks["eliminated"] = random.choice(rem)
        else:
            picks["eliminated"] = "None"
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_rank"] = shuffled[:4]
    elif week == 8:
        picks["star_baker"] = random.choice(active_bakers)
        rem = [b for b in active_bakers if b != picks["star_baker"]]
        picks["in_line_sb"] = random.choice(rem) if rem else picks["star_baker"]
        rem_elim = [b for b in active_bakers if b != picks["star_baker"]]
        if is_double_elim and len(rem_elim) >= 2:
            picks["eliminated"] = random.sample(rem_elim, 2)
            rem_trb = [b for b in active_bakers if b not in picks["eliminated"]]
            picks["in_trouble"] = random.choice(rem_trb) if rem_trb else picks["star_baker"]
        else:
            picks["eliminated"] = random.choice(rem_elim) if rem_elim else picks["star_baker"]
            rem_trb = [b for b in active_bakers if b != picks["eliminated"]]
            picks["in_trouble"] = random.choice(rem_trb) if rem_trb else picks["star_baker"]
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_rank"] = shuffled[:5]
    else:
        picks["star_baker"] = random.choice(active_bakers)
        rem = [b for b in active_bakers if b != picks["star_baker"]]
        picks["in_line_sb"] = random.choice(rem) if rem else picks["star_baker"]
        rem_elim = [b for b in active_bakers if b != picks["star_baker"]]
        if is_double_elim and len(rem_elim) >= 2:
            picks["eliminated"] = random.sample(rem_elim, 2)
            rem_trb = [b for b in active_bakers if b not in picks["eliminated"]]
            picks["in_trouble"] = random.choice(rem_trb) if rem_trb else picks["star_baker"]
        else:
            picks["eliminated"] = random.choice(rem_elim) if rem_elim else picks["star_baker"]
            rem_trb = [b for b in active_bakers if b != picks["eliminated"]]
            picks["in_trouble"] = random.choice(rem_trb) if rem_trb else picks["star_baker"]
        
        shuffled = list(active_bakers)
        random.shuffle(shuffled)
        picks["tech_top_3"] = shuffled[:3]
        rem_bot = [b for b in active_bakers if b not in picks["tech_top_3"]]
        random.shuffle(rem_bot)
        picks["tech_bottom_3"] = rem_bot[:3]
        
    return picks

# --- 5. INITIALIZE SESSION STATE ---
saved_members, saved_weekly, saved_season = load_league_data()

if "league_members" not in st.session_state:
    if saved_members:
        st.session_state.league_members = saved_members
    else:
        clean_m = {
            "AI Brian": {
                "avatar": "🤖",
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
        }
        for p in DEFAULT_ROSTER:
            clean_m[p] = {
                "avatar": None,
                "weekly_picks": {},
                "season_picks": {},
                "total_score": 0,
                "weekly_breakdown": {},
                "pin": None
            }
        b_av = load_ai_brian_avatar()
        if b_av:
            clean_m["AI Brian"]["avatar"] = b_av
        st.session_state.league_members = clean_m

# Auto-migrate roster to remove legacy test profiles and add missing members
for p in DEFAULT_ROSTER:
    if p not in st.session_state.league_members:
        st.session_state.league_members[p] = {
            "avatar": None,
            "weekly_picks": {},
            "season_picks": {},
            "total_score": 0,
            "weekly_breakdown": {},
            "pin": None
        }

for old_key in ["Steve", "Craig", "You"]:
    if old_key in st.session_state.league_members:
        del st.session_state.league_members[old_key]

if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_weekly if saved_weekly is not None else {}

if "season_results" not in st.session_state:
    st.session_state.season_results = saved_season if saved_season is not None else {}

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "authenticated_players" not in st.session_state:
    st.session_state.authenticated_players = {}

if "current_week" not in st.session_state:
    st.session_state.current_week = 1

# --- 6. HEADER ---
norman_path = None
for p in ["normanbeaver.jpg", "assets/normanbeaver.jpg", "normanbeaver.png", "assets/normanbeaver.png"]:
    if os.path.exists(p):
        norman_path = p
        break

if norman_path:
    try:
        with open(norman_path, "rb") as f:
            b64_beaver = base64.b64encode(f.read()).decode("utf-8")
        ext = "png" if norman_path.endswith(".png") else "jpeg"
        st.markdown(f"""
        <style>
            .header-container {{
                display: flex;
                align-items: center;
                gap: 18px;
                margin-top: 5px;
                margin-bottom: 22px;
            }}
            .header-title {{
                margin: 0;
                padding: 0;
                font-size: 2.2rem;
                font-weight: 800;
                line-height: 1.2;
                color: var(--text-color, #2C1810);
            }}
            [data-theme="dark"] .header-title,
            .stApp[data-theme="dark"] .header-title,
            @media (prefers-color-scheme: dark) {{
                .header-title {{
                    color: #FFFFFF !important;
                }}
            }}
        </style>
        <div class="header-container">
            <img src="data:image/{ext};base64,{b64_beaver}" style="height: 80px; width: auto; border-radius: 8px; object-fit: contain;">
            <h1 class="header-title">Great British Baking Show Fantasy League 2026</h1>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        col_logo, col_title = st.columns([1, 6])
        with col_logo:
            st.image(norman_path, width=80)
        with col_title:
            st.title("Great British Baking Show Fantasy League 2026")
else:
    st.title("Great British Baking Show Fantasy League 2026")

# --- 7. SIDEBAR ---
with st.sidebar:
    st.header("📸 Upload Avatar Photo")
    st.write("Select your player name below to upload or manage your profile picture!")
    
    roster_players = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    sb_player = st.selectbox("Select Player Profile:", ["-- Select Your Name --"] + roster_players)
    
    if sb_player != "-- Select Your Name --":
        p_pin = st.session_state.league_members[sb_player].get("pin")
        is_authed = st.session_state.authenticated_players.get(sb_player, False)
        
        if p_pin is not None and not is_authed:
            st.warning(f"🔒 Profile locked for **{sb_player}**.")
            st.info("Unlock your profile in the **📝 Submit Predictions** tab using your 4-digit PIN to upload an avatar!")
        else:
            uploaded_file = st.file_uploader(f"Choose Photo for {sb_player}", type=["png", "jpg", "jpeg"], key=f"uploader_{sb_player}")
            if uploaded_file is not None:
                try:
                    img = Image.open(uploaded_file)
                    img = img.convert("RGB")
                    img = img.resize((250, 200))
                    
                    # Convert to Base64 data URL
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                    data_url = f"data:image/png;base64,{b64_str}"
                    
                    st.session_state.league_members[sb_player]["avatar"] = data_url
                    
                    # Also save disk backup
                    os.makedirs("assets/avatars", exist_ok=True)
                    try:
                        img.save(f"assets/avatars/{sb_player}.png", format="PNG")
                    except Exception:
                        pass
                        
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Avatar updated and saved permanently for {sb_player}!")
                except Exception as e:
                    st.error(f"Error saving image: {e}")
            
            cur_av = st.session_state.league_members[sb_player].get("avatar")
            if cur_av:
                render_player_avatar(cur_av, width=150, caption=f"{sb_player}'s Avatar")

    st.markdown("---")
    st.subheader("🗓️ Active Competition Week")
    st.session_state.current_week = st.slider("Select Episode Week:", 1, 10, st.session_state.current_week)
    
    st.markdown("---")
    st.header("🎯 Points Reference Guide")
    st.warning("⏰ **Weekly voting window ends on Tuesdays at 2:00 PM CT (Houston) / 8:00 PM BST right before the UK broadcast.**")
    
    with st.expander("🌟 Season-Long Projections (130 Max Pts)", expanded=False):
        st.markdown("""
        *   **Season Winner:** 40 pts
        *   **Finalist Consolation:** 15 pts *(if winner makes Top 3 but loses)*
        *   **Other 3 Semifinalists:** 10 pts each *(30 pts max)*
        *   **Hollywood Handshakes:** 20 pts *(spot-on)* / 10 pts *(+/- 1)*
        *   **Crying Events:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        *   **Innuendos Count:** 20 pts *(spot-on)* / 10 pts *(+/- 5)*
        """)
        
    with st.expander("📅 Standard Weeks (Weeks 2-7)", expanded=False):
        st.markdown("""
        *   **Star Baker:** 5 pts
        *   **Eliminated Baker:** 5 pts
        *   **In Line:** 2 pts
        *   **In Trouble:** 2 pts
        *   **Top 3 Technical:** Exact 1st (3 pts), 2nd/3rd (2 pts), wrong spot (1 pt), Sweep (10 pts)
        *   **Bottom 3 Technical:** Exact Last (3 pts), 9th/10th (2 pts), wrong spot (1 pt), Sweep (10 pts)
        *   **Star League Member:** +5 pts
        """)

# --- 8. MAIN TABS ---
tab_lead, tab_submit, tab_analytics, tab_admin = st.tabs([
    "📊 Leaderboard & Standings", 
    "📝 Submit Predictions", 
    "📈 Baker Analytics", 
    "👑 Admin Panel"
])

# --- TAB 1: LEADERBOARD & STANDINGS ---
with tab_lead:
    st.header("🏆 Live Leaderboard")
    sorted_members = sorted(
        st.session_state.league_members.items(),
        key=lambda item: item[1]["total_score"],
        reverse=True
    )

    col_hr, col_ha, col_hp, col_hs = st.columns([1, 1.2, 5, 2])
    with col_hr: st.markdown("**Rank**")
    with col_ha: st.markdown("**Avatar**")
    with col_hp: st.markdown("**Player Name**")
    with col_hs: st.markdown("**Total Points**")
    st.markdown("<hr style='margin: 4px 0 12px 0; border-top: 2px solid #D36B5F;'>", unsafe_allow_html=True)

    for idx, (member_name, data) in enumerate(sorted_members):
        rank = idx + 1
        rank_badge = f"🥇 #{rank}" if rank == 1 else (f"🥈 #{rank}" if rank == 2 else (f"🥉 #{rank}" if rank == 3 else f"#{rank}"))
        col_r, col_a, col_p, col_s = st.columns([1, 1.2, 5, 2])
        with col_r:
            st.markdown(f"<div style='padding-top:12px;'><h3>{rank_badge}</h3></div>", unsafe_allow_html=True)
        with col_a:
            render_player_avatar(data.get("avatar"), width=50)
        with col_p:
            st.markdown(f"<div style='padding-top:12px;'><h3><strong>{member_name}</strong></h3></div>", unsafe_allow_html=True)
        with col_s:
            st.markdown(f"<div style='padding-top:12px;'><h3><strong>{data['total_score']} pts</strong></h3></div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    st.markdown("---")
    st.header("🔍 Individual Player Scorecards")
    player_names = list(st.session_state.league_members.keys())
    selected_player = st.selectbox("Choose Player Scorecard to View:", player_names)
    p_data = st.session_state.league_members[selected_player]
    
    col_sc1, col_sc2 = st.columns([1, 4])
    with col_sc1:
        render_player_avatar(p_data.get("avatar"), width=120, caption=f"{selected_player}'s Avatar")
    with col_sc2:
        st.subheader(f"📊 Detailed Point Matrix: {selected_player}")
        st.markdown(f"**Total Combined Score:** `{p_data['total_score']} pts`")
        
        all_weeks = [w for w in get_sorted_weekly_result_weeks() if w != 1]
        if not all_weeks:
            st.info("No prediction episode broadcast results published yet. Weekly line-item calculations will appear here after Episode 2!")
        else:
            st.markdown("#### 📅 Weekly Episodic Scorecards")
            for w_num in all_weeks:
                res = get_weekly_result(w_num)
                pred_w = p_data["weekly_picks"].get(w_num, {})
                with st.expander(f"Week {w_num} Breakdown (Episode Results)", expanded=False):
                    raw_pts = calculate_weekly_score(pred_w, res, w_num)
                    weekly_scores_all = {m: calculate_weekly_score(m_data["weekly_picks"].get(w_num, {}), res, w_num) for m, m_data in st.session_state.league_members.items()}
                    max_score_w = max(weekly_scores_all.values()) if weekly_scores_all else 0
                    has_star_bonus = (raw_pts == max_score_w and raw_pts > 0)
                    
                    itemized_rows = get_weekly_itemized_breakdown(pred_w, res, w_num)
                    if has_star_bonus:
                        itemized_rows.append({
                            "Category": "🌟 Star League Member Bonus",
                            "Your Prediction": "Highest Weekly Scorer",
                            "Actual Broadcast Result": f"Highest Score ({raw_pts} pts)",
                            "Points Awarded": "+5 pts",
                            "Details & Explanations": "Awarded +5 bonus pts for top weekly performance!"
                        })
                    st.dataframe(pd.DataFrame(itemized_rows), use_container_width=True, hide_index=True)
                    st.markdown(f"**Week {w_num} Total Awarded:** `{p_data['weekly_breakdown'].get(w_num, raw_pts + (5 if has_star_bonus else 0))} pts`")

            if st.session_state.season_results:
                st.markdown("#### 🌟 Season-Long Predictions")
                with st.expander("Final Season Projections Scorecard", expanded=True):
                    s_pred = p_data["season_picks"]
                    s_act = st.session_state.season_results
                    s_pts = calculate_season_score(s_pred, s_act)
                    st.write(f"**Season Winner Pick:** `{s_pred.get('winner', 'None')}` (Actual: `{s_act.get('winner', 'N/A')}`)")
                    st.write(f"**Semifinalists Pick:** `{', '.join(s_pred.get('semifinalists', []))}`")
                    st.markdown(f"**Season Projections Total Points Earned:** `{s_pts} pts`")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab_submit:
    st.header("📝 Submit Your Predictions")
    active_roster = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
    
    col_p1, col_p2 = st.columns([2, 3])
    with col_p1:
        active_sub_player = st.selectbox("Select Player Profile Submitting Predictions:", active_roster, index=0)
        
    p_pin = st.session_state.league_members[active_sub_player].get("pin")
    is_authed = st.session_state.authenticated_players.get(active_sub_player, False)
    
    if p_pin is None:
        st.info(f"🔑 **First Visit for {active_sub_player}?** Please create a 4-digit Security PIN to lock and protect your prediction ballot.")
        with st.form(f"pin_setup_form_{active_sub_player}"):
            new_pin = st.text_input("Create 4-Digit Security PIN", type="password", max_chars=4)
            confirm_pin = st.text_input("Confirm 4-Digit Security PIN", type="password", max_chars=4)
            set_pin_btn = st.form_submit_button("Set My Security PIN")
            if set_pin_btn:
                if len(new_pin) == 4 and new_pin.isdigit() and new_pin == confirm_pin:
                    st.session_state.league_members[active_sub_player]["pin"] = new_pin
                    st.session_state.authenticated_players[active_sub_player] = True
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    st.success(f"Security PIN set successfully for {active_sub_player}! Your ballot is unlocked.")
                    st.rerun()
                else:
                    st.error("PINs must be exactly 4 digits and match!")
    elif not is_authed:
        st.warning(f"🔒 Profile **{active_sub_player}** is PIN protected.")
        with st.form(f"pin_verify_form_{active_sub_player}"):
            entered_pin = st.text_input(f"Enter 4-Digit PIN for {active_sub_player}", type="password", max_chars=4)
            verify_btn = st.form_submit_button("Unlock Ballot")
            if verify_btn:
                if entered_pin == p_pin:
                    st.session_state.authenticated_players[active_sub_player] = True
                    st.success(f"PIN verified! Welcome back, {active_sub_player}.")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again or ask the Administrator to reset it.")
    else:
        st.success(f"🔓 **Ballot Unlocked for {active_sub_player}**")
        if st.button("🔒 Lock Profile Session"):
            st.session_state.authenticated_players[active_sub_player] = False
            st.rerun()
            
        st.markdown("---")
        
        # 1. VISUAL BAKER GALLERY
        current_elim_gallery = get_current_eliminated_bakers(st.session_state.current_week)
        active_gallery_bakers = [b for b in ALL_BAKERS if b not in current_elim_gallery]
        
        with st.expander("📸 Visual Baker Gallery (Class of 2026)", expanded=False):
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

        # 2. SEASON-LONG PREDICTIONS FORM (EXCLUSIVELY OPEN IN WEEK 2)
        if st.session_state.current_week == 2:
            st.markdown("---")
            with st.expander("🌟 Season-Long Projections (130 Max Pts | Locks Pre-Week 2)", expanded=True):
                existing_s = st.session_state.league_members[active_sub_player].get("season_picks", {})
                def_winner = existing_s.get("winner")
                opts_win = ["-- Select Season Winner --"] + ALL_BAKERS
                def_winner_idx = opts_win.index(def_winner) if def_winner in opts_win else 0
                
                user_winner_raw = st.selectbox(
                    "Predict Season Winner (Show Champion) [40 pts if winner, 15 pts if runner-up consolation]", 
                    opts_win, 
                    index=def_winner_idx,
                    key=f"{active_sub_player}_win_pick_w2"
                )
                user_winner = user_winner_raw if not user_winner_raw.startswith("-- Select") else "None"
                remaining_for_semis = [b for b in ALL_BAKERS if b != user_winner]
                def_semis = [b for b in existing_s.get("semifinalists", []) if b in remaining_for_semis]
                
                user_semis = st.multiselect(
                    "Predict Other 3 Semifinalists [10 pts each | 30 pts max]", 
                    remaining_for_semis, 
                    default=def_semis,
                    max_selections=3,
                    key=f"{active_sub_player}_semis_pick_w2"
                )
                
                user_handshakes = st.number_input("Predict Seasonal Handshakes [Spot-on = 20 pts, +/-1 = 10 pts]", min_value=0, value=existing_s.get("handshakes", 0), key=f"{active_sub_player}_hs_pick_w2")
                user_crying = st.number_input("Predict Seasonal Crying [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=existing_s.get("crying", 0), key=f"{active_sub_player}_cry_pick_w2")
                user_innuendos = st.number_input("Predict Seasonal Innuendos [Spot-on = 20 pts, +/-5 = 10 pts]", min_value=0, value=existing_s.get("innuendos", 0), key=f"{active_sub_player}_inn_pick_w2")
                
                if st.button(f"Lock Season-Long Predictions for {active_sub_player}", key=f"btn_lock_season_{active_sub_player}"):
                    if len(user_semis) != 3:
                        st.error("Please select exactly 3 other semifinalists.")
                    else:
                        st.session_state.league_members[active_sub_player]["season_picks"] = {
                            "winner": user_winner,
                            "semifinalists": user_semis,
                            "handshakes": user_handshakes,
                            "crying": user_crying,
                            "innuendos": user_innuendos
                        }
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success(f"Season long projections saved for {active_sub_player}!")

        # 3. WEEKLY BALLOT FORM (DISABLED COMPLETELY IN WEEK 1)
        st.markdown("---")
        st.subheader(f"📅 Submit Weekly Predictions: Week {st.session_state.current_week}")
        
        if st.session_state.current_week == 1:
            st.info("🔍 **Week 1 Scouting Period:** Episode 1 serves as the official scouting phase to evaluate the bakers. No predictions (neither season-long projections nor weekly ballots) can be submitted during Week 1. Season-long projections and Week 2 prediction ballots will open in **Week 2**!")
        else:
            current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
            active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
            
            st.info(f"Active Bakers in the Tent for Week {st.session_state.current_week}: " + ", ".join(active_bakers))
            
            prev_week_num = st.session_state.current_week - 1
            prev_week_results = st.session_state.weekly_results.get(prev_week_num, {})
            prev_week_was_grace = (prev_week_results.get("eliminated") == "None")
            
            is_double_elim = False
            if st.session_state.current_week < 10:
                is_double_elim = st.checkbox("📢 Is this a Double-Elimination Week?", value=prev_week_was_grace, key=f"dbl_elim_chk_{active_sub_player}_w{st.session_state.current_week}")

            existing_w = st.session_state.league_members[active_sub_player]["weekly_picks"].get(st.session_state.current_week, {})
            cur_w = st.session_state.current_week
            
            with st.form(f"weekly_predictions_form_{active_sub_player}_w{cur_w}"):
                weekly_picks = {}
                raw_selections = []
                
                if cur_w == 10:
                    def_champ = existing_w.get("show_champion")
                    opts_champ, champ_idx = get_tech_options(active_bakers, f"{active_sub_player}_w10_champ", def_champ, "-- Select Show Champion --")
                    champ_sel = st.selectbox("Predict Show Champion [15 pts at stake]", opts_champ, index=champ_idx, key=f"{active_sub_player}_w10_champ")
                    weekly_picks["show_champion"] = champ_sel if not champ_sel.startswith("-- Select") else "None"
                    raw_selections.append(weekly_picks["show_champion"])
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    def_tr = existing_w.get("tech_rank", [])
                    def_t1 = def_tr[0] if len(def_tr) > 0 else None
                    def_t2 = def_tr[1] if len(def_tr) > 1 else None
                    def_t3 = def_tr[2] if len(def_tr) > 2 else None
                    
                    opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w10_t1", def_t1, "-- Select 1st Place --")
                    tech_1st = st.selectbox("Technical 1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w10_t1")
                    opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w10_t2", def_t2, "-- Select 2nd Place --")
                    tech_2nd = st.selectbox("Technical 2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w10_t2")
                    opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w10_t3", def_t3, "-- Select 3rd Place --")
                    tech_3rd = st.selectbox("Technical 3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w10_t3")
                    
                    weekly_picks["tech_rank"] = [tech_1st, tech_2nd, tech_3rd]
                    raw_selections.extend(weekly_picks["tech_rank"])
                    
                elif cur_w == 9:
                    def_sb = existing_w.get("star_baker")
                    opts_sb, sb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w9_sb", def_sb, "-- Select Star Baker --")
                    sb_sel = st.selectbox("Predict Star Baker [5 pts at stake]", opts_sb, index=sb_idx, key=f"{active_sub_player}_w9_sb")
                    weekly_picks["star_baker"] = sb_sel if not sb_sel.startswith("-- Select") else "None"
                    raw_selections.append(weekly_picks["star_baker"])
                    
                    def_el = existing_w.get("eliminated")
                    if is_double_elim:
                        el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                        el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                        opts_el1, el1_i = get_tech_options(active_bakers, f"{active_sub_player}_w9_el1", el1, "-- Select Eliminated Baker #1 --")
                        opts_el2, el2_i = get_tech_options(active_bakers, f"{active_sub_player}_w9_el2", el2, "-- Select Eliminated Baker #2 --")
                        elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", opts_el1, index=el1_i, key=f"{active_sub_player}_w9_el1")
                        elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", opts_el2, index=el2_i, key=f"{active_sub_player}_w9_el2")
                        weekly_picks["eliminated"] = [b for b in [elim_1, elim_2] if not b.startswith("-- Select")]
                        raw_selections.extend(weekly_picks["eliminated"])
                    else:
                        opts_el, el_idx = get_tech_options(active_bakers, f"{active_sub_player}_w9_el", def_el, "-- Select Eliminated Baker --")
                        el_sel = st.selectbox("Predict Eliminated Baker [5 pts at stake]", opts_el, index=el_idx, key=f"{active_sub_player}_w9_el")
                        weekly_picks["eliminated"] = el_sel if not el_sel.startswith("-- Select") else "None"
                        raw_selections.append(weekly_picks["eliminated"])
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    def_tr = existing_w.get("tech_rank", [])
                    def_t1 = def_tr[0] if len(def_tr) > 0 else None
                    def_t2 = def_tr[1] if len(def_tr) > 1 else None
                    def_t3 = def_tr[2] if len(def_tr) > 2 else None
                    def_t4 = def_tr[3] if len(def_tr) > 3 else None
                    
                    opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t1", def_t1, "-- Select 1st Place --")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w9_t1")
                    opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t2", def_t2, "-- Select 2nd Place --")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w9_t2")
                    opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t3", def_t3, "-- Select 3rd Place --")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w9_t3")
                    opts4, idx4 = get_tech_options(active_bakers, f"{active_sub_player}_w9_t4", def_t4, "-- Select 4th Place --")
                    t4 = st.selectbox("Technical 4th Place [3 pts]", opts4, index=idx4, key=f"{active_sub_player}_w9_t4")
                    
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4]
                    raw_selections.extend(weekly_picks["tech_rank"])

                elif cur_w == 8:
                    col1, col2 = st.columns(2)
                    with col1:
                        def_sb = existing_w.get("star_baker")
                        opts_sb, sb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_sb", def_sb, "-- Select Star Baker --")
                        sb_sel = st.selectbox("Predict Star Baker [5 pts at stake]", opts_sb, index=sb_idx, key=f"{active_sub_player}_w8_sb")
                        weekly_picks["star_baker"] = sb_sel if not sb_sel.startswith("-- Select") else "None"
                        raw_selections.append(weekly_picks["star_baker"])
                        
                        def_inl = existing_w.get("in_line_sb")
                        opts_inl, inl_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_inl", def_inl, "-- Select In Line Baker --")
                        inl_sel = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", opts_inl, index=inl_idx, key=f"{active_sub_player}_w8_inl")
                        weekly_picks["in_line_sb"] = inl_sel if not inl_sel.startswith("-- Select") else "None"
                        raw_selections.append(weekly_picks["in_line_sb"])
                    with col2:
                        def_el = existing_w.get("eliminated")
                        def_trb = existing_w.get("in_trouble")
                        opts_trb, trb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_trb", def_trb, "-- Select In Trouble Baker --")
                        trb_sel = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", opts_trb, index=trb_idx, key=f"{active_sub_player}_w8_trb")
                        weekly_picks["in_trouble"] = trb_sel if not trb_sel.startswith("-- Select") else "None"
                        raw_selections.append(weekly_picks["in_trouble"])
                        
                        if is_double_elim:
                            el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                            el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                            opts_el1, el1_i = get_tech_options(active_bakers, f"{active_sub_player}_w8_el1", el1, "-- Select Eliminated Baker #1 --")
                            opts_el2, el2_i = get_tech_options(active_bakers, f"{active_sub_player}_w8_el2", el2, "-- Select Eliminated Baker #2 --")
                            elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", opts_el1, index=el1_i, key=f"{active_sub_player}_w8_el1")
                            elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", opts_el2, index=el2_i, key=f"{active_sub_player}_w8_el2")
                            weekly_picks["eliminated"] = [b for b in [elim_1, elim_2] if not b.startswith("-- Select")]
                            raw_selections.extend(weekly_picks["eliminated"])
                        else:
                            opts_el, el_idx = get_tech_options(active_bakers, f"{active_sub_player}_w8_el", def_el, "-- Select Eliminated Baker --")
                            el_sel = st.selectbox("Predict Eliminated Baker [5 pts at stake]", opts_el, index=el_idx, key=f"{active_sub_player}_w8_el")
                            weekly_picks["eliminated"] = el_sel if not el_sel.startswith("-- Select") else "None"
                            raw_selections.append(weekly_picks["eliminated"])
                    
                    st.write("Predict Technical Challenge Final Rank:")
                    def_tr = existing_w.get("tech_rank", [])
                    def_t1 = def_tr[0] if len(def_tr) > 0 else None
                    def_t2 = def_tr[1] if len(def_tr) > 1 else None
                    def_t3 = def_tr[2] if len(def_tr) > 2 else None
                    def_t4 = def_tr[3] if len(def_tr) > 3 else None
                    def_t5 = def_tr[4] if len(def_tr) > 4 else None
                    
                    opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t1", def_t1, "-- Select 1st Place --")
                    t1 = st.selectbox("Technical 1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w8_t1")
                    opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t2", def_t2, "-- Select 2nd Place --")
                    t2 = st.selectbox("Technical 2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w8_t2")
                    opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t3", def_t3, "-- Select 3rd Place --")
                    t3 = st.selectbox("Technical 3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w8_t3")
                    opts4, idx4 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t4", def_t4, "-- Select 4th Place --")
                    t4 = st.selectbox("Technical 4th Place [2 pts]", opts4, index=idx4, key=f"{active_sub_player}_w8_t4")
                    opts5, idx5 = get_tech_options(active_bakers, f"{active_sub_player}_w8_t5", def_t5, "-- Select 5th Place --")
                    t5 = st.selectbox("Technical 5th Place [3 pts]", opts5, index=idx5, key=f"{active_sub_player}_w8_t5")
                    
                    weekly_picks["tech_rank"] = [t1, t2, t3, t4, t5]
                    raw_selections.extend(weekly_picks["tech_rank"])
                    
                else:
                    # Standard Weeks 2-7
                    col1, col2 = st.columns(2)
                    with col1:
                        def_sb = existing_w.get("star_baker")
                        opts_sb, sb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_sb", def_sb, "-- Select Star Baker --")
                        sb_sel = st.selectbox("Predict Star Baker [5 pts at stake]", opts_sb, index=sb_idx, key=f"{active_sub_player}_w{cur_w}_std_sb")
                        weekly_picks["star_baker"] = sb_sel if not sb_sel.startswith("-- Select") else "None"
                        raw_selections.append(weekly_picks["star_baker"])
                        
                        def_inl = existing_w.get("in_line_sb")
                        opts_inl, inl_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_inl", def_inl, "-- Select In Line Baker --")
                        inl_sel = st.selectbox("Predict In Line for Star Baker [2 pts if nominated but doesn't win]", opts_inl, index=inl_idx, key=f"{active_sub_player}_w{cur_w}_std_inl")
                        weekly_picks["in_line_sb"] = inl_sel if not inl_sel.startswith("-- Select") else "None"
                        raw_selections.append(weekly_picks["in_line_sb"])
                    with col2:
                        def_el = existing_w.get("eliminated")
                        def_trb = existing_w.get("in_trouble")
                        opts_trb, trb_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_trb", def_trb, "-- Select In Trouble Baker --")
                        trb_sel = st.selectbox("Predict In Trouble of Elimination [2 pts if bottom nominated but saved]", opts_trb, index=trb_idx, key=f"{active_sub_player}_w{cur_w}_std_trb")
                        weekly_picks["in_trouble"] = trb_sel if not trb_sel.startswith("-- Select") else "None"
                        raw_selections.append(weekly_picks["in_trouble"])
                        
                        if is_double_elim:
                            el1 = def_el[0] if isinstance(def_el, list) and len(def_el) > 0 else None
                            el2 = def_el[1] if isinstance(def_el, list) and len(def_el) > 1 else None
                            opts_el1, el1_i = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el1", el1, "-- Select Eliminated Baker #1 --")
                            opts_el2, el2_i = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el2", el2, "-- Select Eliminated Baker #2 --")
                            elim_1 = st.selectbox("Predict Eliminated Baker #1 [5 pts at stake]", opts_el1, index=el1_i, key=f"{active_sub_player}_w{cur_w}_std_el1")
                            elim_2 = st.selectbox("Predict Eliminated Baker #2 [5 pts at stake]", opts_el2, index=el2_i, key=f"{active_sub_player}_w{cur_w}_std_el2")
                            weekly_picks["eliminated"] = [b for b in [elim_1, elim_2] if not b.startswith("-- Select")]
                            raw_selections.extend(weekly_picks["eliminated"])
                        else:
                            opts_el, el_idx = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_el", def_el, "-- Select Eliminated Baker --")
                            el_sel = st.selectbox("Predict Eliminated Baker [5 pts at stake]", opts_el, index=el_idx, key=f"{active_sub_player}_w{cur_w}_std_el")
                            weekly_picks["eliminated"] = el_sel if not el_sel.startswith("-- Select") else "None"
                            raw_selections.append(weekly_picks["eliminated"])
                        
                    st.markdown("---")
                    st.write("Predict Technical Challenge Placements:")
                    col_t_top, col_t_bot = st.columns(2)
                    
                    def_top3 = existing_w.get("tech_top_3", [])
                    def_bot3 = existing_w.get("tech_bottom_3", [])
                    def_t1 = def_top3[0] if len(def_top3) > 0 else None
                    def_t2 = def_top3[1] if len(def_top3) > 1 else None
                    def_t3 = def_top3[2] if len(def_top3) > 2 else None
                    def_b3 = def_bot3[0] if len(def_bot3) > 0 else None
                    def_b2 = def_bot3[1] if len(def_bot3) > 1 else None
                    def_b1 = def_bot3[2] if len(def_bot3) > 2 else None
                    
                    with col_t_top:
                        opts1, idx1 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t1", def_t1, "-- Select 1st Place --")
                        t1 = st.selectbox("1st Place [3 pts]", opts1, index=idx1, key=f"{active_sub_player}_w{cur_w}_std_t1")
                        opts2, idx2 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t2", def_t2, "-- Select 2nd Place --")
                        t2 = st.selectbox("2nd Place [2 pts]", opts2, index=idx2, key=f"{active_sub_player}_w{cur_w}_std_t2")
                        opts3, idx3 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_t3", def_t3, "-- Select 3rd Place --")
                        t3 = st.selectbox("3rd Place [2 pts]", opts3, index=idx3, key=f"{active_sub_player}_w{cur_w}_std_t3")
                        weekly_picks["tech_top_3"] = [t1, t2, t3]
                        raw_selections.extend(weekly_picks["tech_top_3"])
                        
                    with col_t_bot:
                        opts_b3, idx_b3 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b3", def_b3, "-- Select 3rd-to-last Place --")
                        b_3rd_last = st.selectbox("3rd-to-last Place [2 pts]", opts_b3, index=idx_b3, key=f"{active_sub_player}_w{cur_w}_std_b3")
                        opts_b2, idx_b2 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b2", def_b2, "-- Select 2nd-to-last Place --")
                        b_2nd_last = st.selectbox("2nd-to-last Place [2 pts]", opts_b2, index=idx_b2, key=f"{active_sub_player}_w{cur_w}_std_b2")
                        opts_b1, idx_b1 = get_tech_options(active_bakers, f"{active_sub_player}_w{cur_w}_std_b1", def_b1, "-- Select Last Place --")
                        b_last = st.selectbox("Last Place [3 pts]", opts_b1, index=idx_b1, key=f"{active_sub_player}_w{cur_w}_std_b1")
                        weekly_picks["tech_bottom_3"] = [b_3rd_last, b_2nd_last, b_last]
                        raw_selections.extend(weekly_picks["tech_bottom_3"])

                submitted = st.form_submit_button("Submit Predictions")
                if submitted:
                    all_selected_bakers = [b for b in raw_selections if b in active_bakers and not str(b).startswith("-- Select") and b != "None"]
                    duplicates = sorted(list(set([b for b in all_selected_bakers if all_selected_bakers.count(b) > 1])))
                    if duplicates:
                        st.error(f"⚠️ **Duplicate Selection Error:** You cannot select the same baker for more than one category on your ballot. The following baker(s) were selected multiple times: **{', '.join(duplicates)}**. Please ensure each baker is selected only once across your ballot, then submit again.")
                    else:
                        st.session_state.league_members[active_sub_player]["weekly_picks"][cur_w] = weekly_picks
                        ai_picks = generate_ai_brian_weekly_picks(cur_w, active_bakers, is_double_elim=is_double_elim)
                        st.session_state.league_members["AI Brian"]["weekly_picks"][cur_w] = ai_picks
                        save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                        st.success(f"Predictions saved for {active_sub_player}!")

# --- TAB 3: BAKER ANALYTICS ---
with tab_analytics:
    st.header("📈 Contestant Analytics & Career Performance Matrix")
    current_eliminated_latest = get_current_eliminated_bakers(st.session_state.current_week)
    
    baker_stats = {}
    for baker in ALL_BAKERS:
        baker_stats[baker] = {
            "star_baker_cnt": 0,
            "in_line_cnt": 0,
            "in_trouble_cnt": 0,
            "handshake_cnt": 0,
            "tech_ranks": [],
            "tech_rank_pcts": []
        }
        
    for w in get_sorted_weekly_result_weeks():
        res = get_weekly_result(w)
        sb = res.get("star_baker")
        if sb and sb in baker_stats:
            baker_stats[sb]["star_baker_cnt"] += 1
            
        for inl in res.get("in_line_sb", []):
            if inl in baker_stats: baker_stats[inl]["in_line_cnt"] += 1
                
        for trb in res.get("in_trouble", []):
            if trb in baker_stats: baker_stats[trb]["in_trouble_cnt"] += 1
                
        for hs in res.get("handshake_bakers", []):
            if hs in baker_stats: baker_stats[hs]["handshake_cnt"] += 1
                
        t_ranks = res.get("tech_rank", [])
        if t_ranks:
            num_in_tech = len(t_ranks)
            for pos_idx, baker in enumerate(t_ranks):
                if baker in baker_stats:
                    pos = pos_idx + 1
                    baker_stats[baker]["tech_ranks"].append((w, pos))
                    pct = round(((num_in_tech - pos + 1) / num_in_tech) * 100, 1)
                    baker_stats[baker]["tech_rank_pcts"].append(pct)

    with st.expander("📊 Contestant Performance Matrix Summary", expanded=True):
        matrix_rows = []
        for baker in ALL_BAKERS:
            if baker in current_eliminated_latest:
                continue
            s = baker_stats[baker]
            avg_fin = round(sum(pos for _, pos in s["tech_ranks"]) / len(s["tech_ranks"]), 1) if s["tech_ranks"] else "N/A"
            avg_pct = round(sum(s["tech_rank_pcts"]) / len(s["tech_rank_pcts"]), 1) if s["tech_rank_pcts"] else "N/A"
            matrix_rows.append({
                "Contestant": baker + " 🧁",
                "Star Baker Titles 🌟": s["star_baker_cnt"],
                "In Line Nominee 📈": s["in_line_cnt"],
                "In Trouble Nominee ⚠️": s["in_trouble_cnt"],
                "Avg Tech Rank": avg_fin,
                "Relative Tech Rank %": f"{avg_pct}%" if avg_pct != "N/A" else "N/A",
                "Handshakes 🤝": s["handshake_cnt"]
            })
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    active_inspect_bakers = [b for b in ALL_BAKERS if b not in current_eliminated_latest]
    if not active_inspect_bakers:
        active_inspect_bakers = ALL_BAKERS
    selected_ana_baker = st.selectbox("Select Baker to Inspect:", active_inspect_bakers, key="ana_baker_select")
    
    ana_s = baker_stats[selected_ana_baker]
    b_img_orig = load_baker_image(selected_ana_baker)
    
    col_ana1, col_ana2 = st.columns([1, 3])
    with col_ana1:
        if b_img_orig is not None:
            st.image(b_img_orig, caption=f"{selected_ana_baker} (Active)", use_container_width=True)
        else:
            st.markdown(f"### **{selected_ana_baker}**")

    with col_ana2:
        st.markdown(f"#### 🏅 {selected_ana_baker}'s Career Accolades")
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Star Baker", f"{ana_s['star_baker_cnt']} 🌟")
        with m2: st.metric("In Line", f"{ana_s['in_line_cnt']} 📈")
        with m3: st.metric("In Trouble", f"{ana_s['in_trouble_cnt']} ⚠️")
        with m4: st.metric("Handshakes", f"{ana_s['handshake_cnt']} 🤝")
            
        st.markdown("---")
        avg_fin_val = round(sum(pos for _, pos in ana_s["tech_ranks"]) / len(ana_s["tech_ranks"]), 1) if ana_s["tech_ranks"] else "N/A"
        avg_pct_val = round(sum(ana_s["tech_rank_pcts"]) / len(ana_s["tech_rank_pcts"]), 1) if ana_s["tech_rank_pcts"] else "N/A"
        st.markdown(f"**Average Technical Finish:** `{avg_fin_val}` | **Technical Relative Rank %:** `{avg_pct_val}%`")

        if ana_s["tech_ranks"]:
            st.markdown("##### 📈 Technical Placement Trajectory")
            df_chart = pd.DataFrame({
                "Week": [f"W{w}" for w, _ in ana_s["tech_ranks"]],
                "Technical Position": [pos for _, pos in ana_s["tech_ranks"]]
            }).set_index("Week")
            st.line_chart(df_chart)

# --- TAB 4: ADMIN PANEL ---
with tab_admin:
    st.header("👑 League Administrator Console")
    
    if not st.session_state.admin_authenticated:
        st.warning("🔒 **Administrator Lock Screen**")
        with st.form("admin_login_form"):
            pin_input = st.text_input("Enter Admin PIN", type="password")
            login_btn = st.form_submit_button("Unlock Admin Panel")
            if login_btn:
                if pin_input == "6284":
                    st.session_state.admin_authenticated = True
                    st.success("Admin PIN verified! Unlocking console...")
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again.")
    else:
        st.success("🔓 **Authenticated as League Administrator**")
        if st.button("🔒 Lock Console Session"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        st.markdown("---")
        with st.expander("🔑 Player Security PIN Management & Reset", expanded=False):
            active_roster = sorted([m for m in st.session_state.league_members if m != "AI Brian"])
            p_to_reset = st.selectbox("Select Player Profile to Reset PIN:", ["-- Select Player --"] + active_roster)
            if p_to_reset != "-- Select Player --":
                cur_p_status = "Locked 🔒" if st.session_state.league_members[p_to_reset].get("pin") else "Unset 🔓"
                st.write(f"Current PIN Status for **{p_to_reset}**: `{cur_p_status}`")
                if st.button(f"Reset PIN for {p_to_reset}"):
                    st.session_state.league_members[p_to_reset]["pin"] = None
                    if p_to_reset in st.session_state.authenticated_players:
                        st.session_state.authenticated_players[p_to_reset] = False
                    st.success(f"Security PIN reset for {p_to_reset}!")
                    st.rerun()

        st.markdown("---")
        st.write("Input official broadcast results:")
        current_eliminated = get_current_eliminated_bakers(st.session_state.current_week)
        active_bakers = [b for b in ALL_BAKERS if b not in current_eliminated]
        
        with st.form("admin_actuals_form"):
            st.subheader(f"Input Broadcast Results for Week {st.session_state.current_week}")
            actuals = {}
            cur_w = st.session_state.current_week
            
            if cur_w == 10:
                opts_sc = ["-- Select Show Champion --"] + active_bakers
                act_sc_sel = st.selectbox("Actual Show Champion", opts_sc, index=0, key="admin_act_sc_w10")
                actuals["show_champion"] = act_sc_sel if not act_sc_sel.startswith("-- Select") else "None"
                
                st.markdown("### 🏆 Final Seasonal Broadcast Totals")
                opts_win = ["-- Select Season Winner --"] + active_bakers
                act_winner_sel = st.selectbox("Actual Season Winner (Show Champion)", opts_win, index=0, key="act_w10_winner")
                act_winner = act_winner_sel if not act_winner_sel.startswith("-- Select") else "None"
                
                act_semis = st.multiselect("Actual Semifinalists (Select 4)", ALL_BAKERS, default=[], key="act_w10_semis")
                act_finalists = st.multiselect("Actual Finalists (Select 3)", ALL_BAKERS, default=[], key="act_w10_finalists")
                act_handshakes = st.number_input("Actual Total Handshakes across Season", min_value=0, value=5, key="act_w10_hs")
                act_crying = st.number_input("Actual Total Crying Scenes across Season", min_value=0, value=12, key="act_w10_cry")
                act_innuendos = st.number_input("Actual Total Sexual Innuendos across Season", min_value=0, value=48, key="act_w10_inn")
                actuals_season = {
                    "winner": act_winner,
                    "semifinalists": act_semis,
                    "finalists": act_finalists,
                    "handshakes": act_handshakes,
                    "crying": act_crying,
                    "innuendos": act_innuendos
                }
                
            elif cur_w == 9:
                opts_sb9 = ["-- Select Star Baker --"] + active_bakers
                act_sb9_sel = st.selectbox("Actual Star Baker", opts_sb9, index=0, key="admin_act_sb_w9")
                actuals["star_baker"] = act_sb9_sel if not act_sb9_sel.startswith("-- Select") else "None"
                
                elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key="admin_elim_type_w9")
                if elim_type == "Single Elimination":
                    opts_el9 = ["-- Select Eliminated Baker --"] + active_bakers
                    act_el9_sel = st.selectbox("Actual Eliminated Baker", opts_el9, index=0, key="admin_act_elim_w9")
                    actuals["eliminated"] = act_el9_sel if not act_el9_sel.startswith("-- Select") else "None"
                elif elim_type == "No Elimination (Sickness/Grace Week)":
                    actuals["eliminated"] = "None"
                else:
                    opts_el9_1 = ["-- Select Eliminated Baker #1 --"] + active_bakers
                    act_el9_1 = st.selectbox("Actual Eliminated Baker #1", opts_el9_1, index=0, key="admin_act_elim_1_w9")
                    opts_el9_2 = ["-- Select Eliminated Baker #2 --"] + active_bakers
                    act_el9_2 = st.selectbox("Actual Eliminated Baker #2", opts_el9_2, index=0, key="admin_act_elim_2_w9")
                    actuals["eliminated"] = [b for b in [act_el9_1, act_el9_2] if not b.startswith("-- Select")]

            else:
                col1, col2 = st.columns(2)
                with col1:
                    opts_sb = ["-- Select Star Baker --", "None (No Star Baker)"] + active_bakers
                    act_sb_sel = st.selectbox("Actual Star Baker", opts_sb, index=0, key=f"admin_act_sb_w{cur_w}")
                    actuals["star_baker"] = act_sb_sel if act_sb_sel not in ["-- Select Star Baker --", "None (No Star Baker)"] else "None"
                    actuals["in_line_sb"] = st.multiselect("Actual 'In Line' Nominees", active_bakers, key=f"admin_in_line_w{cur_w}")
                with col2:
                    elim_type = st.radio("Elimination Status", ["Single Elimination", "No Elimination (Sickness/Grace Week)", "Double Elimination"], horizontal=True, key=f"admin_elim_type_w{cur_w}")
                    if elim_type == "Single Elimination":
                        opts_el = ["-- Select Eliminated Baker --"] + active_bakers
                        act_el_sel = st.selectbox("Actual Eliminated Baker", opts_el, index=0, key=f"admin_act_elim_w{cur_w}")
                        actuals["eliminated"] = act_el_sel if not act_el_sel.startswith("-- Select") else "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"admin_in_trouble_w{cur_w}")
                    elif elim_type == "No Elimination (Sickness/Grace Week)":
                        actuals["eliminated"] = "None"
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees (Sickness consolations)", active_bakers, key=f"admin_in_trouble_w{cur_w}")
                    else:
                        opts_el1 = ["-- Select Eliminated Baker #1 --"] + active_bakers
                        act_el1_sel = st.selectbox("Actual Eliminated Baker #1", opts_el1, index=0, key=f"admin_act_elim_1_w{cur_w}")
                        opts_el2 = ["-- Select Eliminated Baker #2 --"] + active_bakers
                        act_el2_sel = st.selectbox("Actual Eliminated Baker #2", opts_el2, index=0, key=f"admin_act_elim_2_w{cur_w}")
                        actuals["eliminated"] = [b for b in [act_el1_sel, act_el2_sel] if not b.startswith("-- Select")]
                        actuals["in_trouble"] = st.multiselect("Actual 'In Trouble' Nominees", active_bakers, key=f"admin_in_trouble_w{cur_w}")
                    
            st.markdown("---")
            st.markdown(f"### 📊 Actual Technical Challenge Rankings (1st through {len(active_bakers)}th Place)")
            num_bakers = len(active_bakers)
            cols_per_row = 3
            admin_keys = [f"admin_full_tech_w{cur_w}_r{r}" for r in range(1, num_bakers + 1)]
            full_tech_ranks = []
            
            for i in range(num_bakers):
                rank_num = i + 1
                ord_str = "1st" if rank_num == 1 else ("2nd" if rank_num == 2 else ("3rd" if rank_num == 3 else f"{rank_num}th"))
                if i % cols_per_row == 0:
                    t_cols = st.columns(min(cols_per_row, num_bakers - i))
                col = t_cols[i % cols_per_row]
                with col:
                    key_r = f"admin_full_tech_w{cur_w}_r{rank_num}"
                    placeholder = f"-- Select {ord_str} Place --"
                    opts, idx = get_tech_options(active_bakers, key_r, None, placeholder)
                    sel_baker = st.selectbox(f"Actual Technical {ord_str} Place", opts, index=idx, key=key_r)
                    if sel_baker and not str(sel_baker).startswith("-- Select"):
                        full_tech_ranks.append(sel_baker)
                    else:
                        full_tech_ranks.append(None)

            cleaned_tech_ranks = [b for b in full_tech_ranks if b is not None]
            actuals["tech_rank"] = cleaned_tech_ranks
            if len(cleaned_tech_ranks) >= 3:
                actuals["tech_top_3"] = cleaned_tech_ranks[:3]
                actuals["tech_bottom_3"] = cleaned_tech_ranks[-3:]
            else:
                actuals["tech_top_3"] = cleaned_tech_ranks
                actuals["tech_bottom_3"] = cleaned_tech_ranks

            st.markdown("---")
            st.markdown("### 🤝 Hollywood Handshakes")
            col_hs1, col_hs2 = st.columns(2)
            with col_hs1:
                act_handshake_bakers = st.multiselect("Bakers Receiving Hollywood Handshakes This Week", active_bakers, key=f"handshake_bakers_w{cur_w}")
                act_handshake_cnt = st.number_input("Number of Handshakes in Episode", min_value=0, value=len(act_handshake_bakers), key=f"handshake_cnt_w{cur_w}")
            with col_hs2:
                act_handshake_stamps = st.text_input("Description & Video Timestamps", value="", key=f"handshake_stamps_w{cur_w}")

            st.markdown("### 😢 Crying Incidents")
            col_cry1, col_cry2 = st.columns(2)
            with col_cry1:
                act_crying_cnt = st.number_input("Number of Crying Incidents in Episode", min_value=0, value=0, key=f"crying_cnt_w{cur_w}")
            with col_cry2:
                act_crying_stamps = st.text_input("Description & Video Timestamps", value="", key=f"crying_stamps_w{cur_w}")

            st.markdown("### 💬 Sexual Innuendos")
            col_inn1, col_inn2 = st.columns(2)
            with col_inn1:
                act_innuendo_cnt = st.number_input("Number of Sexual Innuendos in Episode", min_value=0, value=0, key=f"innuendo_cnt_w{cur_w}")
            with col_inn2:
                act_innuendo_stamps = st.text_input("Description & Video Timestamps", value="", key=f"innuendo_stamps_w{cur_w}")

            actuals["handshake_bakers"] = act_handshake_bakers
            actuals["handshake_count"] = act_handshake_cnt
            actuals["handshake_timestamps"] = act_handshake_stamps
            actuals["crying_count"] = act_crying_cnt
            actuals["crying_timestamps"] = act_crying_stamps
            actuals["innuendo_count"] = act_innuendo_cnt
            actuals["innuendo_timestamps"] = act_innuendo_stamps
            
            submit_actuals = st.form_submit_button("Publish Actual Results & Recalculate Standings")
            if submit_actuals:
                if len(actuals.get("tech_rank", [])) < len(active_bakers):
                    st.error(f"⚠️ Please select a baker for all {len(active_bakers)} Technical Challenge ranks before publishing!")
                else:
                    st.session_state.weekly_results[cur_w] = actuals
                    if cur_w == 10:
                        st.session_state.season_results = actuals_season
                    save_league_data(st.session_state.league_members, st.session_state.weekly_results, st.session_state.season_results)
                    
                    for member_name in st.session_state.league_members:
                        st.session_state.league_members[member_name]["total_score"] = 0
                        st.session_state.league_members[member_name]["weekly_breakdown"] = {}
                        
                    all_weeks_scored = get_sorted_weekly_result_weeks()
                    for w in all_weeks_scored:
                        act_w = get_weekly_result(w)
                        weekly_raw = {}
                        for m_name, m_data in st.session_state.league_members.items():
                            pred_w = m_data["weekly_picks"].get(w, {})
                            raw_score = calculate_weekly_score(pred_w, act_w, w)
                            weekly_raw[m_name] = raw_score
                            m_data["weekly_breakdown"][w] = raw_score
                            
                        if weekly_raw:
                            max_raw = max(weekly_raw.values())
                            for m_name, raw_s in weekly_raw.items():
                                if raw_s == max_raw and raw_s > 0:
                                    st.session_state.league_members[m_name]["weekly_breakdown"][w] += 5
                                    
                    if st.session_state.season_results:
                        for m_name, m_data in st.session_state.league_members.items():
                            season_pred = m_data["season_picks"]
                            season_score = calculate_season_score(season_pred, st.session_state.season_results)
                            m_data["season_score"] = season_score
                            
                    for m_name, m_data in st.session_state.league_members.items():
                        weekly_total = sum(m_data["weekly_breakdown"].values())
                        season_total = m_data.get("season_score", 0)
                        m_data["total_score"] = weekly_total + season_total
                        
                    st.success("Leaderboard updated! All player predictions scored and verified against official rule constraints.")

        st.markdown("---")
        st.subheader("🧹 Reset Season Data (Post-Testing Wipe)")
        confirm_reset = st.checkbox("I confirm I want to wipe all test predictions, weekly scores, and published results.", key="chk_confirm_season_reset")
        if st.button("🧹 Reset All League Data To Zero", type="primary"):
            if not confirm_reset:
                st.error("⚠️ Please check the confirmation box above before resetting!")
            else:
                clean_members = {
                    "AI Brian": {
                        "avatar": "🤖",
                        "weekly_picks": {},
                        "season_picks": {},
                        "total_score": 0,
                        "weekly_breakdown": {},
                        "pin": None
                    }
                }
                for p_name in DEFAULT_ROSTER:
                    clean_members[p_name] = {
                        "avatar": None,
                        "weekly_picks": {},
                        "season_picks": {},
                        "total_score": 0,
                        "weekly_breakdown": {},
                        "pin": None
                    }
                b_av = load_ai_brian_avatar()
                if b_av: clean_members["AI Brian"]["avatar"] = b_av
                save_league_data(clean_members, {}, {})
                keys_to_clear = [k for k in list(st.session_state.keys()) if k != "admin_authenticated"]
                for k in keys_to_clear: del st.session_state[k]
                st.session_state.league_members = clean_members
                st.session_state.weekly_results = {}
                st.session_state.season_results = {}
                st.session_state.current_week = 1
                st.session_state.authenticated_players = {}
                st.rerun()
