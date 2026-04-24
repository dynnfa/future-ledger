### Task 6: Normalize Price Rows And Implement Reference Price Fallback Rules

**Files:**
- Create: `src/future_ledger/normalize/prices.py`
- Create: `src/future_ledger/metrics/dividend_yield.py`
- Test: `tests/normalize/test_prices.py`
- Test: `tests/metrics/test_dividend_yield.py`
- Create: `tests/fixtures/prices/600000_daily.csv`

- [ ] **Step 1: Write failing tests for price normalization and fallback lookup**

```python
from datetime import date
from pathlib import Path
from decimal import Decimal

import pandas as pd

from future_ledger.metrics.dividend_yield import resolve_reference_price
from future_ledger.normalize.prices import normalize_price_history


def test_normalize_price_history_sorts_by_date():
    frame = pd.read_csv(Path("tests/fixtures/prices/600000_daily.csv"))
    points = normalize_price_history("600000", frame)
    assert points[0].date < points[-1].date


def test_resolve_reference_price_uses_previous_trading_day():
    frame = pd.DataFrame(
        [
            {"日期": "2025-06-30", "收盘": 10.00},
            {"日期": "2025-07-02", "收盘": 10.20},
        ]
    )
    points = normalize_price_history("600000", frame)

    result = resolve_reference_price(points, ex_dividend_date=date(2025, 7, 1))

    assert result.reference_price == Decimal("10.00")
    assert result.reference_price_date == date(2025, 6, 30)
    assert result.reference_price_fallback_used is True
```

- [ ] **Step 2: Run tests to verify the modules are missing**

Run: `pytest tests/normalize/test_prices.py tests/metrics/test_dividend_yield.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement price normalization**

```python
def normalize_price_history(stock_code: str, frame: pd.DataFrame) -> list[PricePoint]:
    points = [
        PricePoint(
            stock_code=stock_code,
            date=date.fromisoformat(str(row["日期"])),
            close=Decimal(str(row["收盘"])),
        )
        for row in frame.to_dict(orient="records")
    ]
    return sorted(points, key=lambda point: point.date)
```

- [ ] **Step 4: Implement reproducible dividend-yield lookup and calculation**

```python
@dataclass(frozen=True)
class ReferencePriceResult:
    reference_price: Decimal | None
    reference_price_date: date | None
    reference_price_rule: str
    reference_price_fallback_used: bool


def resolve_reference_price(points: list[PricePoint], ex_dividend_date: date | None) -> ReferencePriceResult:
    if ex_dividend_date is None:
        return ReferencePriceResult(None, None, "ex_dividend_previous_close", False)

    eligible = [point for point in points if point.date <= ex_dividend_date]
    if not eligible:
        return ReferencePriceResult(None, None, "ex_dividend_previous_close", False)

    selected = eligible[-1]
    return ReferencePriceResult(
        reference_price=selected.close,
        reference_price_date=selected.date,
        reference_price_rule="ex_dividend_previous_close",
        reference_price_fallback_used=selected.date != ex_dividend_date,
    )


def calculate_dividend_yield(cash_dividend_per_share: Decimal | None, reference_price: Decimal | None) -> Decimal | None:
    if cash_dividend_per_share is None or reference_price in (None, Decimal("0")):
        return None
    return (cash_dividend_per_share / reference_price) * Decimal("100")
```

- [ ] **Step 5: Run tests to verify price normalization and yield lookup pass**

Run: `pytest tests/normalize/test_prices.py tests/metrics/test_dividend_yield.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/future_ledger/normalize/prices.py src/future_ledger/metrics/dividend_yield.py tests/normalize/test_prices.py tests/metrics/test_dividend_yield.py tests/fixtures/prices/600000_daily.csv
git commit -m "feat: add price normalization and dividend yield rules"
```
