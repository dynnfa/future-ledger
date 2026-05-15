# FutureLedger v0 05 Price Normalization Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Convert AKShare daily price frames into sorted, valid `PricePoint` instances for dividend-yield and one-year return calculations.

## Current State

- `src/future_ledger/normalize/prices.py` maps `日期` and `收盘` into `PricePoint`.
- The current function returns only a list of points and does not report invalid rows.
- Sorting by date exists.
- Missing, zero, negative, duplicate, and malformed prices are not specified.

## Inputs

- Six-digit stock code.
- Raw AKShare daily price pandas `DataFrame`.
- Source metadata with source name and requested date range.

## Outputs

- `list[PricePoint]` sorted by `date` ascending.
- `list[SourceErrorRow]` for skipped malformed rows and duplicate conflicts.

## Domain Contracts

- Raw AKShare column mapping:
  - `日期` -> `PricePoint.date`.
  - `收盘` -> `PricePoint.close`.
- Date parsing accepts `YYYY-MM-DD`, `YYYY/MM/DD`, and timestamp strings whose first 10 characters form a date.
- Close price parsing accepts numeric values and numeric strings.
- `PricePoint.close` must be greater than `Decimal("0")`.
- Duplicate dates with the same close keep one point and do not emit an error.
- Duplicate dates with different closes keep the later raw row and emit `SourceErrorRow(stage="price_normalize", message="duplicate price date")`.
- Returned points are always sorted ascending and contain no duplicate dates.

## Error Handling

- Missing `日期` skips the row and emits `SourceErrorRow(stage="price_normalize", message="missing price date")`.
- Invalid date skips the row and emits `SourceErrorRow(stage="price_normalize", message="invalid price date")`.
- Missing `收盘` skips the row and emits `SourceErrorRow(stage="price_normalize", message="missing close price")`.
- Zero or negative close skips the row and emits `SourceErrorRow(stage="price_normalize", message="non-positive close price")`.
- Invalid close decimal skips the row and emits `SourceErrorRow(stage="price_normalize", message="invalid close price")`.
- A frame with no valid price points returns an empty list plus row-level source errors.

## Data Quality Flags

- The normalizer emits source errors, not final report flags.
- Metrics convert missing usable prices into `missing_reference_price` or `missing_return_price`.

## Acceptance Criteria

- Fixture price frames normalize into sorted `PricePoint` rows.
- Invalid rows are skipped with deterministic source error messages.
- Duplicate conflicting dates do not create duplicate `PricePoint` rows.
- Downstream metrics can rely on sorted valid points and avoid repeated full-list sorting.

## Tests

- `tests/normalize/test_prices.py::test_normalize_price_history_sorts_by_date` remains the sorting fixture test.
- `tests/normalize/test_prices.py::test_normalize_price_history_skips_non_positive_close` expects one source error and no point for zero or negative close.
- `tests/normalize/test_prices.py::test_normalize_price_history_reports_invalid_date_and_close` expects two source errors.
- `tests/normalize/test_prices.py::test_normalize_price_history_deduplicates_same_close` expects one point and no error.
- `tests/normalize/test_prices.py::test_normalize_price_history_keeps_later_duplicate_conflict` expects the later close and source error `duplicate price date`.
- Run `uv run pytest tests/normalize/test_prices.py -q`.

## Out of Scope

- Fetching raw price history.
- Adjusted-price selection beyond the AKShare v0 daily close source.
- Filling non-trading days.
- Return calculation.

## Dependencies

- Depends on `future_ledger.domain.PricePoint` and `SourceErrorRow`.
- Consumes output from source fetching.
- Feeds dividend-yield metrics, return metrics, and report assembly.
