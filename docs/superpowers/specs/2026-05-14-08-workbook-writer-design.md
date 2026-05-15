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
