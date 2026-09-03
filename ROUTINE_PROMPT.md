# Daily dashboard data refresh

You are updating `data.json` in this repository from YCharts. The file feeds
a live dashboard, so correctness matters more than speed. Follow every step.
If anything fails validation, do not commit — report and stop.

## Portfolios (fixed — do not look these up or reinterpret)

| Display name     | YCharts ID |
|------------------|-----------:|
| Moderate         | 552644     |
| Abs Rtn Moderate | 555767     |
| Tax Moderate     | 1146880    |
| Aggressive       | 597223     |
| All Tactical     | 1297251    |
| Macro            | 1729042    |

Benchmarks (name / ticker): S&P 500 / SPYM · Dow / DIA · Nasdaq 100 / QQQ ·
U.S. Bonds / AGG · U.S. Dollar / UUP · Commodities / PDBC

## Steps

**1. Model YTD and prior-day return.** Call `get_model_portfolio_points` with
all six IDs and `calc_names="ytd_total_return,roc_1"`. Record the date on the
returned points — that is the as-of date. Values are in **percent**; divide
by 100.

**2. Benchmark YTD.** Call `get_fund_data` with the six benchmark tickers.
Take `ytd_total_return` from each. Percent; divide by 100.

**3. Holdings, flattened.** Call `get_model_portfolio_holdings` with the six
IDs, `weight_type="target"`. These models hold **sleeves** — nested
portfolios whose `security_id` starts with `P:` — up to three levels deep.
For every `P:` holding, fetch that portfolio's holdings and multiply weights
down the path until only real tickers remain. Cache: many sleeves are shared.

  - Drop any holding with weight `0.000000` (inactive universe positions).
  - Map `$:CASH`, `M:FZFXX`, `M:FDRXX` → ticker `CASH`.
  - Weights are percent; divide by 100.
  - Each model must sum to 1.000 ± 0.005. If one doesn't, a sleeve failed to
    expand — stop and report which.

**4. Write `data.json`** at the repo root, exactly this shape:

```json
{
  "ytd_as_of": "YYYY-MM-DD",
  "generated_at": "<ISO 8601 with offset>",
  "source": "YCharts (MCP, cloud routine)",
  "benchmarks": [
    { "name": "S&P 500", "ticker": "SPYM", "dashName": "S&P 500", "ytd": 0.1287 }
  ],
  "models": [
    { "name": "Moderate", "group": "NelsonCorp", "portfolio_id": 552644,
      "ytd": 0.0934, "prior_day": 0.0055,
      "holdings": [ { "ticker": "VTI", "weight": 0.1575 } ] }
  ]
}
```

Order benchmarks and models exactly as listed above. Sort holdings by
weight descending. Round weights to 6 decimals.

**5. Validate.** Run:

```
python validate_data.py data.json --prev <previous data.json from git>
```

Get the previous file with `git show HEAD:data.json > /tmp/prev.json`. Exit
code 0 means safe. Anything else: **do not commit**. Paste the validator
output in your summary and stop.

**6. Commit only if changed.** If `data.json` is byte-identical to HEAD,
there is nothing to do — say so and stop. Otherwise:

```
git add data.json
git commit -m "Daily data refresh (as of <ytd_as_of>)"
git push origin main
```

**7. Summary.** Lead with the validator's `CHANGED` lines — which tickers
entered or left a model, which weights moved. Then the six model YTDs and
the as-of date. If nothing changed in holdings, say so in one line.

## Do not

- Change `index.html`, `validate_data.py`, or any file other than `data.json`
- Guess a portfolio ID or resolve models by name
- Commit if validation fails, even if the failure seems minor
- Retry a failed push more than once
