from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import DividendRecord, SourceErrorRow, StockIdentity

SOURCE_NAME = "akshare.stock_fhps_detail_em"
NORMALIZE_STAGE = "dividend_normalize"


def normalize_dividend_detail(
    stock: StockIdentity, frame: pd.DataFrame
) -> tuple[list[DividendRecord], list[SourceErrorRow]]:
    records: list[DividendRecord] = []
    errors: list[SourceErrorRow] = []
    seen_periods: set[str] = set()

    for row in frame.to_dict(orient="records"):
        report_period = _string_or_none(row.get("报告期"))
        if report_period is None:
            errors.append(_error(stock.code, "missing report period", row))
            continue

        report_year = _report_year_or_none(report_period)
        if report_year is None:
            errors.append(_error(stock.code, "invalid report period", row))
            continue

        if report_period in seen_periods:
            errors.append(_error(stock.code, "duplicate report period", row))
            continue

        cash_dividend_per_10_shares = _decimal_or_none(row.get("每10股派息"))
        seen_periods.add(report_period)
        records.append(
            DividendRecord(
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
                eps=_decimal_or_none(row.get("每股收益")),
                net_asset_per_share=_decimal_or_none(row.get("每股净资产")),
                profit_growth_yoy_pct=_decimal_or_none(row.get("净利润同比增长")),
                provider_yield_pct=_decimal_or_none(row.get("现金分红-股息率")),
                source=SOURCE_NAME,
            )
        )

    return sorted(records, key=lambda item: item.report_year, reverse=True), errors


def _report_year_or_none(report_period: str) -> int | None:
    try:
        return int(report_period[:4])
    except ValueError:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    text = _string_or_none(value)
    if text is None:
        return None

    normalized = text.replace(",", "").removesuffix("%").strip()
    try:
        return Decimal(normalized)
    except InvalidOperation:
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
        return date.fromisoformat(text[:10].replace("/", "-"))
    except ValueError:
        return None


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
