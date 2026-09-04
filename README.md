# NelsonCorp Daily Performance Dashboard

Live daily returns from Finnhub, YTD and weights from YCharts via a daily
cloud routine. Fully automated, no API key, no local machine.

```
6am CT, Anthropic cloud                  every 60s, in the browser
┌────────────────────────────┐          ┌──────────────────────────┐
│ Claude Code routine        │          │ index.html               │
│  YCharts MCP connector     │          │  data.json  → weights,   │
│  → flatten sleeves         │  commit  │              YTD as-of   │
│  → data.json               │ ───────► │  Finnhub    → today's    │
│  → validate_data.py gate   │          │              move        │
│  → git push main           │          └──────────────────────────┘
└────────────────────────────┘
```

**Setup:** `SETUP_ROUTINE.md`. **What the routine does:** `ROUTINE_PROMPT.md`.

## What's shown

**Daily** is live: Finnhub prices × flattened target weights, every minute.

**YTD** is YCharts' prior-close figure compounded with today's live move —
but only when today's move isn't already inside the base. The label says
which state it's in:

| Label | When | What it is |
|---|---|---|
| YTD *live* | market open | base × (1 + today's move) |
| YTD *thru today's close* | after 4pm, before the 6am refresh | base × (1 + today's close move) |
| YTD *thru Sep 3* | pre-open, weekends | base alone — today's move is already in it |
| YTD *base Sep 3 ⚠* | routine missed a day | understated; banner explains |

The guard against double-counting: between the 6am refresh and the 9:30
open, the base already includes yesterday but Finnhub still reports
yesterday's move. The page shows the base alone in that window.

The compounding only ever covers one session. If the routine misses a day,
the missing session can't be recovered from live prices, so the page says
so rather than showing a plausible wrong number.

## Why this shape

YCharts model calculations lag one trading day and catch up overnight. A
6am run gets yesterday's close reliably. The routine runs on Anthropic's
cloud using your existing YCharts connector, so the credential problem that
blocked a plain cron job doesn't apply.

## Six benchmarks, 13 strategy portfolios, 20 sleeve portfolios

S&P 500 / SPYM · Dow / DIA · Nasdaq 100 / QQQ · U.S. Bonds / AGG ·
U.S. Dollar / UUP · Commodities / PDBC

Strategy portfolios are grouped Core → Absolute Return → Tactical → Tax Sensitive → IA3; sleeves are grouped Standard (Equity, Macro, Alternatives & Bonds) then Tax Sensitive (Equity, Fixed Income). Every display name, group and YCharts ID is in `ROUTINE_PROMPT.md` and `validate_data.py` — those two lists must agree. IDs were confirmed by matching YCharts holdings against the old workbook, not by name.

## Adding or removing a model

Edit the table in `ROUTINE_PROMPT.md` (and paste it into the routine's Instructions) **and**
`EXPECTED_STRATEGIES` / `EXPECTED_SLEEVES` in `validate_data.py`. Both, or the validator rejects the
next run. Ask me for the ID if you don't have it — I'll confirm by holdings.

## Honest caveats

- **Target weights, not drifted.** Intraday model returns are directional.
- **Missing quotes show.** A ticker Finnhub can't price appears as reduced
  coverage on the card, not silently as zero.
- **Finnhub key lives in `config.js`**, not `index.html`, so page updates
  never overwrite it. It's still public and gets revoked now and then; the
  page names the problem when it happens. Fix: edit `config.js`, one line.
- **Rate limit is 60 calls/min.** Each open tab uses ~14/min during market
  hours. Background tabs pause polling, and a rate-limit hit keeps the last
  prices and retries after 2.5 minutes rather than going blank.
- **Routines are research preview.**
