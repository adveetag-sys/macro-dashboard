"""Indicator registry: one entry per number on the dashboard.

Each indicator says where its data comes from, how to turn it into one
value per month, which stage of the chain it belongs to, and the rule that
labels it a tailwind (T), headwind (H) or neutral (N) for India.

Series IDs were correct as far as we know when this was written. If a
fetch fails, check the ID on fred.stlouisfed.org or finance.yahoo.com.
"""

START = "1995-01-01"

# Stages of the transmission chain
STAGES = {
    "L": ("1", "Moves first", "US data, the Fed and oil"),
    "T": ("2", "Carries the change", "Yields, the dollar and foreign money"),
    "R": ("3", "Reacts", "Rupee, RBI and Indian inflation"),
    "F": ("4", "Moves last", "Stocks, metals and volatility"),
}

# --- Raw inputs -----------------------------------------------------------
# source: fred | yahoo | manual
# agg:    how to turn daily/weekly data into one monthly value
#         "last" = value at month end, "mean" = average, "sum" = total
RAW = {
    # FRED (free API key: https://fred.stlouisfed.org/docs/api/api_key.html)
    "payems":   {"source": "fred", "id": "PAYEMS",          "agg": "last"},  # nonfarm payrolls, thousands
    "unrate":   {"source": "fred", "id": "UNRATE",          "agg": "last"},
    "cpi_us":   {"source": "fred", "id": "CPIAUCSL",        "agg": "last"},  # index
    "gdp_us":   {"source": "fred", "id": "A191RL1Q225SBEA", "agg": "last"},  # real GDP, % q/q annualised
    "dff":      {"source": "fred", "id": "DFF",             "agg": "last"},  # effective fed funds rate
    "walcl":    {"source": "fred", "id": "WALCL",           "agg": "last"},  # Fed total assets, $ millions (from 2002)
    "wresbal":  {"source": "fred", "id": "WRESBAL",         "agg": "last"},  # reserve balances, $ millions
    "brent":    {"source": "fred", "id": "DCOILBRENTEU",    "agg": "last"},
    "us10":     {"source": "fred", "id": "DGS10",           "agg": "last"},
    "us2":      {"source": "fred", "id": "DGS2",            "agg": "last"},
    "vix":      {"source": "fred", "id": "VIXCLS",          "agg": "last"},
    "usdinr":   {"source": "fred", "id": "DEXINUS",         "agg": "last"},  # rupees per dollar, from 1973
    # India series published on FRED by the OECD / IMF (used if no RBI file is supplied)
    "in10":     {"source": "fred", "id": "INDIRLTLT01STM",  "agg": "last"},  # India long-term govt bond yield
    "cpi_in":   {"source": "fred", "id": "INDCPIALLMINMEI", "agg": "last"},  # India CPI index
    "fx_in":    {"source": "fred", "id": "TRESEGINM052N",   "agg": "last"},  # India reserves excl. gold, $ millions

    # Yahoo Finance (via yfinance; unofficial, may need fixing now and then)
    "nifty":    {"source": "yahoo", "id": "^NSEI",     "agg": "last"},
    "bank":     {"source": "yahoo", "id": "^NSEBANK",  "agg": "last"},
    "sp":       {"source": "yahoo", "id": "^GSPC",     "agg": "last"},
    "ndx":      {"source": "yahoo", "id": "^NDX",      "agg": "last"},
    "gold":     {"source": "yahoo", "id": "GC=F",      "agg": "last"},
    "silver":   {"source": "yahoo", "id": "SI=F",      "agg": "last"},
    "dxy":      {"source": "yahoo", "id": "DX-Y.NYB",  "agg": "last"},
    "invix":    {"source": "yahoo", "id": "^INDIAVIX", "agg": "last"},

    # Manual CSVs in data/manual/ (see README). Columns: month,<name>
    "repo":     {"source": "manual", "file": "rbi.csv",   "col": "repo"},
    "liq":      {"source": "manual", "file": "rbi.csv",   "col": "liquidity_lakh_cr"},
    "cad_in":   {"source": "manual", "file": "rbi.csv",   "col": "cad_pct_gdp"},
    "fx_rbi":   {"source": "manual", "file": "rbi.csv",   "col": "fx_reserves_bn"},
    "cpi_rbi":  {"source": "manual", "file": "rbi.csv",   "col": "cpi_yoy"},
    "fii":      {"source": "manual", "file": "flows.csv", "col": "fii_cr"},
    "dii":      {"source": "manual", "file": "flows.csv", "col": "dii_cr"},
    "pmi_us":   {"source": "manual", "file": "pmi.csv",   "col": "us_pmi"},
    "pmi_in":   {"source": "manual", "file": "pmi.csv",   "col": "india_pmi"},
}

