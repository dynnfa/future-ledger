### Task 4: Add Universe Loading And ST Filtering

**Files:**
- Create: `src/future_ledger/sources/akshare_client.py`
- Create: `src/future_ledger/sources/universe.py`
- Test: `tests/sources/test_universe.py`

- [ ] **Step 1: Write failing universe-filter tests**

```python
import pandas as pd

from future_ledger.sources.universe import build_universe


def test_build_universe_excludes_st_names():
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "600001", "名称": "*ST 示例"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )

    result = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert [stock.code for stock in result] == ["600000", "000001"]


def test_build_universe_applies_limit_after_filtering():
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )
    result = build_universe(frame, universe="all-a-excluding-st", limit=1)
    assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify the module does not exist yet**

Run: `pytest tests/sources/test_universe.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the universe builder**

```python
from future_ledger.domain import StockIdentity


def _market_for_code(code: str) -> str:
    if code.startswith("6"):
        return "SH"
    return "SZ"


def build_universe(frame, universe: str, limit: int | None) -> list[StockIdentity]:
    if universe != "all-a-excluding-st":
        raise ValueError(f"Unsupported universe: {universe}")

    stocks = [
        StockIdentity(code=row["代码"], name=row["名称"], market=_market_for_code(row["代码"]))
        for _, row in frame.iterrows()
        if "ST" not in str(row["名称"]).upper()
    ]
    if limit is not None:
        return stocks[:limit]
    return stocks
```

- [ ] **Step 4: Add the AKShare client surface used later by the pipeline**

```python
import akshare as ak


def fetch_a_share_spot() -> pd.DataFrame:
    return ak.stock_zh_a_spot_em()


def fetch_dividend_detail(symbol: str) -> pd.DataFrame:
    return ak.stock_fhps_detail_em(symbol=symbol)


def fetch_price_history(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    return ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date)
```

- [ ] **Step 5: Run tests to verify universe filtering passes**

Run: `pytest tests/sources/test_universe.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/future_ledger/sources/akshare_client.py src/future_ledger/sources/universe.py tests/sources/test_universe.py
git commit -m "feat: add stock universe filtering"
```
