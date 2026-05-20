"""Dividend yield and return metrics.

Pure functions operating on domain types — no upstream I/O here.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from future_ledger.domain import PricePoint

PERCENT_QUANT = Decimal("0.01")


def last_price_on_or_before(points: list[PricePoint], target_date: date) -> PricePoint | None:
    """Return the last price point with date <= target_date from a date-sorted list."""
    selected: PricePoint | None = None
    for point in points:
        if point.date > target_date:
            break
        selected = point
    return selected
