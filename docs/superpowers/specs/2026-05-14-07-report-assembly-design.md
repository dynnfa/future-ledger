# FutureLedger v0 07 Report Assembly Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Assemble normalized dividends, normalized prices, metric results, source errors, and run metadata into `future_ledger.domain.ReportTables`.

This module is the boundary between calculation modules and output modules. The workbook writer must be able to render every sheet by consuming only `ReportTables`; it must not call AKShare, inspect raw DataFrames, or recalculate metrics.

## Current State

- `src/future_ledger/domain.py` defines `DividendRankRow`, `DividendLongRow`, `PricePoint`, `SourceErrorRow`, `MetadataRow`, and `ReportTables`.
- `src/future_ledger/pipeline.py` exposes `run_scan(config: RunConfig) -> ReportTables`, but it currently returns `ReportTables.empty()`.
- `DividendRankRow.annual_fields` is typed as `dict[str, object]` inside a frozen dataclass, so the row is not deeply immutable.
- Existing tests construct domain rows directly but do not verify assembled report semantics.

## Inputs

- `RunConfig` with resolved `years`, `as_of`, `universe`, `output`, `limit`, and `cache_dir`.
- A sequence of `StockIdentity` rows selected by the universe module.
- Per-stock normalized `DividendRecord` rows.
- Per-stock normalized `PricePoint` rows.
- Per-stock dividend-yield results containing reference price, reference date, fallback flag, and calculated yield.
- Per-stock trailing one-year return results.
- `SourceErrorRow` rows emitted by source, cache, normalization, and metric modules.
- Source metadata rows containing source package version, source priority, fetch timestamp, request range, and row counts.
- A generated timestamp in ISO 8601 format with timezone.

## Outputs

- `ReportTables.dividend_rank`: one `DividendRankRow` per stock that reached report assembly, including stocks with missing dividend years or missing metrics.
- `ReportTables.dividend_long`: one `DividendLongRow` per normalized dividend record used for the report window.
- `ReportTables.price_points`: the `PricePoint` rows used as reference prices for dividend yield and one-year return windows.
- `ReportTables.source_errors`: all recoverable failures from upstream modules plus assembly-level data-quality errors.
- `ReportTables.metadata`: run parameters, source versions, source priority, generated timestamp, and the research-only disclaimer.

## Domain Contracts

- AKShare raw column names are prohibited in this module.
- Downstream output uses only `future_ledger.domain` types.
- `DividendRankRow.annual_fields` must become an immutable `Mapping[str, object]` or be copied defensively at construction time so mutating caller-owned dictionaries cannot alter frozen rows.
- Rank rows are sorted by `latest_dividend_yield_pct` descending; rows with missing latest yield are included after ranked rows with `rank_latest_yield=None`.
- Rank numbers are dense and start at `1` for the first row with a non-missing latest yield.
- The report window contains at most `RunConfig.years` report years per stock, selected by `report_year` descending.
- Annual expansion fields use this order for each report year: `YYYY_report_period`, `YYYY_cash_dividend_per_10_shares`, `YYYY_cash_dividend_per_share`, `YYYY_reference_price`, `YYYY_reference_price_date`, `YYYY_dividend_yield_pct`, `YYYY_registration_date`, `YYYY_ex_dividend_date`, `YYYY_plan_status`, `YYYY_eps`, `YYYY_net_asset_per_share`, `YYYY_profit_growth_yoy_pct`, `YYYY_source`.
- `dividend_year_count_5y` counts normalized report years with a non-null `cash_dividend_per_share`.
- `continuous_dividend_5y` is true only when every year in the requested lookback window has a dividend record with a non-null per-share dividend.
- `has_missing_years_5y` is true when fewer than `RunConfig.years` report years are present.
- `source_priority_used` is `akshare.stock_fhps_detail_em` for v0 dividend data.

## Error Handling

- Recoverable per-stock failures are appended to `ReportTables.source_errors` and do not stop assembly for other stocks.
- A stock with no valid dividend records still produces a rank row with empty dividend fields, `rank_latest_yield=None`, and `data_quality_flags=("no_valid_dividend_records",)`.
- Missing cash dividend or ex-dividend dates from metrics produce empty affected metric fields and preserve `missing_cash_dividend` or `missing_ex_dividend_date`.
- Missing reference prices produce empty yield fields and the `missing_reference_price` flag.
- Missing return start or end prices produce empty return fields and the `missing_return_price` flag.
- Invalid return start prices produce empty return fields and preserve `invalid_return_start_price`.
- Missing dividend certainty for the one-year return window produces the `uncertain_dividend_window` flag.
- Fatal programmer errors, such as passing objects that are not domain types, are not converted into `SourceErrorRow`.

## Data Quality Flags

- `no_valid_dividend_records`: the stock has no normalized dividend records after dividend normalization.
- `has_missing_years_5y`: fewer than `RunConfig.years` report years are available.
- `missing_cash_dividend`: a dividend record lacks per-share cash dividend.
- `missing_ex_dividend_date`: a dividend record lacks ex-dividend date.
- `missing_reference_price`: no usable price exists on or before the ex-dividend date.
- `missing_return_price`: the one-year return window lacks a usable start or end price.
- `uncertain_dividend_window`: source data cannot determine whether dividends occurred inside the return window.
- `invalid_return_start_price`: the return start close is zero or negative despite normalization guarantees.
- `duplicate_report_period`: dividend normalization reported more than one row for the same report period.
- `empty_dividend_detail`: the dividend source returned an empty frame for the stock.

## Acceptance Criteria

- `assemble_report_tables(...)` returns a populated `ReportTables` object without invoking live sources.
- Stocks with complete data are ranked by latest calculated dividend yield.
- Stocks with missing latest yield remain visible after ranked stocks.
- Long-form rows mirror the same dividend records used to build annual wide fields.
- Metadata includes `years`, `as_of`, `universe`, `limit`, `cache_dir`, `source_priority`, `generated_at`, `akshare_version`, and `disclaimer`.
- All data quality flags are stable strings suitable for filtering in Excel.
- No AKShare column names appear in report assembly code or tests.

## Tests

- `tests/test_domain_models.py` verifies `DividendRankRow.annual_fields` cannot be mutated through caller-owned dictionaries.
- `tests/test_report_assembly.py::test_assemble_report_tables_ranks_by_latest_yield` builds two stocks with fixture domain objects and expects ranks `1` and `2`.
- `tests/test_report_assembly.py::test_assemble_report_tables_keeps_missing_yield_rows_unranked` expects a stock with missing reference price to have `rank_latest_yield is None` and `missing_reference_price` in flags.
- `tests/test_report_assembly.py::test_assemble_report_tables_expands_annual_fields_in_column_order` verifies the annual field keys for a five-year window.
- `tests/test_report_assembly.py::test_assemble_report_tables_carries_source_errors_and_metadata` verifies source errors and metadata are copied into `ReportTables`.
- Run `uv run pytest tests/test_domain_models.py tests/test_report_assembly.py -q`.

## Out of Scope

- Fetching live AKShare data.
- Writing Excel workbooks.
- CLI parsing.
- Investment ranking rules beyond sorting by latest calculated dividend yield.

## Dependencies

- Depends on `future_ledger.domain` types.
- Consumes outputs from dividend normalization, price normalization, dividend-yield metrics, return metrics, and source fetching.
- Feeds the workbook writer and CLI pipeline.
