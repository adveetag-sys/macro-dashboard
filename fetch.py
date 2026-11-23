"""Download every automatic series into data/raw/<name>.csv (columns: date,value).

Run:  python fetch.py
FRED is read from its public CSV download link, so no API key is needed.
A series that fails keeps its previous file, so one broken source never
wipes the dashboard. Failures are listed in data/fetch_log.json.
"""
import io
import json
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


def fetch_fred(series_id: str) -> pd.Series:
    resp = requests.get(FRED_URL.format(id=series_id, start=START), timeout=60,
                        headers={"User-Agent": "macro-dashboard/1.0"})
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # FRED uses "." for missing
    return df.dropna().set_index("date")["value"]


def fetch_yahoo(ticker: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(ticker, start=START, interval="1d", progress=False, auto_adjust=False,
                     threads=False, timeout=30)
    if df.empty:
        raise ValueError("no rows returned")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):  # newer yfinance returns one column per ticker
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.dropna().rename("value")


PER_SERIES_SECONDS = 90  # give up on one series after this long and keep its old file


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
    log = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ok": [], "failed": {}}
    for name, spec in RAW.items():
        if spec["source"] == "manual":
            continue
        try:
            fn = fetch_fred if spec["source"] == "fred" else fetch_yahoo
            s = with_time_limit(fn, spec["id"])
            s.rename("value").to_frame().to_csv(RAW_DIR / f"{name}.csv", index_label="date")
            log["ok"].append(name)
            print(f"ok      {name:8s} {spec['id']:18s} {len(s):6d} rows, last {s.index.max().date()}")
        except Exception as exc:  # keep the old file and carry on
            log["failed"][name] = f"{spec['id']}: {exc}"
            print(f"FAILED  {name:8s} {spec['id']:18s} {exc}")
        time.sleep(0.5)  # be polite to the free endpoints
    Path("data/fetch_log.json").write_text(json.dumps(log, indent=2))
    print(f"\n{len(log['ok'])} ok, {len(log['failed'])} failed")


if __name__ == "__main__":
    main()
