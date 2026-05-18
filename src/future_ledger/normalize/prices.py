from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import PricePoint, SourceErrorRow, SourceMetadata

NORMALIZE_STAGE = "price_normalize"


def normalize_price_history(
    stock_code: str,
    frame: pd.DataFrame,
    metadata: SourceMetadata,
) -> tuple[list[PricePoint], list[SourceErrorRow]]:
    errors: list[SourceErrorRow] = []
    points_by_date: dict[date, PricePoint] = {}

    rows: list[dict[str, Any]] = frame.to_dict(orient="records")
    for row in rows:
        parsed_date, date_error = _parse_price_date(row.get("日期"))
        if date_error is not None:
            errors.append(_error(stock_code, date_error, row, metadata))
            continue

        parsed_close, close_error = _parse_close(row.get("收盘"))
        if close_error is not None:
            errors.append(_error(stock_code, close_error, row, metadata))
            continue

        assert parsed_date is not None
        assert parsed_close is not None
        point = PricePoint(
            stock_code=stock_code,
            date=parsed_date,
            close=parsed_close,
        )

        existing = points_by_date.get(point.date)
        if existing is None:
            points_by_date[point.date] = point
            continue

        if existing.close == point.close:
            continue

        errors.append(_error(stock_code, "duplicate price date", row, metadata))
        points_by_date[point.date] = point

    return sorted(points_by_date.values(), key=lambda point: point.date), errors


def _parse_price_date(value: Any) -> tuple[date | None, str | None]:
    text = _string_or_none(value)
    if text is None:
        return None, "missing price date"

    try:
        return date.fromisoformat(text[:10].replace("/", "-")), None
    except ValueError:
        return None, "invalid price date"


def _parse_close(value: Any) -> tuple[Decimal | None, str | None]:
    text = _string_or_none(value)
    if text is None:
        return None, "missing close price"

    try:
        close = Decimal(text)
    except InvalidOperation:
        return None, "invalid close price"

    if not close.is_finite():
        return None, "invalid close price"

    if close <= Decimal("0"):
        return None, "non-positive close price"

    return close, None


def _string_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in {"", "-", "--", "None"}:
        return None
    return text


def _error(
    stock_code: str,
    message: str,
    row: dict[str, Any],
    metadata: SourceMetadata,
) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=stock_code,
        stage=NORMALIZE_STAGE,
        message=message,
        raw_detail=_raw_detail(row, metadata),
    )


def _raw_detail(row: dict[str, Any], metadata: SourceMetadata) -> str:
    request_start = metadata.request_start_date or ""
    request_end = metadata.request_end_date or ""
    return (
        f"{metadata.source_name}:"
        f"{metadata.upstream_function}:"
        f"{request_start}:"
        f"{request_end}:"
        f"{row}"
    )
