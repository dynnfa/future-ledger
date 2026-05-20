from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any

from future_ledger.domain import (
    DividendLongRow,
    DividendRankRow,
    DividendRecord,
    MetadataRow,
    PricePoint,
    ReportTables,
    RunConfig,
    SourceErrorRow,
    SourceMetadata,
    StockIdentity,
)

SOURCE_PRIORITY_USED = "akshare.stock_fhps_detail_em"
REPORT_DISCLAIMER = "Research only; not investment advice."

ANNUAL_FIELD_SUFFIXES = (
    "report_period",
    "cash_dividend_per_10_shares",
    "cash_dividend_per_share",
    "reference_price",
    "reference_price_date",
    "dividend_yield_pct",
    "registration_date",
    "ex_dividend_date",
    "plan_status",
    "eps",
    "net_asset_per_share",
    "profit_growth_yoy_pct",
    "source",
)

DATA_QUALITY_FLAG_ORDER = (
    "no_valid_dividend_records",
    "has_missing_years_5y",
    "missing_cash_dividend",
    "missing_ex_dividend_date",
    "missing_reference_price",
    "missing_return_price",
    "uncertain_dividend_window",
    "invalid_return_start_price",
    "duplicate_report_period",
    "empty_dividend_detail",
)


@dataclass(frozen=True)
class DividendMetricInput:
    stock_code: str
    report_period: str
    reference_price: Decimal | None
    reference_price_date: date | None
    dividend_yield_pct: Decimal | None
    dividend_yield_source: str
    data_quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReturnMetricInput:
    stock_code: str
    start_price_date: date | None
    end_price_date: date | None
    cash_dividends_1y: Decimal | None
    total_return_1y_pct: Decimal | None
    annualized_return_1y_pct: Decimal | None
    data_quality_flags: tuple[str, ...] = ()


def assemble_report_tables(
    *,
    config: RunConfig,
    stocks: Sequence[StockIdentity],
    dividends: Sequence[DividendRecord],
    prices: Sequence[PricePoint],
    dividend_metrics: Sequence[DividendMetricInput],
    return_metrics: Sequence[ReturnMetricInput],
    source_errors: Sequence[SourceErrorRow],
    source_metadata: Sequence[SourceMetadata],
    generated_at: str,
) -> ReportTables:
    _require_sequence_type(stocks, StockIdentity, "stocks")
    _require_sequence_type(dividends, DividendRecord, "dividends")
    _require_sequence_type(prices, PricePoint, "prices")
    _require_sequence_type(dividend_metrics, DividendMetricInput, "dividend_metrics")
    _require_sequence_type(return_metrics, ReturnMetricInput, "return_metrics")
    _require_sequence_type(source_errors, SourceErrorRow, "source_errors")
    _require_sequence_type(source_metadata, SourceMetadata, "source_metadata")

    stock_order = {stock.code: index for index, stock in enumerate(stocks)}
    dividends_by_stock = _dividends_by_stock(stocks, dividends)
    dividend_metric_by_key = {
        (metric.stock_code, metric.report_period): metric for metric in dividend_metrics
    }
    return_metric_by_stock = {metric.stock_code: metric for metric in return_metrics}
    source_errors_by_stock = _source_errors_by_stock(source_errors)
    fetched_at_by_stock = _fetched_at_by_stock(source_metadata)

    rank_rows: list[DividendRankRow] = []
    long_rows: list[DividendLongRow] = []

    for stock in stocks:
        window_records = _window_records(dividends_by_stock[stock.code], config)
        stock_return_metric = return_metric_by_stock.get(stock.code)
        stock_error_flags = _flags_from_source_errors(source_errors_by_stock.get(stock.code, []))
        rank_rows.append(
            _rank_row(
                stock=stock,
                config=config,
                window_records=window_records,
                dividend_metric_by_key=dividend_metric_by_key,
                return_metric=stock_return_metric,
                source_error_flags=stock_error_flags,
                fetched_at=fetched_at_by_stock.get(stock.code, generated_at),
            )
        )
        long_rows.extend(_long_rows(window_records, dividend_metric_by_key))

    return ReportTables(
        dividend_rank=_rank_rows(rank_rows, stock_order),
        dividend_long=long_rows,
        price_points=_used_price_points(prices, dividend_metrics, return_metrics, stock_order),
        source_errors=list(source_errors),
        metadata=_metadata_rows(config, source_metadata, generated_at),
    )


