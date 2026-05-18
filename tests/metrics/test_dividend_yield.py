from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import SourceMetadata
from future_ledger.metrics.dividend_yield import (
    calculate_dividend_yield,
    resolve_reference_price,
)
from future_ledger.normalize.prices import normalize_price_history


def test_resolve_reference_price_uses_previous_trading_day() -> None:
    frame = pd.DataFrame(
        [
            {"日期": "2025-06-30", "收盘": "10.00"},
            {"日期": "2025-07-02", "收盘": "10.20"},
        ]
    )
    points, errors = normalize_price_history("600000", frame, _metadata("600000"))
    assert errors == []

    result = resolve_reference_price(points, ex_dividend_date=date(2025, 7, 1))

    assert result.reference_price == Decimal("10.00")
    assert result.reference_price_date == date(2025, 6, 30)
    assert result.reference_price_rule == "ex_dividend_previous_close"
    assert result.reference_price_fallback_used is True


def test_resolve_reference_price_uses_exact_ex_dividend_close_without_fallback() -> None:
    frame = pd.DataFrame(
        [
            {"日期": "2025-06-30", "收盘": "10.00"},
            {"日期": "2025-07-01", "收盘": "10.10"},
        ]
    )
    points, errors = normalize_price_history("600000", frame, _metadata("600000"))
    assert errors == []

    result = resolve_reference_price(points, ex_dividend_date=date(2025, 7, 1))

    assert result.reference_price == Decimal("10.10")
    assert result.reference_price_date == date(2025, 7, 1)
    assert result.reference_price_fallback_used is False


def test_calculate_dividend_yield_returns_percent() -> None:
    result = calculate_dividend_yield(
        cash_dividend_per_share=Decimal("0.41"),
        reference_price=Decimal("10.00"),
    )

    assert result == Decimal("4.100")


def test_calculate_dividend_yield_returns_none_without_usable_inputs() -> None:
    assert calculate_dividend_yield(None, Decimal("10.00")) is None
    assert calculate_dividend_yield(Decimal("0.41"), None) is None
    assert calculate_dividend_yield(Decimal("0.41"), Decimal("0")) is None


def _metadata(symbol: str) -> SourceMetadata:
    return SourceMetadata(
        source_name="akshare",
        stage="price_fetch",
        symbol=symbol,
        fetched_at="2026-05-14T08:30:00+00:00",
        akshare_version="1.17.0",
        row_count=1,
        upstream_function="stock_zh_a_hist",
        request_start_date="20250630",
        request_end_date="20260417",
    )
