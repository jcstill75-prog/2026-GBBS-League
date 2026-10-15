import os
import json
import base64
import random
import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText

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
    .main { background-color: #f9f8f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0ebe1;
        border-radius: 4px 4px 0px 0px;
        font-weight: 600;
        color: #5c4033;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d7c49e !important;
        color: #2c1d11 !important;
    }
    div.stButton > button {
        background-color: #8c6239;
        color: white;
        border-radius: 4px;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #6d4b2b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

### --- 2. PERSISTENCE & EMAIL ENGINE ---
DATA_FILE = "league_data.json"

def send_admin_email(subject, body):
    try:
        secrets = st.secrets.get("email", {})
        sender_email = secrets.get("sender_email")
        sender_password = secrets.get("sender_password")
        admin_email = secrets.get("admin_email")
        
        if not sender_email or not sender_password or not admin_email:
            return
            
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = admin_email
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [admin_email], msg.as_string())
    except Exception:
        pass

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
                    return data
        except Exception:
            pass
    return {}

def save_league_data():
    try:
        payload = {
            "league_members": st.session_state.get("league_members", {}),
            "weekly_results": st.session_state.get("weekly_results", {}),
            "season_results": st.session_state.get("season_results", {}),
            "disputes": st.session_state.get("disputes", []),
            "admin_deadline_override": st.session_state.get("admin_deadline_override", False),
            "week_publication_timestamps": st.session_state.get("week_publication_timestamps", {})
        }
        with open(DATA_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass

# Initialize session state from disk
saved_data = load_league_data()
if "league_members" not in st.session_state:
    st.session_state.league_members = saved_data.get("league_members", {})
if "weekly_results" not in st.session_state:
    st.session_state.weekly_results = saved_data.get("weekly_results", {})
if "season_results" not in st.session_state:
    st.session_state.season_results = saved_data.get("season_results", {})
if "disputes" not in st.session_state:
    st.session_state.disputes = saved_data.get("disputes", [])
if "admin_deadline_override" not in st.session_state:
    st.session_state.admin_deadline_override = saved_data.get("admin_deadline_override", False)
if "week_publication_timestamps" not in st.session_state:
    st.session_state.week_publication_timestamps = saved_data.get("week_publication_timestamps", {})

### --- 3. SIDEBAR SCORING GUIDE ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/cupcake.png", width=60)
    st.title("GBBS Fantasy League 2026")
    st.markdown("---")
    
    st.markdown("### 📜 Scoring Reference Guide")
    
    with st.expander("1. Season-Wide Predictions", expanded=True):
        st.markdown("""
        - **Series Champion (Winner):** 10 pts
        - **Runner-Up (Finalist 2):** 5 pts
        - **Runner-Up (Finalist 3):** 5 pts
        - **First Baker Eliminated (Week 1):** 8 pts
        - **First Baker Eliminated (Week 2):** 5 pts
        """)
        
    with st.expander("2. Weekly Predictions (Weeks 2–7)", expanded=False):
        st.markdown("""
        - **Star Baker:** 5 pts
        - **Eliminated Baker:** 5 pts
        - **In Line for Star Baker:** 2 pts
        - **In Trouble for Elimination:** 2 pts
        - **Technical (Weeks 2–7):**
          - Exact Top 3 Sweep: +10 pts
          - Individual Correct Position: +3 pts
          - Individual Wrong Position (Top/Bot 3): +1 pt
        """)
        
    with st.expander("3. Weekly Predictions (Weeks 8–10)", expanded=False):
        st.markdown("""
        - **Star Baker:** 5 pts
        - **Eliminated Baker:** 5 pts
        - **In Line for Star Baker:** 2 pts
        - **In Trouble for Elimination:** 2 pts
        - **Technical (Weeks 8–10):**
          - Full Ranking Exact Match: +15 pts
        - **Star Member Weekly Bonus:** +5 pts
        """)

### --- 4. MAIN NAVIGATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🏆 Leaderboard & Standings",
    "📝 Submit Predictions",
    "🧁 Show Results",
    "👑 Admin Panel"
])

with tab1:
    st.header("🏆 League Leaderboard & Player Scorecards")
    st.write("View live standings and explore member prediction history.")

with tab2:
    st.header("📝 Submit Weekly & Season Predictions")
    st.write("Cast your ballots before the weekly deadline.")

with tab3:
    st.header("🧁 Show Results & Episode Breakdown")
    st.write("Review official broadcast outcomes, chaos counters, and log disputes.")

with tab4:
    st.header("👑 Admin Panel")
    st.write("Publish official results, manage league members, override deadlines, and restore backups.")
    
    # JSON Backup / Restore section
    st.markdown("---")
    st.subheader("📦 Database Backup & Restore")
    
    # Download backup button
    backup_json = json.dumps({
        "league_members": st.session_state.league_members,
        "weekly_results": st.session_state.weekly_results,
        "season_results": st.session_state.season_results,
        "disputes": st.session_state.disputes,
        "admin_deadline_override": st.session_state.admin_deadline_override,
        "week_publication_timestamps": st.session_state.week_publication_timestamps
    }, indent=2)
    
    st.download_button(
        label="📥 Download JSON Backup",
        data=backup_json,
        file_name=f"gbbs_league_backup_{datetime.datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )
    
    # Upload / Restore backup section
    uploaded_backup = st.file_uploader("📤 Upload Saved JSON Backup", type=["json"])
    if uploaded_backup is not None:
        if st.button("Confirm & Restore Uploaded Data", type="primary"):
            try:
                restored_data = json.load(uploaded_backup)
                if isinstance(restored_data, dict):
                    if "league_members" in restored_data:
                        st.session_state.league_members = restored_data["league_members"]
                    if "weekly_results" in restored_data:
                        w_res = {}
                        for k, v in restored_data["weekly_results"].items():
                            try:
                                w_res[int(k)] = v
                            except Exception:
                                w_res[k] = v
                        st.session_state.weekly_results = w_res
                    if "season_results" in restored_data:
                        st.session_state.season_results = restored_data["season_results"]
                    if "disputes" in restored_data:
                        st.session_state.disputes = restored_data["disputes"]
                    
                    save_league_data()
                    st.success("✅ League data successfully restored from uploaded JSON backup!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to parse JSON file: {e}")
