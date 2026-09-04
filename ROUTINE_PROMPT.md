# Daily dashboard data refresh

You are updating `data.json` in this repository from YCharts. The file feeds a live dashboard, so correctness matters more than speed. Follow every step. If anything fails validation, do not commit — report and stop.

## Strategy portfolios (fixed — do not look these up or reinterpret)

| Display name | Group | YCharts ID |
|---|---|---:|
| Conservative | Core | 597220 |
| Moderate | Core | 552644 |
| Aggressive | Core | 597223 |
| Absolute Return Conservative | Absolute Return | 604837 |
| Absolute Return Moderate | Absolute Return | 555767 |
| Absolute Return Moderate-Aggressive | Absolute Return | 604832 |
| All Tactical | Tactical | 1297251 |
| Macro | Tactical | 1729042 |
| Tax Conservative | Tax Sensitive | 1146887 |
| Tax Moderate | Tax Sensitive | 1146880 |
| Tax Aggressive | Tax Sensitive | 1146891 |
| IA3 High Income | IA3 | 1589463 |
| IA3 Cash Management | IA3 | 1589508 |

## Sleeve portfolios (fixed)

| Display name | Group | YCharts ID |
|---|---|---:|
| Core Stock | Standard · Equity | 548985 |
| Tactical Stock L/S | Standard · Equity | 1141466 |
| Tactical Stock L/S (S&P) | Standard · Equity | 1470892 |
| Regional Stock L/S | Standard · Equity | 1141467 |
| Defined Risk | Standard · Equity | 1145523 |
| Big Picture L/S (SPHB/USMV) | Standard · Macro | 1184181 |
| Bond Duration L/S (XLK/XLE) | Standard · Macro | 1271763 |
| Dollar L/S (AMLP/GDX) | Standard · Macro | 1195046 |
| Economic Regime | Standard · Macro | 1962097 |
| Real Estate | Standard · Alternatives & Bonds | 1145687 |
| Commodity | Standard · Alternatives & Bonds | 1146127 |
| Dollar | Standard · Alternatives & Bonds | 1146153 |
| Core Bond 1 | Standard · Alternatives & Bonds | 548980 |
| Tax Core Stock | Tax Sensitive · Equity | 1146835 |
| Tax Tactical Stock | Tax Sensitive · Equity | 1146853 |
| Tax Tactical Stock L/S | Tax Sensitive · Equity | 1146860 |
| Tax Regional Stock | Tax Sensitive · Equity | 1146845 |
| Tax Var Rate Preferred | Tax Sensitive · Fixed Income | 1534983 |
| Tax Core Bond BOXX | Tax Sensitive · Fixed Income | 1277723 |
| Tax Int-Term Muni 1 | Tax Sensitive · Fixed Income | 1277725 |

Benchmarks (name / ticker): S&P 500 / SPYM · Dow / DIA · Nasdaq 100 / QQQ · U.S. Bonds / AGG · U.S. Dollar / UUP · Commodities / PDBC

## Steps

1. Points. Call get_model_portfolio_points with ALL 33 IDs above (strategies + sleeves) and calc_names="ytd_total_return,roc_1". Record the date on the returned points — that is the as-of date. Values are in PERCENT; divide by 100.

2. Benchmark YTD. Call get_fund_data with the six benchmark tickers. Take ytd_total_return from each. Percent; divide by 100.

3. Holdings, flattened. Call get_model_portfolio_holdings for all 33 IDs, weight_type="target" (batches of 10). Strategy portfolios hold SLEEVES — nested portfolios whose security_id starts with "P:" — up to three levels deep. Some sleeves also nest. For every P: holding, fetch that portfolio's holdings and multiply weights down the path until only real tickers remain. Cache: many sleeves are shared.
   - Drop any holding with weight 0.000000 (inactive universe positions).
   - Map $:CASH, M:FZFXX, M:FDRXX to ticker CASH.
   - Weights are percent; divide by 100.
   - Each portfolio must sum to 1.000 ± 0.005. If one doesn't, a sleeve failed to expand — stop and report which.

4. Write data.json at the repo root with this exact shape (two lists, same item schema):
{
  "ytd_as_of": "YYYY-MM-DD",
  "generated_at": "<ISO 8601 with offset>",
  "source": "YCharts (MCP, cloud routine)",
  "benchmarks": [ { "name": "S&P 500", "ticker": "SPYM", "dashName": "S&P 500", "ytd": 0.1287 } ],
  "strategies": [ { "name": "Conservative", "group": "Core", "portfolio_id": 597220, "ytd": 0.0452, "prior_day": 0.0063, "holdings": [ { "ticker": "IEF", "weight": 0.1567 } ] } ],
  "sleeves":    [ { "name": "Core Stock", "group": "Standard · Equity", "portfolio_id": 548985, "ytd": 0.1483, "prior_day": 0.0107, "holdings": [ { "ticker": "VTI", "weight": 1.0 } ] } ]
}
Use the display names and groups EXACTLY as in the tables above, in that order. Sort holdings by weight descending. Round weights to 6 decimals.

5. Validate. Run:  git show HEAD:data.json > /tmp/prev.json && python validate_data.py data.json --prev /tmp/prev.json
Exit code 0 means safe. Anything else: DO NOT COMMIT. Paste the validator output in your summary and stop.

6. Commit only if data changed. If every ytd, prior_day, benchmark ytd and holding weight is identical to HEAD (ignore generated_at, key order, source), say so and stop. Otherwise:
   git add data.json && git commit -m "Daily data refresh (as of <ytd_as_of>)" && git push origin main
   (If the push is redirected to a claude/ branch, that is expected — a GitHub Action promotes it to main after re-validating.)

7. Summary. Lead with the validator's CHANGED lines — which tickers entered or left a portfolio, which weights moved. Then the 13 strategy YTDs and the as-of date. If holdings didn't change, say so in one line.

## Do not
- Change index.html, config.js, validate_data.py, or any file other than data.json
- Guess a portfolio ID or resolve portfolios by name
- Commit if validation fails, even if the failure seems minor
- Retry a failed push more than once
