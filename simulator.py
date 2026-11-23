"""Forecasting simulator: the calculations behind the Simulator tab.

Three tools, each with a track record so you can judge how far to trust it:
  1. vix_range      expected Nifty range priced in by India VIX (option-market maths)
  2. analogs        the past months most like a given month, and what happened next
  3. what_if        how India indicators have typically moved when US drivers moved

Everything here is history-based. It describes ranges and odds, not a prediction, and it is not trading advice.
"""
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- 1. India VIX range

def load_daily(path):
    s = pd.read_csv(path, parse_dates=["date"], index_col="date")["value"].dropna()
    return s[~s.index.duplicated()].sort_index()


def vix_range(spot, vix, days):
    """India VIX is the market's expected annual move in %. Over `days` calendar days the expected
    move is VIX x sqrt(days / 365). 1 sigma covers about 68% of outcomes, 2 sigma about 95%."""
    sig = vix / 100 * np.sqrt(days / 365)
    return {"sigma_pct": sig * 100,
            "lo1": spot * np.exp(-sig), "hi1": spot * np.exp(sig),
            "lo2": spot * np.exp(-2 * sig), "hi2": spot * np.exp(2 * sig)}


def vix_track_record(nifty, vix, days):
    """Every trading day since India VIX began: did Nifty end `days` later inside the 1- and 2-sigma range?"""
    df = pd.concat({"n": nifty, "v": vix}, axis=1).dropna()
    target = df.index + pd.Timedelta(days=days)
    pos = nifty.index.searchsorted(target)          # first trading day on or after the target date
    ok = pos < len(nifty)
    df, pos = df[ok], pos[ok]
    fwd = nifty.iloc[pos].values
    move = np.abs(np.log(fwd / df["n"].values))
    sig = df["v"].values / 100 * np.sqrt(days / 365)
    return {"n": len(df), "in1": float(np.mean(move <= sig)), "in2": float(np.mean(move <= 2 * sig)),
            "since": df.index[0]}


# ---------------------------------------------------------------- 2. what happened next

HORIZONS = (3, 6, 12)


def outcomes(vals):
    """For every month: Nifty % change, rupee % change (+ = rupee weaker) and total FII flows over the next 3/6/12 months."""
    out = {}
    for h in HORIZONS:
        out[f"nifty_{h}"] = (vals["nifty"].shift(-h) / vals["nifty"] - 1) * 100
        out[f"inr_{h}"] = (vals["inr"].shift(-h) / vals["inr"] - 1) * 100
        out[f"fii_{h}"] = vals["fii"][::-1].rolling(h, min_periods=h).sum()[::-1].shift(-1)
    return pd.DataFrame(out, index=vals.index)


def distances(ranks, month, pool):
    """Average gap in percentile rank between `month` and each month in `pool` (0 = identical).
    Needs at least 60% of the month's indicators to be available in the other month too."""
    me = ranks.loc[month]
    have = me.notna()
    sub = ranks.loc[pool, have[have].index]
    d = (sub - me[have]).abs()
    n = d.notna().sum(axis=1)
    dist = d.mean(axis=1)
    return dist[n >= 0.6 * have.sum()].sort_values()


def pick_spaced(dist, k=15, gap=3):
    """Nearest months, but never two within `gap` months of each other (neighbouring months are near-copies)."""
    chosen = []
    for m in dist.index:
        p = pd.Period(m, "M")
        if all(abs((p - pd.Period(c, "M")).n) >= gap for c in chosen):
            chosen.append(m)
        if len(chosen) == k:
            break
    return chosen


def analogs(ranks, outs, month, k=15):
    """The k past months most like `month` whose full 12-month aftermath is known."""
    i = list(ranks.index).index(month)
    pool = [m for m in ranks.index[: max(0, i - 12 + 1)] if outs.loc[m, "nifty_12"] == outs.loc[m, "nifty_12"]]
    if not pool:
        return [], pd.Series(dtype=float)
    dist = distances(ranks, month, pool)
    picks = pick_spaced(dist, k)
    return picks, dist[picks]


def summarise(outs, picks, col):
    x = outs.loc[picks, col].dropna()
    if x.empty:
        return None
    return {"n": len(x), "median": x.median(), "up": float((x > 0).mean()), "lo": x.min(), "hi": x.max(),
            "p10": x.quantile(0.1), "p90": x.quantile(0.9)}


