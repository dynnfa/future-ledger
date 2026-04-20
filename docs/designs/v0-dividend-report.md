# FutureLedger v0 Dividend Report Design

Status: DRAFT
Generated: 2026-04-20

## Product Boundary

FutureLedger v0 is a local Python CLI for A-share dividend research.

It is not a portfolio manager, not an investment-advice product, and not a bank
deposit-rate scraper. Bank fixed-deposit rate collection is deferred to v2 in
`TODOS.md` because public bank pages change frequently and add a separate parser
failure surface before the dividend pipeline is proven.

## v0 Command

```bash
future-ledger dividends scan \
  --years 5 \
  --as-of 2026-04-20 \
  --universe all-a-excluding-st \
  --output reports/dividend_rank.xlsx
```

Defaults:
- `--years`: `5`
- `--as-of`: current local date
- `--universe`: `all-a-excluding-st`
- `--output`: `reports/dividend_rank.xlsx`

Universe rule:
- Exclude ST stocks by default. These are not useful for the long-hold dividend
  research workflow v0 is optimizing for.
- Include stocks with fewer than 5 report years, but mark them with
  `has_missing_years_5y` and `dividend_year_count_5y`. Missing history is a
  data-quality signal, not a reason to silently drop the row.

## Scope

In scope:
- Python CLI.
- A-share dividend report using AKShare.
- One wide row per stock, sorted by latest annual dividend yield.
- Last 5 report years expanded into same-row fields.
- Long-form annual dividend table.
- Raw source cache for reproducibility.
- Source error sheet.
- Metadata sheet with run parameters, AKShare version, source priority, and
  non-investment-advice disclaimer.
- Trailing one-year annualized return calculation as of a selected date.

Not in scope:
- Bank fixed-deposit rate scraping.
- Web dashboard.
- Investment recommendations.
- Portfolio allocation.
- Multi-source reconciliation beyond the primary v0 source.

## Source Priority

Primary v0 source:
- `akshare.stock_fhps_detail_em(symbol)`

This Eastmoney-backed AKShare interface is the default because it exposes report
period, cash dividend ratio, dividend yield, EPS, net assets per share, profit
growth, registration date, ex-dividend date, and plan status.

Deferred sources:
- Sina dividend detail.
- CNInfo dividend history.
- Tonghuashun dividend detail.

Do not mix sources silently. If future versions add fallback sources, every row
must expose `source_priority_used` and conflict flags.

## Dividend Yield Rule

Dividend yield must be reproducible and explicit.

v0 rule:

```text
dividend_yield_pct =
  cash_dividend_per_share / reference_close_price * 100
```

Reference price:
1. Use the closing price on the ex-dividend date.
2. If the ex-dividend date has no trading price, use the nearest previous
   trading day's closing price.
3. If no usable price is found, leave the calculated yield empty and add a
   `missing_reference_price` data-quality flag.

Required lineage fields:
- `reference_price`
- `reference_price_date`
- `reference_price_rule`
- `reference_price_fallback_used`
- `dividend_yield_source`: `calculated_ex_dividend_close`

Provider dividend-yield fields may be included as raw reference fields, but v0
ranking should use the locally calculated yield above so the calculation rule is
consistent across rows.

## Trailing One-Year Annualized Return

FutureLedger v0 should include a trailing one-year annualized return metric.

User input:
- `--as-of YYYY-MM-DD`
- Defaults to the current local date.

Calculation window:
- `window_end = as_of`
- `window_start = as_of - 1 year`

Return rule:

```text
total_return_1y_pct =
  (end_close_price - start_close_price + cash_dividends_in_window)
  / start_close_price * 100

annualized_return_1y_pct = total_return_1y_pct
```

Because the window is exactly one year, the annualized return equals the
one-year total return. Keep both columns anyway because future versions may
support arbitrary windows.

Price rules:
1. `start_close_price`: closing price on `window_start`, or nearest later
   trading day's close if `window_start` is not a trading day.
2. `end_close_price`: closing price on `window_end`, or nearest previous
   trading day's close if `window_end` is not a trading day.
