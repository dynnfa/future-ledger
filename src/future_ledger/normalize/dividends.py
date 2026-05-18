from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import DividendRecord, SourceErrorRow, StockIdentity

SOURCE_NAME = "akshare.stock_fhps_detail_em"
NORMALIZE_STAGE = "dividend_normalize"
PLAN_STATUS_PRIORITY = {
    "实施": 5,
    "股东大会通过": 4,
    "董事会预案": 3,
    "预案": 2,
}


def normalize_dividend_detail(
    stock: StockIdentity, frame: pd.DataFrame
) -> tuple[list[DividendRecord], list[SourceErrorRow]]:
    errors: list[SourceErrorRow] = []
    selected_rows: dict[str, tuple[int, int, int, dict[str, Any]]] = {}

    for index, row in enumerate(frame.to_dict(orient="records")):
        report_period = _string_or_none(row.get("报告期"))
        if report_period is None:
            errors.append(_error(stock.code, "missing report period", row))
            continue

        canonical_report_period = _canonical_report_period_or_none(report_period)
        if canonical_report_period is None:
            errors.append(_error(stock.code, "invalid report period", row))
            continue

        report_year = int(canonical_report_period[:4])
        priority = _plan_status_priority(row.get("方案进度"))
        existing = selected_rows.get(canonical_report_period)
        if existing is not None:
            errors.append(_error(stock.code, "duplicate report period", row))
            existing_priority, existing_index, _, _ = existing
            if priority < existing_priority:
                continue
            if priority == existing_priority and index < existing_index:
                continue

        selected_rows[canonical_report_period] = (priority, index, report_year, row)

    records = [
        _record_from_row(stock, report_year, report_period, row, errors)
        for report_period, (_, _, report_year, row) in selected_rows.items()
    ]
    return sorted(records, key=lambda item: item.report_year, reverse=True), errors


def _record_from_row(
    stock: StockIdentity,
    report_year: int,
    report_period: str,
    row: dict[str, Any],
    errors: list[SourceErrorRow],
) -> DividendRecord:
    cash_dividend_per_10_shares = _decimal_or_none(
        row.get("每10股派息"),
        field_name="cash_dividend_per_10_shares",
        stock_code=stock.code,
        row=row,
        errors=errors,
        allow_percent=False,
    )
    return DividendRecord(
        stock_code=stock.code,
        stock_name=stock.name,
        market=stock.market,
        report_year=report_year,
        report_period=report_period,
        cash_dividend_per_10_shares=cash_dividend_per_10_shares,
        cash_dividend_per_share=_per_share(cash_dividend_per_10_shares),
        ex_dividend_date=_date_or_none(row.get("除权除息日")),
        registration_date=_date_or_none(row.get("股权登记日")),
        plan_status=_string_or_none(row.get("方案进度")),
        eps=_decimal_or_none(
            row.get("每股收益"),
            field_name="eps",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=False,
        ),
        net_asset_per_share=_decimal_or_none(
            row.get("每股净资产"),
            field_name="net_asset_per_share",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=False,
        ),
        profit_growth_yoy_pct=_decimal_or_none(
            row.get("净利润同比增长"),
            field_name="profit_growth_yoy_pct",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=True,
        ),
        provider_yield_pct=_decimal_or_none(
            row.get("现金分红-股息率"),
            field_name="provider_yield_pct",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=True,
        ),
        source=SOURCE_NAME,
    )


def _plan_status_priority(value: Any) -> int:
    status = _string_or_none(value)
    if status is None:
        return 0
    return PLAN_STATUS_PRIORITY.get(status, 1)


def _canonical_report_period_or_none(report_period: str) -> str | None:
    if len(report_period) < 4 or not report_period[:4].isdigit():
        return None
    try:
        return _date_or_none_required(report_period).isoformat()
    except ValueError:
        return None


def _decimal_or_none(
    value: Any,
    *,
    field_name: str,
    stock_code: str,
    row: dict[str, Any],
    errors: list[SourceErrorRow],
    allow_percent: bool,
) -> Decimal | None:
    text = _string_or_none(value)
    if text is None:
        return None

    normalized = text.replace(",", "").strip()
    if normalized.endswith("%"):
        if not allow_percent:
            errors.append(_error(stock_code, f"invalid decimal field: {field_name}", row))
            return None
        normalized = normalized.removesuffix("%").strip()
    elif "%" in normalized:
        errors.append(_error(stock_code, f"invalid decimal field: {field_name}", row))
        return None

    try:
        return Decimal(normalized)
    except InvalidOperation:
        errors.append(_error(stock_code, f"invalid decimal field: {field_name}", row))
        return None


def _per_share(per_10_shares: Decimal | None) -> Decimal | None:
    if per_10_shares is None:
        return None
    return per_10_shares / Decimal("10")


def _date_or_none(value: Any) -> date | None:
    text = _string_or_none(value)
    if text is None:
        return None
    try:
        return _date_or_none_required(text)
    except ValueError:
        return None


def _date_or_none_required(text: str) -> date:
    return date.fromisoformat(text[:10].replace("/", "-"))


def _string_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    return text


def _error(stock_code: str, message: str, row: dict[str, Any]) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=stock_code,
        stage=NORMALIZE_STAGE,
        message=message,
        raw_detail=str(row),
    )
