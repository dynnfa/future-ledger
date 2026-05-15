# FutureLedger v0 04 Dividend Normalization Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Convert AKShare dividend-detail frames into normalized `DividendRecord` instances and normalization errors.

## Current State

- `src/future_ledger/normalize/dividends.py` maps AKShare columns into `DividendRecord`.
- Duplicate report years currently use first-seen wins.
- The normalizer infers market from stock code and can raise `ValueError` for unknown prefixes.
- Percent and non-percent numeric fields use the same parser.

## Inputs

- `StockIdentity` with `code`, `name`, and `market`.
- Raw AKShare dividend-detail pandas `DataFrame`.
- Source metadata containing source name and fetched timestamp.

## Outputs

- `list[DividendRecord]` sorted by `report_year` descending.
- `list[SourceErrorRow]` for skipped rows, duplicate rows, malformed fields, and stock-level normalization failures.

## Domain Contracts

- Raw AKShare column mapping:
  - `报告期` -> `DividendRecord.report_period` and derived `report_year`.
  - `每10股派息` -> `cash_dividend_per_10_shares`.
  - `除权除息日` -> `ex_dividend_date`.
  - `股权登记日` -> `registration_date`.
  - `方案进度` -> `plan_status`.
  - `每股收益` -> `eps`.
  - `每股净资产` -> `net_asset_per_share`.
  - `净利润同比增长` -> `profit_growth_yoy_pct`.
  - `现金分红-股息率` -> `provider_yield_pct`.
- `cash_dividend_per_share` equals `cash_dividend_per_10_shares / Decimal("10")`.
- Percent fields keep percent units: `"5.30%"` becomes `Decimal("5.30")`, not `Decimal("0.053")`.
- Non-percent decimal fields reject values with a percent sign.
- Date parsing accepts `YYYY-MM-DD`, `YYYY/MM/DD`, and timestamp strings whose first 10 characters form a date.
- Missing optional numeric/date fields become `None`.
- The normalizer uses `StockIdentity.market`; it must not infer market from code.
- `source` is `akshare.stock_fhps_detail_em` for v0.

## Error Handling

- Missing or unparsable `报告期` skips the row and emits `SourceErrorRow(stage="dividend_normalize", message="missing report period")` or `message="invalid report period"`.
- Duplicate report periods are resolved by plan-status priority and emit `SourceErrorRow(stage="dividend_normalize", message="duplicate report period")`.
- Plan-status priority is `实施` > `股东大会通过` > `董事会预案` > `预案` > any other non-empty status > missing status.
- When two duplicate rows have the same plan-status priority, keep the row that appears later in the raw frame and emit the duplicate error.
- Malformed optional decimals become `None` and emit `SourceErrorRow(stage="dividend_normalize", message="invalid decimal field: <field_name>")`.
- Unknown stock-code prefixes are handled by universe selection; dividend normalization receives a `StockIdentity` and does not raise for prefixes.

## Data Quality Flags

- The normalizer emits source errors, not final report flags.
- Report assembly converts duplicate-period errors into `duplicate_report_period`.
- Report assembly converts empty normalized record sets into `no_valid_dividend_records`.

## Acceptance Criteria

- Fixture dividend frames normalize into deterministic `DividendRecord` values.
- Duplicate report periods prefer finalized implementation rows.
- Percent fields and non-percent decimal fields use field-specific parsing rules.
- Missing report period rows are skipped with source errors.
- Unknown code prefixes cannot halt dividend normalization because market is supplied by `StockIdentity`.

## Tests

- `tests/normalize/test_dividends.py::test_normalize_dividend_detail_maps_required_fields_from_fixture` remains the fixture mapping test.
- `tests/normalize/test_dividends.py::test_normalize_dividend_detail_prefers_implemented_duplicate_report_period` verifies plan-status priority.
- `tests/normalize/test_dividends.py::test_normalize_dividend_detail_uses_stock_identity_market` passes a nonstandard code with `market="BJ"` and expects no prefix inference.
- `tests/normalize/test_dividends.py::test_percent_fields_keep_percent_units` verifies `5.30%` becomes `Decimal("5.30")`.
- `tests/normalize/test_dividends.py::test_non_percent_decimal_rejects_percent_sign` expects a source error for `每股收益="2.10%"`.
- Run `uv run pytest tests/normalize/test_dividends.py -q`.

## Out of Scope

- Fetching raw dividend frames.
- Calculating dividend yield.
- Ranking stocks.
- Parsing non-AKShare dividend providers.

## Dependencies

- Depends on `future_ledger.domain.StockIdentity`, `DividendRecord`, and `SourceErrorRow`.
- Consumes output from source fetching.
- Feeds metrics and report assembly.
