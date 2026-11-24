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
# Two steps, following the dashboard's flow chart:
#   step 1  US leaders (jobs, inflation, growth, Fed) -> US markets (US 10Y, dollar, S&P 500)
#   step 2  US markets + oil -> India (Nifty, rupee, FII, India 10Y, India CPI)
# Linking leaders straight to India gives backwards answers ("Fed hikes -> Nifty up", because the Fed hikes
# in booms); going through the markets keeps each link sensible. The S&P 500 stands in for global risk mood.

LEADERS = {  # key: (label, unit, slider min, max, step, help)
    "jobs":  ("US hiring pace", "k jobs/month", -400.0, 400.0, 25.0, "change in average monthly job gains vs the last 3 months"),
    "cpi":   ("US CPI inflation", "pts", -2.0, 2.0, 0.1, "change in the yearly inflation rate"),
    "gdp":   ("US GDP growth", "pts", -6.0, 6.0, 0.5, "change in quarterly annualised growth"),
    "fed":   ("Fed funds rate", "pts", -1.5, 1.5, 0.25, "+0.25 = one hike"),
    "fedBs": ("Fed balance sheet", "%", -10.0, 10.0, 0.5, "+ = money printing (QE), − = tightening (QT)"),
    "brent": ("Brent oil", "%", -50.0, 50.0, 1.0, "price change"),
}
FIXED_LEADERS = ("brent", "cpi", "gdp")    # you set these
LINKED_LEADERS = ("jobs", "fed", "fedBs")   # these follow the fixed ones (with a Follows switch in the app)
# The Fed rate follows the Taylor rule (John Taylor, 1993), not a learned slope: learned from this data the Fed
# "cuts when inflation rises" (it reacts late and cut hard in slowdowns), which is backwards for a what-if.
# Taylor's rule moves the policy rate 1.5x any change in inflation and 0.5x any change in growth. Central banks move
# gradually: research (Clarida, Gali and Gertler, 2000) finds a smoothing of about 0.75-0.8 per quarter, so within
# one 3-month window the Fed takes about a quarter of the full step ("inertial Taylor rule").
TAYLOR_SPEED = 0.25
TAYLOR = {"cpi": 1.5 * TAYLOR_SPEED, "gdp": 0.5 * TAYLOR_SPEED, "brent": 0.0}

MARKETS = {  # key: (label, how measured, unit, slider min, max, step)
    "us10": ("US 10Y yield", "diff", "pts", -1.5, 1.5, 0.01),
    "dxy":  ("Dollar index (DXY)", "pct", "%", -10.0, 10.0, 0.1),
    "sp":   ("S&P 500 (global mood)", "pct", "%", -30.0, 30.0, 0.5),
}
FOLLOW_MARKETS = ("us10",)  # markets that follow the leaders: only the US 10Y link held up on unseen years (see validate)
DRIVERS = {**MARKETS, "brent": ("Brent oil", "pct", "%", -50.0, 50.0, 1.0)}  # US markets + oil
INDIA = {  # step-3 sliders: key: (label, how measured, unit, slider min, max, step, help)
    "rbi":   ("RBI repo rate", "diff", "pts", -1.5, 1.5, 0.25, "+0.25 = one hike; your call, it does not follow the other sliders"),
    "inr":   ("USD/INR", "pct", "%", -10.0, 10.0, 0.1, "+ = rupee weaker"),
    "inCpi": ("India CPI inflation", "diff", "pts", -3.0, 3.0, 0.05, "change in the yearly inflation rate"),
}
FOLLOW = ("inr", "inCpi")  # India sliders that move with the US markets and the repo; the repo itself is left to you
# Which inputs each result uses. India 10Y keeps only its real drivers: with every input it did worse than a
# plain average on years it had not seen. Nifty and FII flows use them all (with shrinkage, see _fit).
RESULT_INPUTS = {
    "nifty": list(DRIVERS) + list(INDIA),
    "fii":   list(DRIVERS) + list(INDIA),
    "in10y": ["us10", "rbi", "inCpi"],
}
STEP2_INPUTS = list(DRIVERS) + ["rbi"]
SHRINK = 0.5        # ridge strength for steps 2 and 3 (chosen by testing on unseen years, see validate)
TRAIN_END = "2016-12"  # validate: learn up to here, test on the years after
TARGETS = {  # final results: key: (label, how measured, unit, note)
    "nifty": ("Nifty", "pct", "%", ""),
    "fii":   ("FII flows", "sum", "₹ cr", "total over the 3 months"),
    "in10y": ("India 10Y yield", "diff", "pts", ""),
}
CRASHES = (("2008-09", "2009-06"), ("2020-03", "2021-06"))  # left out of step 1: COVID swung jobs by millions


def three_month_moves(vals, spec):
    out = {}
    for k, (_, how, *_) in spec.items():
        s = vals[k]
        out[k] = (s.pct_change(3, fill_method=None) * 100 if how == "pct"
                  else s.rolling(3, min_periods=3).sum() if how == "sum" else s.diff(3))
    return pd.DataFrame(out)


