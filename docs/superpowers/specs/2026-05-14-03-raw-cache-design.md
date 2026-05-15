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
- `stage: str` with one of the cache stages `spot`, `dividend_detail`, or `price_history`.
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
- Cache stage names are storage locations, distinct from source metadata stages `spot_fetch`, `dividend_fetch`, and `price_fetch`, which are preserved inside metadata sidecars.
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
