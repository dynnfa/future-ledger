from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from future_ledger.domain import DividendRecord, PricePoint


@dataclass(frozen=True)
class ReturnCalculationResult:
    as_of_date: date
    return_window_start: date
    return_window_end: date
    start_close_price: Decimal | None
    start_price_date: date | None
    end_close_price: Decimal | None
    end_price_date: date | None
    cash_dividends_1y: Decimal | None
    total_return_1y_pct: Decimal | None
    annualized_return_1y_pct: Decimal | None
    return_data_quality_flags: tuple[str, ...]


def calculate_trailing_one_year_return(
    stock_code: str,
    as_of: date,
    prices: list[PricePoint],
    dividends: list[DividendRecord],
) -> ReturnCalculationResult:
    window_start = date(as_of.year - 1, as_of.month, as_of.day)
    stock_prices = [point for point in prices if point.stock_code == stock_code]
    start_point = _first_on_or_after(stock_prices, window_start)
    end_point = _last_on_or_before(stock_prices, as_of)

    if start_point is None or end_point is None:
        return ReturnCalculationResult(
            as_of_date=as_of,
            return_window_start=window_start,
            return_window_end=as_of,
            start_close_price=None,
            start_price_date=None,
            end_close_price=None,
            end_price_date=None,
            cash_dividends_1y=None,
            total_return_1y_pct=None,
            annualized_return_1y_pct=None,
            return_data_quality_flags=("missing_return_price",),
        )

    cash_dividends = sum(
        (
            record.cash_dividend_per_share or Decimal("0")
            for record in dividends
            if record.stock_code == stock_code
            and record.ex_dividend_date is not None
            and window_start <= record.ex_dividend_date <= as_of
        ),
        Decimal("0"),
    )
    total_return = (
        (end_point.close - start_point.close + cash_dividends) / start_point.close
    ) * Decimal("100")

    return ReturnCalculationResult(
        as_of_date=as_of,
        return_window_start=window_start,
        return_window_end=as_of,
        start_close_price=start_point.close,
        start_price_date=start_point.date,
        end_close_price=end_point.close,
        end_price_date=end_point.date,
        cash_dividends_1y=cash_dividends,
        total_return_1y_pct=total_return.quantize(Decimal("0.01")),
        annualized_return_1y_pct=total_return.quantize(Decimal("0.01")),
        return_data_quality_flags=(),
    )


def _first_on_or_after(points: list[PricePoint], target_date: date) -> PricePoint | None:
    for point in points:
        if point.date >= target_date:
            return point
    return None


def _last_on_or_before(points: list[PricePoint], target_date: date) -> PricePoint | None:
    selected: PricePoint | None = None
    for point in points:
        if point.date > target_date:
            break
        selected = point
    return selected
