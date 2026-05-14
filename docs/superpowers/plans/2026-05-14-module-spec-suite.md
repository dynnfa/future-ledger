# FutureLedger Module Spec Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the ten v0 module design specs that turn the module-spec index into independently reviewable engineering contracts.

**Architecture:** This is a docs-first implementation plan. Each task owns one functional module spec under `docs/superpowers/specs/`, uses the standard module spec template from the index, and records inputs, outputs, domain contracts, errors, flags, acceptance criteria, and tests without requiring implementation code changes. The task order follows the index recommendation: close the report/workbook/CLI spine first, then tighten cache, source, normalization, metrics, universe, and project-wide verification.

**Tech Stack:** Python 3.11, Typer, pandas, AKShare, openpyxl, tenacity, pytest, ruff, mypy, Markdown specs under `docs/superpowers/specs/`.

---

## Scope Check

This plan implements the module spec suite, not the product modules themselves. The specs are intentionally split by functional module so each one can be written, reviewed, and committed independently. The product implementation plans that follow these specs should be created after the spec suite is accepted.

## File Structure

Create these independent module spec files:

- `docs/superpowers/specs/2026-05-14-07-report-assembly-design.md` defines `ReportTables` assembly and report row contracts.
- `docs/superpowers/specs/2026-05-14-08-workbook-writer-design.md` defines workbook writer sheets, columns, formatting, and failure behavior.
- `docs/superpowers/specs/2026-05-14-09-cli-pipeline-design.md` defines CLI validation, orchestration, progress, and exit semantics.
- `docs/superpowers/specs/2026-05-14-03-raw-cache-design.md` defines raw cache keys, CSV snapshots, metadata sidecars, and runtime behavior.
- `docs/superpowers/specs/2026-05-14-02-source-fetching-design.md` defines the AKShare source client boundary, metadata, retry behavior, and live smoke test boundary.
- `docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md` defines dividend-detail column mapping, parsing, de-duplication, and normalization errors.
- `docs/superpowers/specs/2026-05-14-05-price-normalization-design.md` defines price-history column mapping, sorting, invalid row handling, and duplicate handling.
- `docs/superpowers/specs/2026-05-14-06-metrics-design.md` defines dividend-yield and trailing one-year return rules.
- `docs/superpowers/specs/2026-05-14-01-universe-selection-design.md` defines A-share universe filtering, limit semantics, and market inference.
- `docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md` defines deterministic fixtures, optional live smoke tests, and static analysis expectations.

Existing files used as source material:

- `docs/superpowers/specs/2026-04-28-module-spec-index-design.md`
- `docs/designs/v0-dividend-report.md`
- `src/future_ledger/domain.py`
- `src/future_ledger/pipeline.py`
- `src/future_ledger/cli.py`
- `src/future_ledger/cache.py`
- `src/future_ledger/sources/akshare_client.py`
- `src/future_ledger/sources/universe.py`
- `src/future_ledger/normalize/dividends.py`
- `src/future_ledger/normalize/prices.py`
- `src/future_ledger/metrics/dividend_yield.py`
- `src/future_ledger/metrics/returns.py`
- `tests/`

## Shared Verification Command

Each task uses the same heading validator with its own target file:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/REPLACE_WITH_FILE.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected output:

```text
ok
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

### Task 2: 08 Workbook Writer Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-08-workbook-writer-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-08-workbook-writer-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the workbook writer spec**

Create `docs/superpowers/specs/2026-05-14-08-workbook-writer-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 08 Workbook Writer Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Write `future_ledger.domain.ReportTables` to the v0 Excel workbook at the path requested by the CLI.

The writer is a pure output module. It accepts already assembled report tables, creates parent directories when needed, writes the required sheets in stable order, and applies readable Excel formatting without mutating domain rows.

## Current State

- No workbook writer module exists under `src/future_ledger/`.
- `pyproject.toml` includes `openpyxl` and `pandas`.
- `src/future_ledger/cli.py` prints `workbook writing not yet implemented` after `run_scan()`.
- No tests verify workbook sheets, columns, or formatting.

## Inputs

- `ReportTables` with rank, long, price, source error, and metadata rows.
- Output path from `RunConfig.output`.
- Optional workbook timestamp supplied by the caller for deterministic tests.

## Outputs

- A `.xlsx` workbook containing these sheets in order: `dividend_rank`, `dividend_long`, `price_points`, `source_errors`, `metadata`.
- Parent output directories created with `parents=True` and `exist_ok=True`.
- A returned `Path` pointing to the written workbook.

## Domain Contracts

