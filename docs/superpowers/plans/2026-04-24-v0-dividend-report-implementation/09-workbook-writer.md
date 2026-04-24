### Task 9: Write The Excel Workbook And Metadata Sheet

**Files:**
- Create: `src/future_ledger/reports/workbook.py`
- Test: `tests/reports/test_workbook.py`

- [ ] **Step 1: Write failing workbook-shape tests**

```python
from pathlib import Path

import openpyxl

from future_ledger.domain import MetadataRow, ReportTables
from future_ledger.reports.workbook import write_workbook


def test_write_workbook_creates_required_sheets(tmp_path: Path):
    output = tmp_path / "dividend_rank.xlsx"
    tables = ReportTables(
        dividend_rank=[],
        dividend_long=[],
        price_points=[],
        source_errors=[],
        metadata=[MetadataRow(key="disclaimer", value="FutureLedger is for financial data research only.")],
    )

    write_workbook(output, tables)

    workbook = openpyxl.load_workbook(output)
    assert workbook.sheetnames == [
        "dividend_rank",
        "dividend_long",
        "price_points",
        "source_errors",
        "metadata",
    ]


def test_write_workbook_includes_disclaimer(tmp_path: Path):
    output = tmp_path / "dividend_rank.xlsx"
    tables = ReportTables(
        dividend_rank=[],
        dividend_long=[],
        price_points=[],
        source_errors=[],
        metadata=[MetadataRow(key="disclaimer", value="FutureLedger is for financial data research only. It does not provide investment advice, buy/sell recommendations, or portfolio allocation guidance.")],
    )
    write_workbook(output, tables)
    workbook = openpyxl.load_workbook(output)
    metadata_sheet = workbook["metadata"]
    assert "investment advice" in metadata_sheet["B2"].value
```

- [ ] **Step 2: Run tests to verify workbook writer is missing**

Run: `pytest tests/reports/test_workbook.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement workbook writing**

```python
import pandas as pd


def _records_to_frame(rows: list[object]) -> pd.DataFrame:
    return pd.DataFrame([asdict(row) for row in rows])


def write_workbook(output: Path, tables: ReportTables) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _records_to_frame(tables.dividend_rank).to_excel(writer, sheet_name="dividend_rank", index=False)
        _records_to_frame(tables.dividend_long).to_excel(writer, sheet_name="dividend_long", index=False)
        _records_to_frame(tables.price_points).to_excel(writer, sheet_name="price_points", index=False)
        _records_to_frame(tables.source_errors).to_excel(writer, sheet_name="source_errors", index=False)
        _records_to_frame(tables.metadata).to_excel(writer, sheet_name="metadata", index=False)
```

- [ ] **Step 4: Run tests to verify workbook writing passes**

Run: `pytest tests/reports/test_workbook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/future_ledger/reports/workbook.py tests/reports/test_workbook.py
git commit -m "feat: write dividend workbook sheets"
```
