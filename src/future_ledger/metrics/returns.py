from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from future_ledger.domain import DividendRecord, PricePoint, safe_replace_year
from future_ledger.metrics import PERCENT_QUANT, last_price_on_or_before


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
    window_start = safe_replace_year(as_of, as_of.year - 1)
    stock_prices = [point for point in prices if point.stock_code == stock_code]
    start_point = _first_on_or_after(stock_prices, window_start)
    end_point = last_price_on_or_before(stock_prices, as_of)

    if start_point is None or end_point is None:
        return _empty_result(as_of, window_start, "missing_return_price")

    if start_point.close <= Decimal("0"):
        return _empty_result(as_of, window_start, "invalid_return_start_price")

    cash_dividends, flags = _cash_dividends_in_window(
        stock_code=stock_code,
        dividends=dividends,
        window_start=window_start,
        window_end=as_of,
    )
    total_return = (
        (end_point.close - start_point.close + cash_dividends) / start_point.close
    ) * Decimal("100")
    total_return_pct = total_return.quantize(PERCENT_QUANT)

    return ReturnCalculationResult(
        as_of_date=as_of,
        return_window_start=window_start,
        return_window_end=as_of,
        start_close_price=start_point.close,
        start_price_date=start_point.date,
        end_close_price=end_point.close,
        end_price_date=end_point.date,
        cash_dividends_1y=cash_dividends,
        total_return_1y_pct=total_return_pct,
        annualized_return_1y_pct=total_return_pct,
        return_data_quality_flags=tuple(flags),
    )


def _empty_result(as_of: date, window_start: date, flag: str) -> ReturnCalculationResult:
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
        return_data_quality_flags=(flag,),
    )


def _first_on_or_after(points: list[PricePoint], target_date: date) -> PricePoint | None:
    for point in points:
        if point.date >= target_date:
            return point
    return None


def _cash_dividends_in_window(
    *,
    stock_code: str,
    dividends: list[DividendRecord],
    window_start: date,
    window_end: date,
) -> tuple[Decimal, list[str]]:
    cash_dividends = Decimal("0")
    uncertain_window = False

    for record in dividends:
        if record.stock_code != stock_code:
            continue
        if record.ex_dividend_date is None or record.cash_dividend_per_share is None:
            uncertain_window = True
            continue
        if window_start <= record.ex_dividend_date <= window_end:
            cash_dividends += record.cash_dividend_per_share

    flags = ["uncertain_dividend_window"] if uncertain_window else []
    return cash_dividends, flags
