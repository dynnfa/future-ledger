### Task 8: Build Report Rows And Annual Expansion Columns

**Files:**
- Create: `src/future_ledger/reports/rows.py`
- Test: `tests/reports/test_rows.py`

- [ ] **Step 1: Write failing row-builder tests**

```python
from datetime import date
from decimal import Decimal

from future_ledger.domain import DividendRecord
from future_ledger.reports.rows import build_dividend_rank_rows


def test_build_dividend_rank_rows_expands_annual_fields_for_last_five_years():
    records = [
        DividendRecord(
            stock_code="600000",
            stock_name="浦发银行",
            market="SH",
            report_year=2025,
            report_period="2025-12-31",
            cash_dividend_per_10_shares=Decimal("4.10"),
            cash_dividend_per_share=Decimal("0.41"),
            ex_dividend_date=date(2025, 7, 1),
            registration_date=date(2025, 6, 30),
            plan_status="实施",
            eps=Decimal("1.23"),
            net_asset_per_share=Decimal("12.34"),
            profit_growth_yoy_pct=Decimal("5.6"),
            provider_yield_pct=Decimal("4.0"),
            source="akshare.stock_fhps_detail_em",
        )
    ]

    rows = build_dividend_rank_rows(
        stock_name_by_code={"600000": "浦发银行"},
        market_by_code={"600000": "SH"},
        records_by_code={"600000": records},
        as_of_date=date(2026, 4, 20),
        return_by_code={},
        fetched_at="2026-04-20T08:30:00+08:00",
    )

    assert rows[0].annual_fields["2025_plan_status"] == "实施"
    assert rows[0].dividend_year_count_5y == 1
    assert rows[0].has_missing_years_5y is True
```

- [ ] **Step 2: Run tests to verify the row builder is missing**

Run: `pytest tests/reports/test_rows.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement rank-row assembly**

```python
def build_dividend_rank_rows(...):
    rows = []
    for stock_code, records in records_by_code.items():
        sorted_records = sorted(records, key=lambda record: record.report_year, reverse=True)[:5]
        latest = sorted_records[0] if sorted_records else None
        annual_fields = {}
        for record in sorted_records:
            prefix = str(record.report_year)
            annual_fields[f"{prefix}_report_period"] = record.report_period
            annual_fields[f"{prefix}_cash_dividend_per_10_shares"] = record.cash_dividend_per_10_shares
            annual_fields[f"{prefix}_cash_dividend_per_share"] = record.cash_dividend_per_share
            annual_fields[f"{prefix}_registration_date"] = record.registration_date
            annual_fields[f"{prefix}_ex_dividend_date"] = record.ex_dividend_date
            annual_fields[f"{prefix}_plan_status"] = record.plan_status
            annual_fields[f"{prefix}_eps"] = record.eps
            annual_fields[f"{prefix}_net_asset_per_share"] = record.net_asset_per_share
            annual_fields[f"{prefix}_profit_growth_yoy_pct"] = record.profit_growth_yoy_pct
            annual_fields[f"{prefix}_source"] = record.source
        rows.append(...)
    return _rank_by_latest_yield(rows)
```

- [ ] **Step 4: Add long-table and source-error row builders**

```python
def build_dividend_long_rows(records_by_code: dict[str, list[DividendRecord]]) -> list[DividendLongRow]:
    return [
        DividendLongRow(
            stock_code=record.stock_code,
            stock_name=record.stock_name,
            market=record.market,
            report_year=record.report_year,
            report_period=record.report_period,
            cash_dividend_per_10_shares=record.cash_dividend_per_10_shares,
            cash_dividend_per_share=record.cash_dividend_per_share,
            ex_dividend_date=record.ex_dividend_date,
            registration_date=record.registration_date,
            plan_status=record.plan_status,
            eps=record.eps,
            net_asset_per_share=record.net_asset_per_share,
            profit_growth_yoy_pct=record.profit_growth_yoy_pct,
            dividend_yield_pct=record.provider_yield_pct,
            source=record.source,
        )
        for records in records_by_code.values()
        for record in sorted(records, key=lambda item: item.report_year, reverse=True)
    ]
```

- [ ] **Step 5: Run tests to verify row assembly passes**

Run: `pytest tests/reports/test_rows.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/future_ledger/reports/rows.py tests/reports/test_rows.py
git commit -m "feat: assemble workbook report rows"
```