def _require_sequence_type(
    values: Sequence[object],
    expected_type: type[Any],
    name: str,
) -> None:
    for value in values:
        if not isinstance(value, expected_type):
            raise TypeError(f"{name} must contain {expected_type.__name__} values")


def _dividends_by_stock(
    stocks: Sequence[StockIdentity],
    dividends: Sequence[DividendRecord],
) -> dict[str, list[DividendRecord]]:
    grouped: dict[str, list[DividendRecord]] = {stock.code: [] for stock in stocks}
    for record in dividends:
        if record.stock_code in grouped:
            grouped[record.stock_code].append(record)
    return grouped


def _window_records(records: Sequence[DividendRecord], config: RunConfig) -> list[DividendRecord]:
    expected_years = set(_expected_report_years(config))
    selected = [record for record in records if record.report_year in expected_years]
    return sorted(
        selected,
        key=lambda record: (record.report_year, record.report_period),
        reverse=True,
    )[: config.years]


def _expected_report_years(config: RunConfig) -> tuple[int, ...]:
    latest_report_year = config.as_of.year - 1
    return tuple(range(latest_report_year, latest_report_year - config.years, -1))


def _rank_row(
    *,
    stock: StockIdentity,
    config: RunConfig,
    window_records: Sequence[DividendRecord],
    dividend_metric_by_key: dict[tuple[str, str], DividendMetricInput],
    return_metric: ReturnMetricInput | None,
    source_error_flags: Sequence[str],
    fetched_at: str,
) -> DividendRankRow:
    latest_record = window_records[0] if window_records else None
    latest_metric = (
        dividend_metric_by_key.get((stock.code, latest_record.report_period))
        if latest_record is not None
        else None
    )
    yield_values = _yield_values(window_records, dividend_metric_by_key)
    has_missing_years = len({record.report_year for record in window_records}) < config.years

    return DividendRankRow(
        rank_latest_yield=None,
        stock_code=stock.code,
        stock_name=stock.name,
        market=stock.market,
        latest_report_year=latest_record.report_year if latest_record is not None else None,
        latest_cash_dividend_per_10_shares=(
            latest_record.cash_dividend_per_10_shares if latest_record is not None else None
        ),
        latest_cash_dividend_per_share=(
            latest_record.cash_dividend_per_share if latest_record is not None else None
        ),
        reference_price=latest_metric.reference_price if latest_metric is not None else None,
        reference_price_date=(
            latest_metric.reference_price_date if latest_metric is not None else None
        ),
        latest_dividend_yield_pct=(
            latest_metric.dividend_yield_pct if latest_metric is not None else None
        ),
        dividend_yield_source=(
            latest_metric.dividend_yield_source if latest_metric is not None else ""
        ),
        dividend_year_count_5y=sum(
            1 for record in window_records if record.cash_dividend_per_share is not None
        ),
        continuous_dividend_5y=_continuous_dividend(window_records, config),
        avg_dividend_yield_pct_5y=_avg_decimal(yield_values),
        min_dividend_yield_pct_5y=min(yield_values) if yield_values else None,
        max_dividend_yield_pct_5y=max(yield_values) if yield_values else None,
        as_of_date=config.as_of,
        cash_dividends_1y=return_metric.cash_dividends_1y if return_metric is not None else None,
        total_return_1y_pct=(
            return_metric.total_return_1y_pct if return_metric is not None else None
        ),
        annualized_return_1y_pct=(
            return_metric.annualized_return_1y_pct if return_metric is not None else None
        ),
        has_missing_years_5y=has_missing_years,
        data_quality_flags=_data_quality_flags(
            config=config,
            window_records=window_records,
            dividend_metric_by_key=dividend_metric_by_key,
            return_metric=return_metric,
            source_error_flags=source_error_flags,
            has_missing_years=has_missing_years,
        ),
        source_priority_used=SOURCE_PRIORITY_USED,
        fetched_at=fetched_at,
        annual_fields=_annual_fields(window_records, dividend_metric_by_key),
    )


def _yield_values(
    window_records: Sequence[DividendRecord],
    dividend_metric_by_key: dict[tuple[str, str], DividendMetricInput],
) -> list[Decimal]:
    values: list[Decimal] = []
    for record in window_records:
        metric = dividend_metric_by_key.get((record.stock_code, record.report_period))
        if metric is not None and metric.dividend_yield_pct is not None:
            values.append(metric.dividend_yield_pct)
    return values


