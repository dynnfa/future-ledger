from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest

from future_ledger.domain import SourceMetadata
from future_ledger.normalize.prices import normalize_price_history


def test_normalize_price_history_sorts_by_date() -> None:
    frame = pd.read_csv(
        Path("tests/fixtures/prices/600000_daily_20250630_20260417.csv")
    )

    points, errors = normalize_price_history("600000", frame, _metadata("600000"))

    assert errors == []
    assert [point.date for point in points] == [
        date(2025, 6, 30),
        date(2025, 7, 2),
        date(2026, 4, 17),
    ]
    assert points[0].stock_code == "600000"
    assert points[0].close == Decimal("10.00")


def test_normalize_price_history_accepts_date_variants_and_numeric_closes() -> None:
    frame = pd.DataFrame(
        [
            {"日期": "2025/07/01", "收盘": 10.25},
            {"日期": "2025-07-02 15:00:00", "收盘": Decimal("10.30")},
        ]
    )

    points, errors = normalize_price_history("600000", frame, _metadata("600000"))

    assert errors == []
    assert [(point.date, point.close) for point in points] == [
        (date(2025, 7, 1), Decimal("10.25")),
        (date(2025, 7, 2), Decimal("10.30")),
    ]


def test_normalize_price_history_reports_missing_date_and_close() -> None:
    frame = pd.DataFrame(
        [
            {"日期": "", "收盘": "10.00"},
            {"日期": "2025-07-01"},
            {"日期": "2025-07-02", "收盘": None},
        ]
    )

    points, errors = normalize_price_history("600000", frame, _metadata("600000"))

    assert points == []
    assert [(error.stage, error.message) for error in errors] == [
        ("price_normalize", "missing price date"),
        ("price_normalize", "missing close price"),
        ("price_normalize", "missing close price"),
    ]
    assert all(error.stock_code == "600000" for error in errors)
    assert all(error.raw_detail is not None for error in errors)


@pytest.mark.parametrize("close", ["0", "-0.01", Decimal("0"), Decimal("-2.25")])
def test_normalize_price_history_skips_non_positive_close(close: object) -> None:
    frame = pd.DataFrame([{"日期": "2025-07-01", "收盘": close}])

    points, errors = normalize_price_history("600000", frame, _metadata("600000"))

    assert points == []
    assert [(error.stage, error.message) for error in errors] == [
        ("price_normalize", "non-positive close price"),
    ]


def test_normalize_price_history_reports_invalid_date_and_close() -> None:
    frame = pd.DataFrame(
        [
            {"日期": "2025-02-30", "收盘": "10.00"},
            {"日期": "2025-07-01", "收盘": "not-a-price"},
            {"日期": "2025-07-02", "收盘": "NaN"},
        ]
    )

    points, errors = normalize_price_history("600000", frame, _metadata("600000"))

    assert points == []
    assert [(error.stage, error.message) for error in errors] == [
        ("price_normalize", "invalid price date"),
        ("price_normalize", "invalid close price"),
        ("price_normalize", "invalid close price"),
    ]


def test_normalize_price_history_deduplicates_same_close() -> None:
    frame = pd.DataFrame(
        [
            {"日期": "2025-07-01", "收盘": "10.00"},
            {"日期": "2025-07-01", "收盘": Decimal("10.00")},
        ]
    )

    points, errors = normalize_price_history("600000", frame, _metadata("600000"))

    assert errors == []
    assert [(point.date, point.close) for point in points] == [
        (date(2025, 7, 1), Decimal("10.00")),
    ]


def test_normalize_price_history_keeps_later_duplicate_conflict() -> None:
    frame = pd.DataFrame(
        [
            {"日期": "2025-07-02", "收盘": "10.20"},
            {"日期": "2025-07-01", "收盘": "10.00"},
            {"日期": "2025-07-01", "收盘": "10.50"},
        ]
    )

    points, errors = normalize_price_history("600000", frame, _metadata("600000"))

    assert [(point.date, point.close) for point in points] == [
        (date(2025, 7, 1), Decimal("10.50")),
        (date(2025, 7, 2), Decimal("10.20")),
    ]
    assert [(error.stage, error.message) for error in errors] == [
        ("price_normalize", "duplicate price date"),
    ]


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
