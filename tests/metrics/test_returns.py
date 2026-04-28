from __future__ import annotations

from datetime import date
from decimal import Decimal

from future_ledger.domain import DividendRecord, PricePoint
from future_ledger.metrics.returns import calculate_trailing_one_year_return


def test_calculate_trailing_one_year_return_uses_window_price_fallbacks() -> None:
    prices = [
        PricePoint(stock_code="600000", date=date(2025, 4, 21), close=Decimal("10.00")),
        PricePoint(stock_code="600000", date=date(2026, 4, 17), close=Decimal("10.80")),
    ]
    dividends = [
        DividendRecord(
            stock_code="600000",
            stock_name="浦发银行",
            market="SH",
            report_year=2025,
            report_period="2025-12-31",
            cash_dividend_per_10_shares=Decimal("4.10"),
            cash_dividend_per_share=Decimal("0.41"),
            ex_dividend_date=date(2025, 7, 1),
            registration_date=None,
            plan_status="实施",
            eps=None,
            net_asset_per_share=None,
            profit_growth_yoy_pct=None,
            provider_yield_pct=None,
            source="akshare.stock_fhps_detail_em",
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


def test_calculate_trailing_one_year_return_flags_missing_price_window() -> None:
    result = calculate_trailing_one_year_return(
        stock_code="600000",
        as_of=date(2026, 4, 18),
        prices=[],
        dividends=[],
    )

    assert result.start_close_price is None
    assert result.end_close_price is None
    assert result.cash_dividends_1y is None
    assert result.total_return_1y_pct is None
    assert result.annualized_return_1y_pct is None
    assert result.return_data_quality_flags == ("missing_return_price",)