def analog_track_record(ranks, outs, h=6, start="2006-01", k=15):
    """Test the method on the past without peeking: for each month, use only analogs whose
    h-month outcome was already known at that time, and compare with what actually happened."""
    idx = list(ranks.index)
    rows = []
    for i, m in enumerate(idx):
        if m < start or np.isnan(outs.loc[m, f"nifty_{h}"]):
            continue
        pool = [x for x in idx[: max(0, i - h + 1)] if not np.isnan(outs.loc[x, f"nifty_{h}"])]
        if len(pool) < 30:
            continue
        picks = pick_spaced(distances(ranks, m, pool), k)
        past = outs.loc[picks, f"nifty_{h}"].dropna()
        if len(past) < 5:
            continue
        actual = outs.loc[m, f"nifty_{h}"]
        rows.append({"month": m, "pred_up": past.median() > 0, "actual_up": actual > 0,
                     "inside": past.quantile(0.1) <= actual <= past.quantile(0.9)})
    r = pd.DataFrame(rows)
    if r.empty:
        return None
    return {"n": len(r), "since": r["month"].iloc[0], "direction": float((r["pred_up"] == r["actual_up"]).mean()),
            "always_up": float(r["actual_up"].mean()), "inside": float(r["inside"].mean())}


# ---------------------------------------------------------------- 3. what if

# The Fed rate is not a separate driver: it reaches India through the US 10Y and the dollar, and as a
# separate input it double-counts the 10Y (and picks up "the Fed hikes in booms", which flips signs).
# The S&P 500 stands in for global risk mood, so the other drivers are measured net of the global cycle.
DRIVERS = {  # key: (label, how the 3-month move is measured, unit, slider min, max, step)
    "us10":  ("US 10Y yield", "diff", "pts", -1.5, 1.5, 0.05),
    "dxy":   ("Dollar index (DXY)", "pct", "%", -10.0, 10.0, 0.5),
    "brent": ("Brent oil", "pct", "%", -50.0, 50.0, 1.0),
    "sp":    ("S&P 500 (global mood)", "pct", "%", -30.0, 30.0, 1.0),
}
TARGETS = {  # key: (label, how measured, unit, note)
    "nifty": ("Nifty", "pct", "%", ""),
    "inr":   ("Rupee (USD/INR)", "pct", "%", "+ = rupee weaker"),
    "fii":   ("FII flows", "sum", "₹ cr", "total over the 3 months"),
    "in10y": ("India 10Y yield", "diff", "pts", ""),
    "inCpi": ("India CPI inflation", "diff", "pts", ""),
}


def three_month_moves(vals, spec):
    out = {}
    for k, (_, how, *_) in spec.items():
        s = vals[k]
        out[k] = (s.pct_change(3, fill_method=None) * 100 if how == "pct"
                  else s.rolling(3, min_periods=3).sum() if how == "sum" else s.diff(3))
    return pd.DataFrame(out)


def fit_what_if(vals, start="2005-01"):
    """For each India target, a least-squares fit of its 3-month move on the four drivers' 3-month moves
    over the same window, using every month since `start`. Returns betas, R² and the typical miss."""
    X = three_month_moves(vals, DRIVERS)
    Y = three_month_moves(vals, TARGETS)
    models = {}
    for t in TARGETS:
        d = pd.concat([X, Y[t].rename("y")], axis=1).loc[start:].dropna()
        A = np.column_stack([np.ones(len(d)), d[list(DRIVERS)].values])
        coef, *_ = np.linalg.lstsq(A, d["y"].values, rcond=None)
        resid = d["y"].values - A @ coef
        r2 = 1 - resid.var() / d["y"].var()
        models[t] = {"const": coef[0], "beta": dict(zip(DRIVERS, coef[1:])), "resid_sd": resid.std(ddof=len(coef)),
                     "r2": r2, "n": len(d), "since": d.index[0]}
    return models, X


def what_if(models, moves):
    """Expected 3-month move of each target for the given driver moves, with a 68% range and each driver's part."""
    out = {}
    for t, m in models.items():
        parts = {k: m["beta"][k] * moves.get(k, 0.0) for k in DRIVERS}
        mid = m["const"] + sum(parts.values())
        out[t] = {"mid": mid, "lo": mid - m["resid_sd"], "hi": mid + m["resid_sd"], "parts": parts, "base": m["const"]}
    return out
