# Test and Fixture Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the v0 test and fixture strategy so default verification is deterministic, fixture-backed, network-free, and strict-static-analysis clean.

**Architecture:** The production pipeline already exists, so this plan hardens tests and documentation rather than introducing new runtime abstractions. Default tests use small UTF-8 CSV fixtures and monkeypatched source-client functions; optional live AKShare tests remain isolated under `tests/live/` with the `live_akshare` marker.

**Tech Stack:** Python 3.11, pytest, pandas, openpyxl, Typer, strict mypy, ruff, uv.

---

## Current Project State

Already completed:
- `uv run pytest` passes with `130 passed, 1 skipped`; the skipped test is `tests/live/test_akshare_smoke.py`.
- `uv run ruff check .` passes.
- Fixture convention tests already exist in `tests/test_fixture_strategy.py`.
- Live-test isolation and default AKShare network blocking already exist in `tests/conftest.py` and `tests/test_no_network_default.py`.
- Unit tests already cover CLI validation, domain models, universe selection, AKShare source-client wrapping, raw cache behavior, dividend normalization, price normalization, dividend yield metrics, one-year return metrics, pipeline sequencing, report assembly, and workbook writing.

Known remaining gap:
- `uv run mypy src tests` currently fails in `tests/test_pipeline.py` because three monkeypatch lambdas use `list.append()` in expressions. Strict mypy reports `func-returns-value` at lines 373, 401, and 408.

## File Structure

- Modify: `tests/test_pipeline.py`
  - Replace strict-mypy-hostile sequencing lambdas with typed local helper functions.
  - Add a fixture-backed integration test that runs `run_scan()` from CSV fixture source results, writes a workbook with `write_workbook()`, and checks workbook sheets, headers, cell values, source errors, metadata, and selected report rows.
- Modify: `tests/test_report_assembly.py`
  - Add an explicit test for required data-quality flag aggregation and ordering for missing cash dividend, missing ex-dividend date, missing reference price, return flags, and duplicate report period source errors.
- Create: `tests/fixtures/README.md`
  - Document fixture naming, size, encoding, live-test boundaries, and workbook-golden guidance.

## Task 1: Make Existing Pipeline Tests Strict-Mypy Clean

**Files:**
- Modify: `tests/test_pipeline.py:367-410`

- [ ] **Step 1: Run mypy to capture the current failure**

Run:

```bash
uv run mypy src tests
```

Expected: FAIL with these three errors:

```text
tests/test_pipeline.py:373: error: "append" of "list" does not return a value (it only ever returns None)  [func-returns-value]
tests/test_pipeline.py:401: error: "append" of "list" does not return a value (it only ever returns None)  [func-returns-value]
tests/test_pipeline.py:408: error: "append" of "list" does not return a value (it only ever returns None)  [func-returns-value]
```

- [ ] **Step 2: Replace expression lambdas with typed local helpers**

In `tests/test_pipeline.py`, inside `test_run_scan_sequences_source_cache_normalize_metrics_and_assembly`, replace the current `build_universe`, `write_cache`, `normalize_dividend_detail`, and `normalize_price_history` monkeypatch blocks with this code:

```python
    def fake_build_universe(
        frame: pd.DataFrame,
        universe: str,
        limit: int | None,
    ) -> tuple[list[StockIdentity], list[SourceErrorRow]]:
        stages.append("build_universe")
        return [stock], []

    def fake_write_cache(cache_dir: Path, key: str, frame: pd.DataFrame) -> None:
        stages.append(f"cache:{key.split('/')[0]}")

    def fake_normalize_dividend_detail(
        received_stock: StockIdentity,
        frame: pd.DataFrame,
    ) -> tuple[list[DividendRecord], list[SourceErrorRow]]:
        stages.append("normalize_dividend")
        return [dividend_record], []

    def fake_normalize_price_history(
        stock_code: str,
        frame: pd.DataFrame,
        metadata: SourceMetadata,
    ) -> tuple[list[PricePoint], list[SourceErrorRow]]:
        stages.append("normalize_price")
        return [price_point], []

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _stage_result(stages, "fetch_spot", "spot_fetch", "all_a"),
    )
    monkeypatch.setattr("future_ledger.pipeline.build_universe", fake_build_universe)
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_dividend_detail",
        lambda symbol: _stage_result(stages, "fetch_dividend", "dividend_fetch", symbol),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_price_history",
        lambda symbol, start_date, end_date: _stage_result(
            stages,
            "fetch_price",
            "price_fetch",
            symbol,
            request_start_date=start_date,
            request_end_date=end_date,
        ),
    )
    monkeypatch.setattr("future_ledger.pipeline.write_cache", fake_write_cache)
    monkeypatch.setattr(
        "future_ledger.pipeline.write_metadata",
        lambda cache_dir, key, metadata, empty: None,
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.normalize_dividend_detail",
        fake_normalize_dividend_detail,
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.normalize_price_history",
        fake_normalize_price_history,
    )
```

