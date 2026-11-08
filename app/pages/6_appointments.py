import plotly.graph_objects as go
import streamlit as st

from app import ui
from app.ui import m

a, p, h = ui.data()
ui.hero("Appointments & No-shows", "Outpatient appointments: who misses them, when, and what reduces no-shows.",
        tags=["Appointments", "No-show rate"])
if ui.empty_guard(p):
    st.stop()

n = m.noshow_summary(p)
ui.kpi_row([
    ui.kpi("Appointments", f"{len(p):,}", f"{(p.status == 'Attended').mean() * 100:.1f}% attended", ui.TEAL, "📅"),
    ui.kpi("No-show rate", f"{n['rate']:.1f}%", f"{n['no_shows']:,} missed visits", ui.VIOLET, "🚫",
           "good" if n["rate"] <= 10 else ("warn" if n["rate"] <= 15 else "bad")),
    ui.kpi("Cancellation rate", f"{n['cancel_rate']:.1f}%", "cancelled in advance", ui.ORANGE, "↩️"),
    ui.kpi("Missed slots / week", f"{n['missed_slots_per_week']:,.0f}", "clinic capacity lost", ui.PINK, "⌛"),
    ui.kpi("SMS reminder effect", f"{n['sms_no'] - n['sms_yes']:.1f} pts", f"{n['sms_yes']:.1f}% with vs {n['sms_no']:.1f}% without",
           ui.GOOD, "💬"),
])

c1, c2 = st.columns(2)
with c1:
    nb = m.noshow_by(p, "lead_time_band", m.BAND_ORDER)
    fig = go.Figure(go.Bar(x=nb.lead_time_band.astype(str), y=nb.noshow_rate, marker=dict(color=ui.VIOLET, cornerradius=4),
                           text=[f"{v:.1f}%" for v in nb.noshow_rate], textposition="outside", customdata=nb.appointments,
                           hovertemplate="Booked %{x} ahead: %{y:.1f}% no-show<br>%{customdata:,} appointments<extra></extra>"))
    fig.update_yaxes(ticksuffix="%")
    ui.show(ui.style(fig, 330, False, "No-show rate by booking lead time", "the longer the wait, the more no-shows"))
with c2:
    sm = m.noshow_by(p[p.sms_reminder != "Unknown"], "sms_reminder")
    fig = go.Figure(go.Bar(x=["SMS reminder sent" if v == "Yes" else "No reminder" for v in sm.sms_reminder],
                           y=sm.noshow_rate, marker=dict(color=[ui.GOOD if v == "Yes" else ui.SOFT for v in sm.sms_reminder],
                                                         cornerradius=4),
                           text=[f"{v:.1f}%" for v in sm.noshow_rate], textposition="outside",
                           hovertemplate="%{x}: %{y:.1f}% no-show<extra></extra>"))
    fig.update_yaxes(ticksuffix="%")
    ui.show(ui.style(fig, 330, False, "Do SMS reminders help?", "Q5"))

c1, c2 = st.columns(2)
with c1:
    hm = (p.groupby(["weekday", "age_group"], observed=True).no_show.mean().mul(100).unstack()
          .reindex(m.WEEKDAYS))
    fig = go.Figure(go.Heatmap(z=hm.values, x=[str(c) for c in hm.columns], y=hm.index,
                               colorscale=[[0, "#f5f3ff"], [1, "#6d28d9"]], showscale=False, xgap=3, ygap=3,
                               text=[[f"{v:.1f}%" for v in row] for row in hm.values], texttemplate="%{text}",
                               hovertemplate="%{y}, age %{x}: %{text}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    ui.show(ui.style(fig, 330, False, "No-show rate by weekday and age group", "18–30 on Mondays and Fridays"))
with c2:
    dp = m.noshow_by(p, "department")
    ui.show(ui.hbar(dp, "department", "noshow_rate", "No-show rate by department", fmt="{:.1f}%",
                    color=ui.DEPT_COLORS, height=330))

mo = m.appointments_monthly(p)
fig = go.Figure()
fig.add_bar(x=mo.month, y=mo.appointments, name="Appointments", marker=dict(color=ui.SOFT, cornerradius=3),
            hovertemplate="%{x|%b %Y}: %{y:,} appointments<extra></extra>")
ui.show(ui.style(fig, 280, False, "Appointments per month"))
ui.callout("<b>Actions (based on the full dataset):</b> send SMS reminders to every patient (today about 3 in 10 get none), add a second "
           "reminder for visits booked 30+ days ahead, and overbook slightly on Monday/Friday slots for 18–30 year olds.")
ui.footer()
