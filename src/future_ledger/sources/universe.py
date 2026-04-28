from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import StockIdentity


def _market_for_code(code: str) -> str:
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    raise ValueError(f"Unsupported A-share stock code prefix: {code!r}")


def build_universe(frame: pd.DataFrame, universe: str, limit: int | None) -> list[StockIdentity]:
    if universe != "all-a-excluding-st":
        raise ValueError(f"Unsupported universe: {universe}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1")

    stocks = [
        StockIdentity(code=row["代码"], name=row["名称"], market=_market_for_code(row["代码"]))
        for _, row in frame.iterrows()
        if "ST" not in str(row["名称"]).upper()
    ]
    if limit is not None:
        return stocks[:limit]
    return stocks
