# FutureLedger v0 06 Metrics Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Calculate dividend-yield and trailing one-year return metrics from normalized dividends and prices.

## Current State

- `src/future_ledger/metrics/dividend_yield.py` resolves a reference price on or before the ex-dividend date and calculates unquantized percentage yield.
- `src/future_ledger/metrics/returns.py` calculates trailing one-year return but can fail for February 29 because it constructs `date(as_of.year - 1, as_of.month, as_of.day)`.
- Price lookup functions sort eligible prices on every lookup.
- Current reference price rule string is `ex_dividend_previous_close`, which does not fully describe exact-date eligibility.

## Inputs

- `DividendRecord` values with per-share cash dividends and ex-dividend dates.
- Sorted `PricePoint` values for the same stock.
- `as_of: date`.
- Requested lookback years from `RunConfig.years`.

## Outputs

- `ReferencePriceResult` with `reference_price`, `reference_price_date`, `reference_price_rule`, and `reference_price_fallback_used`.
- `DividendYieldResult` with `dividend_yield_pct` and `data_quality_flags`.
- `ReturnCalculationResult` with one-year start/end prices, dates, cash dividends, total return, annualized return, and return flags.

## Domain Contracts

- Dividend yield formula is `cash_dividend_per_share / reference_close_price * 100`.
- Reference price selection uses the closing price on the ex-dividend date when available.
- If the ex-dividend date has no trading price, reference price falls back to the nearest previous trading day's close.
- If no previous or exact price exists, yield is `None` and flag `missing_reference_price` is emitted.
- `reference_price_rule` is `ex_dividend_close_or_previous_trading_day`.
- `dividend_yield_source` used by report assembly is `calculated_ex_dividend_close`.
- Dividend yield is quantized to `Decimal("0.01")`.
- One-year window end is `as_of`.
- One-year window start is `as_of` with the year decremented by one; for February 29, use February 28 in the previous year.
- Start price uses the first trading day on or after `window_start`.
- End price uses the last trading day on or before `window_end`.
- Dividends in the return window include cash dividends whose ex-dividend date is in `[window_start, window_end]`.
- Return formula is `(end_close_price - start_close_price + cash_dividends_in_window) / start_close_price * 100`.
- `total_return_1y_pct` and `annualized_return_1y_pct` are equal for v0 and quantized to `Decimal("0.01")`.
- Price lookup receives sorted valid points from price normalization and must not sort the full list per lookup.

## Error Handling

- Missing `cash_dividend_per_share` yields `None` plus `missing_cash_dividend`.
- Missing ex-dividend date yields `None` plus `missing_ex_dividend_date`.
- Missing reference price yields `None` plus `missing_reference_price`.
- Missing start or end return price yields empty return metrics plus `missing_return_price`.
- Missing or uncertain dividend data for the one-year window yields `uncertain_dividend_window`.
- Zero or negative start price is impossible after price normalization; if encountered, return metrics are empty plus `invalid_return_start_price`.

## Data Quality Flags

- `missing_cash_dividend`: dividend record lacks per-share cash dividend.
- `missing_ex_dividend_date`: dividend record lacks ex-dividend date.
- `missing_reference_price`: no usable reference close exists.
- `missing_return_price`: no usable start or end close exists.
- `uncertain_dividend_window`: dividend source coverage cannot confirm dividend inclusion for the one-year window.
- `invalid_return_start_price`: start close is zero or negative despite normalization guarantees.

## Acceptance Criteria

- Exact ex-dividend date close is eligible for dividend yield.
- Previous trading-day fallback is used only when exact ex-dividend close is missing.
- Dividend yield precision is two decimal places.
- February 29 `as_of` does not crash one-year return calculation.
- Price lookup uses pre-sorted points and linear or binary search helpers instead of sorting on every lookup.
- Missing inputs produce stable flags, not exceptions.

## Tests

- `tests/metrics/test_dividend_yield.py::test_resolve_reference_price_uses_exact_ex_dividend_close_without_fallback` remains the exact-date test.
- `tests/metrics/test_dividend_yield.py::test_calculate_dividend_yield_quantizes_to_two_decimals` expects `Decimal("4.10")`.
- `tests/metrics/test_dividend_yield.py::test_calculate_dividend_yield_flags_missing_reference_price` expects flag `missing_reference_price`.
- `tests/metrics/test_returns.py::test_calculate_trailing_one_year_return_handles_february_29` uses `as_of=date(2024, 2, 29)` and expects `return_window_start=date(2023, 2, 28)`.
- `tests/metrics/test_returns.py::test_calculate_trailing_one_year_return_flags_uncertain_dividend_window` expects `uncertain_dividend_window`.
- `tests/metrics/test_returns.py::test_calculate_trailing_one_year_return_uses_window_price_fallbacks` remains the fallback test.
- Run `uv run pytest tests/metrics/test_dividend_yield.py tests/metrics/test_returns.py -q`.

## Out of Scope

- Multi-year annualized return windows.
- Provider dividend-yield reconciliation.
- Price adjustment method selection.
- Portfolio-level total return.

## Dependencies

- Depends on `future_ledger.domain.DividendRecord` and `PricePoint`.
- Consumes normalized outputs from dividend and price normalization.
- Feeds report assembly.