def leader_moves(vals):
    return pd.DataFrame({
        "jobs": vals["usJobs"].rolling(3).mean().diff(3),
        "cpi": vals["usCpi"].diff(3),
        "gdp": vals["gdp"].diff(3),
        "fed": vals["fed"].diff(3),
        "fedBs": vals["fedBs"].pct_change(3, fill_method=None) * 100,
        "brent": vals["brent"].pct_change(3, fill_method=None) * 100,
    })


def _ridge(X, y, lam=0.05):
    """Least squares with a little shrinkage, so two inputs that move together (jobs and GDP) share an effect
    instead of fighting over it. Inputs are scaled first so the shrinkage treats them alike."""
    mu, sd = X.mean(), X.std()
    A = ((X - mu) / sd).values
    yc = y - y.mean()
    b = np.linalg.solve(A.T @ A + lam * len(A) * np.eye(A.shape[1]), A.T @ yc.values)
    resid = yc.values - A @ b
    return dict(zip(X.columns, b / sd.values)), 1 - resid.var() / yc.var(), resid.std(ddof=A.shape[1] + 1)


def _normal(d):
    return d[[not any(a <= i <= b for a, b in CRASHES) for i in d.index]]


def fit_leader_links(vals, start="2003-01"):
    """Step 1a: how hiring pace and the Fed balance sheet have moved with Brent, US inflation and US GDP
    (normal times, same 3-month window); the Fed rate uses the Taylor rule."""
    L = leader_moves(vals).loc[start:]
    out = {}
    for t in LINKED_LEADERS:
        if t == "fed":
            out[t] = {"beta": dict(TAYLOR), "rule": "inertial Taylor rule", "r2": np.nan}
            continue
        d = _normal(pd.concat([L[list(FIXED_LEADERS)], L[t].rename("y")], axis=1).dropna())
        out[t] = _fit_simple(d, list(FIXED_LEADERS))
    return out


def implied_leaders(link_models, fixed):
    """Moves of the linked leaders implied by the fixed leaders' moves (step 1a)."""
    return {t: sum(m["beta"][k] * fixed.get(k, 0.0) for k in FIXED_LEADERS) for t, m in link_models.items()}


def _fit_simple(d, cols, lam=0.05):
    beta, r2, sd = _ridge(d[cols], d["y"], lam)
    return {"beta": beta, "r2": r2, "resid_sd": sd, "n": len(d)}


def fit_leaders(vals, start="2003-01"):
    """Step 1: how each US market's 3-month move has followed the leaders' moves in normal times."""
    L = leader_moves(vals)
    M = three_month_moves(vals, MARKETS)
    models = {}
    for t in MARKETS:
        d = pd.concat([L, M[t].rename("y")], axis=1).loc[start:].dropna()
        d = d[[not any(a <= i <= b for a, b in CRASHES) for i in d.index]]
        beta, r2, sd = _ridge(d[list(LEADERS)], d["y"])
        models[t] = {"beta": beta, "r2": r2, "resid_sd": sd, "n": len(d)}
    return models, L


def _fit(d, cols, lam=SHRINK):
    """Least squares with shrinkage (ridge regression) on inputs scaled to the same size. Plain least squares
    with 7 overlapping inputs gave effects that flipped sign between 2005-16 and 2017-26 and predicted unseen
    years worse than a plain average; shrinking pulls unstable effects toward zero and fixed that."""
    X, y = d[cols], d["y"]
    mu, sd = X.mean(), X.std()
    A = ((X - mu) / sd).values
    b = np.linalg.solve(A.T @ A + lam * len(A) * np.eye(len(cols)), A.T @ (y.values - y.mean()))
    beta = b / sd.values
    const = y.mean() - float((mu.values * beta).sum())
    resid = y.values - const - X.values @ beta
    return {"const": const, "beta": dict(zip(cols, beta)), "resid_sd": resid.std(ddof=len(cols) + 1),
            "r2": 1 - resid.var() / y.var(), "n": len(d), "since": d.index[0]}


def _frame(vals, start="2005-01"):
    X = pd.concat([three_month_moves(vals, DRIVERS), three_month_moves(vals, INDIA)], axis=1)
    Y = three_month_moves(vals, TARGETS)
    return X.loc[start:], Y.loc[start:]


def fit_india(vals, start="2005-01"):
    """Step 2: how the rupee and India CPI have moved with the US markets, oil and the repo rate
    (3-month moves over the same window)."""
    X, _ = _frame(vals, start)
    return {t: _fit(pd.concat([X[STEP2_INPUTS], X[t].rename("y")], axis=1).dropna(), STEP2_INPUTS) for t in FOLLOW}


def fit_what_if(vals, start="2005-01"):
    """Step 3: Nifty, FII flows and India 10Y on the inputs in RESULT_INPUTS, all as 3-month moves
    over the same window, every month since `start`."""
    X, Y = _frame(vals, start)
    models = {t: _fit(pd.concat([X[RESULT_INPUTS[t]], Y[t].rename("y")], axis=1).dropna(), RESULT_INPUTS[t]) for t in TARGETS}
    return models, X


