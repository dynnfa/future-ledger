from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast

from future_ledger.domain import PricePoint

REFERENCE_PRICE_RULE = "ex_dividend_close_or_previous_trading_day"
DIVIDEND_YIELD_SOURCE = "calculated_ex_dividend_close"
PERCENT_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class ReferencePriceResult:
    reference_price: Decimal | None
    reference_price_date: date | None
    reference_price_rule: str
    reference_price_fallback_used: bool


@dataclass(frozen=True)
class DividendYieldResult:
    dividend_yield_pct: Decimal | None
    data_quality_flags: tuple[str, ...]


def resolve_reference_price(
    points: list[PricePoint], ex_dividend_date: date | None
) -> ReferencePriceResult:
    if ex_dividend_date is None:
        return ReferencePriceResult(None, None, REFERENCE_PRICE_RULE, False)

    selected: PricePoint | None = None
    for point in points:
        if point.date > ex_dividend_date:
            break
        selected = point

    if selected is None:
        return ReferencePriceResult(None, None, REFERENCE_PRICE_RULE, False)

    return ReferencePriceResult(
        reference_price=selected.close,
        reference_price_date=selected.date,
        reference_price_rule=REFERENCE_PRICE_RULE,
        reference_price_fallback_used=selected.date != ex_dividend_date,
    )


def calculate_dividend_yield(
    cash_dividend_per_share: Decimal | None, reference_price: Decimal | None
) -> DividendYieldResult:
    flags: list[str] = []
    if cash_dividend_per_share is None:
        flags.append("missing_cash_dividend")
    if reference_price is None or reference_price <= Decimal("0"):
        flags.append("missing_reference_price")

    if flags:
        return DividendYieldResult(
            dividend_yield_pct=None,
            data_quality_flags=tuple(flags),
        )

    cash_dividend = cast(Decimal, cash_dividend_per_share)
    reference_close = cast(Decimal, reference_price)
    return DividendYieldResult(
        dividend_yield_pct=(
            (cash_dividend / reference_close) * Decimal("100")
        ).quantize(PERCENT_QUANT),
        data_quality_flags=(),
    )
