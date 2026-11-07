import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

a, p, h = ui.data()
ui.hero("Healthcare Patient Analytics",
        "Admissions, length of stay, treatment cost, 30-day readmissions and appointment no-shows across "
        "5 hospitals and 6 departments.",
        tags=["Executive Overview", "Jan 2024 – Dec 2025", "Synthetic · de-identified"])
if ui.empty_guard(a, p):
    st.stop()

k = m.kpis(a, p)
ui.kpi_row([
    ui.kpi("Admissions", f"{k['admissions']:,}", f"{k['patients']:,} unique patients", ui.TEAL, "🛏️"),
    ui.kpi("Avg length of stay", f"{k['avg_los']:.1f} days", f"median {k['median_los']:.1f} days", ui.BLUE, "⏱️"),
    ui.kpi("Avg treatment cost", ui.money(k["avg_cost"]), f"{ui.money(k['total_cost'])} total", ui.ORANGE, "💵"),
    ui.kpi("30-day readmission", f"{k['readmission_rate']:.1f}%", "target ≤ 14%", ui.PINK, "🔁",
           "good" if k["readmission_rate"] <= 14 else ("warn" if k["readmission_rate"] <= 16 else "bad")),
    ui.kpi("Appointment no-show", f"{k['noshow_rate']:.1f}%", f"{k['appointments']:,} appointments", ui.VIOLET, "📅",
           "good" if k["noshow_rate"] <= 10 else ("warn" if k["noshow_rate"] <= 15 else "bad")),
    ui.kpi("Emergency admissions", f"{k['emergency_share']:.1f}%", f"avg recovery score {k['avg_recovery']:.0f}/100",
           ui.LIME, "🚑"),
])

ui.section("Business questions: answered", "Every answer updates with the sidebar filters.")
ans = m.business_answers({"admissions": a, "appointments": p})
cols = st.columns(5)
for c, x, color in zip(cols, ans, [ui.TEAL, ui.VIOLET, ui.ORANGE, ui.PINK, ui.BLUE]):
    with c:
        ui.insight(x["q"], x["a"], x["d"], color)

left, right = st.columns([3, 2])
with left:
    mo = m.monthly(a)
    fig = go.Figure()
    fig.add_bar(x=mo.month, y=mo.admissions, name="Admissions", marker=dict(color=ui.SOFT, cornerradius=3),
                hovertemplate="%{x|%b %Y}: %{y:,} admissions<extra></extra>")
    fig.add_scatter(x=mo.month, y=mo.admissions.rolling(3, min_periods=1).mean(), name="3-month average",
                    line=dict(color=ui.TEAL, width=2.5), mode="lines",
                    hovertemplate="%{x|%b %Y}: %{y:,.0f} (3-month avg)<extra></extra>")
    ui.show(ui.style(fig, 340, True, "Monthly admissions", "winter peaks every December–February"))
with right:
    dep = m.admissions_by_department(a)
    ui.show(ui.hbar(dep, "department", "admissions", "Admissions by department", "Q1",
                    color=ui.DEPT_COLORS, height=340))

c1, c2 = st.columns(2)
with c1:
    hp = m.hospital_performance(a, p, h)
    fig = go.Figure(go.Bar(x=ui.short(hp.hospital_name),
                           y=hp.readmission_rate, marker=dict(color=[ui.BAD if v > 16 else ui.TEAL for v in hp.readmission_rate],
                                                              cornerradius=4),
                           text=[f"{v:.1f}%" for v in hp.readmission_rate], textposition="outside",
                           hovertemplate="%{x}: %{y:.1f}% readmitted<extra></extra>"))
    fig.add_hline(y=14, line=dict(color=ui.INK_2, dash="dot", width=1.5))
    ui.show(ui.style(fig, 320, False, "30-day readmission rate by hospital", "dotted line = 14% target · red = above 16%"))
with c2:
    nb = m.noshow_by(p, "lead_time_band", m.BAND_ORDER)
    fig = go.Figure(go.Bar(x=nb.lead_time_band.astype(str), y=nb.noshow_rate,
                           marker=dict(color=ui.VIOLET, cornerradius=4),
                           text=[f"{v:.1f}%" for v in nb.noshow_rate], textposition="outside",
                           hovertemplate="Booked %{x} ahead: %{y:.1f}% no-show<extra></extra>"))
    ui.show(ui.style(fig, 320, False, "No-show rate by how far ahead the visit was booked", "Q5"))

ui.callout("<b>Headline:</b> Riverside Community Hospital has the highest readmission rate and the longest stays; "
           "patients 60+ account for the largest share of services; and appointments booked more than a month "
           "ahead are missed about four times as often as same-day bookings. See the Insights Report for actions.")
ui.footer()
