# Python Code Review Report

**Date**: 2026-04-28
**Branch**: main
**Files reviewed**: 5 (1 modified, 4 new)
**Static analysis**: ruff passed, mypy passed, pytest 10/10 passed

---

## Files Reviewed

| File | Status | Description |
|------|--------|-------------|
| `src/future_ledger/domain.py` | Modified | Added `stock_name`, `market`, `report_period`, `cash_dividend_per_10_shares`, `eps`, `net_asset_per_share`, `profit_growth_yoy_pct`, `source` fields to `DividendRecord` |
| `src/future_ledger/metrics/dividend_yield.py` | New | Dividend yield calculation using reference price |
| `src/future_ledger/metrics/returns.py` | New | Trailing 1-year total return calculation |
| `src/future_ledger/normalize/dividends.py` | New | AKShare DataFrame -> `DividendRecord` normalization |
| `src/future_ledger/normalize/prices.py` | New | AKShare DataFrame -> `PricePoint` normalization |

---

## [HIGH] Leap-year crash in `date()` constructor

**File**: `src/future_ledger/metrics/returns.py:31`

`date(as_of.year - 1, as_of.month, as_of.day)` crashes on Feb 29 when the prior year is not a leap year.

```python
# Current
window_start = date(as_of.year - 1, as_of.month, as_of.day)

# Fix
try:
    window_start = date(as_of.year - 1, as_of.month, as_of.day)
except ValueError:
    window_start = date(as_of.year - 1, 2, 28)
```

---

## [HIGH] O(n log n) sort for date lookups

**File**: `src/future_ledger/metrics/returns.py:80-97`

`_first_on_or_after` and `_last_on_or_before` sort the full filtered list every call. Since `normalize_price_history` returns sorted data, use `min()`/`max()` with `default=None` for O(n):

```python
def _first_on_or_after(points: list[PricePoint], target: date) -> PricePoint | None:
    return min((p for p in points if p.date >= target), key=lambda p: p.date, default=None)

def _last_on_or_before(points: list[PricePoint], target: date) -> PricePoint | None:
    return max((p for p in points if p.date <= target), key=lambda p: p.date, default=None)
```

---

## [MEDIUM] Reference price includes ex-dividend day

**File**: `src/future_ledger/metrics/dividend_yield.py:27`

Filter uses `point.date <= ex_dividend_date`, which includes the ex-dividend close (already dividend-adjusted), understating yield. Consider `<` instead of `<=`.

---

## [MEDIUM] Dedup is "first-seen wins", may keep stale entry

**File**: `src/future_ledger/normalize/dividends.py:35-44`

When AKShare returns a provisional entry ("董事会预案") before a finalized one ("实施"), the stale provisional entry wins. Prefer entries with `plan_status == "实施"`.

---

## [MEDIUM] `_market_for_code` raises `ValueError` on unknown prefix

**File**: `src/future_ledger/normalize/dividends.py:77`

One unexpected code prefix halts the entire batch pipeline. Consider returning a fallback or converting to `SourceErrorRow`.

---

## [MEDIUM] Mutable `dict` field inside frozen dataclass

**File**: `src/future_ledger/domain.py:115`

`annual_fields: dict[str, object]` in `DividendRankRow` is mutable despite the frozen dataclass. Reassignment is blocked but contents can be mutated. Consider `Mapping[str, object]`.

---

## [MEDIUM] `calculate_dividend_yield` lacks `.quantize()`

**File**: `src/future_ledger/metrics/dividend_yield.py:51`

Unlike `returns.py`, the yield result has inconsistent Decimal precision. Add `.quantize(Decimal("0.01"))`.

---

## [MEDIUM] `_decimal_or_none` silently strips `%` suffix

**File**: `src/future_ledger/normalize/dividends.py:86`

Works for percentage columns, but if a non-percentage field ever contains `%`, the value is silently off by 100x. Also does not handle parenthesized negatives `"(5.30)"`.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 6 |
| LOW | 2 |

**Verdict: WARNING** — no blockers. The two HIGH items (leap-year crash, inefficient sort) are worth fixing in the next iteration.
