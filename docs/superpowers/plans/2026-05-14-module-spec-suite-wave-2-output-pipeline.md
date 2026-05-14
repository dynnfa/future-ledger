# FutureLedger Module Spec Suite Wave 2: Output and Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the workbook writer and CLI pipeline specs after the report table contract exists.

**Architecture:** Wave 2 can run Tasks 2 and 3 in parallel once Wave 1 is complete. The workbook writer and CLI pipeline both consume the report assembly contract but own separate spec files and should not edit each other.

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

Dispatch both tasks in parallel after Wave 1 has completed and the report assembly spec is committed.

```text
Task 2: 08-workbook-writer
Task 3: 09-cli-pipeline
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
