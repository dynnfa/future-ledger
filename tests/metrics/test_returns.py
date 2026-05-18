from __future__ import annotations

from datetime import date
from decimal import Decimal

from future_ledger.domain import DividendRecord, PricePoint
from future_ledger.metrics.returns import calculate_trailing_one_year_return


def test_calculate_trailing_one_year_return_uses_window_price_fallbacks() -> None:
    prices = [
        _price(date(2025, 4, 21), "10.00"),
        _price(date(2026, 4, 17), "10.80"),
    ]
    dividends = [
        _dividend(
            report_year=2025,
            cash_dividend_per_share=Decimal("0.41"),
            ex_dividend_date=date(2025, 7, 1),
        )
    ]

    result = calculate_trailing_one_year_return(
        stock_code="600000",
        as_of=date(2026, 4, 18),
        prices=prices,
        dividends=dividends,
    )

    assert result.as_of_date == date(2026, 4, 18)
    assert result.return_window_start == date(2025, 4, 18)
    assert result.return_window_end == date(2026, 4, 18)
    assert result.start_close_price == Decimal("10.00")
    assert result.start_price_date == date(2025, 4, 21)
    assert result.end_close_price == Decimal("10.80")
    assert result.end_price_date == date(2026, 4, 17)
    assert result.cash_dividends_1y == Decimal("0.41")
    assert result.total_return_1y_pct == Decimal("12.10")
    assert result.annualized_return_1y_pct == Decimal("12.10")
    assert result.return_data_quality_flags == ()


def test_calculate_trailing_one_year_return_handles_february_29() -> None:
    prices = [
        _price(date(2023, 2, 28), "10.00"),
        _price(date(2024, 2, 29), "11.00"),
    ]

    result = calculate_trailing_one_year_return(
        stock_code="600000",
        as_of=date(2024, 2, 29),
        prices=prices,
        dividends=[],
    )

    assert result.return_window_start == date(2023, 2, 28)
    assert result.return_window_end == date(2024, 2, 29)
    assert result.start_price_date == date(2023, 2, 28)
    assert result.end_price_date == date(2024, 2, 29)
    assert result.cash_dividends_1y == Decimal("0")
    assert result.total_return_1y_pct == Decimal("10.00")
    assert result.annualized_return_1y_pct == Decimal("10.00")
    assert result.return_data_quality_flags == ()


def test_calculate_trailing_one_year_return_flags_uncertain_dividend_window() -> None:
    prices = [
        _price(date(2025, 1, 1), "10.00"),
        _price(date(2026, 1, 1), "11.00"),
    ]
    dividends = [
        _dividend(
            report_year=2025,
            cash_dividend_per_share=Decimal("0.40"),
            ex_dividend_date=date(2025, 7, 1),
        ),
        _dividend(
            report_year=2024,
            cash_dividend_per_share=None,
            ex_dividend_date=None,
        ),
    ]

    result = calculate_trailing_one_year_return(
        stock_code="600000",
        as_of=date(2026, 1, 1),
        prices=prices,
        dividends=dividends,
    )

    assert result.cash_dividends_1y == Decimal("0.40")
    assert result.total_return_1y_pct == Decimal("14.00")
    assert result.annualized_return_1y_pct == Decimal("14.00")
    assert result.return_data_quality_flags == ("uncertain_dividend_window",)


def test_calculate_trailing_one_year_return_flags_missing_price_window() -> None:
    result = calculate_trailing_one_year_return(
        stock_code="600000",
        as_of=date(2026, 4, 18),
        prices=[],
        dividends=[],
    )

    assert result.return_window_start == date(2025, 4, 18)
    assert result.start_close_price is None
    assert result.start_price_date is None
    assert result.end_close_price is None
    assert result.end_price_date is None
    assert result.cash_dividends_1y is None
    assert result.total_return_1y_pct is None
    assert result.annualized_return_1y_pct is None
    assert result.return_data_quality_flags == ("missing_return_price",)


def test_calculate_trailing_one_year_return_flags_invalid_start_price() -> None:
    prices = [
        _price(date(2025, 1, 1), "0"),
        _price(date(2026, 1, 1), "11.00"),
    ]

    result = calculate_trailing_one_year_return(
        stock_code="600000",
        as_of=date(2026, 1, 1),
        prices=prices,
        dividends=[],
    )

    assert result.start_close_price is None
    assert result.start_price_date is None
    assert result.end_close_price is None
    assert result.end_price_date is None
    assert result.cash_dividends_1y is None
    assert result.total_return_1y_pct is None
    assert result.annualized_return_1y_pct is None
    assert result.return_data_quality_flags == ("invalid_return_start_price",)


def _price(point_date: date, close: str) -> PricePoint:
    return PricePoint(
        stock_code="600000",
        date=point_date,
        close=Decimal(close),
    )


def _dividend(
    *,
    report_year: int,
    cash_dividend_per_share: Decimal | None,
    ex_dividend_date: date | None,
) -> DividendRecord:
    cash_dividend_per_10_shares = (
        cash_dividend_per_share * Decimal("10")
        if cash_dividend_per_share is not None
        else None
    )
    return DividendRecord(
        stock_code="600000",
        stock_name="浦发银行",
        market="SH",
        report_year=report_year,
        report_period=f"{report_year}-12-31",
        cash_dividend_per_10_shares=cash_dividend_per_10_shares,
        cash_dividend_per_share=cash_dividend_per_share,
        ex_dividend_date=ex_dividend_date,
        registration_date=None,
        plan_status="实施",
        eps=None,
        net_asset_per_share=None,
        profit_growth_yoy_pct=None,
        provider_yield_pct=None,
        source="akshare.stock_fhps_detail_em",
    )
