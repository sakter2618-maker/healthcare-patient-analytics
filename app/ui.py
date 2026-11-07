"""
ui.py — shared look & feel for every dashboard page: colors, CSS, KPI cards, chart style,
cached data and the sidebar filters.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics as m  # noqa: E402

# Categorical palette (validated for color-blind separation) + reserved status colors
SERIES = ["#0891b2", "#e8710a", "#6d28d9", "#65a30d", "#db2777", "#2563eb"]
TEAL, ORANGE, VIOLET, LIME, PINK, BLUE = SERIES
GOOD, WARN, BAD = "#16a34a", "#f59e0b", "#dc2626"
INK, INK_2, MUTED, GRID, AXIS = "#0f172a", "#475569", "#94a3b8", "#e2e8f0", "#cbd5e1"
SOFT = "#a5d8e6"                                     # neutral bar fill (one-series charts)
DEPT_COLORS = dict(zip(["General Medicine", "Cardiology", "Orthopedics", "Neurology", "Oncology", "Pediatrics"], SERIES))

CSS = """
<style>
:root { --ink:#0f172a; --ink2:#475569; --muted:#94a3b8; --line:rgba(15,23,42,.08); }
.block-container { padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1400px; }
html, body, [class*="css"] { font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }

.hero { position:relative; overflow:hidden; border-radius: 20px; padding: 24px 28px; margin-bottom: 18px; color:#fff;
        background: radial-gradient(1200px 300px at 110% -40%, rgba(255,255,255,.18), transparent 60%),
                    linear-gradient(118deg, #0b4f6c 0%, #0e7490 42%, #0891b2 70%, #2563eb 125%);
        box-shadow: 0 14px 34px -14px rgba(14,116,144,.55); }
.hero::after { content:"+"; position:absolute; right:26px; top:-18px; font-size:150px; font-weight:200;
               color: rgba(255,255,255,.10); line-height:1; }
.hero h1 { color:#fff; font-size: 1.7rem; margin: 2px 0 6px; line-height: 1.22; font-weight: 760; letter-spacing:-.01em; }
.hero p  { color: rgba(255,255,255,.9); margin: 0; font-size: .96rem; max-width: 900px; }
.hero .tag { display:inline-block; background: rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.3);
             padding: 2px 11px; border-radius: 999px; font-size: .74rem; margin: 0 6px 6px 0; font-weight:600; }

.kpi-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 4px 0 18px; }
.kpi { background:#fff; border:1px solid var(--line); border-radius: 16px; padding: 14px 16px 12px;
       box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 8px 20px -14px rgba(15,23,42,.18); position:relative; }
.kpi .icon { position:absolute; right:12px; top:12px; width:30px; height:30px; border-radius:10px; display:grid;
             place-items:center; font-size:15px; background: color-mix(in srgb, var(--accent) 14%, white); }
.kpi .label { color: var(--ink2); font-size: .74rem; font-weight: 650; text-transform: uppercase; letter-spacing: .05em;
              padding-right: 34px; }
.kpi .value { color: var(--ink); font-size: 1.68rem; font-weight: 780; margin: 4px 0 2px; line-height: 1.15; }
.kpi .note  { color: var(--muted); font-size: .78rem; }
.kpi .bar { height:4px; border-radius:4px; background: var(--accent); width: 34px; margin-top: 8px; }
.pill { display:inline-block; font-size:.7rem; font-weight:700; padding:1px 8px; border-radius:999px; margin-right:4px; color:#fff; }
.pill.good { background:#16a34a; } .pill.warn { background:#f59e0b; color:#0f172a; } .pill.bad { background:#dc2626; }

.sec { font-size: 1.1rem; font-weight: 740; color: var(--ink); margin: 20px 0 2px; }
.sec-sub { color: var(--ink2); font-size: .86rem; margin: 0 0 8px; }
.insight { border-radius: 16px; padding: 14px 16px; margin: 6px 0 10px; background:#fff; border:1px solid var(--line);
           border-left: 5px solid var(--accent); height: 100%; box-shadow: 0 8px 20px -16px rgba(15,23,42,.25); }
.insight .q { font-size: .74rem; font-weight: 700; color: var(--ink2); text-transform: uppercase; letter-spacing:.05em; }
.insight .a { font-size: 1.04rem; font-weight: 760; color: var(--ink); margin: 5px 0 4px; line-height:1.3; }
.insight .d { font-size: .85rem; color: var(--ink2); line-height:1.45; }
.callout { background: linear-gradient(90deg, #ecfeff, #f0f9ff); border:1px solid #bae6fd; border-radius: 14px;
           padding: 12px 16px; color:#0c4a6e; font-size:.9rem; margin: 8px 0 14px; }
.foot { color: var(--muted); font-size: .78rem; margin-top: 28px; border-top:1px solid var(--line); padding-top:10px; }
.chart-title { font-size: .98rem; font-weight: 720; color: var(--ink); margin: 14px 0 6px; line-height: 1.3; }
.chart-title span { font-weight: 500; color: var(--ink2); font-size:.85rem; }
[data-testid="stPlotlyChart"] { background:#fff; border:1px solid var(--line); border-radius:16px; padding: 6px 6px 0;
                                 box-shadow: 0 8px 20px -18px rgba(15,23,42,.3); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #f0fdfa 0%, #f8fafc 60%); }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

@media (max-width: 640px) {
  .hero { padding: 16px 16px; border-radius: 16px; } .hero h1 { font-size: 1.25rem; } .hero::after { display:none; }
  .kpi .value { font-size: 1.3rem; } .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .block-container { padding-left: 1rem; padding-right: 1rem; }
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading hospital data…")
def load():
    d = m.load()
    return {k: v.copy() for k, v in d.items()}


def data():
    """Admissions + appointments filtered by the sidebar."""
    d = load()
    f = st.session_state.get("filters") or {}
    a = m.filt(d["admissions"], f.get("hospitals"), f.get("departments"), f.get("start"), f.get("end"), "admit_datetime")
    p = m.filt(d["appointments"], f.get("hospitals"), f.get("departments"), f.get("start"), f.get("end"),
               "appointment_datetime")
    return a, p, d["hospitals"]


# ---------------------------------------------------------------------------- blocks
def hero(title, subtitle, tags=()):
    t = "".join(f'<span class="tag">{x}</span>' for x in tags)
    st.markdown(f'<div class="hero">{t}<h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def kpi(label, value, note="", accent=TEAL, icon="", status=None):
    pill = ""
    if status:
        pill = f'<span class="pill {status}">{ {"good": "✓ Good", "warn": "! Watch", "bad": "✕ Act"}[status] }</span>'
    ic = f'<div class="icon">{icon}</div>' if icon else ""
    return (f'<div class="kpi" style="--accent:{accent}">{ic}<div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="note">{pill}{note}</div><div class="bar"></div></div>')


def kpi_row(cards):
    st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def section(title, sub=""):
    st.markdown(f'<div class="sec">{title}</div>' + (f'<div class="sec-sub">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def insight(q, a, d, accent=TEAL):
    st.markdown(f'<div class="insight" style="--accent:{accent}"><div class="q">{q}</div><div class="a">{a}</div>'
                f'<div class="d">{d}</div></div>', unsafe_allow_html=True)


def callout(html):
    st.markdown(f'<div class="callout">{html}</div>', unsafe_allow_html=True)


def footer():
    st.markdown('<div class="foot">Healthcare Patient Analytics · Portfolio project by Salma Akter · '
                'All data is synthetic and de-identified (src/generate_data.py); hospital names are fictional '
                'and no real patient information is used.</div>', unsafe_allow_html=True)


def style(fig: go.Figure, height=360, legend=True, title="", sub=""):
    fig.update_layout(
        height=height, template="plotly_white", title=None,
        meta={"ui_title": title, "ui_sub": sub},
        font=dict(family="Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif", size=12, color=INK_2),
        margin=dict(l=8, r=36, t=12, b=8), paper_bgcolor="#fff", plot_bgcolor="#fff",
        hoverlabel=dict(bgcolor="#fff", font_size=12, font_color=INK, bordercolor=AXIS),
        showlegend=legend and len(fig.data) > 1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="", font=dict(size=11)),
        bargap=0.3,
    )
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    fig.update_traces(cliponaxis=False, selector=dict(type="scatter"))
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickfont=dict(color=MUTED), automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS, tickfont=dict(color=MUTED), automargin=True)
    return fig


def show(fig):
    meta = fig.layout.meta if isinstance(fig.layout.meta, dict) else {}
    if meta.get("ui_title"):
        sub = f' <span>· {meta["ui_sub"]}</span>' if meta.get("ui_sub") else ""
        st.markdown(f'<div class="chart-title">{meta["ui_title"]}{sub}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": True})


def hbar(df, y, x, title, sub="", fmt="{:,.0f}", color=None, height=300, highlight=None):
    """Horizontal bar, largest on top, value labels; optional highlight of one category."""
    df = df.sort_values(x)
    if color is None:
        colors = [TEAL if (highlight is None or v == highlight) else SOFT for v in df[y]]
    else:
        colors = [color.get(v, SOFT) for v in df[y]] if isinstance(color, dict) else color
    fig = go.Figure(go.Bar(x=df[x], y=df[y], orientation="h", marker=dict(color=colors, cornerradius=4),
                           text=[fmt.format(v) for v in df[x]], textposition="outside",
                           hovertemplate="%{y}: %{text}<extra></extra>"))
    fig.update_xaxes(range=[0, float(df[x].max()) * 1.22])     # room for the value labels
    return style(fig, height, False, title, sub)


def short(names):
    """'Riverside Community Hospital' -> 'Riverside' (keeps chart labels horizontal)."""
    return [n.split()[0] for n in names]


def money(x):
    x = float(x)
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.1f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:,.1f}K"
    return f"${x:,.0f}"


def empty_guard(*dfs) -> bool:
    if any(df is None or len(df) == 0 for df in dfs):
        st.info("No records match the current filters. Clear a filter or widen the date range in the sidebar.")
        return True
    return False