- The writer consumes only `ReportTables` and primitive output settings.
- The writer must not import `akshare`, call source modules, run metrics, or inspect pandas DataFrames from upstream sources.
- Sheet rows are converted from dataclasses using explicit column maps, not dataclass field order.
- `None` values are written as blank Excel cells.
- `Decimal` values are written as numeric cells, not strings.
- `date` values are written as date cells with `yyyy-mm-dd` formatting.
- `tuple[str, ...]` data quality flags are written as `|`-joined strings.
- `annual_fields` are expanded after the core `dividend_rank` columns in the order supplied by report assembly.

## Error Handling

- If the output suffix is not `.xlsx`, raise `ConfigError` with message `--output must end with .xlsx`.
- If the parent path exists as a file, raise `ConfigError` with message `output parent is not a directory`.
- If openpyxl cannot save the workbook because the path is unwritable, raise `ConfigError` with message `failed to write workbook`.
- Empty `ReportTables` still produce all five sheets with headers.

## Data Quality Flags

- The writer does not create new data quality flags.
- The writer preserves `data_quality_flags` from `DividendRankRow` and `return_data_quality_flags` already folded into rank rows by report assembly.

## Acceptance Criteria

- `write_workbook(tables, output_path)` writes all five required sheets in stable order.
- `dividend_rank` uses the core column order from `docs/designs/v0-dividend-report.md`, followed by annual expansion fields.
- `dividend_long`, `price_points`, `source_errors`, and `metadata` use explicit column lists.
- Numeric dividend yield and return percentage columns use percentage-style numeric formatting while retaining percent-unit values from the domain model.
- Date columns use `yyyy-mm-dd`.
- Boolean columns use Excel booleans.
- Empty report tables produce a workbook with headers and no data rows.

## Tests

- `tests/test_workbook_writer.py::test_write_workbook_creates_required_sheets_in_order` loads the workbook with openpyxl and expects the sheet order `["dividend_rank", "dividend_long", "price_points", "source_errors", "metadata"]`.
- `tests/test_workbook_writer.py::test_write_workbook_preserves_rank_column_order` verifies the header row for `dividend_rank`.
- `tests/test_workbook_writer.py::test_write_workbook_writes_empty_tables_with_headers` verifies every sheet has one header row when `ReportTables.empty()` is written.
- `tests/test_workbook_writer.py::test_write_workbook_rejects_non_xlsx_output` expects `ConfigError`.
- `tests/test_workbook_writer.py::test_write_workbook_creates_parent_directories` writes to a nested temporary directory.
- Run `uv run pytest tests/test_workbook_writer.py -q`.

## Out of Scope

- Generating `ReportTables`.
- Fetching or caching source data.
- Creating charts, formulas, pivot tables, or workbook macros.
- Styling beyond stable headers, widths, frozen top row, date formats, numeric formats, and boolean cells.

## Dependencies

- Depends on `future_ledger.domain.ReportTables`.
- Depends on `future_ledger.errors.ConfigError`.
- Feeds the CLI command by producing the final workbook file.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-08-workbook-writer-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify sheet and failure contracts**

Run:

```bash
rg -n "dividend_rank|dividend_long|price_points|source_errors|metadata|ConfigError|\\.xlsx" docs/superpowers/specs/2026-05-14-08-workbook-writer-design.md
```

Expected: output includes all five sheet names, `ConfigError`, and `.xlsx`.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-08-workbook-writer-design.md
git commit -m "docs: specify workbook writer module"
```

### Task 3: 09 CLI Pipeline Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-09-cli-pipeline-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-09-cli-pipeline-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the CLI pipeline spec**

Create `docs/superpowers/specs/2026-05-14-09-cli-pipeline-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 09 CLI Pipeline Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Connect `future-ledger dividends scan` inputs to the full local v0 dividend workflow: universe selection, source fetching, raw caching, normalization, metrics, report assembly, and workbook writing.

## Current State

- `src/future_ledger/cli.py` defines `future-ledger dividends scan` with `--years`, `--as-of`, `--universe`, `--output`, `--limit`, and `--cache-dir`.
- CLI validation exists for `--years`, `--as-of`, and `--limit`.
- `src/future_ledger/pipeline.py` exposes `run_scan(config: RunConfig) -> ReportTables`, but it returns empty tables.
- The CLI prints a completion message that says workbook writing is absent.

## Inputs

- CLI command: `future-ledger dividends scan`.
- `--years`: positive integer, default `5`.
- `--as-of`: ISO date `YYYY-MM-DD`, default current local date.
- `--universe`: universe name, default `all-a-excluding-st`.
- `--output`: `.xlsx` path, default `reports/dividend_rank.xlsx`.
- `--limit`: optional positive integer for development runs.
- `--cache-dir`: raw source cache directory, default `.future_ledger/cache`.

## Outputs

- A populated workbook at `--output`.
- User-visible progress messages for universe size, processed stock count, source error count, and workbook path.
- Process exit code `0` when scan completes with recoverable per-stock errors.
- Non-zero Typer failure for fatal validation, configuration, source-universe, and output-path errors.

## Domain Contracts