- [ ] **Step 3: Run the focused pipeline sequencing test**

Run:

```bash
uv run pytest tests/test_pipeline.py::test_run_scan_sequences_source_cache_normalize_metrics_and_assembly -q
```

Expected: PASS.

- [ ] **Step 4: Run mypy again**

Run:

```bash
uv run mypy src tests
```

Expected: PASS with:

```text
Success: no issues found in 34 source files
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: make pipeline sequencing test mypy clean"
```

## Task 2: Add Explicit Data-Quality Flag Coverage

**Files:**
- Modify: `tests/test_report_assembly.py`

- [ ] **Step 1: Add the failing report assembly flag test**

In `tests/test_report_assembly.py`, add this test after `test_assemble_report_tables_carries_source_errors_metadata_and_used_prices`:

```python
def test_assemble_report_tables_orders_required_data_quality_flags_from_inputs() -> None:
    stock = _stock("600000", "浦发银行", "SH")
    dividend = DividendRecord(
        stock_code="600000",
        stock_name="浦发银行",
        market="SH",
        report_year=2025,
        report_period="2025-12-31",
        cash_dividend_per_10_shares=None,
        cash_dividend_per_share=None,
        ex_dividend_date=None,
        registration_date=None,
        plan_status="实施",
        eps=None,
        net_asset_per_share=None,
        profit_growth_yoy_pct=None,
        provider_yield_pct=None,
        source="akshare.stock_fhps_detail_em",
    )
    duplicate_error = SourceErrorRow(
        stock_code="600000",
        stage="dividend_normalize",
        message="duplicate report period",
        raw_detail="kept implemented row",
    )

    tables = assemble_report_tables(
        config=_config(),
        stocks=[stock],
        dividends=[dividend],
        prices=[],
        dividend_metrics=[
            _dividend_metric(
                "600000",
                2025,
                None,
                None,
                flags=("missing_reference_price",),
            )
        ],
        return_metrics=[
            ReturnMetricInput(
                stock_code="600000",
                start_price_date=None,
                end_price_date=None,
                cash_dividends_1y=None,
                total_return_1y_pct=None,
                annualized_return_1y_pct=None,
                data_quality_flags=(
                    "missing_return_price",
                    "uncertain_dividend_window",
                    "invalid_return_start_price",
                ),
            )
        ],
        source_errors=[duplicate_error],
        source_metadata=[],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    assert tables.dividend_rank[0].data_quality_flags == (
        "has_missing_years_5y",
        "missing_cash_dividend",
        "missing_ex_dividend_date",
        "missing_reference_price",
        "missing_return_price",
        "uncertain_dividend_window",
        "invalid_return_start_price",
        "duplicate_report_period",
    )
```

- [ ] **Step 2: Run the new test**

Run:

```bash
uv run pytest tests/test_report_assembly.py::test_assemble_report_tables_orders_required_data_quality_flags_from_inputs -q
```

Expected: PASS. If this fails, inspect `DATA_QUALITY_FLAG_ORDER` and `_flags_from_source_errors()` in `src/future_ledger/report_assembly.py`; the expected behavior is the tuple shown in Step 1.

- [ ] **Step 3: Run report assembly tests**

Run:

```bash
uv run pytest tests/test_report_assembly.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_report_assembly.py
git commit -m "test: cover report data quality flag aggregation"
```

## Task 3: Add Fixture-Backed Pipeline-to-Workbook Integration

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add imports needed by the integration test**

In `tests/test_pipeline.py`, change the top imports to include `datetime`, `load_workbook`, and `write_workbook`:

