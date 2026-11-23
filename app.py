"""Macro Dashboard: USA -> India.   Run locally with:  streamlit run app.py"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import INDICATORS, PULSE, STAGES, TRENDS
from topics import TOPICS
from events import EVENTS, KEY
from indicator_info import INFO
import simulator as sim

EVENT_IMPACT = {
    "fomc": ("Fed decision", "Sets US rates. A hike or hawkish tone pushes US yields and the dollar up, which usually means FII selling and a weaker rupee. A cut does the reverse. India reacts the next morning."),
    "rbi": ("RBI decision", "Changes the repo rate and liquidity steps. Moves bond yields, Bank Nifty and the rupee the same day."),
    "us_jobs": ("US jobs", "Strong hiring keeps the Fed tight: yields and the dollar rise. One of the biggest market movers each month."),
    "us_cpi": ("US inflation", "A hot reading raises rate-hike fears: dollar up, FII outflows, pressure on Indian stocks."),
    "in_cpi": ("India inflation", "Above 6% raises the odds of an RBI hike; below 4% opens room for cuts. Moves bond yields and banks."),
    "in_gdp": ("India growth", "Strong growth supports earnings and foreign interest. A weak number raises rate-cut hopes."),
    "pmi": ("Factory surveys", "Early signal of growth turning. Above 50 = expanding."),
    "tax": ("Advance tax", "Companies pay tax to the government, pulling cash out of banks. Liquidity tightens for a few days and short-term rates jump; watch Bank Nifty."),
    "budget": ("Budget", "Sets government borrowing (bond supply, so India 10Y), taxes and spending. Usually a high-volatility day."),
}

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
@st.cache_data(ttl=600)
def load(stamp):
    """stamp = file times, so new data is picked up as soon as it lands."""
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

stamp = tuple(Path(f).stat().st_mtime for f in ["data/monthly.csv", "data/signals.csv", "data/meta.json", "data/manual/events.csv"] if Path(f).exists())
vals, sigs, asof, meta, events = load(stamp)
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


def val_at(k, month):
    return vals.loc[month, k] if month in vals.index else np.nan


def sig_at(k, month):
    return sigs.loc[month, k] if month in sigs.index else ""


SCORED = [i["k"] for i in INDICATORS if i["rule"]["type"] != "neutral"]


TREND = {i["k"] for i in INDICATORS if i["rule"].get("pct")} | {"fedBs", "gold", "silver"}
RATES = {"fed", "us10", "in10y", "gap", "rbi"}


@st.cache_data(show_spinner=False)
def state_ranks(v):
    """Each month described by numbers that are comparable across 25 years, as percentile ranks (0 to 1).
    Prices and balance sheets: 6-month % change (their level only drifts up over time).
    Interest rates: level and 6-month change. Everything else: level."""
    f = {}
    for k in v.columns:
        s = v[k]
        if k in TREND:
            f[k] = s.pct_change(6, fill_method=None) * 100
        elif k in RATES:
            f[k] = s
            f[k + "_chg"] = s.diff(6)
        else:
            f[k] = s
    return pd.DataFrame(f).rank(pct=True)


RANKS = state_ranks(vals)


def label_score(m1, m2):
    """Share of indicators that carry the same headwind/tailwind/neutral label in both months."""
    both = [k for k in SCORED if sig_at(k, m1) and sig_at(k, m2)]
    same = [k for k in both if sig_at(k, m1) == sig_at(k, m2)]
    return (len(same) / len(both) if both else 0.0), len(same), len(both)


def level_score(m1, m2):
    """How close the actual numbers are. Average gap in percentile rank, scaled so identical = 100%,
    two random months = about 33%, opposite ends of history = 0%."""
    if m1 not in RANKS.index or m2 not in RANKS.index:
        return 0.0, 0
    d = (RANKS.loc[m1] - RANKS.loc[m2]).abs().dropna()
    return (max(0.0, 1 - 2 * d.mean()) if len(d) else 0.0), len(d)


def match_score(m1, m2):
    """Half label agreement, half closeness of the actual numbers."""
    lab, same, n = label_score(m1, m2)
    lev, _ = level_score(m1, m2)
    return 0.5 * lab + 0.5 * lev, same, n, lab, lev


def first_of_topic(topic):
    return next(i["k"] for i in INDICATORS if i["topic"] == topic)


def open_page(k):
    st.session_state.open = k


CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False}


def sparkline(series, color, height=70, marker=None, k=None, shade=None):
    """Line chart: hover shows month + value. Zoom, pan and drag are switched off."""
    s = series.copy()
    s.index = pd.PeriodIndex(s.index, freq="M").to_timestamp()
    labels = [fmt(k, v) if k else f"{v:,.2f}" for v in s.values]
    fig = go.Figure(go.Scatter(
        x=s.index, y=s.values, mode="lines", line=dict(color=color, width=2), connectgaps=False,
        customdata=labels, hovertemplate="%{x|%b %Y}<br><b>%{customdata}</b><extra></extra>"))
    for a, b, c in shade or []:
        fig.add_vrect(x0=pd.Period(a, "M").to_timestamp(), x1=pd.Period(b, "M").to_timestamp("M"),
                      fillcolor=c, opacity=0.18, line_width=0, layer="below")
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
    VIEWS = ["Dashboard", "Understand the flow", "Past events", "Compare to past events", "Simulator"]
    ss.view = st.radio("View", VIEWS, horizontal=True, label_visibility="collapsed",
                       index=VIEWS.index(ss.view) if ss.view in VIEWS else 0)
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
    info = INFO.get(k, {})
    c = st.columns(2)
    with c[0].container(border=True):
        st.markdown("<p class='cap'>What it is</p>", unsafe_allow_html=True)
        st.write(info.get("what", t["what"]))
        st.markdown("<p class='cap'>Where it comes from</p>", unsafe_allow_html=True)
        st.write(info.get("source", ""))
    with c[1].container(border=True):
        st.markdown("<p class='cap'>How to read it</p>", unsafe_allow_html=True)
        st.write(info.get("read", t["how"]))
        st.markdown("<p class='cap'>What to watch</p>", unsafe_allow_html=True)
        st.write(info.get("watch", ""))
    with st.container(border=True):
        st.markdown("<p class='cap'>How it reaches India</p>", unsafe_allow_html=True)
        st.write(info.get("path", t["india"]))
    left, right = st.columns([3, 2])
    with left.container(border=True):
        span = st.radio("Range", ["Last 10 years", "Full history"], horizontal=True, label_visibility="collapsed", key=f"span-{k}")
        s_all = vals[k].dropna()
        if span == "Last 10 years":
            s_all = s_all[s_all.index >= str(int(m[:4]) - 10) + m[4:]]
            s_all = s_all[s_all.index <= months[-1]]
        shade = [(e["runup"], e["worst"], e["color"]) for e in EVENTS.values()
                 if len(s_all) and e["worst"] >= s_all.index[0] and e["runup"] <= s_all.index[-1]]
        st.markdown("<p class='cap'>Dotted line = selected month · shaded = past events (run-up to worst)</p>", unsafe_allow_html=True)
        st.plotly_chart(sparkline(s_all, STAGE_COLOR[ind["stage"]], height=320, marker=m, k=k, shade=shade), width="stretch", config=CHART_CONFIG)
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
        st.markdown("<p class='cap'>In past events</p>", unsafe_allow_html=True)
        rows = []
        for e in EVENTS.values():
            rows.append({"Event": e["name"],
                         "Run-up": f"{fmt(k, val_at(k, e['runup']))}  ({label_month(e['runup'])})",
                         "Worst point": f"{fmt(k, val_at(k, e['worst']))}  ({label_month(e['worst'])})",
                         "For India at worst": SIG_TEXT.get(sig_at(k, e["worst"]), "")})
        rows.append({"Event": "Selected month", "Run-up": "", "Worst point": f"{fmt(k, row_v[k])}  ({label_month(m)})",
                     "For India at worst": SIG_TEXT.get(row_s[k], "")})
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, width="stretch")
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
            rows = [i for i in INDICATORS if i["stage"] == stage and vals[i["k"]].notna().any()]  # hide rows with no data at all

            def draw(i):
                k = i["k"]
                a, b = st.columns([5, 1])
                note = asof_note(k, m)
                a.markdown(f"<div class='rowline'><span>{i['label']}</span><b>{fmt(k, row_v[k])}</b></div>{pill(row_s[k])}"
                           + (f" <span class='muted' style='font-size:12px'>{note}</span>" if note else ""), unsafe_allow_html=True)
                b.button("›", key=f"row-{k}", on_click=open_page, args=(k,), help=f"Open {i['label']}")

            for i in rows:
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
        nxt = events[events["date"] >= start].sort_values("date").head(8)
        if nxt.empty:
            st.caption("Add dates to data/manual/events.csv to list them here.")
        for _, e in nxt.iterrows():
            tag, note = EVENT_IMPACT.get(str(e.get("type", "")).strip(), ("", ""))
            st.markdown(f"**{e['date']:%d %b %Y}** · {e['event']}"
                        + (f"<br><span class='muted' style='font-size:12px'><b>{tag}:</b> {note}</span>" if note else ""),
                        unsafe_allow_html=True)

# ---------- flow view ----------
elif ss.view == "Understand the flow":
    st.caption("Change flows from the top down. Pick a box below the chart to open its page.")
    order = ["usdata", "brent", "fed", "incpi", "yields", "dollar", "metals", "usstocks", "fii", "inr", "rbi", "nifty", "vix"]
    fill = {"T": "#0F3B2A", "H": "#46161B", "N": "#1C212C", "": "#1C212C"}
    lines = ['digraph G {', 'rankdir=TB; bgcolor="transparent"; nodesep=0.4; ranksep=0.5;',
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fontcolor="#F3F4F6", penwidth=2];',
             'edge [color="#5B6886", arrowsize=0.7];']
    for tp in order:
        ks = [i["k"] for i in INDICATORS if i["topic"] == tp and vals[i["k"]].notna().any()]
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


# ---------- past events ----------
elif ss.view == "Past events":
    keys = list(EVENTS)
    ek = st.radio("Event", keys, horizontal=True, format_func=lambda x: EVENTS[x]["name"], label_visibility="collapsed")
    e = EVENTS[ek]
    a, b = st.columns([3, 2])
    a.header(e["name"])
    a.markdown(f"**Trigger:** {e['trigger']}")
    b.markdown(f"<p class='cap'>Timeline</p>"
               f"<div class='rowline'><span>Run-up</span><b>{label_month(e['runup'])}</b></div>"
               f"<div class='rowline'><span>Worst for India</span><b>{label_month(e['worst'])}</b></div>"
               f"<div class='rowline'><span>Calmer again</span><b>{label_month(e['calm'])}</b></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<p class='cap'>What happened</p>", unsafe_allow_html=True)
        st.write(e["story"])
    st.markdown("<p class='cap'>How the chain fired</p>", unsafe_allow_html=True)
    cc = st.columns(4)
    for col, (stage, (title, text)) in zip(cc, zip(STAGES, e["chain"])):
        with col.container(border=True):
            st.markdown(f"<div class='stagehead' style='border-color:{STAGE_COLOR[stage]}'><b>{title}</b></div>", unsafe_allow_html=True)
            st.write(text)
    with st.container(border=True):
        st.markdown("<p class='cap'>Key numbers · run-up vs worst point · and today</p>", unsafe_allow_html=True)
        rows = []
        for k in KEY:
            v1, v2 = val_at(k, e["runup"]), val_at(k, e["worst"])
            rows.append({"Indicator": IND[k]["label"], f"Run-up · {label_month(e['runup'])}": fmt(k, v1),
                         f"Worst · {label_month(e['worst'])}": fmt(k, v2), "For India at worst": SIG_TEXT.get(sig_at(k, e["worst"]), ""),
                         f"Today · {label_month(m)}": fmt(k, row_v[k])})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("— means no data for that month (for example, FII data starts in 2014 and India VIX in 2008).")
    st.markdown("<p class='cap'>Around the event · shaded = run-up to worst</p>", unsafe_allow_html=True)
    lo = (pd.Period(e["runup"], "M") - 12).strftime("%Y-%m")
    hi = (pd.Period(e["calm"], "M") + 6).strftime("%Y-%m")
    grid = st.columns(4)
    for n, k in enumerate(KEY):
        sk = vals.loc[(vals.index >= lo) & (vals.index <= hi), k].dropna()
        with grid[n % 4].container(border=True):
            st.markdown(f"<p class='cap'>{IND[k]['label']}</p>", unsafe_allow_html=True)
            if len(sk) > 2:
                st.plotly_chart(sparkline(sk, e["color"], height=150, k=k, shade=[(e["runup"], e["worst"], e["color"])]),
                                width="stretch", config=CHART_CONFIG, key=f"ev-{ek}-{k}")
            else:
                st.caption("No data for this period")
    l1, l2 = st.columns(2)
    with l1.container(border=True):
        st.markdown("<p class='cap'>Lesson</p>", unsafe_allow_html=True)
        st.write(e["lesson"])
    with l2.container(border=True):
        st.markdown("<p class='cap'>Warning signs to watch today</p>", unsafe_allow_html=True)
        st.write(e["watch"])

# ---------- compare ----------
elif ss.view == "Compare to past events":
    st.subheader(f"{label_month(m)} compared with five past events")
    st.caption("Each indicator is labelled tailwind, neutral or headwind for India by the same rules every month. "
               "The match % blends two things equally: how many indicators carry the same label in both months, and how close the "
               "actual numbers are (each indicator ranked against its own 25-year history; prices compared by their 6-month % move). "
               "Run-up = the calm before; worst = the month India was hit hardest. Pick another month at the top to compare it instead.")
    score_rows = []
    for ek, e in EVENTS.items():
        r, rs, rn, rl, rv = match_score(m, e["runup"])
        w, ws, wn, wl, wv = match_score(m, e["worst"])
        score_rows.append(dict(key=ek, name=e["name"], color=e["color"], r=r, rs=rs, rn=rn, rl=rl, rv=rv,
                               w=w, ws=ws, wn=wn, wl=wl, wv=wv))
    best = max(score_rows, key=lambda x: max(x["r"], x["w"]))
    which = "run-up" if best["r"] >= best["w"] else "worst point"
    with st.container(border=True):
        st.markdown(f"<p class='cap'>Closest match</p><div class='big' style='font-size:22px'>{best['name']} · {which} "
                    f"({max(best['r'], best['w']):.0%})</div>", unsafe_allow_html=True)
    fig = go.Figure()
    names = [x["name"] for x in score_rows]
    fig.add_bar(y=names, x=[x["r"] * 100 for x in score_rows], name="Like the run-up", orientation="h", marker_color="#60A5FA",
                customdata=[f"labels {x['rs']} of {x['rn']} same · numbers {x['rv']:.0%} close" for x in score_rows],
                hovertemplate="%{y}<br>Run-up: <b>%{x:.0f}%</b><br>%{customdata}<extra></extra>")
    fig.add_bar(y=names, x=[x["w"] * 100 for x in score_rows], name="Like the worst point", orientation="h", marker_color="#F87171",
                customdata=[f"labels {x['ws']} of {x['wn']} same · numbers {x['wv']:.0%} close" for x in score_rows],
                hovertemplate="%{y}<br>Worst: <b>%{x:.0f}%</b><br>%{customdata}<extra></extra>")
    fig.update_layout(barmode="group", height=330, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(range=[0, 100], ticksuffix="%", gridcolor="#1F2A44", fixedrange=True), yaxis=dict(autorange="reversed", fixedrange=True),
                      dragmode=False, legend=dict(orientation="h", y=1.12), hoverlabel=dict(bgcolor="#111A2E", font=dict(color="#E5E7EB")))
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

    pick = st.radio("Side by side with", list(EVENTS), horizontal=True, format_func=lambda x: EVENTS[x]["name"],
                    index=list(EVENTS).index(best["key"]))
    e = EVENTS[pick]

    def cell(k, month):
        return f"{fmt(k, val_at(k, month))}<br>{pill(sig_at(k, month))}"

    html = ["<table style='width:100%;border-collapse:collapse;font-size:14px'>",
            "<tr style='text-align:left;color:#A3ADBF'><th style='padding:6px'>Indicator</th>"
            f"<th>Today · {label_month(m)}</th><th>Run-up · {label_month(e['runup'])}</th><th>Worst · {label_month(e['worst'])}</th><th>Same as</th></tr>"]
    for stage in STAGES:
        html.append(f"<tr><td colspan=5 style='padding:10px 6px 4px;color:{STAGE_COLOR[stage]};font-weight:700'>{STAGES[stage][1]}</td></tr>")
        for i in [i for i in INDICATORS if i["stage"] == stage and vals[i["k"]].notna().any()]:
            k = i["k"]
            now = sig_at(k, m)
            same = [lbl for lbl, mo in (("run-up", e["runup"]), ("worst", e["worst"])) if now and sig_at(k, mo) == now and i["rule"]["type"] != "neutral"]
            html.append(f"<tr style='border-top:1px solid #1F2A44'><td style='padding:6px'>{i['label']}</td><td>{cell(k, m)}</td>"
                        f"<td>{cell(k, e['runup'])}</td><td>{cell(k, e['worst'])}</td><td class='muted'>{' + '.join(same) or '—'}</td></tr>")
    html.append("</table>")
    with st.container(border=True):
        st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("Neutral-only indicators (PMI, GDP, gold, silver) have no label, so they count only in the numbers half of the match %.")

# ---------- simulator ----------
else:
    st.subheader("Simulator")
    st.caption("Three ways to think about what could come next, each built only from this dashboard's own history and each with its "
               "track record shown. They give ranges and odds, not a prediction, and they are not trading advice. "
               "Big shocks (2008, March 2020) sit outside anything history-based.")

    @st.cache_data(show_spinner=False)
    def sim_daily(stamp):
        return sim.load_daily("data/raw/nifty.csv"), sim.load_daily("data/raw/invix.csv")

    @st.cache_data(show_spinner="Testing the method on past years...")
    def sim_vix_record(stamp, days):
        n, v = sim_daily(stamp)
        return sim.vix_track_record(n, v, days)

    @st.cache_data(show_spinner=False)
    def sim_outcomes(stamp):
        return sim.outcomes(vals)

    @st.cache_data(show_spinner="Testing the method on past years...")
    def sim_analog_record(stamp, h):
        return sim.analog_track_record(RANKS, sim_outcomes(stamp), h)

    @st.cache_data(show_spinner=False)
    def sim_models(stamp):
        return sim.fit_what_if(vals)

    @st.cache_data(show_spinner=False)
    def sim_lead_models(stamp):
        return sim.fit_leaders(vals)

    def fmt_move(x, unit):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        return {"%": f"{x:+.1f}%", "pts": f"{x:+.2f} pts", "₹ cr": f"{'+' if x >= 0 else '−'}₹{abs(x):,.0f} cr"}[unit]

    def card(title, big, lines):
        st.markdown(f"<p class='cap'>{title}</p><div class='big' style='font-size:24px'>{big}</div>"
                    + "".join(f"<div class='muted' style='font-size:13px'>{x}</div>" for x in lines), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["Nifty range from India VIX", "What happened next", "What if"])

    # ----- 1. India VIX range
    with t1:
        nifty_d, vix_d = sim_daily(stamp)
        spot, vix_now = float(nifty_d.iloc[-1]), float(vix_d.iloc[-1])
        st.markdown("India VIX is the yearly move the options market is pricing in for Nifty. Scaled down to your time window, "
                    "it gives the range Nifty is expected to stay inside: about 68% of the time inside 1 sigma, 95% inside 2 sigma. "
                    "For an option expiry, pick the number of calendar days left to expiry.")
        days = st.select_slider("Calendar days ahead", options=[1, 2, 3, 4, 5, 7, 10, 14, 21, 30, 45, 60, 90], value=7)
        rg = sim.vix_range(spot, vix_now, days)
        c1, c2, c3 = st.columns(3)
        with c1.container(border=True):
            card(f"Nifty · {nifty_d.index[-1]:%d %b %Y}", f"{spot:,.0f}", [f"India VIX {vix_now:.1f} ({vix_d.index[-1]:%d %b})"])
        with c2.container(border=True):
            card(f"68% range · {days} days", f"{rg['lo1']:,.0f} – {rg['hi1']:,.0f}",
                 [f"±{rg['sigma_pct']:.1f}% · about ±{spot * rg['sigma_pct'] / 100:,.0f} points"])
        with c3.container(border=True):
            card(f"95% range · {days} days", f"{rg['lo2']:,.0f} – {rg['hi2']:,.0f}",
                 [f"±{2 * rg['sigma_pct']:.1f}% · about ±{2 * spot * rg['sigma_pct'] / 100:,.0f} points"])

        hist = nifty_d.loc[nifty_d.index[-1] - pd.Timedelta(days=180):]
        t_end = nifty_d.index[-1] + pd.Timedelta(days=days)
        steps = pd.date_range(nifty_d.index[-1], t_end, periods=30)
        cone = [sim.vix_range(spot, vix_now, max((d - nifty_d.index[-1]).days, 0)) for d in steps]
        fig = go.Figure()
        for lo, hi, col, name in (("lo2", "hi2", "rgba(96,165,250,0.15)", "95% range"), ("lo1", "hi1", "rgba(96,165,250,0.30)", "68% range")):
            fig.add_scatter(x=list(steps) + list(steps[::-1]), y=[c[hi] for c in cone] + [c[lo] for c in cone][::-1],
                            fill="toself", fillcolor=col, line=dict(width=0), name=name, hoverinfo="skip")
        fig.add_scatter(x=hist.index, y=hist.values, mode="lines", line=dict(color="#E5E7EB", width=2), name="Nifty",
                        hovertemplate="%{x|%d %b %Y}<br><b>%{y:,.0f}</b><extra></extra>")
        for key, lbl in (("hi1", "68% high"), ("lo1", "68% low"), ("hi2", "95% high"), ("lo2", "95% low")):
            fig.add_scatter(x=[t_end], y=[rg[key]], mode="markers", marker=dict(color="#60A5FA", size=7), showlegend=False,
                            hovertemplate=f"{lbl} by %{{x|%d %b}}<br><b>%{{y:,.0f}}</b><extra></extra>")
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          dragmode=False, legend=dict(orientation="h", y=1.1), hoverlabel=dict(bgcolor="#111A2E", font=dict(color="#E5E7EB")),
                          xaxis=dict(fixedrange=True, gridcolor="#1F2A44"), yaxis=dict(fixedrange=True, gridcolor="#1F2A44", tickformat=","))
        st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

        rec = sim_vix_record(stamp, days)
        with st.container(border=True):
            st.markdown("<p class='cap'>Track record</p>", unsafe_allow_html=True)
            st.write(f"On every trading day since {rec['since']:%b %Y} ({rec['n']:,} days), Nifty ended {days} days later "
                     f"inside the 1-sigma range **{rec['in1']:.0%}** of the time (theory: 68%) and inside 2 sigma **{rec['in2']:.0%}** (theory: 95%).")
            st.caption("India VIX has usually priced in bigger moves than actually happened. That gap is what option sellers earn most of the time, "
                       "and it disappears in sudden shocks (March 2020, election results), when moves blow through 2 sigma.")

    # ----- 2. what happened next
    with t2:
        outs = sim_outcomes(stamp)
        st.markdown(f"Finds the 15 past months whose readings looked most like **{label_month(m)}** across every indicator "
                    "(same method as the Compare page's 'numbers' score), then shows what Nifty, the rupee and FII flows actually did afterwards. "
                    "Only months whose full 12-month aftermath is known are used, and no two picks are within 3 months of each other.")
        h = st.radio("Looking ahead", sim.HORIZONS, index=1, horizontal=True, format_func=lambda x: f"{x} months")
        picks, dist = sim.analogs(RANKS, outs, m)
        if len(picks) < 5:
            st.info("Not enough earlier history to find similar months for this date. Pick a month from 2006 onwards.")
        else:
            c1, c2, c3 = st.columns(3)
            for col, key, title, unit, note in ((c1, "nifty", "Nifty", "%", ""), (c2, "inr", "Rupee (USD/INR)", "%", "+ = rupee weaker"),
                                                (c3, "fii", f"FII flows, {h}-month total", "₹ cr", "")):
                sm = sim.summarise(outs, picks, f"{key}_{h}")
                with col.container(border=True):
                    if sm is None:
                        card(title, "—", ["no data"])
                        continue
                    up_word = "rupee weaker" if key == "inr" else "net buying" if key == "fii" else "higher"
                    card(f"{title} · median after {h} months", fmt_move(sm["median"], unit),
                         [f"{up_word} in {sm['up']:.0%} of the {sm['n']} cases",
                          f"middle 80%: {fmt_move(sm['p10'], unit)} to {fmt_move(sm['p90'], unit)}",
                          f"worst {fmt_move(sm['lo'], unit)} · best {fmt_move(sm['hi'], unit)}"] + ([note] if note else []))

            pts = outs.loc[picks, f"nifty_{h}"]
            fig = go.Figure(go.Scatter(
                x=pts.values, y=[1 - 2 * d for d in dist[picks]], mode="markers+text", text=[label_month(p) for p in picks],
                textposition="top center", textfont=dict(size=10, color="#A3ADBF"), marker=dict(size=10, color=["#34D399" if x >= 0 else "#F87171" for x in pts.values]),
                customdata=[label_month(p) for p in picks], hovertemplate="%{customdata}<br>Nifty next " + str(h) + " months: <b>%{x:+.1f}%</b><extra></extra>"))
            fig.add_vline(x=0, line_color="#4B5563")
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", dragmode=False,
                              xaxis=dict(title=f"Nifty change over the next {h} months", ticksuffix="%", fixedrange=True, gridcolor="#1F2A44"),
                              yaxis=dict(title="How similar", tickformat=".0%", fixedrange=True, gridcolor="#1F2A44"),
                              hoverlabel=dict(bgcolor="#111A2E", font=dict(color="#E5E7EB")))
            st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

            actual = outs.loc[m, f"nifty_{h}"]
            if not np.isnan(actual):
                st.info(f"What actually happened after {label_month(m)}: Nifty {actual:+.1f}% over the next {h} months.")

            table = pd.DataFrame({
                "Month": [label_month(p) for p in picks],
                "Similarity": [f"{max(0, 1 - 2 * d):.0%}" for d in dist[picks]],
                f"Nifty next {h}m": [fmt_move(outs.loc[p, f"nifty_{h}"], "%") for p in picks],
                f"Rupee next {h}m": [fmt_move(outs.loc[p, f"inr_{h}"], "%") for p in picks],
                f"FII next {h}m": [fmt_move(outs.loc[p, f"fii_{h}"], "₹ cr") for p in picks]})
            with st.expander("The 15 similar months"):
                st.dataframe(table, hide_index=True, width="stretch")

            rec = sim_analog_record(stamp, h)
            if rec:
                with st.container(border=True):
                    st.markdown("<p class='cap'>Track record</p>", unsafe_allow_html=True)
                    st.write(f"Tested on {rec['n']} months since {label_month(rec['since'])}, each time using only the past as it was known then: "
                             f"the real {h}-month Nifty move landed inside the similar months' middle-80% range **{rec['inside']:.0%}** of the time (ideal: 80%). "
                             f"Calling up or down from the median was right **{rec['direction']:.0%}** of the time, against **{rec['always_up']:.0%}** for simply "
                             f"always guessing 'up'.")
                    st.caption("So use this for the size of the range (what a bad and a good outcome looked like in similar setups), not for direction.")

    # ----- 3. what if
    with t3:
        models, moves_hist = sim_models(stamp)
        lead_models, lead_hist = sim_lead_models(stamp)
        any_m = next(iter(models.values()))
        st.markdown("Set how much things move over the next **3 months**. It works in two steps, like the flow chart: the **US leaders** move "
                    "the **US markets** (US 10Y, dollar, S&P 500), and those plus oil move **India**. Each step is learned from history: "
                    f"step 2 from {any_m['n']} overlapping 3-month windows since {label_month(any_m['since'])}, step 1 from normal times "
                    "(the 2008–09 and 2020–21 crashes are left out because their swings were far outside anything else). Leave a slider at 0 for 'no change'.")
        st.caption("PMI is not a slider: the dashboard has PMI only from 2025, too short to learn from.")

        last_lead = lead_hist.dropna(how="all").iloc[-1]
        last_mkt = moves_hist.dropna(how="all").iloc[-1]
        b1, b2 = st.columns([1, 1])
        if b1.button("Fill in the last 3 months' actual moves"):
            for k, (_, _, lo, hi, step, _) in sim.LEADERS.items():
                v = last_lead.get(k, np.nan)
                ss[f"wl_{k}"] = 0.0 if np.isnan(v) else round(float(np.clip(round(v / step) * step, lo, hi)), 2)
            implied = sim.implied_markets(lead_models, {k: ss[f"wl_{k}"] for k in sim.LEADERS})
            for k, (_, _, _, lo, hi, step) in sim.MARKETS.items():
                v = last_mkt.get(k, np.nan) - implied[k]
                ss[f"wm_{k}"] = 0.0 if np.isnan(v) else round(float(np.clip(round(v / step) * step, lo, hi)), 2)
            st.rerun()
        if b2.button("Reset all to 0"):
            for k in sim.LEADERS:
                ss[f"wl_{k}"] = 0.0
            for k in sim.MARKETS:
                ss[f"wm_{k}"] = 0.0
            st.rerun()

        st.markdown("<p class='cap'>Step 1 · US leaders</p>", unsafe_allow_html=True)
        leaders = {}
        cols = st.columns(3)
        for n, (k, (lbl, unit, lo, hi, step, hint)) in enumerate(sim.LEADERS.items()):
            with cols[n % 3]:
                ss.setdefault(f"wl_{k}", 0.0)
                leaders[k] = st.slider(f"{lbl} ({unit})", float(lo), float(hi), step=float(step), key=f"wl_{k}", help=hint)
                lv = last_lead.get(k, np.nan)
                last_txt = "—" if np.isnan(lv) else f"{lv:+,.0f}k" if k == "jobs" else fmt_move(lv, unit)
                st.caption(f"Last 3 months: {last_txt}")

        st.markdown("<p class='cap'>Step 2 · US markets: extra moves on top of what the leaders imply</p>", unsafe_allow_html=True)
        implied = sim.implied_markets(lead_models, leaders)
        extra = {}
        cols = st.columns(3)
        for col, (k, (lbl, _, unit, lo, hi, step)) in zip(cols, sim.MARKETS.items()):
            with col:
                ss.setdefault(f"wm_{k}", 0.0)
                extra[k] = st.slider(f"{lbl}, extra ({unit})", float(lo), float(hi), step=float(step), key=f"wm_{k}")
                st.caption(f"Leaders imply {fmt_move(implied[k], unit)} · total {fmt_move(implied[k] + extra[k], unit)} · "
                           f"last 3 months: {fmt_move(last_mkt.get(k, np.nan), unit)}")

        res = sim.what_if(models, lead_models, leaders, extra)
        names = {**{k: v[0] for k, v in sim.LEADERS.items()}, **{"x_" + k: v[0].split(" (")[0] + " (extra)" for k, v in sim.MARKETS.items()}}
        html = ["<table style='width:100%;border-collapse:collapse;font-size:14px'>",
                "<tr style='text-align:left;color:#A3ADBF'><th style='padding:6px'>India</th><th>Expected 3-month move</th><th>Likely range (68%)</th>"
                "<th>Biggest pushes</th><th>How much history explains</th></tr>"]
        for t, (lbl, _, unit, note) in sim.TARGETS.items():
            r, mdl = res["india"][t], models[t]
            parts = sorted(r["parts"].items(), key=lambda kv: -abs(kv[1]))
            pushes = ", ".join(f"{names[k]} {fmt_move(v, unit)}" for k, v in parts[:3]
                               if abs(v) >= {"%": 0.05, "pts": 0.005, "₹ cr": 50}[unit]) or "—"
            html.append(f"<tr style='border-top:1px solid #1F2A44'><td style='padding:6px'>{lbl}<div class='muted' style='font-size:12px'>{note}</div></td>"
                        f"<td><b>{fmt_move(r['mid'], unit)}</b></td><td>{fmt_move(r['lo'], unit)} to {fmt_move(r['hi'], unit)}</td>"
                        f"<td class='muted'>{pushes}</td><td>{mdl['r2']:.0%}</td></tr>")
        html.append("</table>")
        with st.container(border=True):
            st.markdown("".join(html), unsafe_allow_html=True)

        with st.expander("Rules of thumb behind this"):
            st.markdown("**Step 1 · how US markets have moved with the leaders** (normal times, each leader moving alone)")
            rows = []
            for k, (lbl, unit, *_r) in sim.LEADERS.items():
                one, one_lbl = {"jobs": (100, "+100k/month"), "brent": (10, "+10%"), "fedBs": (10, "+10%")}.get(k, (1, "+1 pt"))
                row = {"Leader": f"{lbl} {one_lbl}"}
                for mk, (ml, _, mu, *_m) in sim.MARKETS.items():
                    row[ml.split(" (")[0]] = fmt_move(lead_models[mk]["beta"][k] * one, mu)
                rows.append(row)
            rows.append({"Leader": "How much leaders explain", **{ml.split(" (")[0]: f"{lead_models[mk]['r2']:.0%}" for mk, (ml, *_m) in sim.MARKETS.items()}})
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.markdown("**Step 2 · how India has moved with US markets and oil** (each moving alone)")
            rows = []
            for t, (lbl, _, unit, _) in sim.TARGETS.items():
                mdl = models[t]
                row = {"India": lbl, "With nothing moving": fmt_move(mdl["const"], unit)}
                for k, (dl, _, du, *_r) in sim.DRIVERS.items():
                    one = 1.0 if du == "pts" else 10.0
                    row[f"{dl.split(' (')[0]} {'+1 pt' if du == 'pts' else '+10%'}"] = fmt_move(mdl["beta"][k] * one, unit)
                rows.append(row)
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption("'With nothing moving' is the typical drift of a 3-month window (Nifty has tended to rise, the rupee to weaken slowly).")
        st.caption("Leaders matter mostly through their surprise: markets move when jobs, inflation or the Fed come in different from what was expected, "
                   "which these monthly numbers only partly capture, so step 1 explains only 6–18% of market moves. "
                   "'How much history explains' is the share of past 3-month India moves the US markets and oil account for (R²): about 40% for Nifty; "
                   "FII flows and India CPI depend mostly on other things, so their ranges are wide. These are relationships that held on average, "
                   "not cause and effect, and they shift over time (for example, DIIs now absorb much more FII selling than before 2020).")

st.caption(f"Sources: FRED, Yahoo Finance, RBI, MoSPI, NSE and MSEI (FII/DII). Missing indicators: {', '.join(meta.get('missing_indicators', [])) or 'none'}. "
           "Tailwind/headwind labels come from simple rules in config.py, not from a forecast.")
