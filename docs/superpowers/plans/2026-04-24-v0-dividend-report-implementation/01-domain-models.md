### Task 1: Expand Domain Types To Match The Workbook Contract

**Files:**
- Modify: `src/future_ledger/domain.py`
- Test: `tests/test_domain_models.py`

- [ ] **Step 1: Write the failing domain-shape tests**

```python
from datetime import date
from decimal import Decimal
from pathlib import Path

from future_ledger.domain import DividendLongRow, DividendRankRow, MetadataRow, RunConfig


def test_run_config_defaults_cache_dir():
    config = RunConfig(
        years=5,
        as_of=date(2026, 4, 20),
        universe="all-a-excluding-st",
        output=Path("reports/dividend_rank.xlsx"),
    )
    assert config.cache_dir == Path(".future_ledger/cache")


def test_dividend_rank_row_tracks_required_columns():
    row = DividendRankRow(
        rank_latest_yield=1,
        stock_code="600000",
        stock_name="浦发银行",
        market="SH",
        latest_report_year=2025,
        latest_cash_dividend_per_10_shares=Decimal("4.10"),
        latest_cash_dividend_per_share=Decimal("0.41"),
        reference_price=Decimal("10.25"),
        reference_price_date=date(2025, 7, 1),
        latest_dividend_yield_pct=Decimal("4.00"),
        dividend_yield_source="calculated_ex_dividend_close",
        dividend_year_count_5y=5,
        continuous_dividend_5y=True,
        avg_dividend_yield_pct_5y=Decimal("3.80"),
        min_dividend_yield_pct_5y=Decimal("3.10"),
        max_dividend_yield_pct_5y=Decimal("4.20"),
        as_of_date=date(2026, 4, 20),
        cash_dividends_1y=Decimal("0.41"),
        total_return_1y_pct=Decimal("6.50"),
        annualized_return_1y_pct=Decimal("6.50"),
        has_missing_years_5y=False,
        data_quality_flags=("none",),
        source_priority_used="akshare.stock_fhps_detail_em",
        fetched_at="2026-04-20T08:30:00+08:00",
        annual_fields={"2025_plan_status": "实施"},
    )
    assert row.annual_fields["2025_plan_status"] == "实施"
```

- [ ] **Step 2: Run tests to verify the types are still missing**

Run: `pytest tests/test_domain_models.py -v`
Expected: FAIL with import errors for `DividendLongRow` and `MetadataRow`, or constructor signature mismatches on `DividendRankRow`.

- [ ] **Step 3: Implement the expanded dataclasses**

```python
@dataclass(frozen=True)
class DividendYearDetail:
    report_year: int
    report_period: str
    cash_dividend_per_10_shares: Decimal | None
    cash_dividend_per_share: Decimal | None
    reference_price: Decimal | None
    reference_price_date: date | None
    dividend_yield_pct: Decimal | None
    registration_date: date | None
    ex_dividend_date: date | None
    plan_status: str | None
    eps: Decimal | None
    net_asset_per_share: Decimal | None
    profit_growth_yoy_pct: Decimal | None
    source: str


@dataclass(frozen=True)
class DividendRankRow:
    rank_latest_yield: int | None
    stock_code: str
    stock_name: str
    market: str
    latest_report_year: int | None
    latest_cash_dividend_per_10_shares: Decimal | None
    latest_cash_dividend_per_share: Decimal | None
    reference_price: Decimal | None
    reference_price_date: date | None
    latest_dividend_yield_pct: Decimal | None
    dividend_yield_source: str
    dividend_year_count_5y: int
    continuous_dividend_5y: bool
    avg_dividend_yield_pct_5y: Decimal | None
    min_dividend_yield_pct_5y: Decimal | None
    max_dividend_yield_pct_5y: Decimal | None
    as_of_date: date
    cash_dividends_1y: Decimal | None
    total_return_1y_pct: Decimal | None
    annualized_return_1y_pct: Decimal | None
    has_missing_years_5y: bool
    data_quality_flags: tuple[str, ...]
    source_priority_used: str
    fetched_at: str
    annual_fields: dict[str, object]
```

- [ ] **Step 4: Add the remaining long-row and metadata dataclasses**

```python
@dataclass(frozen=True)
class DividendLongRow:
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
    dividend_yield_pct: Decimal | None
    source: str


@dataclass(frozen=True)
class MetadataRow:
    key: str
    value: str
```

- [ ] **Step 5: Run tests to verify the new shapes pass**

Run: `pytest tests/test_domain_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/future_ledger/domain.py tests/test_domain_models.py
git commit -m "feat: expand domain models for dividend workbook"
```
