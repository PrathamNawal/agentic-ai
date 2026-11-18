"""Streamlit dashboard: monitor, tweak, and teach the Metric Anomaly Investigator.

    streamlit run app.py
"""
import streamlit as st

import ui

st.set_page_config(page_title="Metric Anomaly Investigator", page_icon="🕵️", layout="wide")
ui.gate()
ui.bootstrap()
ui.sidebar()

pages = [
    st.Page("pages/overview.py", title="Overview", icon="📊", default=True),
    st.Page("pages/run.py", title="Run the agent", icon="▶️"),
    st.Page("pages/review.py", title="Review & grade", icon="✅"),
    st.Page("pages/memory_page.py", title="Memory", icon="🧠"),
    st.Page("pages/configure.py", title="Configure", icon="⚙️"),
    st.Page("pages/data_page.py", title="Data explorer", icon="🔎"),
]
st.navigation(pages).run()
