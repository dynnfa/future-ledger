# FutureLedger Module Spec Suite Wave 1: Report Assembly Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the report assembly module spec that defines the report table contracts consumed by later waves.

**Architecture:** Wave 1 is intentionally serial and contains only Task 1. It establishes `ReportTables`, rank rows, long rows, metadata rows, data quality flags, and assembly behavior before workbook, CLI, and test strategy specs consume those contracts.

**Tech Stack:** Python 3.11, Typer, pandas, AKShare, openpyxl, tenacity, pytest, ruff, mypy, Markdown specs under `docs/superpowers/specs/`.

---

## Source Context

This plan is split from `docs/superpowers/plans/2026-05-14-module-spec-suite.md`. It preserves the original task numbers so commits, reviews, and cross-module references line up with the master plan.

## Execution Rules

- Use one fresh agent per task.
- Keep each agent scoped to the files listed in its task.
- Do not combine task ownership across spec files.
- Run each task's verification commands before committing that task.
- After all tasks in this wave finish, run a quick consistency pass for names, stages, flags, and dependencies introduced inside this wave.

## Wave Task Order

Run this task first and complete its review before starting Wave 2.

```text
Task 1: 07-report-assembly
```

### Task 1: 07 Report Assembly Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-07-report-assembly-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-07-report-assembly-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the report assembly spec**

Create `docs/superpowers/specs/2026-05-14-07-report-assembly-design.md` with this exact Markdown:

```markdown
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
- Missing reference prices produce empty yield fields and the `missing_reference_price` flag.
- Missing return start or end prices produce empty return fields and the `missing_return_price` flag.
- Missing dividend certainty for the one-year return window produces the `uncertain_dividend_window` flag.
- Fatal programmer errors, such as passing objects that are not domain types, are not converted into `SourceErrorRow`.

## Data Quality Flags

- `no_valid_dividend_records`: the stock has no normalized dividend records after dividend normalization.
- `has_missing_years_5y`: fewer than `RunConfig.years` report years are available.
- `missing_reference_price`: no usable price exists on or before the ex-dividend date.
- `missing_return_price`: the one-year return window lacks a usable start or end price.
- `uncertain_dividend_window`: source data cannot determine whether dividends occurred inside the return window.
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
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-07-report-assembly-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify assigned risks are covered**

Run:

```bash
rg -n "run_scan|annual_fields|missing_reference_price|missing_return_price" docs/superpowers/specs/2026-05-14-07-report-assembly-design.md
```

Expected: output includes lines for `run_scan`, `annual_fields`, `missing_reference_price`, and `missing_return_price`.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-07-report-assembly-design.md
git commit -m "docs: specify report assembly module"
```