```python
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pytest
from openpyxl import load_workbook  # type: ignore[import-untyped]

from future_ledger.cache import cache_key, read_cache, read_metadata, write_cache, write_metadata
from future_ledger.domain import (
    DividendRecord,
    PricePoint,
    ReportTables,
    RunConfig,
    SourceErrorRow,
    SourceFetchResult,
    SourceMetadata,
    StockIdentity,
)
from future_ledger.pipeline import run_scan
from future_ledger.workbook_writer import write_workbook
```

- [ ] **Step 2: Add the failing fixture integration test**

In `tests/test_pipeline.py`, add this test before `_config`:

```python
def test_pipeline_fixture_integration_writes_expected_report_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_root = Path("tests/fixtures")
    spot_frame = pd.read_csv(
        fixture_root / "akshare" / "spot_a_share.csv",
        dtype={"代码": str},
    )
    dividend_frame = pd.read_csv(fixture_root / "akshare" / "dividend_detail_600000.csv")
    price_frame = pd.read_csv(
        fixture_root / "prices" / "600000_daily_20250630_20260417.csv"
    )

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(spot_frame, "spot_fetch", "all_a", "stock_zh_a_spot_em"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_dividend_detail",
        lambda symbol: _result(
            dividend_frame,
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_price_history",
        lambda symbol, start_date, end_date: _result(
            price_frame,
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        ),
    )

    config = RunConfig(
        years=2,
        as_of=date(2026, 4, 17),
        universe="all-a-excluding-st",
        output=tmp_path / "fixture-report.xlsx",
        limit=1,
        cache_dir=tmp_path / "cache",
    )

    tables = run_scan(config)
    output = write_workbook(
        tables,
        config.output,
        workbook_timestamp=datetime(2026, 5, 14, 8, 30, 0),
    )

    workbook = load_workbook(output)
    rank_sheet = workbook["dividend_rank"]
    long_sheet = workbook["dividend_long"]
    price_sheet = workbook["price_points"]
    error_sheet = workbook["source_errors"]
    metadata_sheet = workbook["metadata"]

    assert tables.source_errors == []
    assert len(tables.dividend_rank) == 1
    assert tables.dividend_rank[0].stock_code == "600000"
    assert tables.dividend_rank[0].latest_dividend_yield_pct == Decimal("3.80")
    assert tables.dividend_rank[0].cash_dividends_1y == Decimal("0.38")
    assert tables.dividend_rank[0].total_return_1y_pct == Decimal("11.80")
    assert tables.dividend_rank[0].data_quality_flags == ()

    assert workbook.sheetnames == [
        "dividend_rank",
        "dividend_long",
        "price_points",
        "source_errors",
        "metadata",
    ]
    assert [cell.value for cell in rank_sheet[1]][:24] == [
        "rank_latest_yield",
        "stock_code",
        "stock_name",
        "market",
        "latest_report_year",
        "latest_cash_dividend_per_10_shares",
        "latest_cash_dividend_per_share",
        "reference_price",
        "reference_price_date",
        "latest_dividend_yield_pct",
        "dividend_yield_source",
        "dividend_year_count_5y",
        "continuous_dividend_5y",
        "avg_dividend_yield_pct_5y",
        "min_dividend_yield_pct_5y",
        "max_dividend_yield_pct_5y",
        "as_of_date",
        "cash_dividends_1y",
        "total_return_1y_pct",
        "annualized_return_1y_pct",
        "has_missing_years_5y",
        "data_quality_flags",
        "source_priority_used",
        "fetched_at",
    ]
    assert rank_sheet["A2"].value == 1
    assert rank_sheet["B2"].value == "600000"
    assert rank_sheet["C2"].value == "浦发银行"
    assert rank_sheet["J2"].value == 3.8
    assert rank_sheet["R2"].value == 0.38
    assert rank_sheet["S2"].value == 11.8
    assert rank_sheet["U2"].value is False
    assert rank_sheet["V2"].value is None
    assert long_sheet.max_row == 3
    assert price_sheet.max_row == 3
    assert error_sheet.max_row == 1

    metadata = {
        metadata_sheet.cell(row=index, column=1).value: metadata_sheet.cell(
            row=index,
            column=2,
        ).value
        for index in range(2, metadata_sheet.max_row + 1)
    }
    assert metadata["years"] == "2"
    assert metadata["as_of"] == "2026-04-17"
    assert metadata["source.price_fetch.600000.request_start_date"] == "20240417"
    assert metadata["source.price_fetch.600000.request_end_date"] == "20260417"
```

