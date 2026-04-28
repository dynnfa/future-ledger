from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import PricePoint


def normalize_price_history(stock_code: str, frame: pd.DataFrame) -> list[PricePoint]:
    points = [
        PricePoint(
            stock_code=stock_code,
            date=date.fromisoformat(str(row["日期"])[:10]),
            close=Decimal(str(row["收盘"])),
        )
        for row in frame.to_dict(orient="records")
    ]
    return sorted(points, key=lambda point: point.date)
