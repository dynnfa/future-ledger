from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.normalize.prices import normalize_price_history


def test_normalize_price_history_sorts_by_date() -> None:
    frame = pd.read_csv(
        Path("tests/fixtures/prices/600000_daily_20250630_20260417.csv")
    )

    points = normalize_price_history("600000", frame)

    assert [point.date for point in points] == [
        date(2025, 6, 30),
        date(2025, 7, 2),
        date(2026, 4, 17),
    ]
    assert points[0].stock_code == "600000"
    assert points[0].close == Decimal("10.00")
