### Task 7: Implement Trailing One-Year Return Calculation

**Files:**
- Create: `src/future_ledger/metrics/returns.py`
- Test: `tests/metrics/test_returns.py`

- [ ] **Step 1: Write failing tests for return window selection**

```python
from datetime import date
from decimal import Decimal

from future_ledger.domain import DividendRecord, PricePoint
from future_ledger.metrics.returns import calculate_trailing_one_year_return


def test_calculate_trailing_one_year_return_uses_window_price_fallbacks():
    prices = [
        PricePoint(stock_code="600000", date=date(2025, 4, 21), close=Decimal("10.00")),
        PricePoint(stock_code="600000", date=date(2026, 4, 17), close=Decimal("10.80")),
    ]
    dividends = [
        DividendRecord(
            stock_code="600000",
            stock_name="浦发银行",
            market="SH",
            report_year=2025,
            report_period="2025-12-31",
            cash_dividend_per_10_shares=Decimal("4.10"),
            cash_dividend_per_share=Decimal("0.41"),
            ex_dividend_date=date(2025, 7, 1),
            registration_date=None,
            plan_status="实施",
            eps=None,
            net_asset_per_share=None,
            profit_growth_yoy_pct=None,
            provider_yield_pct=None,
            source="akshare.stock_fhps_detail_em",
        )
    ]

    result = calculate_trailing_one_year_return(
        stock_code="600000",
        as_of=date(2026, 4, 18),
        prices=prices,
        dividends=dividends,
    )

    assert result.start_close_price == Decimal("10.00")
    assert result.end_close_price == Decimal("10.80")
    assert result.cash_dividends_1y == Decimal("0.41")
    assert result.total_return_1y_pct == Decimal("12.10")
```

- [ ] **Step 2: Run tests to verify the return module is missing**

Run: `pytest tests/metrics/test_returns.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the trailing-one-year return logic**

```python
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


def calculate_trailing_one_year_return(stock_code: str, as_of: date, prices: list[PricePoint], dividends: list[DividendRecord]) -> ReturnCalculationResult:
    window_start = date(as_of.year - 1, as_of.month, as_of.day)
    start_point = _first_on_or_after(prices, window_start)
    end_point = _last_on_or_before(prices, as_of)
    if start_point is None or end_point is None:
        return ReturnCalculationResult(as_of, window_start, as_of, None, None, None, None, None, None, None, ("missing_return_price",))

    cash_dividends = sum(
        (record.cash_dividend_per_share or Decimal("0"))
        for record in dividends
        if record.ex_dividend_date is not None and window_start <= record.ex_dividend_date <= as_of
    )
    total_return = ((end_point.close - start_point.close + cash_dividends) / start_point.close) * Decimal("100")
    return ReturnCalculationResult(
        as_of,
        window_start,
        as_of,
        start_point.close,
        start_point.date,
        end_point.close,
        end_point.date,
        cash_dividends,
        total_return,
        total_return,
        (),
    )
```

- [ ] **Step 4: Run tests to verify return calculations pass**

Run: `pytest tests/metrics/test_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/future_ledger/metrics/returns.py tests/metrics/test_returns.py
git commit -m "feat: add trailing one-year return metrics"
```
