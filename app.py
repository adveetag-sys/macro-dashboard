"""Macro Dashboard: USA -> India.   Run locally with:  streamlit run app.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import INDICATORS, PULSE, STAGES, TRENDS
from topics import TOPICS

st.set_page_config(page_title="Macro Dashboard · USA → India", layout="wide")

IND = {i["k"]: i for i in INDICATORS}
STAGE_COLOR = {"L": "#60A5FA", "T": "#A78BFA", "R": "#2DD4BF", "F": "#FBBF24"}
SIG_TEXT = {"T": "▲ Tailwind", "H": "▼ Headwind", "N": "● Neutral", "": "No data"}
SIG_STYLE = {"T": ("#0F3B2A", "#6EE7B7"), "H": ("#46161B", "#FCA5A5"), "N": ("#1F2A44", "#C7CEDB"), "": ("#1F2A44", "#8A93A4")}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.markdown("""<style>
.block-container{padding-top:1.5rem;max-width:1440px}
.pill{display:inline-block;font-size:12px;font-weight:700;padding:2px 9px;border-radius:999px;white-space:nowrap}
.cap{font-size:11px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#A3ADBF;margin:0}
.big{font-family:ui-monospace,Menlo,monospace;font-weight:700;font-size:26px;color:#F9FAFB}
.stagehead{border-top:4px solid;padding:10px 4px 6px;margin-bottom:4px}
.rowline{display:flex;justify-content:space-between;gap:8px;align-items:baseline;font-size:14px}
.rowline b{font-family:ui-monospace,Menlo,monospace}
.muted{color:#A3ADBF;font-size:13px}
</style>""", unsafe_allow_html=True)


# ---------- data ----------
@st.cache_data(ttl=3600)
def load():
    vals = pd.read_csv("data/monthly.csv", index_col="month")
    sigs = pd.read_csv("data/signals.csv", index_col="month", dtype=str).fillna("")
    asof = pd.read_csv("data/asof.csv", index_col="month", dtype=str).fillna("") if Path("data/asof.csv").exists() else sigs.copy().replace(r".*", "", regex=True)
    meta = json.loads(Path("data/meta.json").read_text()) if Path("data/meta.json").exists() else {}
    ev_path = Path("data/manual/events.csv")
    events = pd.read_csv(ev_path, comment="#", parse_dates=["date"]) if ev_path.exists() else pd.DataFrame(columns=["date", "event"])
    return vals, sigs, asof, meta, events


if not Path("data/monthly.csv").exists():
    st.error("No data yet. Run `python fetch.py` and then `python build.py` (see README).")
    st.stop()

vals, sigs, asof, meta, events = load()
months = list(vals.index)


def fmt(k, v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return IND[k]["fmt"].format(v)


def pill(code):
    bg, fg = SIG_STYLE.get(code, SIG_STYLE[""])
    return f'<span class="pill" style="background:{bg};color:{fg}">{SIG_TEXT.get(code, "")}</span>'


def label_month(m):
    y, mm = m.split("-")
    return f"{MONTHS[int(mm) - 1]} {y}"


def asof_note(k, month):
    a = asof.loc[month, k] if k in asof.columns else ""
    return f"as of {label_month(a)}" if a and a != month else ""


def first_of_topic(topic):
    return next(i["k"] for i in INDICATORS if i["topic"] == topic)


def open_page(k):
    st.session_state.open = k


CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False}


def sparkline(series, color, height=70, marker=None, k=None):
    """Line chart: hover shows month + value. Zoom, pan and drag are switched off."""
    s = series.copy()
    s.index = pd.PeriodIndex(s.index, freq="M").to_timestamp()
    labels = [fmt(k, v) if k else f"{v:,.2f}" for v in s.values]
    fig = go.Figure(go.Scatter(
        x=s.index, y=s.values, mode="lines", line=dict(color=color, width=2), connectgaps=False,
        customdata=labels, hovertemplate="%{x|%b %Y}<br><b>%{customdata}</b><extra></extra>"))
    if marker is not None:
        fig.add_vline(x=pd.Period(marker, "M").to_timestamp(), line=dict(color="#FCD34D", width=1, dash="dot"))
    big = height > 80
    axis = dict(gridcolor="#1F2A44", fixedrange=True, showspikes=True, spikemode="across", spikesnap="data",
                spikethickness=1, spikedash="solid", spikecolor="#64748B")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False, dragmode=False, hovermode="x",
                      hoverlabel=dict(bgcolor="#111A2E", bordercolor=color, font=dict(color="#E5E7EB", size=13)),
                      xaxis=dict(axis, visible=big), yaxis=dict(axis, visible=big, showspikes=False))
    return fig


# ---------- state & header ----------
ss = st.session_state
ss.setdefault("month", months[-1])
ss.setdefault("open", None)
ss.setdefault("view", "Dashboard")

top_l, top_r = st.columns([3, 2])
with top_l:
    st.markdown(f"<p class='cap'>Data to {label_month(months[-1])} · updated {meta.get('built_at', '?')[:10]}</p>", unsafe_allow_html=True)
    st.title(f"Macro Dashboard · {label_month(ss.month)}")
    ss.view = st.radio("View", ["Dashboard", "Understand the flow"], horizontal=True, label_visibility="collapsed",
                       index=0 if ss.view == "Dashboard" else 1)
with top_r:
    years = sorted({m[:4] for m in months}, reverse=True)
    c1, c2 = st.columns(2)
    year = c1.selectbox("Year", years, index=years.index(ss.month[:4]))
    in_year = [m for m in months if m.startswith(year)]
    cur_mm = ss.month if ss.month in in_year else in_year[-1]
    month = c2.selectbox("Month", in_year, index=in_year.index(cur_mm), format_func=lambda m: MONTHS[int(m[5:]) - 1])
    if month != ss.month:
        ss.month, ss.open = month, None
        st.rerun()

m = ss.month
row_v, row_s = vals.loc[m], sigs.loc[m]


# ---------- detail page ----------
def detail_page(k):
    ind, t = IND[k], TOPICS[IND[k]["topic"]]
    st.button(f"← Back to {label_month(m)}", on_click=open_page, args=(None,))
    a, b = st.columns([3, 2])
    a.markdown(f"<p class='cap' style='color:{STAGE_COLOR[ind['stage']]}'>{STAGES[ind['stage']][1]}</p>", unsafe_allow_html=True)
    a.header(ind["label"])
    a.caption(f"{ind['sub']} · updates {t['freq']}" + (f" · latest reading {asof_note(k, m)}" if asof_note(k, m) else ""))
    b.markdown(f"<p class='cap'>On {label_month(m)}</p><div class='big'>{fmt(k, row_v[k])}</div>{pill(row_s[k])} for India",
               unsafe_allow_html=True)
    c = st.columns(3)
    for col, title, text in zip(c, ["What it is", "How it works", "Why India cares"], [t["what"], t["how"], t["india"]]):
        with col.container(border=True):
            st.markdown(f"<p class='cap'>{title}</p>", unsafe_allow_html=True)
            st.write(text)
    left, right = st.columns([3, 2])
    with left.container(border=True):
        st.markdown("<p class='cap'>Full history since 1995 · dotted line = selected month</p>", unsafe_allow_html=True)
        st.plotly_chart(sparkline(vals[k].dropna(), STAGE_COLOR[ind["stage"]], height=320, marker=m, k=k), width="stretch", config=CHART_CONFIG)
        counts = sigs[k].value_counts()
        st.caption(f"Since 1995: headwind in {counts.get('H', 0)} months, tailwind in {counts.get('T', 0)}, neutral in {counts.get('N', 0)}.")
    with right.container(border=True):
        st.markdown("<p class='cap'>Last 24 months</p>", unsafe_allow_html=True)
        idx = months.index(m)
        hist = pd.DataFrame({"Month": [label_month(x) for x in months[max(0, idx - 23): idx + 1]],
                             "Value": [fmt(k, vals.loc[x, k]) for x in months[max(0, idx - 23): idx + 1]],
                             "For India": [SIG_TEXT.get(sigs.loc[x, k], "") for x in months[max(0, idx - 23): idx + 1]]})
        st.dataframe(hist.iloc[::-1], hide_index=True, width="stretch", height=320)
    with st.container(border=True):
        st.markdown("<p class='cap'>In the chain</p>", unsafe_allow_html=True)
        p, ch = st.columns(2)
        p.write("Driven by")
        for tp in t["parents"] or []:
            p.button(f"← {TOPICS[tp]['name']}", key=f"p-{tp}", on_click=open_page, args=(first_of_topic(tp),))
        if not t["parents"]:
            p.caption("Starts the chain")
        ch.write("Drives")
        for tp in t["children"] or []:
            ch.button(f"{TOPICS[tp]['name']} →", key=f"c-{tp}", on_click=open_page, args=(first_of_topic(tp),))
        if not t["children"]:
            ch.caption("End of the chain")


if ss.open:
    detail_page(ss.open)
    st.stop()


# ---------- regime snapshot ----------
def most_like(m):
    z = (vals - vals.mean()) / vals.std()
    idx = months.index(m)
    best, best_d = None, None
    for j, other in enumerate(months):
        if abs(j - idx) < 12:
            continue  # skip the months right around this one
        diff = (z.loc[other] - z.loc[m]).dropna()
        if len(diff) < 8:
            continue
        d = float((diff ** 2).mean())
        if best_d is None or d < best_d:
            best, best_d = other, d
    if best is None:
        return None, 0, 0
    both = [i["k"] for i in INDICATORS if row_s[i["k"]] and sigs.loc[best, i["k"]]]
    match = sum(row_s[k] == sigs.loc[best, k] for k in both)
    return best, match, len(both)


if ss.view == "Dashboard":
    counts = row_s.value_counts()
    heads = [IND[k]["label"] for k in row_s.index if row_s[k] == "H"]
    tails = [IND[k]["label"] for k in row_s.index if row_s[k] == "T"]
    like, match, both = most_like(m)
    with st.container(border=True):
        st.markdown(f"<p class='cap'>Regime snapshot · {label_month(m)}</p>", unsafe_allow_html=True)
        st.markdown(f"**Headwinds:** {', '.join(heads[:6]) or 'none'}  \n**Tailwinds:** {', '.join(tails[:6]) or 'none'}")
        a, b, c, d = st.columns([1, 1, 1, 2])
        a.markdown(f"<span style='color:#34D399;font-size:22px;font-weight:700'>▲ {counts.get('T', 0)}</span> tailwinds", unsafe_allow_html=True)
        b.markdown(f"<span style='color:#F87171;font-size:22px;font-weight:700'>▼ {counts.get('H', 0)}</span> headwinds", unsafe_allow_html=True)
        c.markdown(f"<span style='color:#C7CEDB;font-size:22px;font-weight:700'>● {counts.get('N', 0)}</span> neutral", unsafe_allow_html=True)
        if like:
            d.markdown(f"Most like: **{label_month(like)}** <span class='muted'>({match} of {both} signals match)</span>", unsafe_allow_html=True)

    # ---------- key market pulse ----------
    cols = st.columns(3)
    idx = months.index(m)
    window = months[max(0, idx - 11): idx + 1]
    for col, pair in zip(cols, PULSE):
        with col.container(border=True):
            for k in pair:
                note = asof_note(k, m)
                st.markdown(f"<p class='cap'>{IND[k]['label']}{' · ' + note if note else ''}</p><div class='rowline'><span class='big'>{fmt(k, row_v[k])}</span>{pill(row_s[k])}</div>",
                            unsafe_allow_html=True)
                s12 = vals.loc[window, k]
                if s12.notna().sum() > 2:
                    st.plotly_chart(sparkline(s12, STAGE_COLOR[IND[k]["stage"]], k=k), width="stretch", config=CHART_CONFIG, key=f"sp-{k}")
                st.button("Open", key=f"pulse-{k}", on_click=open_page, args=(k,))

    # ---------- transmission chain ----------
    st.subheader("Transmission chain")
    st.caption("Change flows left to right. Open any row for its full page.")
    cols = st.columns(4)
    for col, (stage, (num, title, note)) in zip(cols, STAGES.items()):
        with col.container(border=True):
            st.markdown(f"<div class='stagehead' style='border-color:{STAGE_COLOR[stage]}'><b>{num} · {title}</b><br><span class='muted'>{note}</span></div>",
                        unsafe_allow_html=True)
            rows = [i for i in INDICATORS if i["stage"] == stage]

            def draw(i):
                k = i["k"]
                a, b = st.columns([5, 1])
                note = asof_note(k, m)
                a.markdown(f"<div class='rowline'><span>{i['label']}</span><b>{fmt(k, row_v[k])}</b></div>{pill(row_s[k])}"
                           + (f" <span class='muted' style='font-size:12px'>{note}</span>" if note else ""), unsafe_allow_html=True)
                b.button("›", key=f"row-{k}", on_click=open_page, args=(k,), help=f"Open {i['label']}")

            for i in [r for r in rows if r["top"]]:
                draw(i)
            rest = [r for r in rows if not r["top"]]
            if rest:
                with st.expander(f"Show {len(rest)} more"):
                    for i in rest:
                        draw(i)

    # ---------- trends + coming up ----------
    left, right = st.columns([2, 1])
    with left.container(border=True):
        st.subheader("Trends · 1 year")
        tc = st.columns(3)
        for col, k in zip(tc, TRENDS):
            s12 = vals.loc[window, k]
            chg = (s12.iloc[-1] / s12.dropna().iloc[0] - 1) * 100 if s12.notna().sum() > 1 else np.nan
            col.markdown(f"<p class='cap'>{IND[k]['label']}</p><span class='big' style='font-size:20px'>{fmt(k, row_v[k])}</span> "
                         f"<span class='muted'>{'' if np.isnan(chg) else f'{chg:+.1f}%'}</span>", unsafe_allow_html=True)
            if s12.notna().sum() > 2:
                col.plotly_chart(sparkline(s12, STAGE_COLOR[IND[k]["stage"]], height=160, k=k), width="stretch",
                                 config=CHART_CONFIG, key=f"tr-{k}")
    with right.container(border=True):
        st.subheader("Coming up")
        start = pd.Period(m, "M").to_timestamp()
        nxt = events[events["date"] >= start].sort_values("date").head(5)
        if nxt.empty:
            st.caption("Add dates to data/manual/events.csv to list them here.")
        for _, e in nxt.iterrows():
            st.markdown(f"**{e['date']:%d %b %Y}** · {e['event']}")

# ---------- flow view ----------
else:
    st.caption("Change flows from the top down. Pick a box below the chart to open its page.")
    order = ["usdata", "brent", "fed", "incpi", "yields", "dollar", "metals", "usstocks", "fii", "inr", "rbi", "nifty", "vix"]
    fill = {"T": "#0F3B2A", "H": "#46161B", "N": "#1C212C", "": "#1C212C"}
    lines = ['digraph G {', 'rankdir=TB; bgcolor="transparent"; nodesep=0.4; ranksep=0.5;',
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fontcolor="#F3F4F6", penwidth=2];',
             'edge [color="#5B6886", arrowsize=0.7];']
    for tp in order:
        ks = [i["k"] for i in INDICATORS if i["topic"] == tp][:2]
        codes = {row_s[k] for k in ks if row_s[k]}
        code = "H" if codes == {"H"} or ("H" in codes and "T" not in codes) else ("T" if "T" in codes and "H" not in codes else "N")
        stage = IND[ks[0]]["stage"]
        body = "\\n".join(f"{IND[k]['label']}: {fmt(k, row_v[k])}" for k in ks)
        lines.append(f'{tp} [label="{TOPICS[tp]["name"]}\\n{body}\\n{SIG_TEXT[code]}", color="{STAGE_COLOR[stage]}", fillcolor="{fill[code]}"];')
    for tp in order:
        for ch in TOPICS[tp]["children"]:
            lines.append(f"{tp} -> {ch};")
    lines.append("}")
    st.graphviz_chart("\n".join(lines), width="stretch")
    pick = st.selectbox("Open a topic", order, format_func=lambda tp: TOPICS[tp]["name"], index=None, placeholder="Choose a box…")
    if pick:
        ss.open, ss.view = first_of_topic(pick), "Dashboard"
        st.rerun()

st.caption(f"Sources: FRED, Yahoo Finance, RBI, NSDL. Missing indicators: {', '.join(meta.get('missing_indicators', [])) or 'none'}. "
           "Tailwind/headwind labels come from simple rules in config.py, not from a forecast.")