- CLI validation resolves a `RunConfig` before calling the pipeline.
- `run_scan(config)` returns `ReportTables` and never writes the workbook.
- Workbook writing is called by the CLI after `run_scan(config)` succeeds.
- Recoverable per-stock fetch, parse, metric, and cache write failures are represented as `SourceErrorRow` and do not raise out of `run_scan`.
- Fatal errors include invalid CLI parameters, unsupported universe names, malformed universe source frames, and invalid workbook output paths.
- Pipeline order is: fetch spot universe frame, build universe, fetch dividend and price frames per stock, write raw cache snapshots, normalize dividends, normalize prices, calculate dividend yield, calculate one-year return, assemble report tables.

## Error Handling

- Invalid `--years` raises `typer.BadParameter("--years must be >= 1")`.
- Invalid `--as-of` raises `typer.BadParameter("Invalid date format: '<value>'. Expected YYYY-MM-DD.")`.
- Invalid `--limit` raises `typer.BadParameter("--limit must be >= 1")`.
- Unsupported `--universe` raises `typer.BadParameter("Unsupported universe: <value>")`.
- Non-`.xlsx` `--output` raises `typer.BadParameter("--output must end with .xlsx")`.
- `ConfigError` from the workbook writer is shown as a CLI error and exits non-zero.
- Per-stock `SourceErrorRow` entries are summarized in stdout and written to the `source_errors` sheet.

## Data Quality Flags

- The CLI creates no data quality flags.
- The pipeline preserves flags created by normalization, metrics, and report assembly.
- The completion message includes the number of source error rows so users know whether to inspect `source_errors`.

## Acceptance Criteria

- Running `future-ledger dividends scan --as-of 2026-04-20 --limit 1 --output tmp/report.xlsx` invokes `run_scan()` with the resolved `RunConfig`.
- A successful scan calls `write_workbook(tables, config.output)`.
- The success message includes `Workbook written: tmp/report.xlsx` and `Rows ranked: <count>`.
- Recoverable source errors do not make the CLI exit non-zero.
- Fatal validation and output errors exit non-zero and do not call source fetching.

## Tests

- `tests/test_cli.py::test_scan_valid_as_of` updates its expectation from the old workbook-missing message to `Workbook written`.
- `tests/test_cli.py::test_scan_writes_workbook_after_run_scan` monkeypatches `run_scan` and `write_workbook` and verifies call order.
- `tests/test_cli.py::test_scan_rejects_non_xlsx_output` expects non-zero exit and `--output must end with .xlsx`.
- `tests/test_pipeline.py::test_run_scan_continues_after_per_stock_source_error` uses fake source functions and expects one source error plus one successful rank row.
- `tests/test_pipeline.py::test_run_scan_sequences_source_cache_normalize_metrics_and_assembly` uses fakes that append stage names to a list and expects the declared order.
- Run `uv run pytest tests/test_cli.py tests/test_pipeline.py -q`.

## Out of Scope

- Live AKShare smoke testing in default CLI tests.
- Alternative subcommands.
- Web server or dashboard orchestration.
- Portfolio management.

## Dependencies

- Depends on universe selection, source fetching, raw cache, normalization, metrics, report assembly, and workbook writer specs.
- Uses `future_ledger.domain.RunConfig` and `future_ledger.domain.ReportTables`.
- Uses Typer for CLI behavior.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-09-cli-pipeline-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify CLI and pipeline contracts**

Run:

```bash
rg -n "future-ledger dividends scan|run_scan|write_workbook|--years|--as-of|--universe|--output|--limit|--cache-dir" docs/superpowers/specs/2026-05-14-09-cli-pipeline-design.md
```

Expected: output includes the command, `run_scan`, `write_workbook`, and all six CLI options.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-09-cli-pipeline-design.md
git commit -m "docs: specify cli pipeline module"
```

### Task 4: 03 Raw Cache Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-03-raw-cache-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-03-raw-cache-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the raw cache spec**

Create `docs/superpowers/specs/2026-05-14-03-raw-cache-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 03 Raw Cache Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Persist raw upstream AKShare frames and source metadata so every workbook run can be audited and reproduced from saved snapshots.

## Current State

- `src/future_ledger/cache.py` defines `cache_key(stage, symbol, ext=".csv")`.
- `read_cache()` and `write_cache()` raise `NotImplementedError`.
- `.future_ledger/cache` is the default cache directory in `RunConfig`.
- No metadata sidecar format exists.

## Inputs

- `cache_dir: Path`.
- `stage: str` with one of `spot`, `dividend_detail`, or `price_history`.
- `symbol: str`, using `all_a` for the A-share spot frame and six-digit stock codes for per-stock frames.
- Raw pandas `DataFrame`.
- `SourceMetadata` values: source name, stage, symbol, fetched timestamp, AKShare version, row count, request start date, request end date, and upstream function name.

