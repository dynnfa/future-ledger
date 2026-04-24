### Task 10: Orchestrate The Full Pipeline With Error Rescue

**Files:**
- Modify: `src/future_ledger/pipeline.py`
- Test: `tests/pipeline/test_run_scan.py`

- [ ] **Step 1: Write failing orchestrator tests with fakes**

```python
from datetime import date
from pathlib import Path

from future_ledger.domain import RunConfig
from future_ledger.pipeline import run_scan


def test_run_scan_rescues_per_stock_fetch_errors(monkeypatch):
    monkeypatch.setattr("future_ledger.pipeline.fetch_stock_universe", lambda: [{"code": "600000", "name": "浦发银行", "market": "SH"}, {"code": "600001", "name": "坏股票", "market": "SH"}])
    monkeypatch.setattr("future_ledger.pipeline.fetch_dividend_records_for_stock", lambda stock, config: [] if stock["code"] == "600000" else (_ for _ in ()).throw(RuntimeError("timeout")))
    monkeypatch.setattr("future_ledger.pipeline.build_report_tables", lambda **_: "REPORTS")

    config = RunConfig(
        years=5,
        as_of=date(2026, 4, 20),
        universe="all-a-excluding-st",
        output=Path("reports/dividend_rank.xlsx"),
    )

    result = run_scan(config)
    assert result == "REPORTS"
```

- [ ] **Step 2: Run tests to verify the stubbed pipeline behavior is insufficient**

Run: `pytest tests/pipeline/test_run_scan.py -v`
Expected: FAIL because `run_scan` does not orchestrate fetch/build/write behavior.

- [ ] **Step 3: Implement the orchestration flow**

```python
def run_scan(config: RunConfig) -> ReportTables:
    universe_frame = fetch_a_share_spot()
    stocks = build_universe(universe_frame, config.universe, config.limit)

    records_by_code = {}
    prices_by_code = {}
    source_errors = []

    for stock in stocks:
        try:
            dividend_frame = fetch_dividend_detail(stock.code)
            records, normalize_errors = normalize_dividend_detail(stock.code, stock.name, dividend_frame)
            records_by_code[stock.code] = records
            source_errors.extend(normalize_errors)
        except Exception as exc:
            source_errors.append(SourceErrorRow(stock_code=stock.code, stage="dividend_fetch", message=str(exc)))
            continue

        try:
            price_frame = fetch_price_history(stock.code, start_date=_price_start(config.as_of), end_date=config.as_of.isoformat())
            prices_by_code[stock.code] = normalize_price_history(stock.code, price_frame)
        except Exception as exc:
            source_errors.append(SourceErrorRow(stock_code=stock.code, stage="price_fetch", message=str(exc)))

    tables = build_report_tables(config=config, stocks=stocks, records_by_code=records_by_code, prices_by_code=prices_by_code, source_errors=source_errors)
    write_workbook(config.output, tables)
    return tables
```

- [ ] **Step 4: Run orchestrator tests**

Run: `pytest tests/pipeline/test_run_scan.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/future_ledger/pipeline.py tests/pipeline/test_run_scan.py
git commit -m "feat: orchestrate dividend scan pipeline"
```
