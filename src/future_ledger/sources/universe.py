from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import SourceErrorRow, StockIdentity
from future_ledger.errors import SourceError
from future_ledger.normalize._util import string_or_none

REQUIRED_COLUMNS = ("代码", "名称")
SUPPORTED_UNIVERSE = "all-a-excluding-st"


def build_universe(
    frame: pd.DataFrame, universe: str, limit: int | None
) -> tuple[list[StockIdentity], list[SourceErrorRow]]:
    if universe != SUPPORTED_UNIVERSE:
        raise ValueError(f"Unsupported universe: {universe}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise SourceError("spot frame missing required columns: 代码, 名称")

    if frame.empty:
        return [], [
            SourceErrorRow(
                stock_code="",
                stage="universe",
                message="empty spot frame",
                raw_detail=None,
            )
        ]

    stocks: list[StockIdentity] = []
    errors: list[SourceErrorRow] = []

    for row in frame.to_dict(orient="records"):
        code = _normalize_code(row.get("代码"))
        raw_detail = str(row)
        if code is None:
            errors.append(_universe_error("", "missing stock code", raw_detail))
            continue
        if len(code) != 6:
            errors.append(_universe_error(code, "invalid stock code length", raw_detail))
            continue

        name = string_or_none(row.get("名称"))
        if name is None:
            errors.append(_universe_error(code, "missing stock name", raw_detail))
            continue

        if "ST" in name.upper():
            continue

        try:
            market = _market_for_code(code)
        except ValueError:
            errors.append(_universe_error(code, "unsupported stock code prefix", raw_detail))
            continue

        stocks.append(StockIdentity(code=code, name=name, market=market))

    if limit is not None:
        stocks = stocks[:limit]
    return stocks, errors


def _market_for_code(code: str) -> str:
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    raise ValueError(f"Unsupported A-share stock code prefix: {code!r}")


def _normalize_code(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    if isinstance(value, float):
        if not value.is_integer():
            return None
        text = str(int(value))
    elif isinstance(value, int):
        text = str(value)
    else:
        text = str(value).strip()
        if text.endswith(".0") and text.removesuffix(".0").isdigit():
            text = text.removesuffix(".0")

    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    if not text.isdigit():
        return None
    if len(text) <= 6:
        return text.zfill(6)
    return text


def _universe_error(stock_code: str, message: str, raw_detail: str | None) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=stock_code,
        stage="universe",
        message=message,
        raw_detail=raw_detail,
    )
