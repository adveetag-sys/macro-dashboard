"""Near-live market prices for the dashboard, pulled from Yahoo Finance when the page is open.

Yahoo's Indian prices run about 15 minutes behind; US and commodity prices are close to real time.
Only market prices can be live. Everything else (CPI, GDP, jobs, repo, FII flows...) is published
daily, weekly, monthly or quarterly, and the dashboard shows the latest release with its date.
"""
import pandas as pd

# dashboard indicator -> Yahoo ticker
TICKERS = {
    "nifty": "^NSEI", "bank": "^NSEBANK", "inVix": "^INDIAVIX", "inr": "INR=X",
    "sp": "^GSPC", "ndx": "^NDX", "vix": "^VIX", "dxy": "DX-Y.NYB", "us10": "^TNX",
    "brent": "BZ=F", "gold": "GC=F", "silver": "SI=F",
}
IST = "Asia/Kolkata"


def _last_points(df, tickers):
    close = df["Close"] if "Close" in df else df
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    out = {}
    for t in tickers:
        if t not in close:
            continue
        s = close[t].dropna()
        if s.empty:
            continue
        ts = pd.Timestamp(s.index[-1])
        ts = (ts.tz_localize("UTC") if ts.tzinfo is None else ts).tz_convert(IST)
        out[t] = (float(s.iloc[-1]), ts)
    return out


def fetch(download=None):
    """Latest price and time for each ticker: {indicator: (value, timestamp in IST)}.
    Tries 5-minute bars first, then daily bars for anything still missing."""
    if download is None:
        import yfinance as yf
        download = yf.download
    tickers = list(TICKERS.values())
    got = {}
    for period, interval in (("5d", "5m"), ("5d", "1d")):
        need = [t for t in tickers if t not in got]
        if not need:
            break
        try:
            df = download(need, period=period, interval=interval, progress=False, auto_adjust=False,
                          threads=True, timeout=10, group_by="column")
            if df is not None and not df.empty:
                got.update(_last_points(df, need))
        except Exception:
            pass
    out = {}
    for k, t in TICKERS.items():
        if t in got:
            v, ts = got[t]
            if k == "us10" and v > 20:  # ^TNX is sometimes quoted as yield x10
                v /= 10
            out[k] = (v, ts)
    return out
