# Macro Dashboard · USA → India

A dashboard that updates itself. Every weekday a GitHub job downloads the latest US and India macro data, labels each indicator as a tailwind or headwind for India, and the Streamlit app shows it month by month back to 1995.

```
fetch.py  ->  data/raw/*.csv        (FRED + Yahoo Finance, automatic)
data/manual/*.csv                   (RBI, FII/DII, PMI, events: you add these monthly)
build.py  ->  data/monthly.csv      (one value per month per indicator)
              data/signals.csv      (T / H / N label per month per indicator)
app.py    ->  the dashboard         (Streamlit)
.github/workflows/update.yml        (runs fetch + build every weekday)
```

## One-time setup (about an hour)

### 1. Try it on your computer
```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python fetch.py      # downloads ~25 series since 1995 (1–2 minutes)
python build.py      # builds the monthly tables
streamlit run app.py # opens the dashboard in your browser
```
No API key is needed: FRED is read through its public CSV download link.
`fetch.py` prints `ok` or `FAILED` for every series. A failed series keeps its old file, and the dashboard shows "—" for it.

### 2. Put it on GitHub
1. Create a new repository on github.com (public is fine; private also works).
2. Upload this whole folder, including the `data/` folder from step 1 and the hidden `.github` and `.streamlit` folders.
3. In the repo: **Settings → Actions → General → Workflow permissions → Read and write permissions → Save.** The job needs this to save new data.
4. Go to the **Actions** tab, open **Update data**, and press **Run workflow** once to check it works.

### 3. Put the dashboard online
1. Sign in at https://share.streamlit.io with your GitHub account.
2. **Create app → pick this repo → main file `app.py` → Deploy.**
3. You get a link like `https://<name>.streamlit.app`. It redeploys by itself whenever the GitHub job commits new data.

## What runs on its own
- Weekdays at 14:17 UTC (19:47 IST), GitHub runs `fetch.py` and `build.py` and commits the new `data/` files.
- Streamlit picks up the new data. Nothing to do.

## Your monthly 10 minutes
Some India data has no clean free download, so you add it by hand. Open the files in `data/manual/` (Excel or GitHub's web editor) and add a row for the new month:

| File | What to add | Where to get it |
|---|---|---|
| `rbi.csv` | repo rate, CPI %, forex reserves ($ bn), liquidity (₹ lakh crore, + surplus), current account % of GDP (quarterly) | RBI DBIE: https://data.rbi.org.in |
| `flows.csv` | net FII and DII equity flows for the month (₹ crore) | NSDL FPI monitor; NSE/BSE for DII |
| `pmi.csv` | US and India manufacturing PMI | ISM and S&P Global press releases |
| `events.csv` | upcoming FOMC, RBI, CPI dates | Fed and RBI calendars |

If `rbi.csv` is empty, India CPI, India 10Y and forex reserves fall back to the OECD/IMF series on FRED (monthly, a little delayed). Repo, liquidity, current account, FII/DII and PMI stay blank until you fill them.

Committing these files also keeps the scheduled job alive: GitHub pauses schedules in repos with no activity for 60 days.

## Changing the tailwind / headwind rules
All rules are in `config.py`, next to each indicator. Examples:
- `{"type": "change", "months": 3, "polarity": -1}`: a big rise over 3 months is a headwind (US 10Y, DXY, Brent). "Big" means more than half its usual 3-month move over the last 5 years.
- `{"type": "level", "good_below": 4.0, "bad_above": 6.0}`: India CPI under 4% is a tailwind, over 6% a headwind.
- `{"type": "sign", "polarity": +1, "dead": 5000}`: FII inflows above ₹5,000 cr are a tailwind, outflows beyond that a headwind.
- `{"type": "neutral"}`: always neutral (gold, silver).

Change a number, run `python build.py`, refresh the app.

"Most like" compares the selected month with every month at least a year away, using all indicators scaled to the same range, and picks the closest.

## Adding an indicator
1. Add its source to `RAW` in `config.py` (a FRED ID, a Yahoo ticker or a manual CSV column).
2. Add an entry to `INDICATORS` with a label, stage (`L`, `T`, `R`, `F`), topic, calculation, format and rule.
3. Run `python fetch.py && python build.py`.

## Known limits
- Yahoo Finance access (`yfinance`) is unofficial and breaks now and then. Usually `pip install -U yfinance` fixes it.
- Some series start after 1995: Fed balance sheet (Dec 2002), Bank Nifty and Nifty on Yahoo (2000s), India VIX (2008). Earlier months show "—".
- FRED series IDs were right when this was written; if one fails, search for the series on fred.stlouisfed.org and update the ID in `config.py`.
- The labels are simple rules, not forecasts or trading advice.
