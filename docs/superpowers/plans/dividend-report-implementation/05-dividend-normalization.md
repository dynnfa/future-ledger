### Task 5: Normalize Dividend Source Rows Into Internal Records

**Files:**
- Create: `src/future_ledger/normalize/dividends.py`
- Modify: `src/future_ledger/domain.py`
- Test: `tests/normalize/test_dividends.py`
- Create: `tests/fixtures/akshare/dividend_detail_600000.csv`

- [ ] **Step 1: Write failing normalization tests from fixture data**

```python
from pathlib import Path

import pandas as pd

from future_ledger.normalize.dividends import normalize_dividend_detail


def test_normalize_dividend_detail_maps_required_fields():
    frame = pd.read_csv(Path("tests/fixtures/akshare/dividend_detail_600000.csv"))

    records, errors = normalize_dividend_detail("600000", "浦发银行", frame)

    assert errors == []
    assert records[0].stock_code == "600000"
    assert records[0].report_year == 2025
    assert records[0].cash_dividend_per_share is not None
    assert records[0].source == "akshare.stock_fhps_detail_em"


def test_normalize_dividend_detail_flags_duplicate_report_year():
    frame = pd.DataFrame(
        [
            {"报告期": "2024-12-31", "现金分红-股息率": "4.0", "除权除息日": "2025-07-01"},
            {"报告期": "2024-12-31", "现金分红-股息率": "4.2", "除权除息日": "2025-07-02"},
        ]
    )
    _, errors = normalize_dividend_detail("600000", "浦发银行", frame)
    assert errors[0].stage == "normalize"
```

- [ ] **Step 2: Run tests to verify the normalizer is missing**

Run: `pytest tests/normalize/test_dividends.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Extend the dividend record to carry all normalized source fields**

```python
@dataclass(frozen=True)
class DividendRecord:
    stock_code: str
    stock_name: str
    market: str
    report_year: int
    report_period: str
    cash_dividend_per_10_shares: Decimal | None
    cash_dividend_per_share: Decimal | None
    ex_dividend_date: date | None
    registration_date: date | None
    plan_status: str | None
    eps: Decimal | None
    net_asset_per_share: Decimal | None
    profit_growth_yoy_pct: Decimal | None
    provider_yield_pct: Decimal | None
    source: str
```

- [ ] **Step 4: Implement normalization with duplicate and missing-period rescue**

```python
def normalize_dividend_detail(stock_code: str, stock_name: str, frame: pd.DataFrame):
    records = []
    errors = []
    seen_years = set()

    for row in frame.to_dict(orient="records"):
        report_period = row.get("报告期")
        if not report_period:
            errors.append(SourceErrorRow(stock_code=stock_code, stage="normalize", message="missing report period"))
            continue

        report_year = int(str(report_period)[:4])
        if report_year in seen_years:
            errors.append(SourceErrorRow(stock_code=stock_code, stage="normalize", message="duplicate report period"))
            continue

        seen_years.add(report_year)
        records.append(
            DividendRecord(
                stock_code=stock_code,
                stock_name=stock_name,
                market="SH" if stock_code.startswith("6") else "SZ",
                report_year=report_year,
                report_period=report_period,
                cash_dividend_per_10_shares=_decimal_or_none(row.get("每10股派息")),
                cash_dividend_per_share=_per_share(row.get("每10股派息")),
                ex_dividend_date=_date_or_none(row.get("除权除息日")),
                registration_date=_date_or_none(row.get("股权登记日")),
                plan_status=_string_or_none(row.get("方案进度")),
                eps=_decimal_or_none(row.get("每股收益")),
                net_asset_per_share=_decimal_or_none(row.get("每股净资产")),
                profit_growth_yoy_pct=_decimal_or_none(row.get("净利润同比增长")),
                provider_yield_pct=_decimal_or_none(row.get("现金分红-股息率")),
                source="akshare.stock_fhps_detail_em",
            )
        )
    return sorted(records, key=lambda item: item.report_year, reverse=True), errors
```

- [ ] **Step 5: Run tests to verify normalization passes**

Run: `pytest tests/normalize/test_dividends.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/future_ledger/domain.py src/future_ledger/normalize/dividends.py tests/normalize/test_dividends.py tests/fixtures/akshare/dividend_detail_600000.csv
git commit -m "feat: normalize akshare dividend detail rows"
```