## Outputs

- CSV snapshot at `cache_dir/<stage>/<cache_id>.csv`.
- JSON metadata sidecar at `cache_dir/<stage>/<cache_id>.metadata.json`.
- `read_cache(cache_dir, key)` returns a pandas `DataFrame` or `None`.
- `read_metadata(cache_dir, key)` returns a dictionary or `None`.

## Domain Contracts

- Cache keys are deterministic and contain no path traversal segments.
- `spot` key: `spot/all_a.csv`.
- `dividend_detail` key: `dividend_detail/<symbol>.csv`.
- `price_history` key: `price_history/<symbol>_<start_date>_<end_date>.csv` where dates use `YYYYMMDD`.
- Metadata sidecars use the same path stem with `.metadata.json`.
- CSV snapshots preserve upstream raw column names because the cache is a source-layer artifact.
- Downstream modules must not consume cached raw column names directly; they must pass cached frames through normalization.
- v0 runtime behavior is write-through: successful live fetches are written to cache, but the CLI does not offer offline cache-only mode.
- `read_cache()` exists for tests, debugging, and future offline workflows.

## Error Handling

- Missing cache files return `None`.
- Malformed CSV snapshots raise `SourceError` with stage `cache_read`.
- Unwritable cache directories append a `SourceErrorRow` with stage `cache_write` and do not fail the whole scan.
- Failed live fetches do not overwrite existing cache files.
- Empty successful frames are cached with row count `0` and metadata field `"empty": true`.

## Data Quality Flags

- The cache module creates no report data quality flags.
- Cache write failures are represented as `SourceErrorRow(stage="cache_write")`.
- Empty successful source frames are represented in metadata and left to source or normalization modules to flag as report data quality.

## Acceptance Criteria

- `write_cache()` creates parent directories and writes CSV using UTF-8.
- `read_cache()` round-trips Chinese column names and values from fixture DataFrames.
- `write_metadata()` writes stable JSON with sorted keys and ISO 8601 timestamps.
- `cache_key()` rejects `symbol` values containing `/`, `\`, `..`, or empty strings.
- Pipeline cache failures are recoverable per stock.

## Tests

- `tests/test_cache.py::test_cache_key_uses_stage_and_symbol` expects `dividend_detail/600000.csv`.
- `tests/test_cache.py::test_price_history_cache_key_includes_date_range` expects `price_history/600000_20250420_20260420.csv`.
- `tests/test_cache.py::test_write_and_read_cache_round_trips_dataframe` writes a DataFrame with `代码` and `名称`.
- `tests/test_cache.py::test_write_and_read_metadata_round_trips_json` verifies source name, row count, and AKShare version.
- `tests/test_cache.py::test_cache_key_rejects_path_traversal` expects `ValueError`.
- Run `uv run pytest tests/test_cache.py -q`.

## Out of Scope

- Cache eviction.
- Cache compression.
- Offline cache-only CLI mode.
- Reconciliation between multiple source providers.

## Dependencies

- Uses pandas for CSV snapshots.
- Uses `future_ledger.errors.SourceError` for malformed cache reads.
- Used by source fetching and pipeline orchestration.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-03-raw-cache-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify cache contracts**

Run:

```bash
rg -n "spot/all_a|dividend_detail/<symbol>|price_history/<symbol>_<start_date>_<end_date>|metadata.json|write-through|cache_write" docs/superpowers/specs/2026-05-14-03-raw-cache-design.md
```

Expected: output includes cache key formats, metadata sidecar naming, write-through behavior, and `cache_write`.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-03-raw-cache-design.md
git commit -m "docs: specify raw cache module"
```

### Task 5: 02 Source Fetching Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-02-source-fetching-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-02-source-fetching-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the source fetching spec**

