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
