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