def _avg_decimal(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _continuous_dividend(records: Sequence[DividendRecord], config: RunConfig) -> bool:
    record_by_year = {record.report_year: record for record in records}
    return all(
        year in record_by_year and record_by_year[year].cash_dividend_per_share is not None
        for year in _expected_report_years(config)
    )


def _data_quality_flags(
    *,
    config: RunConfig,
    window_records: Sequence[DividendRecord],
    dividend_metric_by_key: dict[tuple[str, str], DividendMetricInput],
    return_metric: ReturnMetricInput | None,
    source_error_flags: Sequence[str],
    has_missing_years: bool,
) -> tuple[str, ...]:
    flags: list[str] = []
    if not window_records:
        flags.append("no_valid_dividend_records")
    if has_missing_years:
        flags.append("has_missing_years_5y")

    for record in window_records:
        if record.cash_dividend_per_share is None:
            flags.append("missing_cash_dividend")
        if record.ex_dividend_date is None:
            flags.append("missing_ex_dividend_date")
        metric = dividend_metric_by_key.get((record.stock_code, record.report_period))
        if metric is not None:
            flags.extend(metric.data_quality_flags)

    if return_metric is not None:
        flags.extend(return_metric.data_quality_flags)
    flags.extend(source_error_flags)
    return _ordered_flags(flags)


def _ordered_flags(flags: Sequence[str]) -> tuple[str, ...]:
    seen = set(flags)
    ordered = [flag for flag in DATA_QUALITY_FLAG_ORDER if flag in seen]
    ordered.extend(flag for flag in flags if flag not in DATA_QUALITY_FLAG_ORDER)
    deduped: list[str] = []
    for flag in ordered:
        if flag not in deduped:
            deduped.append(flag)
    return tuple(deduped)


def _annual_fields(
    window_records: Sequence[DividendRecord],
    dividend_metric_by_key: dict[tuple[str, str], DividendMetricInput],
) -> dict[str, object]:
    fields: dict[str, object] = {}
    for record in window_records:
        metric = dividend_metric_by_key.get((record.stock_code, record.report_period))
        values = {
            "report_period": record.report_period,
            "cash_dividend_per_10_shares": record.cash_dividend_per_10_shares,
            "cash_dividend_per_share": record.cash_dividend_per_share,
            "reference_price": metric.reference_price if metric is not None else None,
            "reference_price_date": metric.reference_price_date if metric is not None else None,
            "dividend_yield_pct": metric.dividend_yield_pct if metric is not None else None,
            "registration_date": record.registration_date,
            "ex_dividend_date": record.ex_dividend_date,
            "plan_status": record.plan_status,
            "eps": record.eps,
            "net_asset_per_share": record.net_asset_per_share,
            "profit_growth_yoy_pct": record.profit_growth_yoy_pct,
            "source": record.source,
        }
        for suffix in ANNUAL_FIELD_SUFFIXES:
            fields[f"{record.report_year}_{suffix}"] = values[suffix]
    return fields


def _long_rows(
    window_records: Sequence[DividendRecord],
    dividend_metric_by_key: dict[tuple[str, str], DividendMetricInput],
) -> list[DividendLongRow]:
    rows: list[DividendLongRow] = []
    for record in window_records:
        metric = dividend_metric_by_key.get((record.stock_code, record.report_period))
        rows.append(
            DividendLongRow(
                stock_code=record.stock_code,
                stock_name=record.stock_name,
                market=record.market,
                report_year=record.report_year,
                report_period=record.report_period,
                cash_dividend_per_10_shares=record.cash_dividend_per_10_shares,
                cash_dividend_per_share=record.cash_dividend_per_share,
                ex_dividend_date=record.ex_dividend_date,
                registration_date=record.registration_date,
                plan_status=record.plan_status,
                eps=record.eps,
                net_asset_per_share=record.net_asset_per_share,
                profit_growth_yoy_pct=record.profit_growth_yoy_pct,
                dividend_yield_pct=(metric.dividend_yield_pct if metric is not None else None),
                source=record.source,
            )
        )
    return rows


def _rank_rows(
    rows: Sequence[DividendRankRow],
    stock_order: dict[str, int],
) -> list[DividendRankRow]:
    ranked_rows = [row for row in rows if row.latest_dividend_yield_pct is not None]
    ranked_rows.sort(
        key=lambda row: (-row.latest_dividend_yield_pct, stock_order[row.stock_code])  # type: ignore[operator]
    )

    ranked_with_numbers: list[DividendRankRow] = []
    current_rank = 0
    previous_yield: Decimal | None = None
    for row in ranked_rows:
        if row.latest_dividend_yield_pct != previous_yield:
            current_rank += 1
            previous_yield = row.latest_dividend_yield_pct
        ranked_with_numbers.append(replace(row, rank_latest_yield=current_rank))

    unranked_rows = [row for row in rows if row.latest_dividend_yield_pct is None]
    unranked_rows.sort(key=lambda row: stock_order[row.stock_code])
    return ranked_with_numbers + unranked_rows


def _used_price_points(
    prices: Sequence[PricePoint],
    dividend_metrics: Sequence[DividendMetricInput],
    return_metrics: Sequence[ReturnMetricInput],
    stock_order: dict[str, int],
) -> list[PricePoint]:
    used_keys: set[tuple[str, date]] = set()
    for metric in dividend_metrics:
        if metric.reference_price_date is not None:
            used_keys.add((metric.stock_code, metric.reference_price_date))
    for return_metric in return_metrics:
        if return_metric.start_price_date is not None:
            used_keys.add((return_metric.stock_code, return_metric.start_price_date))
        if return_metric.end_price_date is not None:
            used_keys.add((return_metric.stock_code, return_metric.end_price_date))

    selected = [point for point in prices if (point.stock_code, point.date) in used_keys]
    return sorted(
        selected,
        key=lambda point: (stock_order.get(point.stock_code, len(stock_order)), point.date),
    )


def _source_errors_by_stock(
    source_errors: Sequence[SourceErrorRow],
) -> dict[str, list[SourceErrorRow]]:
    grouped: dict[str, list[SourceErrorRow]] = {}
    for error in source_errors:
        grouped.setdefault(error.stock_code, []).append(error)
    return grouped


def _flags_from_source_errors(source_errors: Sequence[SourceErrorRow]) -> tuple[str, ...]:
    flags: list[str] = []
    for error in source_errors:
        if error.stage == "dividend_normalize" and error.message == "duplicate report period":
            flags.append("duplicate_report_period")
        if error.stage == "dividend_fetch" and error.message in {
            "empty upstream frame",
            "empty dividend detail",
        }:
            flags.append("empty_dividend_detail")
    return tuple(flags)


def _fetched_at_by_stock(source_metadata: Sequence[SourceMetadata]) -> dict[str, str]:
    fetched_at: dict[str, str] = {}
    for metadata in source_metadata:
        fetched_at[metadata.symbol] = metadata.fetched_at
    return fetched_at


def _metadata_rows(
    config: RunConfig,
    source_metadata: Sequence[SourceMetadata],
    generated_at: str,
) -> list[MetadataRow]:
    akshare_versions = sorted(
        {metadata.akshare_version for metadata in source_metadata if metadata.akshare_version}
    )
    rows = [
        MetadataRow(key="years", value=str(config.years)),
        MetadataRow(key="as_of", value=config.as_of.isoformat()),
        MetadataRow(key="universe", value=config.universe),
        MetadataRow(key="limit", value="" if config.limit is None else str(config.limit)),
        MetadataRow(key="cache_dir", value=str(config.cache_dir)),
        MetadataRow(key="source_priority", value=SOURCE_PRIORITY_USED),
        MetadataRow(key="generated_at", value=generated_at),
        MetadataRow(key="akshare_version", value=",".join(akshare_versions)),
        MetadataRow(key="disclaimer", value=REPORT_DISCLAIMER),
    ]
    for metadata in source_metadata:
        rows.extend(_source_metadata_rows(metadata))
    return rows


def _source_metadata_rows(metadata: SourceMetadata) -> list[MetadataRow]:
    prefix = f"source.{metadata.stage}.{metadata.symbol}"
    rows = [
        MetadataRow(key=f"{prefix}.source_name", value=metadata.source_name),
        MetadataRow(key=f"{prefix}.fetched_at", value=metadata.fetched_at),
        MetadataRow(key=f"{prefix}.akshare_version", value=metadata.akshare_version),
        MetadataRow(key=f"{prefix}.row_count", value=str(metadata.row_count)),
        MetadataRow(key=f"{prefix}.upstream_function", value=metadata.upstream_function),
    ]
    if metadata.request_start_date is not None:
        rows.append(
            MetadataRow(
                key=f"{prefix}.request_start_date",
                value=metadata.request_start_date,
            )
        )
    if metadata.request_end_date is not None:
        rows.append(
            MetadataRow(
                key=f"{prefix}.request_end_date",
                value=metadata.request_end_date,
            )
        )
    return rows
