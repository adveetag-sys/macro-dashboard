# Silver ETF / MCX futures cash-and-carry bot

**Trade:** buy a silver ETF on NSE (e.g. SILVERBEES), sell the same number of grams in MCX silver futures (SILVERM by default). You collect the futures premium (the "carry"). Unwind when the premium has shrunk, or a few days before expiry.

## How it decides
```
fut_per_unit = futures_price / 1000 * grams_per_unit        # Rs per ETF unit
gross        = fut_bid_per_unit / etf_ask - 1                # executable premium
net          = gross - round-trip costs
annualised   = net / (1 + margin_pct) * 365 / days_to_expiry  # return on ETF cash + futures margin
```
- **Enter** when `annualised >= min_annual_return` and the ETF offer has enough depth.
- **Exit** when the remaining premium (`fut_ask / etf_bid - 1`) is at or below `exit_remaining_basis`, or `days_to_expiry <= exit_days_before_expiry`.
- **Size:** 1 SILVERM lot = 5,000 g, so ETF units = 5000 / grams_per_unit.

## Execution and safety
- It buys the ETF first, because the ETF is less liquid, then sells the futures. Both are limit orders at the touch plus a small buffer.
- If either leg doesn't fill within `leg_timeout_sec`, the bot cancels it and unwinds the other leg.
- A leg it can't unwind becomes an **orphan**. The bot records it in `positions.json`, retries it every loop, and opens no new pairs until it is flat.
- Positions are saved to disk, so a restart doesn't lose them.
- Other guards: a daily loss limit, a stale-quote check, max open pairs, and trading only within the NSE/MCX overlap window.

## Files
| File | What it does |
|---|---|
| `config.yaml` | All settings |
| `get_token.py` | Daily Kite login, writes `access_token.txt` |
| `fetch_data.py` | Downloads ETF + futures candles into `data.csv` |
| `backtest.py` | Backtests the rules on that CSV |
| `run.py` | Runs the bot (paper or live) |
| `strategy.py`, `broker.py`, `kite_session.py` | Bot logic and broker connection |

## 1. One-time setup
```
pip install kiteconnect pyyaml pandas matplotlib
```
1. Create an app at developers.kite.trade. Put its `api_key` and `api_secret` in `config.yaml`. The historical data API needs the paid Kite Connect plan.
2. **Set `etf.grams_per_unit`.** Compute it as ETF NAV / domestic silver Rs per gram on the same day, using figures from the AMC website. The hedge ratio depends entirely on this number.
3. Set `costs.*` from your broker's actual charges.

## 2. Every morning
```
python get_token.py      # opens the login URL, paste the request_token back
```

## 3. Backtest
```
python fetch_data.py --days 180 --interval 5minute   # -> data.csv
python backtest.py data.csv                          # -> summary, trades.csv, backtest_report.png
python backtest.py data.csv --sweep 0.06 0.08 0.10 0.12
```
- The `--sweep` command compares entry thresholds.
- `--etf-spread-bps` and `--fut-spread-bps` set the bid-ask spread to assume, since candles only have closes. Use ETF spreads you actually see on the order book.
- To try it without an account, run `python backtest.py --demo`. This uses fake data.

**What to look at:**
- `pct_bars_with_signal`: how often the trade exists at all.
- `annualised_return` vs a liquid fund / FD: the alternative use of the same money.
- Exit reasons: lots of `expiry` exits means the premium isn't converging early.
- `max_drawdown`: mark-to-market swings while holding, caused by ETF vs futures noise.

**Data limits:**
- Kite only lists contracts that are currently trading. `fetch_data.py` therefore covers the active SILVERM contracts back to when each was listed, which is a few months.
- For longer history, buy intraday data for expired contracts from a vendor and save it in the same CSV format: `ts, etf, fut_symbol, expiry, fut`.
- Never pair MCX daily closes (23:30) with ETF daily closes (15:30). Silver moves in between, and that gap would look like fake arbitrage.

## 4. Run the bot
```
python run.py --synthetic 400    # offline smoke test, fake market
python run.py                    # paper mode: real Kite quotes, simulated fills
```
Start it before 09:20 IST. It stops after 15:30. Run paper mode for a few weeks, compare `arb.log` against the backtest, then set `mode: live`.

## Things to know before going live
- **It isn't risk-free.** The ETF is valued from an international benchmark converted to a domestic price. MCX futures settle to MCX's own spot price. The two don't converge exactly, so some basis risk is left at exit. The ETF can also trade at a premium or discount to its NAV.
- **MCX silver futures are compulsory-delivery.** Brokers force-close or block positions before the tender period. Set `exit_days_before_expiry` to match your broker's cutoff.
- **Overlap hours:** the ETF trades only during NSE hours (until 15:30), but MCX runs until late evening. The bot trades only in the overlap.
- **Retail algo rules:** SEBI's framework for retail API algos and your broker's rules (static IP, order-rate limits, algo registration) apply. Check them with your broker before going live.
- **Tax:** ETF gains and futures gains are taxed differently (capital gains vs business income). Check with a CA.
- **Verify the contract specs** (lot sizes, quote units, tick sizes) on MCX before trading.
