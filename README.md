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
4. Get a free FRED API key (fred.stlouisfed.org → My Account → API Keys) and add it in the repo under **Settings → Secrets and variables → Actions → New repository secret**, name `FRED_API_KEY`. FRED's public download links are slow from GitHub's servers; the API is not.
5. Go to the **Actions** tab, open **Update data**, and press **Run workflow** once to check it works.

### 3. Put the dashboard online
1. Sign in at https://share.streamlit.io with your GitHub account.
2. **Create app → pick this repo → main file `app.py` → Deploy.**
3. You get a link like `https://<name>.streamlit.app`. It redeploys by itself whenever the GitHub job commits new data.

## What runs on its own
- Weekdays at 14:17 UTC (19:47 IST), GitHub runs `fetch.py` and `build.py` and commits the new `data/` files.
- Streamlit picks up the new data. Nothing to do.

## Your monthly 10 minutes
Some India data has no clean free download, so you add it by hand in `data/manual/` (Excel, Notepad or GitHub's web editor), then push.

### The calendar
| When | What comes out | File · column · which row |
|---|---|---|
| 1st business day | US ISM and HSBC India manufacturing PMI | `pmi.csv` · `us_pmi`, `india_pmi` · previous month |
| Only if flagged | FII and DII net flows are now automatic (see below). Fill `flows.csv` only for a month the build log says is incomplete | `flows.csv` · `fii_cr`, `dii_cr` · that month |
| ~12th–14th | India CPI (MoSPI press release) | `rbi.csv` · `cpi_yoy` · previous month |
| RBI policy day (6 a year) | Repo decision; Governor's statement gives monthly average liquidity | `rbi.csv` · `repo` (that month onwards), `liquidity_lakh_cr` (months it lists) |
| ~25th | RBI Bulletin "State of the Economy" (monthly liquidity average) | `rbi.csv` · `liquidity_lakh_cr` |
| Twice a month | RBI "Money Market Operations" release: line I, net durable liquidity | `rbi.csv` · `durable_lakh_cr` · month of the "as on" date (keep the last one in the month) |
| End of Feb / May / Aug / Nov | India GDP for the quarter (MoSPI) | `rbi.csv` · `gdp_in_yoy` · FIRST month of the quarter (Jul–Sep → `YYYY-07`) |
| ~2–3 months after quarter end | India current account % of GDP (RBI BoP release) | `rbi.csv` · `cad_pct_gdp` · LAST month of the quarter (Jul–Sep → `YYYY-09`) |
| As dates are announced | FOMC, RBI, CPI, jobs, budget dates | `events.csv` · `date,event,type` |

### FII / DII: automatic from December 2026
Every weekday run saves that day's provisional FII/FPI and DII net figures (NSE's feed, or MSEI's page if NSE blocks the request) to `data/auto/fii_dii_daily.csv`, and `build.py` adds them up by month.
- A month is used only if the daily record has no real gaps (starts in the first 5 days, at most 2 weekdays missing for holidays). The current month shows month-to-date.
- If a run misses days, the build log (Actions run → "python build.py" step) prints `FII/DII YYYY-MM: daily record incomplete ... using flows.csv`. Then type that month's full total into `flows.csv` as before.
- If `fii_dii` shows under "failed" in `data/fetch_log.json` for several days in a row, NSE and MSEI are both blocking GitHub's servers: go back to filling `flows.csv` by hand.
- November 2026 still comes from `flows.csv` (the record starts on 23 Nov), so replace its month-to-date figure with the full month on 1 Dec.

### Rules of thumb
- One row per month, `YYYY-MM` in the first column. Leave a cell empty if you don't have it; never type 0 for "unknown".
- Add a new month's row in `rbi.csv` by copying the last line and changing the month and the numbers you have.
- Liquidity is in ₹ lakh crore, + = surplus, − = deficit. FII/DII are in ₹ crore, − = net selling.
- Slow series (GDP, current account, repo, PMI, liquidity) are carried forward up to 3 months, so a missing month shows the last value with an "as of" note.

### Where to get each number
| Number | Source |
|---|---|
| FII / DII (backup only) | tapetide.com monthly "FII and DII Flows" report, or NSE provisional data |
| India CPI | MoSPI CPI press release (mospi.gov.in) |
| Repo, liquidity | RBI monetary policy statement and RBI Bulletin "State of the Economy" (rbi.org.in) |
| India GDP | MoSPI quarterly GDP press note |
| Current account | RBI "Developments in India's Balance of Payments" press release |
| PMI | ISM (ismworld.org) and S&P Global / HSBC India PMI press releases |

### Push
```powershell
git add data/manual
git commit -m "Monthly data update"
git pull
git push
```
No workflow run needed: the dashboard rebuilds at the next scheduled run (weekdays 19:47 IST), or click Run workflow to see it now.

If a manual column is empty, India CPI, India 10Y, India GDP and forex reserves fall back to the OECD/IMF series on FRED. Repo, liquidity, current account, FII/DII and PMI stay blank until you fill them.

Committing these files also keeps the scheduled job alive: GitHub pauses schedules in repos with no activity for 60 days.

## The Simulator tab
Three history-based tools (the maths is in `simulator.py`). Each shows its own track record on the page.
- **Nifty range from India VIX:** the 68% and 95% range the options market is pricing for any number of days ahead. Since 2008, Nifty stayed inside the 1-sigma range about 75% of the time (theory 68%).
- **What happened next:** the 15 past months most like the selected month, and what Nifty, the rupee and FII flows did over the next 3, 6 and 12 months. Good for the size of the range; no better than "Nifty usually rises" for direction.
- **What if:** sliders for US 10Y, dollar, oil and S&P 500 moves over 3 months, giving the typical knock-on for Nifty, rupee, FII flows, India 10Y and India CPI, with a 68% range and how much history explains (R²).
None of it is a prediction or trading advice, and shocks like March 2020 fall outside all three.

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
