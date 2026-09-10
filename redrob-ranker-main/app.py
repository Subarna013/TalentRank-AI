import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="RedRob AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
css = Path("styles/style.css")
if css.exists():
    with open(css) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Initialize session state ───
if "ranking_result" not in st.session_state:
    st.session_state["ranking_result"] = None
if "uploaded_candidates" not in st.session_state:
    st.session_state["uploaded_candidates"] = None
if "shortlisted" not in st.session_state:
    st.session_state["shortlisted"] = set()
if "thresholds" not in st.session_state:
    st.session_state["thresholds"] = {"hire": 15, "review": 40}
    # hire=15 means top 15% CAN be hired (if score >= 60)
    # review=40 means top 40% CAN be reviewed (if score >= 35)

# ─── Sidebar ───
from components.sidebar import sidebar
page = sidebar()

# ─── Page Router ───
if page == "Dashboard":
    from views.dashboard import render
    render()
elif page == "Candidates":
    from views.candidates import render
    render()
elif page == "Rankings":
    from views.leaderboard import render
    render()
elif page == "AI Insights":
    from views.explainability import render
    render()
elif page == "Analytics":
    from views.analytics import render
    render()
elif page == "Fraud Detection":
    from views.fraud import render
    render()
elif page == "Reports":
    from views.export import render
    render()
elif page == "Upload Resumes":
    from views.upload import render
    render()
elif page == "Settings":
    from views.settings import render
    render()
elif page == "API Docs":
    from views.api_docs import render
    render()
else:
    from views.dashboard import render
    render()