- [ ] **Step 3: Run the new integration test**

Run:

```bash
uv run pytest tests/test_pipeline.py::test_pipeline_fixture_integration_writes_expected_report_tables -q
```

Expected: PASS.

- [ ] **Step 4: Run all pipeline and workbook writer tests**

Run:

```bash
uv run pytest tests/test_pipeline.py tests/test_workbook_writer.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: add fixture-backed pipeline workbook integration"
```

## Task 4: Document Fixture Conventions

**Files:**
- Create: `tests/fixtures/README.md`

- [ ] **Step 1: Create the fixture README**

Create `tests/fixtures/README.md` with this exact content:

```markdown
# FutureLedger Test Fixtures

Default fixtures are deterministic UTF-8 CSV files used by `uv run pytest`.
They must not require live AKShare access.

## Naming

- `akshare/spot_a_share.csv`
- `akshare/dividend_detail_<symbol>.csv`
- `prices/<symbol>_daily_<start_date>_<end_date>.csv`
- `cache/<stage>/<cache_id>.csv`
- `workbooks/` is reserved for intentionally small golden `.xlsx` files.

Use six-digit A-share symbols and `YYYYMMDD` date ranges in filenames.

## Size

Default CSV fixtures should stay below 100 data rows. If a test needs a larger
fixture to validate large-frame behavior, document the reason in the test that
uses it.

## Live Data

Tests that call AKShare directly live under `tests/live/`, use the
`live_akshare` marker, and are skipped by default. Run them explicitly with:

```bash
uv run pytest tests/live -m live_akshare
```

## Workbook Goldens

Golden workbook fixtures should compare stable workbook structure: sheet names,
headers, cell types, number formats, and representative values. Do not compare
volatile generated timestamps unless the test supplies a fixed workbook timestamp.
```

- [ ] **Step 2: Run fixture strategy tests**

Run:

```bash
uv run pytest tests/test_fixture_strategy.py tests/test_no_network_default.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/README.md
git commit -m "docs: document test fixture conventions"
```

## Task 5: Final Verification

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run deterministic default tests**

Run:

```bash
uv run pytest
```

Expected: PASS with the live AKShare smoke test skipped.

- [ ] **Step 2: Run ruff**

Run:

```bash
uv run ruff check .
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Run strict mypy**

Run:

```bash
uv run mypy src tests
```

Expected:

```text
Success: no issues found in 34 source files
```

- [ ] **Step 4: Confirm live smoke isolation command**

Run:

```bash
uv run pytest tests/live -m live_akshare --collect-only -q
```

Expected: collection includes `tests/live/test_akshare_smoke.py::test_live_fetch_a_share_spot_smoke` and does not run a live network call.

- [ ] **Step 5: Commit final verification notes if any files changed during verification**

If verification produced no file changes, skip this commit. If a file changed, commit it with:

```bash
git add tests/test_pipeline.py tests/test_report_assembly.py tests/fixtures/README.md
git commit -m "test: complete deterministic fixture strategy"
```

## Self-Review

Spec coverage:
- Deterministic default suite: covered by existing `tests/conftest.py`, `tests/test_no_network_default.py`, and final `uv run pytest`.
- Fixture naming and size: covered by existing `tests/test_fixture_strategy.py` and new `tests/fixtures/README.md`.
- Optional live AKShare tests excluded from default CI: covered by existing live marker tests and collect-only live command.
- Static analysis expectations: covered by Task 1 and final `ruff` plus `mypy`.
- Data quality flags: covered by existing metric/report tests plus Task 2 for missing flag aggregation and `duplicate_report_period`.
- Pipeline-to-workbook integration from fixture source results: covered by Task 3.

Placeholder scan:
- No placeholder markers, incomplete tasks, or unspecified implementation steps.

Type consistency:
- All snippets use existing domain types: `RunConfig`, `SourceFetchResult`, `SourceMetadata`, `SourceErrorRow`, `StockIdentity`, `DividendRecord`, `PricePoint`, and `ReportTables`.
- Commands match the project configuration in `pyproject.toml`.
