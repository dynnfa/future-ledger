### Task 11: Final Integration Pass For Metadata, Compliance, And Regression Coverage

**Files:**
- Modify: `src/future_ledger/pipeline.py`
- Modify: `src/future_ledger/reports/rows.py`
- Modify: `src/future_ledger/reports/workbook.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/reports/test_workbook.py`

- [ ] **Step 1: Add failing regression tests for metadata and command output**

```python
def test_scan_prints_written_workbook_path(monkeypatch):
    def fake_run_scan(config):
        return ReportTables(dividend_rank=[], dividend_long=[], price_points=[], source_errors=[], metadata=[])

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
    result = CliRunner().invoke(app, ["dividends", "scan", "--output", "reports/custom.xlsx"])

    assert result.exit_code == 0
    assert "Wrote workbook: reports/custom.xlsx" in result.output
```

- [ ] **Step 2: Run the focused regression suite**

Run: `pytest tests/test_cli.py tests/reports/test_workbook.py -v`
Expected: FAIL until metadata rows and user-facing output are complete.

- [ ] **Step 3: Fill metadata rows from runtime config and compliance text**

```python
DISCLAIMER = (
    "FutureLedger is for financial data research only. "
    "It does not provide investment advice, buy/sell recommendations, "
    "or portfolio allocation guidance."
)


def build_metadata_rows(config: RunConfig, generated_at: str, akshare_version: str) -> list[MetadataRow]:
    return [
        MetadataRow(key="generated_at", value=generated_at),
        MetadataRow(key="years", value=str(config.years)),
        MetadataRow(key="as_of", value=config.as_of.isoformat()),
        MetadataRow(key="universe", value=config.universe),
        MetadataRow(key="output", value=str(config.output)),
        MetadataRow(key="source_priority", value="akshare.stock_fhps_detail_em"),
        MetadataRow(key="akshare_version", value=akshare_version),
        MetadataRow(key="disclaimer", value=DISCLAIMER),
    ]
```

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`
Expected: PASS

- [ ] **Step 5: Run static checks**

Run: `ruff check src tests && mypy src`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/future_ledger/pipeline.py src/future_ledger/reports/rows.py src/future_ledger/reports/workbook.py tests/test_cli.py tests/reports/test_workbook.py
git commit -m "test: close metadata and integration coverage gaps"
```