Create `docs/superpowers/specs/2026-05-14-02-source-fetching-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 02 Source Fetching Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Isolate live AKShare calls behind a small source-client boundary that returns raw frames plus source lineage metadata.

## Current State

- `src/future_ledger/sources/akshare_client.py` calls `ak.stock_zh_a_spot_em()`, `ak.stock_fhps_detail_em(symbol=...)`, and `ak.stock_zh_a_hist(...)` directly.
- The functions return raw pandas `DataFrame` objects only.
- `tenacity` is installed but source retry behavior is not defined.
- Existing default tests do not call live AKShare endpoints.

## Inputs

- No-argument request for A-share spot data.
- Six-digit stock symbol for dividend detail.
- Six-digit stock symbol plus `start_date` and `end_date` strings in `YYYYMMDD` format for daily price history.
- Optional clock callable for deterministic `fetched_at` metadata in tests.

## Outputs

- `SourceFetchResult(frame: pd.DataFrame, metadata: SourceMetadata, error: SourceErrorRow | None)`.
- `SourceMetadata` fields: `source_name`, `stage`, `symbol`, `fetched_at`, `akshare_version`, `row_count`, `request_start_date`, `request_end_date`, and `upstream_function`.
- Stages: `spot_fetch`, `dividend_fetch`, and `price_fetch`.

## Domain Contracts

- Source functions are the only code allowed to call AKShare.
- Source functions may return raw AKShare column names because they are upstream boundary functions.
- Normalization modules are responsible for converting raw frames into domain types.
- Empty DataFrames are successful fetch results with `row_count=0` and an attached `SourceErrorRow` whose message is `empty upstream frame`.
- Malformed non-DataFrame responses become `SourceErrorRow` with message `malformed upstream response`.
- Live network exceptions become `SourceErrorRow` and an empty DataFrame.
- The source client does not write cache files directly; the pipeline passes successful results to the raw cache module.

## Error Handling

- Each live call retries up to 3 attempts with exponential backoff: initial wait `0.5s`, multiplier `2`, maximum wait `4s`.
- Retries apply to exceptions raised by AKShare and transport-level failures.
- After retries are exhausted, return an empty frame plus `SourceErrorRow(stage=<stage>, message=<exception class>: <message>)`.
- Invalid symbol format raises `ValueError("symbol must be a six-digit A-share code")` before live calls.
- Invalid price date ranges raise `ValueError("start_date must be <= end_date")` before live calls.

## Data Quality Flags

- The source module does not create report data quality flags.
- Empty successful frames are represented as source errors so report assembly can later emit `empty_dividend_detail` or related flags.

## Acceptance Criteria

- Fetch functions return `SourceFetchResult` for spot, dividend detail, and price history.
- Source metadata captures AKShare version and row count for every successful and empty result.
- Default unit tests use monkeypatched AKShare functions and do not access the network.
- Optional live smoke tests are marked `@pytest.mark.live_akshare` and skipped unless explicitly enabled.
- Source-stage names are stable strings used in `source_errors`.

## Tests

- `tests/sources/test_akshare_client.py::test_fetch_a_share_spot_returns_frame_and_metadata` monkeypatches `ak.stock_zh_a_spot_em`.
- `tests/sources/test_akshare_client.py::test_fetch_dividend_detail_records_empty_frame_source_error` monkeypatches an empty DataFrame and expects stage `dividend_fetch`.
- `tests/sources/test_akshare_client.py::test_fetch_price_history_validates_date_range` expects `ValueError`.
- `tests/sources/test_akshare_client.py::test_fetch_source_exception_returns_source_error_after_retries` monkeypatches a raising function and expects an empty frame plus source error.
- `tests/live/test_akshare_smoke.py::test_live_fetch_a_share_spot_smoke` is marked `live_akshare` and skipped by default.
- Run `uv run pytest tests/sources/test_akshare_client.py -q`.

## Out of Scope

- Multi-source fallback beyond AKShare.
- Cache persistence.
- Normalizing raw column names.
- Investment advice or source scoring.

## Dependencies

- Depends on AKShare, pandas, tenacity, and `future_ledger.domain.SourceErrorRow`.
- Feeds raw cache, universe selection, dividend normalization, and price normalization.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-02-source-fetching-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify source boundary contracts**

Run:

```bash
rg -n "SourceFetchResult|SourceMetadata|spot_fetch|dividend_fetch|price_fetch|live_akshare|3 attempts" docs/superpowers/specs/2026-05-14-02-source-fetching-design.md
```

Expected: output includes result and metadata types, all fetch stages, the live smoke marker, and retry count.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-02-source-fetching-design.md
git commit -m "docs: specify source fetching module"
```

### Task 6: 04 Dividend Normalization Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the dividend normalization spec**

Create `docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md` with this exact Markdown:

```markdown
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
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify normalization risk coverage**

Run:

```bash
rg -n "duplicate report period|plan-status priority|Percent fields|StockIdentity.market|invalid decimal field" docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md
```

Expected: output includes duplicate resolution, plan-status priority, percent parsing, market source, and invalid decimal behavior.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md
git commit -m "docs: specify dividend normalization module"
```

### Task 7: 05 Price Normalization Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-05-price-normalization-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-05-price-normalization-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the price normalization spec**

Create `docs/superpowers/specs/2026-05-14-05-price-normalization-design.md` with this exact Markdown:

```markdown
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
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-05-price-normalization-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify price edge-case coverage**

Run:

```bash
rg -n "non-positive close price|duplicate price date|sorted ascending|missing close price|invalid close price" docs/superpowers/specs/2026-05-14-05-price-normalization-design.md
```

Expected: output includes non-positive, duplicate, sorting, missing close, and invalid close contracts.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-05-price-normalization-design.md
git commit -m "docs: specify price normalization module"
```

### Task 8: 06 Metrics Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-06-metrics-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-06-metrics-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the metrics spec**

