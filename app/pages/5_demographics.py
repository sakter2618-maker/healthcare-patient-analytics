import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

a, p, h = ui.data()
ui.hero("Patient Demographics", "Who uses the hospitals: age group, gender and insurance.",
        tags=["Demographics", "Age groups"])
if ui.empty_guard(a, p):
    st.stop()

demo = m.demographics(a, p)
top = demo.sort_values("services", ascending=False).iloc[0]
ui.kpi_row([
    ui.kpi("Unique patients", f"{a.patient_key.nunique():,}", "with at least one stay", ui.TEAL, "👥"),
    ui.kpi("Largest age group", str(top.age_group), f"{top.service_share:.1f}% of all services", ui.PINK, "🧓"),
    ui.kpi("Stays per patient (60+)", (f"{v:.2f}" if pd.notna(v := demo.set_index('age_group').admissions_per_patient.get('60+')) else "—"),
           f"vs {a.groupby('patient_key').size().mean():.2f} overall", ui.ORANGE, "🛏️"),
    ui.kpi("Female share", f"{100 * (a.gender == 'Female').mean():.1f}%", "of admissions", ui.VIOLET, "⚧"),
])

c1, c2 = st.columns([3, 2])
with c1:
    fig = go.Figure()
    fig.add_bar(x=demo.age_group.astype(str), y=demo.admissions, name="Admissions",
                marker=dict(color=ui.TEAL, cornerradius=4), hovertemplate="Age %{x}: %{y:,} admissions<extra></extra>")
    fig.add_bar(x=demo.age_group.astype(str), y=demo.appointments, name="Appointments",
                marker=dict(color=ui.ORANGE, cornerradius=4), hovertemplate="Age %{x}: %{y:,} appointments<extra></extra>")
    fig.update_layout(barmode="group", bargroupgap=0.08)
    ui.show(ui.style(fig, 360, True, "Healthcare services by age group", "Q2"))
with c2:
    fig = go.Figure(go.Pie(labels=demo.age_group.astype(str), values=demo.services, hole=0.6, sort=False,
                           marker=dict(colors=ui.SERIES[:5], line=dict(color="#fff", width=2)),
                           textinfo="label+percent", hovertemplate="Age %{label}: %{value:,} services<extra></extra>"))
    fig.update_layout(annotations=[dict(text=f"<b>{demo.services.sum():,}</b><br>services", showarrow=False,
                                        font=dict(size=14, color=ui.INK))])
    ui.show(ui.style(fig, 360, False, "Share of all services"))

c1, c2 = st.columns(2)
with c1:
    ins = m.insurance_mix(a)
    ui.show(ui.hbar(ins, "insurance_type", "admissions", "Admissions by insurance type", height=300))
with c2:
    fig = go.Figure(go.Bar(x=demo.age_group.astype(str), y=demo.avg_cost, marker=dict(color=ui.BLUE, cornerradius=4),
                           text=[ui.money(v) for v in demo.avg_cost], textposition="outside",
                           hovertemplate="Age %{x}: %{text} per stay<extra></extra>"))
    ui.show(ui.style(fig, 300, False, "Average cost per stay by age group"))

ui.section("Age group table")
st.dataframe(demo[["age_group", "patients", "admissions", "appointments", "service_share", "admissions_per_patient",
                   "avg_los", "avg_cost", "readmission_rate"]], hide_index=True, width="stretch", column_config={
    "age_group": "Age group", "patients": "Patients", "admissions": "Admissions", "appointments": "Appointments",
    "service_share": st.column_config.NumberColumn("Share of services", format="%.1f%%"),
    "admissions_per_patient": st.column_config.NumberColumn("Stays / patient", format="%.2f"),
    "avg_los": st.column_config.NumberColumn("Avg stay (days)", format="%.2f"),
    "avg_cost": st.column_config.NumberColumn("Avg cost", format="$%,.0f"),
    "readmission_rate": st.column_config.NumberColumn("Readmission %", format="%.1f%%")})
ui.footer()