# --- Dashboard indicators -------------------------------------------------
# calc: python expression over the monthly raw table `r` (a DataFrame).
# fmt:  how to print one value.
# rule: how to label it for India
#   {"type": "change", "months": 3, "polarity": +1/-1}
#        compares the change over N months with its own typical size;
#        polarity +1 means "higher is good for India", -1 "higher is bad"
#   {"type": "level", "good_below": x, "bad_above": y}   (or good_above / bad_below)
#   {"type": "sign", "polarity": +1}   positive value = tailwind
#   {"type": "neutral"}
INDICATORS = [
    # 1 Moves first
    dict(k="usJobs", label="US payrolls", stage="L", topic="usdata", top=True, sub="Jobs added that month",
         calc="r.payems.diff()", fmt="{:+,.0f}k", rule={"type": "change", "months": 3, "polarity": -1}),
    dict(k="usCpi", label="US CPI", stage="L", topic="usdata", top=True, sub="Year on year",
         calc="r.cpi_us.pct_change(12) * 100", fmt="{:.1f}%", rule={"type": "level", "good_below": 2.5, "bad_above": 3.5}),
    dict(k="pmi", label="US manufacturing PMI", stage="L", topic="usdata", top=False, sub="Above 50 = growing",
         calc="r.pmi_us", fmt="{:.1f}", rule={"type": "neutral"}),
    dict(k="gdp", label="US GDP growth", stage="L", topic="usdata", top=False, sub="Quarterly, annualised",
         calc="r.gdp_us", fmt="{:.1f}%", rule={"type": "neutral"}),
    dict(k="fed", label="Fed funds rate", stage="L", topic="fed", top=True, sub="Effective rate",
         calc="r.dff", fmt="{:.2f}%", rule={"type": "change", "months": 6, "polarity": -1}),
    dict(k="fedBs", label="Fed balance sheet", stage="L", topic="fed", top=True, sub="QE grows it, QT shrinks it",
         calc="r.walcl / 1e6", fmt="${:.2f}T", rule={"type": "change", "months": 3, "polarity": +1}),
    dict(k="brent", label="Brent crude", stage="L", topic="brent", top=True, sub="$ per barrel",
         calc="r.brent", fmt="${:.0f}", rule={"type": "change", "months": 3, "polarity": -1, "pct": True}),
    # 2 Carries the change
    dict(k="us10", label="US 10Y yield", stage="T", topic="yields", top=True, sub="Prices the Fed",
         calc="r.us10", fmt="{:.2f}%", rule={"type": "change", "months": 3, "polarity": -1}),
    dict(k="gap", label="India–US 10Y gap", stage="T", topic="yields", top=True, sub="Wider pulls in FIIs",
         calc="r.in10 - r.us10", fmt="{:.1f} pts", rule={"type": "change", "months": 3, "polarity": +1}),
    dict(k="dxy", label="DXY", stage="T", topic="dollar", top=True, sub="Dollar vs 6 currencies",
         calc="r.dxy", fmt="{:.1f}", rule={"type": "change", "months": 3, "polarity": -1, "pct": True}),
    dict(k="usRes", label="US bank reserves", stage="T", topic="dollar", top=False, sub="Dollar liquidity",
         calc="r.wresbal / 1e6", fmt="${:.2f}T", rule={"type": "change", "months": 3, "polarity": +1, "pct": True}),
    dict(k="fii", label="FII flows", stage="T", topic="fii", top=True, sub="Net, that month",
         calc="r.fii", fmt="₹{:+,.0f} cr", rule={"type": "sign", "polarity": +1, "dead": 5000}),
    # 3 Reacts
    dict(k="inr", label="USD/INR", stage="R", topic="inr", top=True, sub="Up = weaker rupee",
         calc="r.usdinr", fmt="₹{:.2f}", rule={"type": "change", "months": 3, "polarity": -1, "pct": True}),
    dict(k="rbi", label="RBI repo", stage="R", topic="rbi", top=True, sub="Policy rate",
         calc="r.repo", fmt="{:.2f}%", rule={"type": "change", "months": 6, "polarity": -1}),
    dict(k="inCpi", label="India CPI", stage="R", topic="incpi", top=True, sub="RBI band 2–6%",
         calc="r.cpi_rbi.combine_first(r.cpi_in.pct_change(12) * 100)", fmt="{:.1f}%",
         rule={"type": "level", "good_below": 4.0, "bad_above": 6.0}),
    dict(k="fx", label="Forex reserves", stage="R", topic="rbi", top=True, sub="RBI firepower",
         calc="r.fx_rbi.combine_first(r.fx_in / 1e3)", fmt="${:,.0f}B",
         rule={"type": "change", "months": 3, "polarity": +1, "pct": True}),
    dict(k="inLiq", label="Bank liquidity", stage="R", topic="rbi", top=False, sub="₹ lakh crore, + = surplus",
         calc="r.liq", fmt="{:+.1f}", rule={"type": "sign", "polarity": +1, "dead": 0.5}),
    dict(k="cad", label="India current account", stage="R", topic="incpi", top=False, sub="% of GDP",
         calc="r.cad_in", fmt="{:+.1f}%", rule={"type": "level", "good_above": -1.5, "bad_below": -2.5}),
    # 4 Moves last
    dict(k="nifty", label="Nifty 50", stage="F", topic="nifty", top=True, sub="India large-caps",
         calc="r.nifty", fmt="{:,.0f}", rule={"type": "change", "months": 3, "polarity": +1, "pct": True}),
    dict(k="bank", label="Bank Nifty", stage="F", topic="nifty", top=True, sub="Rates and liquidity",
         calc="r.bank", fmt="{:,.0f}", rule={"type": "change", "months": 3, "polarity": +1, "pct": True}),
    dict(k="sp", label="S&P 500", stage="F", topic="usstocks", top=True, sub="US large-caps",
         calc="r.sp", fmt="{:,.0f}", rule={"type": "change", "months": 3, "polarity": +1, "pct": True}),
    dict(k="ndx", label="Nasdaq 100", stage="F", topic="usstocks", top=False, sub="US tech",
         calc="r.ndx", fmt="{:,.0f}", rule={"type": "change", "months": 3, "polarity": +1, "pct": True}),
    dict(k="gold", label="Gold", stage="F", topic="metals", top=True, sub="$ per ounce",
         calc="r.gold", fmt="${:,.0f}", rule={"type": "neutral"}),
    dict(k="silver", label="Silver", stage="F", topic="metals", top=False, sub="$ per ounce",
         calc="r.silver", fmt="${:.1f}", rule={"type": "neutral"}),
    dict(k="vix", label="VIX", stage="F", topic="vix", top=True, sub="US fear gauge",
         calc="r.vix", fmt="{:.1f}", rule={"type": "level", "good_below": 15, "bad_above": 25}),
    dict(k="inVix", label="India VIX", stage="F", topic="vix", top=False, sub="Sets option prices",
         calc="r.invix", fmt="{:.1f}", rule={"type": "level", "good_below": 13, "bad_above": 20}),
]

# Cards in the "Key market pulse" row (pairs)
PULSE = [["inr", "nifty"], ["us10", "dxy"], ["fii", "gold"]]
# Charts in the "Trends" panel
TRENDS = ["inr", "gold", "silver"]
