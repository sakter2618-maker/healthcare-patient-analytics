import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

a, p, h = ui.data()
ui.hero("Hospital Performance", "How the 5 hospitals compare on length of stay, readmissions, recovery, cost and no-shows.",
        tags=["Hospital Performance", "Scorecard"])
if ui.empty_guard(a, p):
    st.stop()

hp = m.hospital_performance(a, p, h)
best, worst = hp.iloc[0], hp.iloc[-1]
c1, c2, c3 = st.columns(3)
with c1:
    ui.insight("Best performer", best.hospital_name,
               f"Score {best.performance_score:.0f}: {best.readmission_rate:.1f}% readmitted, "
               f"{best.avg_los:.1f}-day average stay, recovery {best.avg_recovery:.1f}/100.", ui.GOOD)
with c2:
    ui.insight("Needs attention", worst.hospital_name,
               f"{worst.readmission_rate:.1f}% readmitted ({worst.readmission_rate - best.readmission_rate:+.1f} pts vs best) "
               f"and stays {worst.avg_los - best.avg_los:+.1f} days longer on average.", ui.BAD)
with c3:
    extra_days = (worst.avg_los - hp.avg_los.median()) * worst.admissions
    ui.insight("What the gap costs", f"≈ {extra_days:,.0f} extra bed-days",
               f"If {worst.hospital_name.split()[0]} matched the median stay it would free about "
               f"{extra_days / 365:,.0f} beds a year.", ui.ORANGE)

ui.section("Scorecard", "Performance score: 100 = best of the five, 50 = weakest (readmissions 35%, stay 25%, "
           "recovery 25%, no-shows 15%).")
tbl = hp[["hospital_name", "hospital_type", "region", "admissions", "avg_los", "readmission_rate", "avg_recovery",
          "avg_cost", "noshow_rate", "performance_score"]]
st.dataframe(tbl, hide_index=True, width="stretch", column_config={
    "hospital_name": "Hospital", "hospital_type": "Type", "region": "Region",
    "admissions": st.column_config.NumberColumn("Admissions", format="%d"),
    "avg_los": st.column_config.NumberColumn("Avg stay (days)", format="%.2f"),
    "readmission_rate": st.column_config.NumberColumn("Readmission %", format="%.1f%%"),
    "avg_recovery": st.column_config.NumberColumn("Recovery score", format="%.1f"),
    "avg_cost": st.column_config.NumberColumn("Avg cost", format="$%,.0f"),
    "noshow_rate": st.column_config.NumberColumn("No-show %", format="%.1f%%"),
    "performance_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
})

c1, c2 = st.columns(2)
short = ui.short(hp.hospital_name)
with c1:
    fig = go.Figure()
    for i, r in hp.iterrows():
        fig.add_scatter(x=[r.avg_los], y=[r.readmission_rate], mode="markers+text", name=short[i],
                        marker=dict(size=12 + r.admissions / 300, color=ui.SERIES[i % 6],
                                    line=dict(color="#fff", width=2)),
                        text=[short[i]], textposition="top center", textfont=dict(color=ui.INK_2, size=11),
                        hovertemplate=f"{r.hospital_name}<br>Avg stay %{{x:.2f}} days<br>Readmitted %{{y:.1f}}%"
                                      f"<br>{r.admissions:,} admissions<extra></extra>")
    fig.update_xaxes(title="Average length of stay (days)")
    fig.update_yaxes(title="30-day readmission rate (%)")
    ui.show(ui.style(fig, 380, False, "Longer stays go with more readmissions", "bubble size = admissions"))
with c2:
    fig = go.Figure(go.Bar(x=short, y=hp.avg_recovery, marker=dict(color=ui.TEAL, cornerradius=4),
                           text=[f"{v:.1f}" for v in hp.avg_recovery], textposition="outside",
                           hovertemplate="%{x}: recovery score %{y:.1f}<extra></extra>"))
    fig.update_yaxes(range=[50, 80], title="Average recovery score (0–100)")
    ui.show(ui.style(fig, 380, False, "Average recovery score at discharge", "axis starts at 50"))

mo = a.assign(month=a.admit_datetime.dt.to_period("Q").dt.to_timestamp()).groupby(["month", "hospital_name"]) \
      .readmitted_30d.mean().mul(100).reset_index()
fig = go.Figure()
for i, name in enumerate(hp.hospital_name):
    s = mo[mo.hospital_name == name]
    fig.add_scatter(x=s.month, y=s.readmitted_30d, name=name, mode="lines+markers",
                    line=dict(color=ui.SERIES[i % 6], width=2), marker=dict(size=8),
                    hovertemplate=f"{name}<br>%{{x|Q%q %Y}}: %{{y:.1f}}%<extra></extra>")
fig.update_yaxes(ticksuffix="%")
ui.show(ui.style(fig, 340, True, "Readmission rate by quarter", "the gap is persistent, not a one-off"))
ui.footer()
