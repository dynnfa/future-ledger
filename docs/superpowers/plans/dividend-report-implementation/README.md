# FutureLedger v0 Dividend Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local CLI command that fetches A-share dividend data with AKShare, calculates explicit dividend yield and trailing 1-year return metrics, and writes the required five-sheet Excel workbook.

**Architecture:** Keep AKShare calls isolated under `sources/`, normalize provider output into internal dataclasses before any metric logic, and keep yield/return calculations as pure functions in `metrics/`. The pipeline should rescue per-stock failures into `source_errors`, write deterministic cache artifacts, and hand fully materialized report tables to the Excel writer.

**Tech Stack:** Python 3.11, Typer, pandas, openpyxl, AKShare, pytest, Decimal dataclasses

---

## Scope Check

The design doc describes one coherent subsystem: a single dividend-research pipeline ending in one workbook. It does not need to be split into separate plan documents. The bank-rate work remains deferred in `docs/TODOS.md` and is intentionally excluded from this plan.

## File Structure

### Existing files to modify

- `src/future_ledger/cli.py`
  Responsibility: parse CLI flags, validate input, invoke the pipeline, surface user-facing errors.
- `src/future_ledger/pipeline.py`
  Responsibility: orchestrate universe load, source fetches, normalization, metrics, report assembly, and workbook output.
- `src/future_ledger/domain.py`
  Responsibility: internal dataclasses and type-safe report row shapes.
- `src/future_ledger/cache.py`
  Responsibility: deterministic raw DataFrame cache read/write logic.
- `tests/test_cli.py`
  Responsibility: CLI help, argument parsing, and command behavior.

### New source and normalization files

- `src/future_ledger/sources/akshare_client.py`
  Responsibility: the only module that imports `akshare`; fetch stock universe, dividend detail, and price history.
- `src/future_ledger/sources/universe.py`
  Responsibility: apply `all-a-excluding-st` filtering and optional `--limit`.
- `src/future_ledger/normalize/dividends.py`
  Responsibility: map AKShare dividend columns into normalized annual dividend records and normalization warnings.
- `src/future_ledger/normalize/prices.py`
  Responsibility: map price DataFrames into sorted `PricePoint` values and reusable lookup helpers.

### New metrics and report files

- `src/future_ledger/metrics/dividend_yield.py`
  Responsibility: ex-dividend reference price selection and reproducible dividend-yield calculation.
- `src/future_ledger/metrics/returns.py`
  Responsibility: 1-year return window price selection and return calculation.
- `src/future_ledger/reports/rows.py`
  Responsibility: build `dividend_rank`, `dividend_long`, `price_points`, and `source_errors` rows.
- `src/future_ledger/reports/workbook.py`
  Responsibility: write the required Excel workbook sheets, sheet order, and metadata content.

### New tests and fixtures

- `tests/test_domain_models.py`
  Responsibility: verify the expanded domain types capture required report fields.
- `tests/test_cache.py`
  Responsibility: deterministic cache behavior.
- `tests/sources/test_universe.py`
  Responsibility: universe filtering and ST exclusion.
- `tests/normalize/test_dividends.py`
  Responsibility: fixture-driven normalization of AKShare dividend rows.
- `tests/normalize/test_prices.py`
  Responsibility: price normalization and sorting rules.
- `tests/metrics/test_dividend_yield.py`
  Responsibility: ex-dividend lookup fallback and missing-price flags.
- `tests/metrics/test_returns.py`
  Responsibility: 1-year window lookup and return computation.
- `tests/reports/test_rows.py`
  Responsibility: ranking rows, annual expansion columns, and data-quality flags.
- `tests/reports/test_workbook.py`
  Responsibility: sheet names, column presence, metadata disclaimer, and writable output.
- `tests/pipeline/test_run_scan.py`
  Responsibility: orchestrator rescue behavior and report assembly using fakes.
- `tests/fixtures/akshare/dividend_detail_600000.csv`
  Responsibility: deterministic dividend-source fixture.
- `tests/fixtures/prices/600000_daily.csv`
  Responsibility: deterministic price fixture for fallback rules.

## Delivery Sequence

Implement in order. Each task below should merge cleanly and keep the project in a runnable state.

### Batch 1: Foundations

- [01-domain-models](./01-domain-models.md)
- [02-cli-and-pipeline-bootstrap](./02-cli-and-pipeline-bootstrap.md)
- [03-cache](./03-cache.md)
- [04-universe-and-akshare-client](./04-universe-and-akshare-client.md)

### Batch 2: Data And Metrics

- [05-dividend-normalization](./05-dividend-normalization.md)
- [06-prices-and-dividend-yield](./06-prices-and-dividend-yield.md)
- [07-trailing-one-year-return](./07-trailing-one-year-return.md)

### Batch 3: Reporting And Integration

- [08-report-rows](./08-report-rows.md)
- [09-workbook-writer](./09-workbook-writer.md)
- [10-pipeline-orchestration](./10-pipeline-orchestration.md)
- [11-final-integration-and-regressions](./11-final-integration-and-regressions.md)

## Self-Review

### Spec coverage

- CLI command shape, defaults, and `--as-of`: covered by Tasks 2 and 11.
- AKShare source priority and no silent source mixing: covered by Tasks 4, 5, and 11.
- Universe rule excluding ST but keeping missing-year stocks: covered by Tasks 4 and 8.
- Explicit dividend-yield lineage and fallback rules: covered by Task 6.
- Trailing one-year annualized return: covered by Task 7.
- Workbook shape with five sheets: covered by Tasks 8 and 9.
- Source error rescue behavior: covered by Tasks 5 and 10.
- Metadata/disclaimer compliance: covered by Tasks 9 and 11.
- Raw cache for reproducibility: covered by Task 3.

No spec gaps remain.

### Placeholder scan

Reviewed for `TBD`, `TODO`, “implement later”, “add validation”, and “write tests for the above” style placeholders. None remain in the task steps.

### Type consistency

- `DividendRecord`, `DividendRankRow`, `DividendLongRow`, `MetadataRow`, and `ReportTables` are introduced before later tasks depend on them.
- `calculate_dividend_yield`, `resolve_reference_price`, and `calculate_trailing_one_year_return` use consistent names across all later tasks.
- `write_workbook` and `run_scan` signatures stay consistent between their dedicated tasks and the final integration pass.
