from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import DividendRecord, SourceErrorRow

SOURCE_NAME = "akshare.stock_fhps_detail_em"


def normalize_dividend_detail(
    stock_code: str, stock_name: str, frame: pd.DataFrame
) -> tuple[list[DividendRecord], list[SourceErrorRow]]:
    records: list[DividendRecord] = []
    errors: list[SourceErrorRow] = []
    seen_years: set[int] = set()

    for row in frame.to_dict(orient="records"):
        report_period = _string_or_none(row.get("报告期"))
        if report_period is None:
            errors.append(
                SourceErrorRow(
                    stock_code=stock_code,
                    stage="normalize",
                    message="missing report period",
                    raw_detail=str(row),
                )
            )
            continue

        report_year = int(report_period[:4])
        if report_year in seen_years:
            errors.append(
                SourceErrorRow(
                    stock_code=stock_code,
                    stage="normalize",
                    message="duplicate report period",
                    raw_detail=str(row),
                )
            )
            continue

        cash_dividend_per_10_shares = _decimal_or_none(row.get("每10股派息"))
        seen_years.add(report_year)
        records.append(
            DividendRecord(
                stock_code=stock_code,
                stock_name=stock_name,
                market=_market_for_code(stock_code),
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


def _market_for_code(stock_code: str) -> str:
    if stock_code.startswith("6"):
        return "SH"
    if stock_code.startswith(("0", "3")):
        return "SZ"
    if stock_code.startswith(("4", "8")):
        return "BJ"
    raise ValueError(f"Unsupported A-share stock code prefix: {stock_code!r}")


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
    return date.fromisoformat(text[:10].replace("/", "-"))


def _string_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    return text
