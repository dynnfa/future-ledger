"""Pipeline orchestration for the dividend scan."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from future_ledger.cache import cache_key, cache_snapshot_paths, write_cache, write_metadata
from future_ledger.domain import (
    DividendRecord,
    PricePoint,
    ReportTables,
    RunConfig,
    SourceErrorRow,
    SourceFetchResult,
    SourceMetadata,
)
from future_ledger.metrics.dividend_yield import (
    DIVIDEND_YIELD_SOURCE,
    calculate_dividend_yield,
    resolve_reference_price,
)
from future_ledger.metrics.returns import calculate_trailing_one_year_return
from future_ledger.normalize.dividends import normalize_dividend_detail
from future_ledger.normalize.prices import normalize_price_history
from future_ledger.report_assembly import (
    DividendMetricInput,
    ReturnMetricInput,
    assemble_report_tables,
)
from future_ledger.sources.akshare_client import (
    fetch_a_share_spot,
    fetch_dividend_detail,
    fetch_price_history,
)
from future_ledger.sources.universe import build_universe


def run_scan(config: RunConfig) -> ReportTables:
    """Execute the full local dividend scan and return assembled report tables."""
    source_errors: list[SourceErrorRow] = []
    source_metadata: list[SourceMetadata] = []
    all_dividends: list[DividendRecord] = []
    all_prices: list[PricePoint] = []
    dividend_metrics: list[DividendMetricInput] = []
    return_metrics: list[ReturnMetricInput] = []

    spot_result = fetch_a_share_spot()
    source_errors.extend(_source_errors_from_result(spot_result))
    source_metadata.append(spot_result.metadata)

    stocks, universe_errors = build_universe(
        spot_result.frame,
        universe=config.universe,
        limit=config.limit,
    )
    source_errors.extend(universe_errors)
    source_errors.extend(
        _write_raw_cache_snapshot(
            config=config,
            key=cache_key("spot", "all_a"),
            result=spot_result,
        )
    )

    start_date, end_date = _price_window(config.as_of, config.years)
    for stock in stocks:
        dividend_result = fetch_dividend_detail(stock.code)
        price_result = fetch_price_history(stock.code, start_date, end_date)

        source_errors.extend(_source_errors_from_result(dividend_result))
        source_errors.extend(_source_errors_from_result(price_result))

        source_errors.extend(
            _write_raw_cache_snapshot(
                config=config,
                key=cache_key("dividend_detail", stock.code),
                result=dividend_result,
            )
        )
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

        source_metadata.append(dividend_result.metadata)
        source_metadata.append(price_result.metadata)

        dividend_records, dividend_errors = normalize_dividend_detail(
            stock,
            dividend_result.frame,
        )
        price_points, price_errors = normalize_price_history(
            stock.code,
            price_result.frame,
            price_result.metadata,
        )
        source_errors.extend(dividend_errors)
        source_errors.extend(price_errors)

        all_dividends.extend(dividend_records)
        all_prices.extend(price_points)

        for record in dividend_records:
            reference = resolve_reference_price(price_points, record.ex_dividend_date)
            yield_result = calculate_dividend_yield(
                record.cash_dividend_per_share,
                reference.reference_price,
            )
            dividend_metrics.append(
                DividendMetricInput(
                    stock_code=record.stock_code,
                    report_period=record.report_period,
                    reference_price=reference.reference_price,
                    reference_price_date=reference.reference_price_date,
                    dividend_yield_pct=yield_result.dividend_yield_pct,
                    dividend_yield_source=DIVIDEND_YIELD_SOURCE,
                    data_quality_flags=yield_result.data_quality_flags,
                )
            )

        return_result = calculate_trailing_one_year_return(
            stock.code,
            config.as_of,
            price_points,
            dividend_records,
        )
        return_metrics.append(
            ReturnMetricInput(
                stock_code=stock.code,
                start_price_date=return_result.start_price_date,
                end_price_date=return_result.end_price_date,
                cash_dividends_1y=return_result.cash_dividends_1y,
                total_return_1y_pct=return_result.total_return_1y_pct,
                annualized_return_1y_pct=return_result.annualized_return_1y_pct,
                data_quality_flags=return_result.return_data_quality_flags,
            )
        )

    return assemble_report_tables(
        config=config,
        stocks=stocks,
        dividends=all_dividends,
        prices=all_prices,
        dividend_metrics=dividend_metrics,
        return_metrics=return_metrics,
        source_errors=source_errors,
        source_metadata=source_metadata,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


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
