# FutureLedger Module Spec Suite Wave 3: Source Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the raw cache, source fetching, and universe selection specs that define data-entry boundaries.

**Architecture:** Wave 3 can run Tasks 4, 5, and 9 in parallel. Cache, source fetching, and universe selection are independent boundary specs with disjoint files, but the controller should reconcile stage names and source error semantics after all three finish.

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

Dispatch all three tasks in parallel after Wave 2 has completed or once the controller confirms their source-boundary contracts do not depend on unfinished output specs.

```text
Task 4: 03-raw-cache
Task 5: 02-source-fetching
Task 9: 01-universe-selection
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