Create `docs/superpowers/specs/2026-05-14-06-metrics-design.md` with this exact Markdown:

```markdown
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
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-06-metrics-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify metric risk coverage**

Run:

```bash
rg -n "February 29|ex-dividend date|previous trading|Decimal\\(\"0\\.01\"\\)|missing_reference_price|missing_return_price|must not sort" docs/superpowers/specs/2026-05-14-06-metrics-design.md
```

Expected: output includes leap-year handling, reference price rules, quantization, missing-price flags, and no repeated sorting.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-06-metrics-design.md
git commit -m "docs: specify metrics module"
```

### Task 9: 01 Universe Selection Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-01-universe-selection-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-01-universe-selection-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the universe selection spec**

Create `docs/superpowers/specs/2026-05-14-01-universe-selection-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 01 Universe Selection Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Build a deterministic list of `StockIdentity` rows from the A-share spot market frame.

## Current State

- `src/future_ledger/sources/universe.py` implements `build_universe(frame, universe, limit)`.
- Supported universe is `all-a-excluding-st`.
- ST filtering uses a case-insensitive substring check on the stock name.
- Market inference maps `6` to `SH`, `0` and `3` to `SZ`, and `4` and `8` to `BJ`.
- Unsupported stock-code prefixes raise `ValueError` and can halt a batch.

## Inputs

- Raw A-share spot pandas `DataFrame` from `akshare.stock_zh_a_spot_em()`.
- `universe: str`.
- `limit: int | None`.

## Outputs

- `list[StockIdentity]` in the same order as the filtered spot frame.
- `list[SourceErrorRow]` for skipped malformed rows and unsupported stock-code prefixes.

## Domain Contracts

- Supported universe names for v0: `all-a-excluding-st`.
- Required raw columns are `代码` and `名称`.
- Stock code is normalized to a zero-padded six-character string when AKShare supplies an integer-like value.
- ST filtering excludes rows whose uppercase `名称` contains `ST`.
- `limit` is applied after ST filtering and after malformed rows are skipped.
- `limit=None` means no development limit.
- Market inference:
  - Prefix `6` -> `SH`.
  - Prefix `0` or `3` -> `SZ`.
  - Prefix `4` or `8` -> `BJ`.
- Unknown prefixes are recoverable row-level source errors and are skipped.
- Missing required columns are fatal source-frame errors because no reliable universe can be built.

## Error Handling

- Unsupported universe raises `ValueError("Unsupported universe: <name>")` before row processing.
- Non-positive limit raises `ValueError("limit must be >= 1")`.
- Missing `代码` or `名称` columns raises `SourceError("spot frame missing required columns: 代码, 名称")`.
- Empty spot frame returns an empty universe and a `SourceErrorRow(stage="universe", message="empty spot frame")`.
- Unsupported prefixes emit `SourceErrorRow(stage="universe", message="unsupported stock code prefix")` and skip the row.
- Missing or blank stock names emit `SourceErrorRow(stage="universe", message="missing stock name")` and skip the row.

## Data Quality Flags

- Universe selection does not create final report flags.
- Skipped universe rows are visible in `source_errors` with stage `universe`.

## Acceptance Criteria

- `all-a-excluding-st` excludes ST rows deterministically.
- Limit is applied after filtering.
- SH, SZ, and BJ market inference is deterministic.
- Unknown prefixes no longer halt the whole scan.
- Default tests do not require live AKShare data.

## Tests

- `tests/sources/test_universe.py::test_build_universe_excludes_st_names` remains the ST filtering test.
- `tests/sources/test_universe.py::test_build_universe_applies_limit_after_filtering` remains the limit test.
- `tests/sources/test_universe.py::test_build_universe_assigns_market_by_code_prefix` remains the market inference test.
- `tests/sources/test_universe.py::test_build_universe_skips_unknown_prefix_with_source_error` expects a source error and no exception for code `900001`.
- `tests/sources/test_universe.py::test_build_universe_rejects_missing_required_columns` expects `SourceError`.
- Run `uv run pytest tests/sources/test_universe.py -q`.

## Out of Scope

- Non-A-share universes.
- Index constituent universes.
- Fundamental or liquidity filtering.
- Live source fetching.

## Dependencies

- Consumes A-share spot frame from source fetching.
- Produces `StockIdentity` rows for pipeline, dividend normalization, and price requests.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-01-universe-selection-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify universe risk coverage**

Run:

```bash
rg -n "all-a-excluding-st|ST|limit|SH|SZ|BJ|unsupported stock code prefix|SourceError" docs/superpowers/specs/2026-05-14-01-universe-selection-design.md
```

Expected: output includes universe name, ST rule, limit rule, market prefixes, unsupported prefix behavior, and `SourceError`.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-01-universe-selection-design.md
git commit -m "docs: specify universe selection module"
```

### Task 10: 10 Test and Fixture Strategy Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the test and fixture strategy spec**

