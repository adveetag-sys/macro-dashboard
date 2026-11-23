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
    VIEWS = ["Dashboard", "Understand the flow", "Past events", "Compare to past events"]
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
else:
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

st.caption(f"Sources: FRED, Yahoo Finance, RBI, MoSPI, NSE and MSEI (FII/DII). Missing indicators: {', '.join(meta.get('missing_indicators', [])) or 'none'}. "
           "Tailwind/headwind labels come from simple rules in config.py, not from a forecast.")
