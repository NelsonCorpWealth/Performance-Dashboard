# NelsonCorp Daily Performance Dashboard

Live daily returns for the firm's strategy and sleeve portfolios, with YTD and
look-through holdings refreshed from YCharts every morning. Runs on GitHub Pages;
nothing runs on a local machine.

**Live:** https://nelsoncorpwealth.github.io/Performance-Dashboard/

```
 6:00am CT, weekdays                            in the browser
 ┌──────────────────────────────┐              ┌──────────────────────────────────────────┐
 │ Claude Code cloud routine    │              │ index.html                               │
 │  • YCharts MCP connector     │  data.json   │  data.json  → portfolios, groups, YTD,   │
 │  • 33 portfolios, sleeves    │ ───────────► │               look-through ETF weights   │
 │    flattened to ETF weights  │  (commit +   │  Finnhub    → live quote for every ETF   │
 │  • validate_data.py gate     │   promote)   │               every 2 min                │
 │  • push → claude/* branch    │              │  Twelve Data→ 5-min intraday bars for    │
 └──────────────┬───────────────┘              │               the six benchmark charts   │
                │ GitHub Action re-validates,  └──────────────────────────────────────────┘
                ▼ fast-forwards to main
```

## What's on the page

**Market Benchmarks** — six ETFs (S&P 500 / SPYM, Dow / DIA, Nasdaq 100 / QQQ,
U.S. Bonds / AGG, U.S. Dollar / UUP, Commodities / PDBC). Each card: today's
move, live YTD, and an intraday price chart on a fixed 9:30–4:00 ET axis that
fills in through the session. Dashed line is the prior close.

**Today's Winners / Losers** — top and bottom five of the ETFs currently held
across the portfolios, by today's move. Floats in the free margin to the right
of the content on wide screens; drops below the benchmarks on narrow ones.

**Strategy Portfolios** — 13, in five label-rail rows: Core, Absolute Return,
Tactical, Tax Sensitive, IA3. Each card: daily, vs S&P 500, live YTD, YTD vs
S&P 500. Holdings detail below, defaulting to Moderate.

**Sleeve Portfolios** — 20, in five rows: Standard Equity, Standard Macro,
Standard Alternatives & Bonds, Tax Sensitive Equity, Tax Sensitive Fixed
Income. Daily and YTD. Holdings detail below, defaulting to Tactical Stock L/S.

## How the numbers work

**Daily** = Σ(look-through ETF weight × that ETF's move from prior close), from
live Finnhub quotes. Target weights, not drifted actuals, so intraday figures
are directional. A ticker Finnhub can't quote shows as reduced coverage on the
card, never as a silent zero.

**YTD** = YCharts' own figure for each portfolio as of the prior close, compounded
with today's live move: `(1 + YTD) × (1 + daily) − 1`. The label states which
case applies:

| Label | When |
|---|---|
| YTD live | market open |
| YTD thru today's close | after 4pm, before the next morning's refresh |
| YTD thru *date* | pre-open and weekends — the base already includes the last session |
| YTD base *date* ⚠ | routine missed a day; figure is understated and a banner says so |

Only one session is ever compounded. Weekends and NYSE holidays are computed
from the exchange rules, so a Monday holiday doesn't trip a false stale warning.

**Intraday charts** are Twelve Data 5-minute bars for the six benchmarks. The
page requests all six in one call, every 5 minutes during market hours, at
most once a minute no matter how many reloads — ~470 of the 800 free daily
credits. If Twelve Data is unavailable the card falls back to a line the page
recorded from its own polls, labeled "partial."

## The daily routine

A Claude Code cloud routine ("Dashboard data refresh", claude.ai/code/routines)
runs weekdays at 6:00am CT. It pulls points and holdings for all 33 portfolios
from YCharts, recursively flattens nested sleeves to ETF weights, writes
`data.json`, runs `validate_data.py`, and commits only if values changed. The
prompt is `ROUTINE_PROMPT.md` — the routine holds its own copy, so edits must
be pasted into its Instructions.

The platform routes its push to a `claude/*` branch. `.github/workflows/
promote-data.yml` re-runs the validator on GitHub's side and fast-forwards
`main` only if `data.json` is the sole changed file. Two independent gates.

YCharts model figures lag a trading day and catch up overnight, so the 6am run
reliably gets the prior close. Changes made in YCharts *after* 6am appear the
next morning — or sooner with **Run now** on the routine page (~4 minutes).

## Files

| File | Role |
|---|---|
| `index.html` | The page. No secrets inside. |
| `config.js` | `FINNHUB_KEY` and `TWELVEDATA_KEY`. Separate so page updates never overwrite them. |
| `data.json` | Written by the routine. Don't edit by hand. |
| `validate_data.py` | The gate: exact portfolio names, groups, order and IDs; weights sum to 100%; percent-vs-decimal leaks; stale as-of. |
| `ROUTINE_PROMPT.md` | What the routine does, including the 33 portfolio IDs. |
| `.github/workflows/promote-data.yml` | Promotes the routine's branch to `main` after re-validating. |

## Adding or removing a portfolio

Edit the table in `ROUTINE_PROMPT.md` **and** `EXPECTED_STRATEGIES` /
`EXPECTED_SLEEVES` in `validate_data.py` (both, or the validator rejects the
next run), then paste the new prompt into the routine's Instructions. Display
order on the page follows the table order. IDs should be confirmed by matching
holdings in YCharts, not by name — several portfolios have near-duplicate names.

## Known limits

- **Both API keys are public.** They sit in `config.js` in this repo. Free
  tiers, disposable, but each gets revoked now and then. The page names which
  one failed; the fix is one line in `config.js`.
- **Finnhub: 60 calls/min.** Each visible tab uses ~20/min during market hours.
  Background tabs pause. A rate-limit hit keeps the last prices and retries.
- **Twelve Data: 8 credits/min, 800/day.** Thin ETFs (UUP, PDBC) report fewer
  bars because they trade less often.
- **Intraday charts need Finnhub's prior close** for the reference line. If
  Finnhub is limited at load, the charts show "intraday…" until it recovers.
- **Routines are in research preview.**
