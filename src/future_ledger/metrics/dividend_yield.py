from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from future_ledger.domain import PricePoint

REFERENCE_PRICE_RULE = "ex_dividend_previous_close"


@dataclass(frozen=True)
class ReferencePriceResult:
    reference_price: Decimal | None
    reference_price_date: date | None
    reference_price_rule: str
    reference_price_fallback_used: bool


def resolve_reference_price(
    points: list[PricePoint], ex_dividend_date: date | None
) -> ReferencePriceResult:
    if ex_dividend_date is None:
        return ReferencePriceResult(None, None, REFERENCE_PRICE_RULE, False)

    eligible = sorted(
        (point for point in points if point.date <= ex_dividend_date),
        key=lambda point: point.date,
    )
    if not eligible:
        return ReferencePriceResult(None, None, REFERENCE_PRICE_RULE, False)

    selected = eligible[-1]
    return ReferencePriceResult(
        reference_price=selected.close,
        reference_price_date=selected.date,
        reference_price_rule=REFERENCE_PRICE_RULE,
        reference_price_fallback_used=selected.date != ex_dividend_date,
    )


def calculate_dividend_yield(
    cash_dividend_per_share: Decimal | None, reference_price: Decimal | None
) -> Decimal | None:
    if (
        cash_dividend_per_share is None
        or reference_price is None
        or reference_price == Decimal("0")
    ):
        return None
    return (cash_dividend_per_share / reference_price) * Decimal("100")