Create `docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 10 Test and Fixture Strategy Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Define the project-wide verification strategy for FutureLedger v0 so default CI remains deterministic and does not depend on live financial endpoints.

## Current State

- Tests exist for CLI validation, domain model construction, universe selection, dividend normalization, price normalization, dividend yield, and one-year return.
- Fixtures exist under `tests/fixtures/akshare/` and `tests/fixtures/prices/`.
- No workbook writer, report assembly, cache, source-client, or pipeline integration tests exist.
- `pyproject.toml` configures `pytest`, `ruff`, and strict `mypy`.

## Inputs

- Module specs `01` through `09`.
- Existing fixture CSVs under `tests/fixtures/`.
- Development commands from `pyproject.toml`.

## Outputs

- A deterministic default test suite.
- Fixture naming conventions.
- Optional live AKShare smoke tests excluded from default CI.
- Static analysis expectations.
- Coverage expectations for known review risks.

## Domain Contracts

- Default verification command is `uv run pytest`.
- Static verification commands are `uv run ruff check .` and `uv run mypy src tests`.
- Default tests must not access the network.
- Fixture files use UTF-8 CSV.
- Fixture paths:
  - `tests/fixtures/akshare/spot_a_share.csv`
  - `tests/fixtures/akshare/dividend_detail_<symbol>.csv`
  - `tests/fixtures/prices/<symbol>_daily_<start_date>_<end_date>.csv`
  - `tests/fixtures/cache/<stage>/<cache_id>.csv`
  - `tests/fixtures/workbooks/` only for intentionally small golden workbooks.
- Fixture date ranges use `YYYYMMDD` in filenames.
- Live tests live under `tests/live/`, use marker `live_akshare`, and are skipped by default.
- Test data should stay small: default fixture CSVs should be under 100 rows unless a test explicitly validates large-frame behavior.

## Error Handling

- A test that would call AKShare without the `live_akshare` marker is a test-suite bug.
- Live smoke failures do not block default CI because live tests are skipped unless explicitly selected.
- Golden workbook tests compare sheet names, headers, cell types, and representative values, not volatile generated timestamps.

## Data Quality Flags

- Every data quality flag introduced by module specs must have at least one unit or integration test.
- Required tested flags: `no_valid_dividend_records`, `has_missing_years_5y`, `missing_reference_price`, `missing_return_price`, `uncertain_dividend_window`, `duplicate_report_period`, and `empty_dividend_detail`.

## Acceptance Criteria

- `uv run pytest` passes without network access.
- `uv run ruff check .` passes.
- `uv run mypy src tests` passes under strict mypy.
- Live smoke tests run only with `uv run pytest tests/live -m live_akshare`.
- Integration tests cover pipeline behavior from fixture source results to workbook shape.
- Known review risks from the module index have explicit tests.

## Tests

- `tests/test_no_network_default.py::test_default_tests_do_not_use_live_akshare_marker` verifies live tests are isolated under `tests/live/`.
- `tests/test_fixture_strategy.py::test_fixture_files_follow_naming_convention` validates fixture paths.
- `tests/test_fixture_strategy.py::test_fixture_files_stay_small` enforces the 100-row default fixture limit.
- `tests/test_pipeline.py::test_pipeline_fixture_integration_writes_expected_report_tables` uses fake source functions and fixtures.
- `tests/test_workbook_writer.py::test_workbook_shape_from_fixture_report_tables` verifies workbook sheets and headers.
- Run `uv run pytest tests/test_fixture_strategy.py tests/test_no_network_default.py -q`.

## Out of Scope

- Performance benchmarking for the full A-share universe.
- Production monitoring.
- Historical backfill validation beyond v0 fixture windows.
- External data-provider contract tests outside optional smoke tests.

## Dependencies

- Summarizes verification requirements from module specs `01` through `09`.
- Depends on `pyproject.toml` pytest, ruff, and mypy configuration.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify test strategy coverage**

Run:

```bash
rg -n "uv run pytest|ruff check|mypy src tests|live_akshare|100 rows|missing_reference_price|duplicate_report_period" docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md
```

Expected: output includes default pytest, static checks, live marker, fixture size limit, and representative data quality flags.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md
git commit -m "docs: specify test and fixture strategy"
```

## Final Cross-Module Review

- [ ] **Step 1: Verify all ten spec files exist**

Run:

