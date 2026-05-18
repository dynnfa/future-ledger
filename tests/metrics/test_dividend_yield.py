from __future__ import annotations

from datetime import date
from decimal import Decimal

from future_ledger.domain import PricePoint
from future_ledger.metrics.dividend_yield import (
    DIVIDEND_YIELD_SOURCE,
    calculate_dividend_yield,
    resolve_reference_price,
)


def test_resolve_reference_price_uses_previous_trading_day() -> None:
    points = [
        _point(date(2025, 6, 30), "10.00"),
        _point(date(2025, 7, 2), "10.20"),
    ]

    result = resolve_reference_price(points, ex_dividend_date=date(2025, 7, 1))

    assert result.reference_price == Decimal("10.00")
    assert result.reference_price_date == date(2025, 6, 30)
    assert result.reference_price_rule == "ex_dividend_close_or_previous_trading_day"
    assert result.reference_price_fallback_used is True


def test_resolve_reference_price_uses_exact_ex_dividend_close_without_fallback() -> None:
    points = [
        _point(date(2025, 6, 30), "10.00"),
        _point(date(2025, 7, 1), "10.10"),
        _point(date(2025, 7, 2), "10.20"),
    ]

    result = resolve_reference_price(points, ex_dividend_date=date(2025, 7, 1))

    assert result.reference_price == Decimal("10.10")
    assert result.reference_price_date == date(2025, 7, 1)
    assert result.reference_price_rule == "ex_dividend_close_or_previous_trading_day"
    assert result.reference_price_fallback_used is False


def test_resolve_reference_price_returns_empty_result_when_no_eligible_close_exists() -> None:
    points = [
        _point(date(2025, 7, 2), "10.20"),
    ]

    result = resolve_reference_price(points, ex_dividend_date=date(2025, 7, 1))

    assert result.reference_price is None
    assert result.reference_price_date is None
    assert result.reference_price_rule == "ex_dividend_close_or_previous_trading_day"
    assert result.reference_price_fallback_used is False


def test_calculate_dividend_yield_quantizes_to_two_decimals() -> None:
    result = calculate_dividend_yield(
        cash_dividend_per_share=Decimal("0.41"),
        reference_price=Decimal("10.00"),
    )

    assert result.dividend_yield_pct == Decimal("4.10")
    assert result.data_quality_flags == ()
    assert DIVIDEND_YIELD_SOURCE == "calculated_ex_dividend_close"


def test_calculate_dividend_yield_flags_missing_cash_dividend() -> None:
    result = calculate_dividend_yield(
        cash_dividend_per_share=None,
        reference_price=Decimal("10.00"),
    )

    assert result.dividend_yield_pct is None
    assert result.data_quality_flags == ("missing_cash_dividend",)


def test_calculate_dividend_yield_flags_missing_reference_price() -> None:
    result = calculate_dividend_yield(
        cash_dividend_per_share=Decimal("0.41"),
        reference_price=None,
    )

    assert result.dividend_yield_pct is None
    assert result.data_quality_flags == ("missing_reference_price",)


def test_calculate_dividend_yield_flags_all_missing_inputs_in_stable_order() -> None:
    result = calculate_dividend_yield(
        cash_dividend_per_share=None,
        reference_price=None,
    )

    assert result.dividend_yield_pct is None
    assert result.data_quality_flags == (
        "missing_cash_dividend",
        "missing_reference_price",
    )


def _point(point_date: date, close: str) -> PricePoint:
    return PricePoint(
        stock_code="600000",
        date=point_date,
        close=Decimal(close),
    )
