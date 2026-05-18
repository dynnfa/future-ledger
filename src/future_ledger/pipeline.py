"""Pipeline orchestration for the dividend scan.

Builds the stock universe, fetches raw source frames, writes raw cache
snapshots, and returns recoverable source/cache errors. Later specs extend
this module with normalization, metrics, report assembly, and workbook output.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from future_ledger.cache import cache_key, cache_snapshot_paths, write_cache, write_metadata
from future_ledger.domain import (
    MetadataRow,
    ReportTables,
    RunConfig,
    SourceErrorRow,
    SourceFetchResult,
)
from future_ledger.sources.akshare_client import (
    fetch_a_share_spot,
    fetch_dividend_detail,
    fetch_price_history,
)
from future_ledger.sources.universe import build_universe


def run_scan(config: RunConfig) -> ReportTables:
    """Execute the raw source-fetch and cache write-through part of the scan.

    Returns populated source errors even when individual stock cache writes
    fail. Report row assembly is implemented by later specs.
    """
    source_errors: list[SourceErrorRow] = []
    metadata_rows: list[MetadataRow] = []

    spot_result = fetch_a_share_spot()
    source_errors.extend(_source_errors_from_result(spot_result))
    source_errors.extend(
        _write_raw_cache_snapshot(
            config=config,
            key=cache_key("spot", "all_a"),
            result=spot_result,
        )
    )
    metadata_rows.extend(_metadata_rows_from_result(spot_result))

    if spot_result.frame.empty:
        return _empty_report(source_errors=source_errors, metadata_rows=metadata_rows)

    stocks, universe_errors = build_universe(
        spot_result.frame,
        universe=config.universe,
        limit=config.limit,
    )
    source_errors.extend(universe_errors)

    start_date, end_date = _price_window(config.as_of, config.years)
    for stock in stocks:
        dividend_result = fetch_dividend_detail(stock.code)
        source_errors.extend(_source_errors_from_result(dividend_result))
        source_errors.extend(
            _write_raw_cache_snapshot(
                config=config,
                key=cache_key("dividend_detail", stock.code),
                result=dividend_result,
            )
        )
        metadata_rows.extend(_metadata_rows_from_result(dividend_result))

        price_result = fetch_price_history(stock.code, start_date, end_date)
        source_errors.extend(_source_errors_from_result(price_result))
        source_errors.extend(
            _write_raw_cache_snapshot(
                config=config,
                key=cache_key(
                    "price_history",
                    stock.code,
                    start_date=start_date,
                    end_date=end_date,
                ),
                result=price_result,
            )
        )
        metadata_rows.extend(_metadata_rows_from_result(price_result))

    return _empty_report(source_errors=source_errors, metadata_rows=metadata_rows)


def _write_raw_cache_snapshot(
    *,
    config: RunConfig,
    key: str,
    result: SourceFetchResult,
) -> list[SourceErrorRow]:
    if not _is_cacheable(result):
        return []

    cache_path, metadata_path = cache_snapshot_paths(config.cache_dir, key)
    try:
        original_cache = _read_existing_bytes(cache_path)
        original_metadata = _read_existing_bytes(metadata_path)
    except OSError as exc:
        return [_cache_write_error(result, key, exc)]

    try:
        write_cache(config.cache_dir, key, result.frame)
        write_metadata(config.cache_dir, key, result.metadata, empty=result.frame.empty)
    except OSError as exc:
        _restore_cache_file(cache_path, original_cache)
        _restore_cache_file(metadata_path, original_metadata)
        return [_cache_write_error(result, key, exc)]
    return []


def _read_existing_bytes(path: Path) -> bytes | None:
    if not path.exists():
        return None
    return path.read_bytes()


def _restore_cache_file(path: Path, content: bytes | None) -> None:
    try:
        if content is None:
            path.unlink(missing_ok=True)
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    except OSError:
        return


def _cache_write_error(result: SourceFetchResult, key: str, exc: OSError) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=result.metadata.symbol,
        stage="cache_write",
        message=f"{exc.__class__.__name__}: {exc}",
        raw_detail=key,
    )


def _is_cacheable(result: SourceFetchResult) -> bool:
    if result.error is None:
        return True
    return result.error.message == "empty upstream frame"


def _source_errors_from_result(result: SourceFetchResult) -> list[SourceErrorRow]:
    if result.error is None:
        return []
    return [result.error]


def _metadata_rows_from_result(result: SourceFetchResult) -> list[MetadataRow]:
    prefix = f"source.{result.metadata.stage}.{result.metadata.symbol}"
    rows = [
        MetadataRow(key=f"{prefix}.source_name", value=result.metadata.source_name),
        MetadataRow(key=f"{prefix}.fetched_at", value=result.metadata.fetched_at),
        MetadataRow(key=f"{prefix}.akshare_version", value=result.metadata.akshare_version),
        MetadataRow(key=f"{prefix}.row_count", value=str(result.metadata.row_count)),
        MetadataRow(key=f"{prefix}.upstream_function", value=result.metadata.upstream_function),
    ]
    if result.metadata.request_start_date is not None:
        rows.append(
            MetadataRow(
                key=f"{prefix}.request_start_date",
                value=result.metadata.request_start_date,
            )
        )
    if result.metadata.request_end_date is not None:
        rows.append(
            MetadataRow(
                key=f"{prefix}.request_end_date",
                value=result.metadata.request_end_date,
            )
        )
    return rows


def _price_window(as_of: date, years: int) -> tuple[str, str]:
    start = _replace_year_with_feb_28_fallback(as_of, as_of.year - years)
    return _yyyymmdd(start), _yyyymmdd(as_of)


def _replace_year_with_feb_28_fallback(value: date, year: int) -> date:
    try:
        return value.replace(year=year)
    except ValueError:
        return value.replace(year=year, day=28)


def _yyyymmdd(value: date) -> str:
    return value.strftime("%Y%m%d")


def _empty_report(
    *,
    source_errors: list[SourceErrorRow],
    metadata_rows: list[MetadataRow],
) -> ReportTables:
    return ReportTables(
        dividend_rank=[],
        dividend_long=[],
        price_points=[],
        source_errors=source_errors,
        metadata=metadata_rows,
    )