3. If either price is missing, leave return metrics empty and add
   `missing_return_price`.

Dividend inclusion rule:
- Include cash dividends whose ex-dividend date is within
  `[window_start, window_end]`.
- Use cash dividend per share, not per 10 shares.
- Missing dividend data is not zero. If the source cannot determine whether a
  dividend occurred in the window, add `uncertain_dividend_window`.

Required output fields:
- `as_of_date`
- `return_window_start`
- `return_window_end`
- `start_close_price`
- `start_price_date`
- `end_close_price`
- `end_price_date`
- `cash_dividends_1y`
- `total_return_1y_pct`
- `annualized_return_1y_pct`
- `return_data_quality_flags`

## Report Shape

Workbook sheets:
1. `dividend_rank`: wide table, one row per stock.
2. `dividend_long`: one row per stock per report year.
3. `price_points`: reference prices used for dividend yield and one-year return.
4. `source_errors`: failed fetches, parse errors, missing fields, and retry status.
5. `metadata`: run parameters, source versions, generated timestamp, and disclaimer.

Core `dividend_rank` columns:
- `rank_latest_yield`
- `stock_code`
- `stock_name`
- `market`
- `latest_report_year`
- `latest_cash_dividend_per_10_shares`
- `latest_cash_dividend_per_share`
- `reference_price`
- `reference_price_date`
- `latest_dividend_yield_pct`
- `dividend_yield_source`
- `dividend_year_count_5y`
- `continuous_dividend_5y`
- `avg_dividend_yield_pct_5y`
- `min_dividend_yield_pct_5y`
- `max_dividend_yield_pct_5y`
- `as_of_date`
- `cash_dividends_1y`
- `total_return_1y_pct`
- `annualized_return_1y_pct`
- `has_missing_years_5y`
- `data_quality_flags`
- `source_priority_used`
- `fetched_at`

Annual expansion fields for each report year:
- `YYYY_report_period`
- `YYYY_cash_dividend_per_10_shares`
- `YYYY_cash_dividend_per_share`
- `YYYY_reference_price`
- `YYYY_reference_price_date`
- `YYYY_dividend_yield_pct`
- `YYYY_registration_date`
- `YYYY_ex_dividend_date`
- `YYYY_plan_status`
- `YYYY_eps`
- `YYYY_net_asset_per_share`
- `YYYY_profit_growth_yoy_pct`
- `YYYY_source`

## Failure Modes

| Codepath | Failure Mode | Rescued? | Test? | User Sees? | Logged? |
|---|---|---:|---:|---|---:|
| dividend source fetch | network timeout | yes | yes | row in `source_errors` | yes |
| dividend source fetch | empty DataFrame | yes | yes | data-quality flag | yes |
| dividend normalization | missing report period | yes | yes | row in `source_errors` | yes |
| dividend normalization | duplicate report period | yes | yes | conflict flag | yes |
| yield calculation | missing ex-dividend date | yes | yes | empty yield + flag | yes |
| yield calculation | missing reference price | yes | yes | empty yield + flag | yes |
| return calculation | missing start/end price | yes | yes | empty return + flag | yes |
| return calculation | uncertain dividend window | yes | yes | empty or flagged return | yes |
| Excel writer | output path unwritable | no | yes | CLI error | yes |

## Test Plan

Required test groups:
- Fixture tests for dividend source normalization.
- Fixture tests for price lookup fallback rules.
- Unit tests for dividend-yield calculation.
- Unit tests for trailing one-year return calculation.
- Excel shape tests verifying required sheets and columns.
- CLI tests for default arguments and custom `--as-of`.
- Optional live AKShare smoke test, excluded from default CI.

Do not make default CI depend on live financial endpoints.

## Compliance

README and workbook metadata must state:

```text
FutureLedger is for financial data research only. It does not provide investment
advice, buy/sell recommendations, or portfolio allocation guidance.
```

## Decisions

1. Default universe is `all-a-excluding-st`.
2. ST stocks are excluded because they do not fit the long-hold dividend
   research use case.
3. Stocks with fewer than 5 report years remain in the report with explicit
   missing-year flags.