def _score(train, test, cols, lam):
    m = _fit(train, cols, lam) if lam is not None else None
    pred = m["const"] + sum(m["beta"][k] * test[k] for k in cols)
    err = test["y"] - pred
    base = ((test["y"] - train["y"].mean()) ** 2).mean()
    return {"skill": 1 - (err ** 2).mean() / base, "corr": float(np.corrcoef(pred, test["y"])[0, 1]),
            "direction": float((np.sign(pred) == np.sign(test["y"])).mean()),
            "inside": float((err.abs() <= m["resid_sd"]).mean()), "n_train": len(train), "n_test": len(test)}


def validate(vals, train_end=TRAIN_END):
    """The fair test: learn every link from data up to `train_end` only, then predict each later 3-month
    window from what the inputs actually did, and compare with what really happened.
    skill: how much smaller the misses are than always guessing the old average (0 = no better, 1 = perfect).
    corr: how closely predictions follow the real moves. direction: share of up/down calls right.
    inside: share of real outcomes inside the 68% range."""
    X, Y = _frame(vals)
    L = leader_moves(vals)
    M = three_month_moves(vals, MARKETS)
    test_start = str(pd.Period(train_end, "M") + 3)  # 3-month windows must not straddle the split
    rows = []

    def add(step, name, d, cols, lam, crash=False):
        tr, te = d.loc[:train_end], d.loc[test_start:]
        if crash:  # step 1 is learned and tested on normal times (COVID's job swings of millions break it)
            tr = tr[[not any(a <= i <= b for a, b in CRASHES) for i in tr.index]]
            te = te[[not any(a <= i <= b for a, b in CRASHES) for i in te.index]]
        rows.append({"step": step, "result": name, **_score(tr, te, cols, lam)})

    Lf = leader_moves(vals)
    for t in LINKED_LEADERS:
        d = pd.concat([Lf[list(FIXED_LEADERS)], Lf[t].rename("y")], axis=1).loc["2003-01":].dropna()
        if t == "fed":  # a fixed rule: nothing to learn, just score it on the test years
            tr, te = _normal(d.loc[:train_end]), _normal(d.loc[test_start:])
            pred = sum(TAYLOR[k] * te[k] for k in FIXED_LEADERS)
            err = te["y"] - pred
            base = ((te["y"] - tr["y"].mean()) ** 2).mean()
            sd = (tr["y"] - sum(TAYLOR[k] * tr[k] for k in FIXED_LEADERS)).std()
            rows.append({"step": "1a", "result": LEADERS[t][0] + " (inertial Taylor rule)", "skill": 1 - (err ** 2).mean() / base,
                         "corr": float(np.corrcoef(pred, te["y"])[0, 1]), "direction": float((np.sign(pred) == np.sign(te["y"])).mean()),
                         "inside": float((err.abs() <= sd).mean()), "n_train": len(tr), "n_test": len(te)})
        else:
            add("1a", LEADERS[t][0], d, list(FIXED_LEADERS), 0.05, crash=True)
    for t, (lbl, *_r) in MARKETS.items():
        add("1", lbl, pd.concat([L, M[t].rename("y")], axis=1).loc["2003-01":].dropna(), list(LEADERS), 0.05, crash=True)
    for t in FOLLOW:
        add("2", INDIA[t][0], pd.concat([X[STEP2_INPUTS], X[t].rename("y")], axis=1).dropna(), STEP2_INPUTS, SHRINK)
    for t, (lbl, *_r) in TARGETS.items():
        add("3", lbl, pd.concat([X[RESULT_INPUTS[t]], Y[t].rename("y")], axis=1).dropna(), RESULT_INPUTS[t], SHRINK)
    return pd.DataFrame(rows), test_start


def implied_markets(lead_models, leaders):
    """US market moves the leaders' moves imply (step 1)."""
    return {m: sum(mdl["beta"][k] * leaders.get(k, 0.0) for k in LEADERS) for m, mdl in lead_models.items()}


def implied_india(india_models, markets, brent, repo=0.0):
    """Rupee and India CPI moves the US markets, oil and the repo rate imply (step 2), without the usual drift."""
    x = {**markets, "brent": brent, "rbi": repo}
    return {t: sum(m["beta"][k] * x.get(k, 0.0) for k in m["beta"]) for t, m in india_models.items()}


def what_if(models, inputs):
    """Step 3: expected 3-month move of each result for the given market, oil and India moves,
    with a 68% range and each input's part."""
    out = {}
    for t, m in models.items():
        parts = {k: m["beta"][k] * inputs.get(k, 0.0) for k in m["beta"]}
        mid = m["const"] + sum(parts.values())
        out[t] = {"mid": mid, "lo": mid - m["resid_sd"], "hi": mid + m["resid_sd"], "parts": parts, "base": m["const"]}
    return out
