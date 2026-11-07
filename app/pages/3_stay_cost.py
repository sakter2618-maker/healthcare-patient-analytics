import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

a, p, h = ui.data()
ui.hero("Length of Stay & Treatment Cost", "How long patients stay and what their treatment costs, by department, "
        "treatment and age.", tags=["Length of Stay", "Treatment Cost"])
if ui.empty_guard(a):
    st.stop()

k = m.kpis(a, p)
cost = m.cost_by_department(a)
long_share = 100 * (a.length_of_stay_days > 10).mean()
ui.kpi_row([
    ui.kpi("Avg length of stay", f"{k['avg_los']:.1f} days", f"median {k['median_los']:.1f}", ui.BLUE, "⏱️"),
    ui.kpi("Stays over 10 days", f"{long_share:.1f}%", f"{(a.length_of_stay_days > 10).sum():,} stays", ui.ORANGE, "📈"),
    ui.kpi("Avg cost per stay", ui.money(k["avg_cost"]), "all departments", ui.TEAL, "💵"),
    ui.kpi("Cost per bed-day", ui.money(a.treatment_cost.sum() / a.length_of_stay_days.sum()), "total cost ÷ bed-days",
           ui.VIOLET, "🛏️"),
    ui.kpi("Highest-cost department", cost.department[0], f"{ui.money(cost.avg_cost[0])} per stay", ui.PINK, "🏷️"),
])

c1, c2 = st.columns(2)
with c1:
    ui.show(ui.hbar(cost, "department", "avg_cost", "Average treatment cost per stay", "Q3",
                    fmt="${:,.0f}", color=ui.DEPT_COLORS, height=330))
with c2:
    los = m.los_by(a, "department").sort_values("avg_los")
    fig = go.Figure()
    fig.add_bar(y=los.department, x=los.avg_los, orientation="h", name="Average",
                marker=dict(color=[ui.DEPT_COLORS[d] for d in los.department], cornerradius=4),
                text=[f"{v:.1f} d" for v in los.avg_los], textposition="outside",
                hovertemplate="%{y}: %{x:.2f} days average<extra></extra>")
    fig.add_scatter(y=los.department, x=los.p90_los, mode="markers", name="90th percentile",
                    marker=dict(symbol="line-ns-open", size=16, color=ui.INK, line=dict(width=2)),
                    hovertemplate="%{y}: 1 in 10 stays longer than %{x:.1f} days<extra></extra>")
    ui.show(ui.style(fig, 330, True, "Length of stay by department", "bar = average, tick = 90th percentile"))

ct = m.cost_by_treatment(a)
fig = go.Figure(go.Heatmap(z=ct.values, x=ct.columns, y=ct.index, colorscale=[[0, "#ecfeff"], [1, "#0e7490"]],
                           text=[[f"${v:,.0f}" for v in row] for row in ct.values], texttemplate="%{text}",
                           textfont=dict(size=12), hovertemplate="%{y} · %{x}: %{text}<extra></extra>",
                           showscale=False, xgap=3, ygap=3))
ui.show(ui.style(fig, 330, False, "Average cost by department and treatment type", "surgery roughly doubles the bill"))

c1, c2 = st.columns(2)
with c1:
    dist = m.los_distribution(a)
    fig = go.Figure(go.Bar(x=dist.band, y=dist.share, marker=dict(color=ui.BLUE, cornerradius=4),
                           text=[f"{v:.1f}%" for v in dist.share], textposition="outside",
                           hovertemplate="%{x}: %{y:.1f}% of stays<extra></extra>"))
    fig.update_yaxes(ticksuffix="%")
    ui.show(ui.style(fig, 320, False, "How long patients stay", "share of all stays"))
with c2:
    la = m.los_by(a, "age_group")
    fig = go.Figure(go.Bar(x=la.age_group.astype(str), y=la.avg_los, marker=dict(color=ui.TEAL, cornerradius=4),
                           text=[f"{v:.1f} d" for v in la.avg_los], textposition="outside",
                           hovertemplate="Age %{x}: %{y:.2f} days<extra></extra>"))
    ui.show(ui.style(fig, 320, False, "Average stay by age group", "60+ patients stay longest"))
ui.footer()
