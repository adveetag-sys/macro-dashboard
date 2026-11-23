"""Download every automatic series into data/raw/<name>.csv (columns: date,value).

Run:  python fetch.py
FRED: if the environment variable FRED_API_KEY is set (free key from
fred.stlouisfed.org), the official API is used; it is the reliable route from
cloud servers such as GitHub Actions. Without a key it falls back to FRED's
public CSV download link, which works fine from a home connection.
A series that fails keeps its previous file, so one broken source never
wipes the dashboard. Failures are listed in data/fetch_log.json.
"""
import io
import json
import os
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from config import RAW, START

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={start}"
FRED_API = "https://api.stlouisfed.org/fred/series/observations"
FRED_KEY = os.environ.get("FRED_API_KEY", "").strip()
TIMEOUT = (10, 30)  # seconds to connect, seconds to wait for data


def fetch_fred(series_id: str) -> pd.Series:
    if FRED_KEY:
        resp = requests.get(FRED_API, timeout=TIMEOUT, params={
            "series_id": series_id, "api_key": FRED_KEY, "file_type": "json", "observation_start": START})
        resp.raise_for_status()
        obs = resp.json()["observations"]
        df = pd.DataFrame(obs)[["date", "value"]]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna().set_index("date")["value"]
    resp = requests.get(FRED_URL.format(id=series_id, start=START), timeout=TIMEOUT,
                        headers={"User-Agent": "Mozilla/5.0 (macro-dashboard)"})
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # FRED uses "." for missing
    return df.dropna().set_index("date")["value"]


def fetch_yahoo(ticker: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(ticker, start=START, interval="1d", progress=False, auto_adjust=False,
                     threads=False, timeout=20)
    if df.empty:
        raise ValueError("no rows returned")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):  # newer yfinance returns one column per ticker
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.dropna().rename("value")


FLOWS_DAILY = Path("data/auto/fii_dii_daily.csv")


def _num(x) -> float:
    return float(str(x).replace(",", "").strip())


def fii_dii_from_nse() -> dict:
    """NSE's own feed for the latest day's FII/FPI and DII net buying (₹ crore). Needs NSE's cookies first."""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
                      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
                      "Referer": "https://www.nseindia.com/reports/fii-dii"})
    s.get("https://www.nseindia.com/reports/fii-dii", timeout=TIMEOUT)
    resp = s.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=TIMEOUT)
    resp.raise_for_status()
    out = {}
    for row in resp.json():
        cat = str(row.get("category", "")).upper()
        key = "fii_cr" if "FII" in cat or "FPI" in cat else "dii_cr" if "DII" in cat else None
        if key:
            out[key] = _num(row["netValue"])
            out["date"] = pd.to_datetime(row["date"], format="%d-%b-%Y")
    return out


def fii_dii_from_msei() -> dict:
    """Backup: MSEI publishes the same combined NSE + BSE + MSEI numbers on a plain web page."""
    import re
    resp = requests.get("https://www.msei.in/downloads/equity-reports/fii-dii-activities", timeout=TIMEOUT,
                        headers={"User-Agent": "Mozilla/5.0 (macro-dashboard)"})
    resp.raise_for_status()
    text = " ".join(re.sub(r"<[^>]+>", " ", resp.text).split())
    out = {}
    for cat, key in (("FII/FPI", "fii_cr"), ("DII", "dii_cr")):
        m = re.search(re.escape(cat) + r"\s+(\d{2}-[A-Za-z]{3}-\d{4})\s+([-\d,.]+)\s+([-\d,.]+)\s+([-\d,.]+)", text)
        if m:
            out[key] = _num(m.group(4))
            out["date"] = pd.to_datetime(m.group(1), format="%d-%b-%Y")
    return out


def fetch_fii_dii(log: dict) -> None:
    """Add the latest trading day's FII/DII net flows to data/auto/fii_dii_daily.csv.
    Only the latest day is published, so this keeps a running daily record; build.py adds it up by month."""
    row, errors = {}, []
    for name, fn in (("NSE", fii_dii_from_nse), ("MSEI", fii_dii_from_msei)):
        try:
            row = with_time_limit(fn)
            if {"date", "fii_cr", "dii_cr"} <= set(row):
                break
            errors.append(f"{name}: incomplete {row}")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
        row = {}
    if not row:
        log["failed"]["fii_dii"] = "; ".join(errors)
        print(f"FAILED  fii_dii  {'; '.join(errors)}", flush=True)
        return
    FLOWS_DAILY.parent.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(FLOWS_DAILY, parse_dates=["date"]) if FLOWS_DAILY.exists() else pd.DataFrame(columns=["date", "fii_cr", "dii_cr"])
    new = pd.concat([old, pd.DataFrame([row])]).drop_duplicates("date", keep="last").sort_values("date")
    new.to_csv(FLOWS_DAILY, index=False, date_format="%Y-%m-%d")
    log["ok"].append("fii_dii")
    print(f"ok      fii_dii  {row['date'].date()}  FII {row['fii_cr']:+,.2f} cr  DII {row['dii_cr']:+,.2f} cr", flush=True)


PER_SERIES_SECONDS = 40  # give up on one series after this long and keep its old file


class TimedOut(Exception):
    pass


def with_time_limit(fn, *args):
    """Run fn(*args) but stop waiting after PER_SERIES_SECONDS."""
    if hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread():  # Linux / macOS / GitHub
        def _raise(signum, frame):
            raise TimedOut(f"took longer than {PER_SERIES_SECONDS}s")
        old = signal.signal(signal.SIGALRM, _raise)
        signal.alarm(PER_SERIES_SECONDS)
        try:
            return fn(*args)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    return fn(*args)  # Windows: no alarm; requests/yfinance timeouts still apply


def main() -> None:
    print(f"FRED via {'API key' if FRED_KEY else 'public CSV link'}", flush=True)
    log = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ok": [], "failed": {}}
    for name, spec in RAW.items():
        if spec["source"] == "manual":
            continue
        try:
            fn = fetch_fred if spec["source"] == "fred" else fetch_yahoo
            s = with_time_limit(fn, spec["id"])
            s.rename("value").to_frame().to_csv(RAW_DIR / f"{name}.csv", index_label="date")
            log["ok"].append(name)
            print(f"ok      {name:8s} {spec['id']:18s} {len(s):6d} rows, last {s.index.max().date()}", flush=True)
        except Exception as exc:  # keep the old file and carry on
            log["failed"][name] = f"{spec['id']}: {exc}"
            print(f"FAILED  {name:8s} {spec['id']:18s} {exc}", flush=True)
        time.sleep(0.5)  # be polite to the free endpoints
    fetch_fii_dii(log)
    Path("data/fetch_log.json").write_text(json.dumps(log, indent=2))
    print(f"\n{len(log['ok'])} ok, {len(log['failed'])} failed")


if __name__ == "__main__":
    main()
