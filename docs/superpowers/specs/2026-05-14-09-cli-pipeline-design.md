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
- Non-zero Typer failure for fatal validation, configuration, universe selection, and output-path errors.

## Domain Contracts

- CLI validation resolves a `RunConfig` before calling the pipeline.
- `run_scan(config)` returns `ReportTables` and never writes the workbook.
- Workbook writing is called by the CLI after `run_scan(config)` succeeds.
- CLI validation rejects syntactically invalid `--output` values and existing-file `--cache-dir` paths before source fetching starts.
- Recoverable per-stock fetch, parse, metric, and cache write failures are represented as `SourceErrorRow` and do not raise out of `run_scan`.
- Fatal errors include invalid CLI parameters, unsupported universe names, malformed universe source frames, and invalid workbook output paths.
- Pipeline order is: fetch spot universe frame, build universe, fetch dividend and price frames per stock, write raw cache snapshots, normalize dividends, normalize prices, calculate dividend yield, calculate one-year return, assemble report tables.

## Error Handling

- Invalid `--years` raises `typer.BadParameter("--years must be >= 1")`.
- Invalid `--as-of` raises `typer.BadParameter("Invalid date format: '<value>'. Expected YYYY-MM-DD.")`.
- Invalid `--limit` raises `typer.BadParameter("--limit must be >= 1")`.
- Unsupported `--universe` raises `typer.BadParameter("Unsupported universe: <value>")`.
- Non-`.xlsx` `--output` raises `typer.BadParameter("--output must end with .xlsx")`.
- If `--cache-dir` exists and is not a directory, raise `typer.BadParameter("--cache-dir must be a directory path")` before source fetching starts.
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
- Fatal pre-run validation errors exit non-zero and do not call source fetching.
- Workbook writer `ConfigError` exits non-zero after `run_scan()` succeeds and does not retry source fetching.

## Tests

- `tests/test_cli.py::test_scan_valid_as_of` updates its expectation from the old workbook-missing message to `Workbook written`.
- `tests/test_cli.py::test_scan_writes_workbook_after_run_scan` monkeypatches `run_scan` and `write_workbook` and verifies call order.
- `tests/test_cli.py::test_scan_rejects_non_xlsx_output` expects non-zero exit and `--output must end with .xlsx`.
- `tests/test_cli.py::test_scan_rejects_cache_dir_that_is_file` expects non-zero exit, `--cache-dir must be a directory path`, and no `run_scan()` call.
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
