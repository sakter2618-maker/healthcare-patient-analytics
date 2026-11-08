import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

a, p, h = ui.data()
ui.hero("30-Day Readmissions", "A readmission = the same patient admitted again within 30 days of discharge, "
        "measured from the actual sequence of stays.", tags=["Readmissions", "Risk score"])
if ui.empty_guard(a):
    st.stop()

r = m.readmission_summary(a)
if a.readmitted_30d.isna().any():
    n_open = int(a.readmitted_30d.isna().sum())
    ui.callout(f"<b>{n_open:,} stay(s)</b> in this selection were discharged in the last 30 days of the data, so "
               "we can't know yet whether they come back. They are left out of the rates (right-censoring)."
               + (" <b>Nothing in this selection can be measured yet — widen the date range.</b>"
                  if a.readmitted_30d.notna().sum() == 0 else ""))
ui.kpi_row([
    ui.kpi("30-day readmission rate", f"{r['rate']:.1f}%", f"{r['readmissions']:,} stays · target ≤ 14%", ui.PINK, "🔁",
           "good" if r["rate"] <= 14 else ("warn" if r["rate"] <= 16 else "bad")),
    ui.kpi("High-risk stays", f"{r['high_risk_share']:.1f}%", "risk score ≥ 25%", ui.ORANGE, "⚠️"),
    ui.kpi("Readmitted: high risk", f"{r['rate_high_risk']:.1f}%", "of stays flagged high risk", ui.BAD, "📍"),
    ui.kpi("Readmitted: low risk", f"{r['rate_low_risk']:.1f}%", "of the remaining stays", ui.TEAL, "✅"),
])

c1, c2 = st.columns(2)
with c1:
    ag = m.readmission_by(a, "age_group")
    fig = go.Figure(go.Bar(x=ag.age_group.astype(str), y=ag.readmission_rate,
                           marker=dict(color=[ui.PINK if g == "60+" else ui.SOFT for g in ag.age_group.astype(str)],
                                       cornerradius=4),
                           text=[f"{v:.1f}%" for v in ag.readmission_rate], textposition="outside",
                           hovertemplate="Age %{x}: %{y:.1f}% readmitted<extra></extra>"))
    fig.update_yaxes(ticksuffix="%")
    ui.show(ui.style(fig, 330, False, "Readmission rate by age group", "60+ is the clear outlier"))
with c2:
    dp = m.readmission_by(a, "department")
    ui.show(ui.hbar(dp, "department", "readmission_rate", "Readmission rate by department",
                    fmt="{:.1f}%", color=ui.DEPT_COLORS, height=330))

c1, c2 = st.columns(2)
with c1:
    cal = m.risk_calibration(a)
    fig = go.Figure(go.Bar(x=cal.risk_band.astype(str), y=cal.actual, marker=dict(color=ui.ORANGE, cornerradius=4),
                           text=[f"{v:.1f}%" for v in cal.actual], textposition="outside",
                           customdata=cal.stays, hovertemplate="Risk %{x}: %{y:.1f}% actually readmitted"
                                                              "<br>%{customdata:,} stays<extra></extra>"))
    fig.update_xaxes(title="Predicted risk score at discharge")
    fig.update_yaxes(title="Actually readmitted (%)", ticksuffix="%")
    ui.show(ui.style(fig, 330, False, "Does the risk score work?", "higher score → more readmissions"))
with c2:
    mo = m.monthly(a)
    fig = go.Figure(go.Scatter(x=mo.month, y=mo.readmission_rate, mode="lines+markers",
                               line=dict(color=ui.PINK, width=2.5), marker=dict(size=8),
                               hovertemplate="%{x|%b %Y}: %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=14, line=dict(color=ui.INK_2, dash="dot", width=1.5))
    fig.update_yaxes(ticksuffix="%", tickformat=".0f", dtick=2)
    ui.show(ui.style(fig, 330, False, "Monthly readmission rate", "dotted line = 14% target · last month excluded (window not complete)"))

ui.callout("<b>How to use the risk score:</b> stays scored 25%+ are readmitted much more often than the rest. "
           "A nurse follow-up call within 72 hours and a medication review for this group target the patients "
           "most likely to come back. The score is a screening tool (AUC ≈ 0.61), not a diagnosis.")
ui.footer()
