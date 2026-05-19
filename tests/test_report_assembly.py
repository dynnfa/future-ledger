from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from future_ledger.domain import (
    DividendRecord,
    PricePoint,
    RunConfig,
    SourceErrorRow,
    SourceMetadata,
    StockIdentity,
)
from future_ledger.report_assembly import (
    DividendMetricInput,
    ReturnMetricInput,
    assemble_report_tables,
)

ANNUAL_SUFFIXES = (
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


def test_assemble_report_tables_ranks_by_latest_yield() -> None:
    stocks = [
        _stock("600000", "浦发银行", "SH"),
        _stock("000001", "平安银行", "SZ"),
    ]
    dividends = [
        _dividend("600000", "浦发银行", "SH", 2025, "0.50"),
        _dividend("000001", "平安银行", "SZ", 2025, "0.40"),
    ]
    dividend_metrics = [
        _dividend_metric("600000", 2025, "5.00", "10.00"),
        _dividend_metric("000001", 2025, "4.00", "10.00"),
    ]

    tables = assemble_report_tables(
        config=_config(),
        stocks=stocks,
        dividends=dividends,
        prices=[
            _price("600000", date(2025, 7, 1), "10.00"),
            _price("000001", date(2025, 7, 1), "10.00"),
        ],
        dividend_metrics=dividend_metrics,
        return_metrics=[
            _return_metric("600000", "0.50", "8.25"),
            _return_metric("000001", "0.40", "6.10"),
        ],
        source_errors=[],
        source_metadata=[_source_metadata("600000"), _source_metadata("000001")],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    assert [row.stock_code for row in tables.dividend_rank] == ["600000", "000001"]
    assert [row.rank_latest_yield for row in tables.dividend_rank] == [1, 2]
    assert tables.dividend_rank[0].latest_dividend_yield_pct == Decimal("5.00")
    assert tables.dividend_rank[0].cash_dividends_1y == Decimal("0.50")
    assert tables.dividend_rank[0].total_return_1y_pct == Decimal("8.25")
    assert tables.dividend_rank[0].data_quality_flags == ("has_missing_years_5y",)


def test_assemble_report_tables_keeps_missing_yield_rows_unranked() -> None:
    stocks = [
        _stock("600000", "浦发银行", "SH"),
        _stock("000001", "平安银行", "SZ"),
    ]
    dividends = [
        _dividend("600000", "浦发银行", "SH", 2025, "0.50"),
        _dividend("000001", "平安银行", "SZ", 2025, "0.40"),
    ]

    tables = assemble_report_tables(
        config=_config(),
        stocks=stocks,
        dividends=dividends,
        prices=[_price("600000", date(2025, 7, 1), "10.00")],
        dividend_metrics=[
            _dividend_metric("600000", 2025, "5.00", "10.00"),
            _dividend_metric(
                "000001",
                2025,
                None,
                None,
                flags=("missing_reference_price",),
            ),
        ],
        return_metrics=[
            _return_metric("600000", "0.50", "8.25"),
            _return_metric("000001", "0.40", "6.10"),
        ],
        source_errors=[],
        source_metadata=[_source_metadata("600000"), _source_metadata("000001")],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    assert [row.stock_code for row in tables.dividend_rank] == ["600000", "000001"]
    missing_yield_row = tables.dividend_rank[1]
    assert missing_yield_row.rank_latest_yield is None
    assert missing_yield_row.latest_dividend_yield_pct is None
    assert "missing_reference_price" in missing_yield_row.data_quality_flags


def test_assemble_report_tables_expands_annual_fields_in_column_order() -> None:
    stock = _stock("600000", "浦发银行", "SH")
    dividends = [
        _dividend("600000", "浦发银行", "SH", 2025, "0.50"),
        _dividend("600000", "浦发银行", "SH", 2024, "0.45"),
        _dividend("600000", "浦发银行", "SH", 2023, "0.40"),
        _dividend("600000", "浦发银行", "SH", 2022, "0.35"),
        _dividend("600000", "浦发银行", "SH", 2021, "0.30"),
    ]

    tables = assemble_report_tables(
        config=_config(),
        stocks=[stock],
        dividends=dividends,
        prices=[_price("600000", date(year, 7, 1), "10.00") for year in range(2021, 2026)],
        dividend_metrics=[
            _dividend_metric("600000", 2025, "5.00", "10.00"),
            _dividend_metric("600000", 2024, "4.50", "10.00"),
            _dividend_metric("600000", 2023, "4.00", "10.00"),
            _dividend_metric("600000", 2022, "3.50", "10.00"),
            _dividend_metric("600000", 2021, "3.00", "10.00"),
        ],
        return_metrics=[_return_metric("600000", "0.50", "8.25")],
        source_errors=[],
        source_metadata=[_source_metadata("600000")],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    expected_keys = [
        f"{year}_{suffix}"
        for year in (2025, 2024, 2023, 2022, 2021)
        for suffix in ANNUAL_SUFFIXES
    ]
    row = tables.dividend_rank[0]
    assert list(row.annual_fields.keys()) == expected_keys
    assert row.annual_fields["2025_report_period"] == "2025-12-31"
    assert row.annual_fields["2025_dividend_yield_pct"] == Decimal("5.00")
    assert row.dividend_year_count_5y == 5
    assert row.continuous_dividend_5y is True
    assert row.has_missing_years_5y is False
    assert row.data_quality_flags == ()


def test_assemble_report_tables_long_rows_mirror_annual_window_records() -> None:
    stock = _stock("600000", "浦发银行", "SH")
    dividends = [
        _dividend("600000", "浦发银行", "SH", 2025, "0.50"),
        _dividend("600000", "浦发银行", "SH", 2024, "0.45"),
        _dividend("600000", "浦发银行", "SH", 2023, "0.40"),
        _dividend("600000", "浦发银行", "SH", 2020, "0.25"),
    ]

    tables = assemble_report_tables(
        config=_config(years=3),
        stocks=[stock],
        dividends=dividends,
        prices=[_price("600000", date(year, 7, 1), "10.00") for year in range(2023, 2026)],
        dividend_metrics=[
            _dividend_metric("600000", 2025, "5.00", "10.00"),
            _dividend_metric("600000", 2024, "4.50", "10.00"),
            _dividend_metric("600000", 2023, "4.00", "10.00"),
            _dividend_metric("600000", 2020, "2.50", "10.00"),
        ],
        return_metrics=[_return_metric("600000", "0.50", "8.25")],
        source_errors=[],
        source_metadata=[_source_metadata("600000")],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    assert [row.report_year for row in tables.dividend_long] == [2025, 2024, 2023]
    assert [row.dividend_yield_pct for row in tables.dividend_long] == [
        Decimal("5.00"),
        Decimal("4.50"),
        Decimal("4.00"),
    ]
    assert "2020_report_period" not in tables.dividend_rank[0].annual_fields


def test_assemble_report_tables_carries_source_errors_metadata_and_used_prices() -> None:
    stock = _stock("600000", "浦发银行", "SH")
    source_error = SourceErrorRow(
        stock_code="600000",
        stage="dividend_fetch",
        message="empty upstream frame",
        raw_detail=None,
    )

    tables = assemble_report_tables(
        config=_config(limit=1),
        stocks=[stock],
        dividends=[],
        prices=[
            _price("600000", date(2025, 4, 21), "9.50"),
            _price("600000", date(2026, 4, 17), "10.20"),
            _price("600000", date(2025, 8, 8), "11.00"),
        ],
        dividend_metrics=[],
        return_metrics=[
            ReturnMetricInput(
                stock_code="600000",
                start_price_date=date(2025, 4, 21),
                end_price_date=date(2026, 4, 17),
                cash_dividends_1y=None,
                total_return_1y_pct=None,
                annualized_return_1y_pct=None,
                data_quality_flags=("uncertain_dividend_window",),
            )
        ],
        source_errors=[source_error],
        source_metadata=[_source_metadata("600000")],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    assert tables.source_errors == [source_error]
    assert [(point.stock_code, point.date) for point in tables.price_points] == [
        ("600000", date(2025, 4, 21)),
        ("600000", date(2026, 4, 17)),
    ]

    row = tables.dividend_rank[0]
    assert row.rank_latest_yield is None
    assert row.data_quality_flags == (
        "no_valid_dividend_records",
        "has_missing_years_5y",
        "uncertain_dividend_window",
        "empty_dividend_detail",
    )

    metadata = {item.key: item.value for item in tables.metadata}
    assert metadata["years"] == "5"
    assert metadata["as_of"] == "2026-04-20"
    assert metadata["universe"] == "all-a-excluding-st"
    assert metadata["limit"] == "1"
    assert metadata["cache_dir"] == ".future_ledger/cache"
    assert metadata["source_priority"] == "akshare.stock_fhps_detail_em"
    assert metadata["generated_at"] == "2026-04-20T08:30:00+08:00"
    assert metadata["akshare_version"] == "1.17.0"
    assert metadata["disclaimer"] == "Research only; not investment advice."
    assert metadata["source.dividend_fetch.600000.row_count"] == "3"


def test_assemble_report_tables_covers_required_data_quality_flags() -> None:
    stocks = [
        _stock("600000", "浦发银行", "SH"),
        _stock("000001", "平安银行", "SZ"),
    ]
    dividends = [
        DividendRecord(
            stock_code="000001",
            stock_name="平安银行",
            market="SZ",
            report_year=2025,
            report_period="2025-12-31",
            cash_dividend_per_10_shares=None,
            cash_dividend_per_share=None,
            ex_dividend_date=None,
            registration_date=None,
            plan_status="实施",
            eps=None,
            net_asset_per_share=None,
            profit_growth_yoy_pct=None,
            provider_yield_pct=None,
            source="akshare.stock_fhps_detail_em",
        )
    ]
    source_errors = [
        SourceErrorRow(
            stock_code="600000",
            stage="dividend_fetch",
            message="empty upstream frame",
            raw_detail=None,
        ),
        SourceErrorRow(
            stock_code="000001",
            stage="dividend_normalize",
            message="duplicate report period",
            raw_detail="{'报告期': '2025-12-31'}",
        ),
    ]

    tables = assemble_report_tables(
        config=_config(),
        stocks=stocks,
        dividends=dividends,
        prices=[],
        dividend_metrics=[
            DividendMetricInput(
                stock_code="000001",
                report_period="2025-12-31",
                reference_price=None,
                reference_price_date=None,
                dividend_yield_pct=None,
                dividend_yield_source="calculated_ex_dividend_close",
                data_quality_flags=("missing_reference_price",),
            )
        ],
        return_metrics=[
            ReturnMetricInput(
                stock_code="000001",
                start_price_date=None,
                end_price_date=None,
                cash_dividends_1y=None,
                total_return_1y_pct=None,
                annualized_return_1y_pct=None,
                data_quality_flags=(
                    "missing_return_price",
                    "uncertain_dividend_window",
                    "invalid_return_start_price",
                ),
            )
        ],
        source_errors=source_errors,
        source_metadata=[_source_metadata("600000"), _source_metadata("000001")],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    observed_flags = {
        flag
        for row in tables.dividend_rank
        for flag in row.data_quality_flags
    }

    assert observed_flags >= {
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
    }


def _config(years: int = 5, limit: int | None = None) -> RunConfig:
    return RunConfig(
        years=years,
        as_of=date(2026, 4, 20),
        universe="all-a-excluding-st",
        output=Path("reports/dividend_rank.xlsx"),
        limit=limit,
        cache_dir=Path(".future_ledger/cache"),
    )


def _stock(code: str, name: str, market: str) -> StockIdentity:
    return StockIdentity(code=code, name=name, market=market)


def _dividend(
    code: str,
    name: str,
    market: str,
    report_year: int,
    cash_dividend_per_share: str | None,
) -> DividendRecord:
    per_share = Decimal(cash_dividend_per_share) if cash_dividend_per_share is not None else None
    return DividendRecord(
        stock_code=code,
        stock_name=name,
        market=market,
        report_year=report_year,
        report_period=f"{report_year}-12-31",
        cash_dividend_per_10_shares=per_share * Decimal("10") if per_share is not None else None,
        cash_dividend_per_share=per_share,
        ex_dividend_date=date(report_year, 7, 1),
        registration_date=date(report_year, 6, 30),
        plan_status="实施",
        eps=Decimal("2.10"),
        net_asset_per_share=Decimal("18.50"),
        profit_growth_yoy_pct=Decimal("5.30"),
        provider_yield_pct=None,
        source="akshare.stock_fhps_detail_em",
    )


def _price(code: str, point_date: date, close: str) -> PricePoint:
    return PricePoint(stock_code=code, date=point_date, close=Decimal(close))


def _dividend_metric(
    code: str,
    report_year: int,
    dividend_yield_pct: str | None,
    reference_price: str | None,
    flags: tuple[str, ...] = (),
) -> DividendMetricInput:
    return DividendMetricInput(
        stock_code=code,
        report_period=f"{report_year}-12-31",
        reference_price=Decimal(reference_price) if reference_price is not None else None,
        reference_price_date=date(report_year, 7, 1) if reference_price is not None else None,
        dividend_yield_pct=Decimal(dividend_yield_pct) if dividend_yield_pct is not None else None,
        dividend_yield_source="calculated_ex_dividend_close",
        data_quality_flags=flags,
    )


def _return_metric(
    code: str,
    cash_dividends_1y: str | None,
    total_return_1y_pct: str | None,
    flags: tuple[str, ...] = (),
) -> ReturnMetricInput:
    return ReturnMetricInput(
        stock_code=code,
        start_price_date=date(2025, 4, 21),
        end_price_date=date(2026, 4, 17),
        cash_dividends_1y=Decimal(cash_dividends_1y) if cash_dividends_1y is not None else None,
        total_return_1y_pct=(
            Decimal(total_return_1y_pct) if total_return_1y_pct is not None else None
        ),
        annualized_return_1y_pct=(
            Decimal(total_return_1y_pct) if total_return_1y_pct is not None else None
        ),
        data_quality_flags=flags,
    )


def _source_metadata(symbol: str) -> SourceMetadata:
    return SourceMetadata(
        source_name="akshare",
        stage="dividend_fetch",
        symbol=symbol,
        fetched_at="2026-04-20T08:20:00+08:00",
        akshare_version="1.17.0",
        row_count=3,
        upstream_function="stock_fhps_detail_em",
        request_start_date=None,
        request_end_date=None,
    )