```bash
uv run python -c 'from pathlib import Path; files=["2026-05-14-01-universe-selection-design.md","2026-05-14-02-source-fetching-design.md","2026-05-14-03-raw-cache-design.md","2026-05-14-04-dividend-normalization-design.md","2026-05-14-05-price-normalization-design.md","2026-05-14-06-metrics-design.md","2026-05-14-07-report-assembly-design.md","2026-05-14-08-workbook-writer-design.md","2026-05-14-09-cli-pipeline-design.md","2026-05-14-10-test-and-fixture-strategy-design.md"]; missing=[f for f in files if not (Path("docs/superpowers/specs")/f).exists()]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 2: Scan for placeholder language**

Run:

```bash
uv run python -c 'from pathlib import Path; terms=["T"+"BD","TO"+"DO","implement "+"later","fill in "+"details","add appropriate "+"error handling","Write tests for "+"the above","Similar to "+"Task"]; hits=[];
for p in sorted(Path("docs/superpowers/specs").glob("2026-05-14-*-design.md")):
    text=p.read_text()
    for term in terms:
        if term in text:
            hits.append(f"{p}:{term}")
assert not hits, hits
print("ok")'
```

Expected: `ok`.

- [ ] **Step 3: Verify every spec has the standard template**

Run:

```bash
uv run python -c 'from pathlib import Path; headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; failures={};
for p in sorted(Path("docs/superpowers/specs").glob("2026-05-14-*-design.md")):
    text=p.read_text()
    missing=[h for h in headings if h not in text]
    if missing:
        failures[str(p)]=missing
assert not failures, failures
print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Commit cross-module review fixes if any were needed**

If no fixes were needed, skip this commit. If fixes were needed, run:

```bash
git add docs/superpowers/specs/2026-05-14-*-design.md
git commit -m "docs: align module spec suite"
```

## Self-Review Notes

Spec coverage:

- `01-universe-selection` is covered by Task 9.
- `02-source-fetching` is covered by Task 5.
- `03-raw-cache` is covered by Task 4.
- `04-dividend-normalization` is covered by Task 6.
- `05-price-normalization` is covered by Task 7.
- `06-metrics` is covered by Task 8.
- `07-report-assembly` is covered by Task 1.
- `08-workbook-writer` is covered by Task 2.
- `09-cli-pipeline` is covered by Task 3.
- `10-test-and-fixture-strategy` is covered by Task 10.

Known review risks are assigned:

- Unknown stock-code prefixes: Task 9.
- Live endpoint instability: Task 5 and Task 10.
- Cache functions absent: Task 4.
- Dividend duplicate periods and parsing semantics: Task 6.
- Price sorting and malformed prices: Task 7.
- February 29, reference price eligibility, precision, and lookup sorting: Task 8.
- Empty `run_scan()` and mutable `annual_fields`: Task 1.
- Missing workbook writer: Task 2.
- CLI workbook message and orchestration path: Task 3.
- Deterministic fixture strategy: Task 10.

Placeholder scan:

- The plan uses concrete file paths, commands, expected outputs, and exact Markdown for every created spec file.
- The placeholder scan above is expressed with split string fragments so the plan can be checked without matching its own validation command.

Type consistency:

- Domain names match the current code: `RunConfig`, `StockIdentity`, `DividendRecord`, `PricePoint`, `DividendRankRow`, `DividendLongRow`, `SourceErrorRow`, `MetadataRow`, and `ReportTables`.
- Stage names are stable within the specs: `spot_fetch`, `dividend_fetch`, `price_fetch`, `cache_read`, `cache_write`, `dividend_normalize`, `price_normalize`, and `universe`.

## Agent Execution Strategy

Use one fresh agent per task, but execute tasks in dependency-aware waves. Do not assign one agent to a bundle such as Tasks 1-3, because that blurs report, workbook, and CLI boundaries. The controller should coordinate waves, review each task result, and resolve cross-spec consistency before starting dependent waves.

Recommended order:

```text
Wave 1:
  Task 1: 07-report-assembly

Wave 2:
  Task 2: 08-workbook-writer
  Task 3: 09-cli-pipeline

Wave 3:
  Task 4: 03-raw-cache
  Task 5: 02-source-fetching
  Task 9: 01-universe-selection

Wave 4:
  Task 6: 04-dividend-normalization
  Task 7: 05-price-normalization

Wave 5:
  Task 8: 06-metrics

Wave 6:
  Task 10: 10-test-and-fixture-strategy

Final:
  Final Cross-Module Review
```

Rationale:

- Task 1 runs first because it defines the `ReportTables`, row, metadata, and flag contracts consumed by workbook, CLI, and test strategy specs.
- Tasks 2 and 3 can run in parallel after Task 1 because workbook output and CLI orchestration both consume the report contract but do not own the same spec file.
- Tasks 4, 5, and 9 can run in parallel because cache, source fetching, and universe selection define separate data-entry boundaries.
- Tasks 6 and 7 can run in parallel because dividend normalization and price normalization own separate modules and produce separate domain outputs.
- Task 8 should wait for Tasks 6 and 7 so metric flags and assumptions match normalized dividend and price contracts.
- Task 10 should run last because it summarizes test expectations across the previous nine module specs.
- The final cross-module review should check naming, stages, flags, fixture conventions, and dependency language across all ten specs.
