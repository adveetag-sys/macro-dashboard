"""Turn raw files into the monthly tables the app reads.

Run:  python build.py
Writes:
  data/monthly.csv   one row per month, one column per dashboard indicator
  data/signals.csv   same shape, each cell T (tailwind), H (headwind) or N
  data/asof.csv      which month each shown value actually comes from
  data/meta.json     last update time and which sources are missing
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from config import INDICATORS, RAW, START

DATA = Path("data")


def auto_flows_monthly() -> pd.DataFrame:
    """Monthly FII/DII totals from the daily record fetch.py keeps (data/auto/fii_dii_daily.csv).
    A month counts only if the record has no real gaps: it starts within the first 5 days of the month
    and misses at most 2 weekdays (allowing for market holidays). The current month is month-to-date."""
    path = DATA / "auto" / "fii_dii_daily.csv"
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, parse_dates=["date"]).dropna().drop_duplicates("date")
    rows = {}
    for month, g in d.groupby(d["date"].dt.to_period("M")):
        days = set(g["date"].dt.normalize())
        weekdays = pd.bdate_range(month.start_time, g["date"].max())
        missing = sum(1 for x in weekdays if x not in days)
        if g["date"].min().day <= 5 and missing <= 2:
            rows[month] = {"fii": g["fii_cr"].sum(), "dii": g["dii_cr"].sum()}
        else:
            print(f"FII/DII {month}: daily record incomplete ({len(days)} days, {missing} weekdays missing), using flows.csv")
    return pd.DataFrame.from_dict(rows, orient="index")


DAILY = {}     # every fetched series at its own frequency (daily, weekly, ...), filled by load_raw_monthly
UNFILLED = {}  # monthly raw series before slow ones are carried forward, to date each latest value honestly


def read_raw(name):
    path = DATA / "raw" / f"{name}.csv"
    if not path.exists():
        return None
    s = pd.read_csv(path, parse_dates=["date"], index_col="date")["value"].dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def load_daily(name, spec):
    """A fetched series, with a fresher copy's newer days added on the end when config says "extend"
    (FRED publishes Brent, USD/INR, US 10Y and VIX a day to a week late; Yahoo has them the same day)."""
    s = read_raw(name)
    ext = read_raw(spec["extend"]) if spec.get("extend") else None
    if s is None or s.empty:
        return ext
    if ext is not None and not ext.empty:
        newer = ext[ext.index > s.index.max()]
        if len(newer):
            if 8 <= newer.iloc[0] / s.iloc[-1] <= 12:  # Yahoo's ^TNX can quote the yield x10
                newer = newer / 10
            if 0.5 <= newer.iloc[0] / s.iloc[-1] <= 2:  # same scale (VIX can genuinely move 30% in a day): safe to join
                s = pd.concat([s, newer])
            else:
                print(f"{name}: {spec['extend']} looks off ({newer.iloc[0]:.2f} vs {s.iloc[-1]:.2f}), not joined")
    return s


def frequency(s):
    gap = s.index.to_series().diff().dt.days.tail(20).median()
    return "daily" if gap <= 4 else "weekly" if gap <= 10 else "monthly" if gap <= 45 else "quarterly"


def latest_dates(raw, asof_row):
    """For each indicator's latest value, when that number is really from: the exact day for daily and
    weekly data, the month for monthly data and anything typed in by hand, the quarter for quarterly data.
    Slow series are carried forward a few months in the tables, so this looks at the data before that."""
    import re
    out = {}
    for ind in INDICATORS:
        k, calc = ind["k"], ind["calc"]
        month = asof_row.get(k, "")
        if not month:
            continue
        end = pd.Period(month, "M").end_time
        found = []
        for t in dict.fromkeys(re.findall(r"\br\.(\w+)", calc)):
            s = DAILY.get(t)
            if s is not None:
                s = s[s.index <= end]
                if s.empty:
                    continue
                f = frequency(s)
                found.append((f, s.index.max()))
            elif t in UNFILLED:
                u = UNFILLED[t].dropna()
                u = u[u.index <= pd.Period(month, "M")]
                if u.empty:
                    continue
                found.append(("monthly", u.index.max().to_timestamp()))
            else:
                continue
            if "combine_first" in calc:  # the first source that has data is the one shown
                break
        if not found:
            continue
        slow = [x for x in found if x[0] in ("monthly", "quarterly")]
        f, day = min(slow or found, key=lambda x: x[1])  # only as fresh as its stalest part
        if f == "quarterly":
            out[k] = {"label": f"Q{day.quarter} {day.year}", "freq": f, "date": day.strftime("%Y-%m-%d")}
        elif f == "monthly":
            out[k] = {"label": day.strftime("%b %Y"), "freq": f, "date": day.strftime("%Y-%m-%d")}
        else:
            out[k] = {"label": day.strftime("%d %b %Y").lstrip("0"), "freq": f, "date": day.strftime("%Y-%m-%d")}
    return out


def load_raw_monthly() -> pd.DataFrame:
    months = pd.period_range(START, pd.Timestamp.today(), freq="M")
    out = pd.DataFrame(index=months)
    manual_cache = {}
    for name, spec in RAW.items():
        if spec["source"] == "manual":
            path = DATA / "manual" / spec["file"]
            if not path.exists():
                out[name] = np.nan
                continue
            if path not in manual_cache:
                m = pd.read_csv(path, comment="#")
                m["month"] = pd.PeriodIndex(pd.to_datetime(m["month"]), freq="M")
                manual_cache[path] = m.groupby("month").last()
            df = manual_cache[path]
            out[name] = df[spec["col"]].reindex(months) if spec["col"] in df else np.nan
            continue
        s = load_daily(name, spec)
        if s is None:
            out[name] = np.nan
            continue
        DAILY[name] = s
        monthly = getattr(s.resample("ME"), spec.get("agg", "last"))()
        monthly.index = monthly.index.to_period("M")
        out[name] = monthly.reindex(months)
    auto = auto_flows_monthly()
    for col in ["fii", "dii"]:
        if col in out and not auto.empty:
            a = auto[col].reindex(months)
            out[col] = a.combine_first(out[col])  # a complete automatic month replaces the manual figure
    UNFILLED.update({c: out[c].copy() for c in out.columns})
    # quarterly / slow series: carry the last known value forward a few months
    for col in ["gdp_us", "cad_in", "repo", "pmi_us", "pmi_in", "liq", "dliq"]:
        out[col] = out[col].ffill(limit=3)
    return out


def compute_indicators(r: pd.DataFrame) -> pd.DataFrame:
    vals = pd.DataFrame(index=r.index)
    for ind in INDICATORS:
        try:
            vals[ind["k"]] = eval(ind["calc"], {"np": np}, {"r": r})  # expressions come from config.py
        except Exception as exc:
            print(f"could not compute {ind['k']}: {exc}")
            vals[ind["k"]] = np.nan
    return vals


def classify(s: pd.Series, rule: dict) -> pd.Series:
    out = pd.Series("N", index=s.index)
    t = rule["type"]
    if t == "neutral":
        pass
    elif t == "change":
        n = rule.get("months", 3)
        d = s.pct_change(n, fill_method=None) * 100 if rule.get("pct") else s.diff(n)
        # "a big move" = more than half its usual size over the last 5 years
        thr = 0.5 * d.rolling(60, min_periods=24).std()
        thr = thr.fillna(d.abs().median())
        signed = d * rule["polarity"]
        out[signed > thr] = "T"
        out[signed < -thr] = "H"
    elif t == "level":
        if "good_below" in rule:
            out[s < rule["good_below"]] = "T"
            out[s > rule["bad_above"]] = "H"
        else:
            out[s > rule["good_above"]] = "T"
            out[s < rule["bad_below"]] = "H"
    elif t == "sign":
        dead = rule.get("dead", 0)
        out[s * rule["polarity"] > dead] = "T"
        out[s * rule["polarity"] < -dead] = "H"
    out[s.isna()] = ""  # no data -> no label
    return out


def main() -> None:
    raw = load_raw_monthly()
    actual = compute_indicators(raw)  # only months that have a real reading
    sig_actual = pd.DataFrame({ind["k"]: classify(actual[ind["k"]], ind["rule"]) for ind in INDICATORS}, index=actual.index)
    # Monthly / weekly releases lag (e.g. October CPI comes out in November), so carry the
    # latest reading forward up to 3 months and remember which month it really belongs to.
    vals = actual.ffill(limit=3)
    sigs = sig_actual.replace("", np.nan).ffill(limit=3).fillna("")
    asof = pd.DataFrame({c: pd.Series(np.where(actual[c].notna(), actual.index.astype(str), None), index=actual.index)
                         for c in actual.columns}).ffill(limit=3).fillna("")
    keep = vals.notna().sum(axis=1) >= 5  # keep months that have at least a handful of indicators
    vals, sigs, asof = vals[keep], sigs[keep], asof[keep]
    for df in (vals, sigs, asof):
        df.index = df.index.astype(str)
    vals.to_csv(DATA / "monthly.csv", index_label="month")
    sigs.to_csv(DATA / "signals.csv", index_label="month")
    asof.to_csv(DATA / "asof.csv", index_label="month")
    latest = latest_dates(raw, asof.iloc[-1].to_dict()) if len(asof) else {}
    daily_flows = DATA / "auto" / "fii_dii_daily.csv"
    if daily_flows.exists() and "fii" in latest:  # the newest single day, shown next to the monthly total
        d = pd.read_csv(daily_flows, parse_dates=["date"]).dropna().sort_values("date")
        if len(d):
            x = d.iloc[-1]
            latest["fii"]["last_day"] = {"label": x["date"].strftime("%d %b").lstrip("0"), "fii": float(x["fii_cr"]), "dii": float(x["dii_cr"])}
    (DATA / "latest.json").write_text(json.dumps(latest, indent=1))
    missing = [ind["k"] for ind in INDICATORS if vals[ind["k"]].notna().sum() == 0]
    meta = {"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "first_month": vals.index.min() if len(vals) else None,
            "last_month": vals.index.max() if len(vals) else None,
            "missing_indicators": missing}
    (DATA / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"built {len(vals)} months ({meta['first_month']} to {meta['last_month']}); missing: {missing or 'none'}")


if __name__ == "__main__":
    main()
