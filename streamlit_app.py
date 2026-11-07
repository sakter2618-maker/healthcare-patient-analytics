"""
Healthcare Patient Analytics — Streamlit dashboard
Run locally:   streamlit run streamlit_app.py
"""

import pandas as pd
import streamlit as st

from app import ui

st.set_page_config(page_title="Healthcare Patient Analytics", page_icon="🏥", layout="wide",
                   initial_sidebar_state="auto")
ui.inject_css()

pages = [
    st.Page("app/pages/1_overview.py", title="Executive Overview", icon="📊", default=True),
    st.Page("app/pages/2_hospitals.py", title="Hospital Performance", icon="🏥"),
    st.Page("app/pages/3_stay_cost.py", title="Length of Stay & Cost", icon="💵"),
    st.Page("app/pages/4_readmissions.py", title="Readmissions", icon="🔁"),
    st.Page("app/pages/5_demographics.py", title="Patient Demographics", icon="👥"),
    st.Page("app/pages/6_appointments.py", title="Appointments & No-shows", icon="📅"),
    st.Page("app/pages/7_data_quality.py", title="Data Cleaning & SQL", icon="🧹"),
]
nav = st.navigation(pages)

d = ui.load()
a = d["admissions"]
lo, hi = a.admit_datetime.min().date(), a.admit_datetime.max().date()
with st.sidebar:
    st.markdown("### 🏥 Filters")
    rng = st.date_input("Date range", value=(lo, hi), min_value=lo, max_value=hi)
    start, end = (rng if isinstance(rng, (tuple, list)) and len(rng) == 2 else (lo, hi))
    hosp = st.multiselect("Hospital", sorted(d["hospitals"].hospital_name), placeholder="All hospitals")
    dept = st.multiselect("Department", sorted(a.department.unique()), placeholder="All departments")
    st.caption("Filters apply to every page. Leave a box empty to include everything.")
    st.divider()
    st.caption("Synthetic, de-identified data · Python · PostgreSQL · Excel · Power BI · Streamlit")

st.session_state["filters"] = dict(start=pd.Timestamp(start), end=pd.Timestamp(end), hospitals=hosp, departments=dept)
nav.run()
