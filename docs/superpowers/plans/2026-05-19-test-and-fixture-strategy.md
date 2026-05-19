# Test and Fixture Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the deterministic v0 verification strategy by closing the remaining data-quality coverage and fixture-driven pipeline-to-workbook integration gaps.

**Architecture:** Keep default tests offline by continuing to use small UTF-8 CSV fixtures, monkeypatched source calls, and `tests/live/` for optional AKShare smoke tests. The already-built normalizers, metrics, report assembly, workbook writer, fixture strategy tests, and no-network tests stay in place; this plan wires `run_scan()` through those completed modules and adds the missing coverage assertions.

**Tech Stack:** Python 3.11, pytest, pandas, openpyxl, Typer, Decimal, dataclasses, uv, ruff, strict mypy.

---

## Execution Prerequisite: Independent Branch

Development for this plan must happen on an isolated branch or worktree before any code edits.

- Branch name: `feature/test-and-fixture-strategy`
- The current repository contains untracked plan files from other features. Leave unrelated untracked files untouched.
- If using the main workspace directly, run:

```bash
git switch -c feature/test-and-fixture-strategy
```

- If using an isolated worktree, use the `superpowers:using-git-worktrees` skill at execution time and create a worktree from `feature/test-and-fixture-strategy`.
- Do not implement this plan on `main`, `feature/pipeline`, `feature/workbook-writer`, `feature/report-assembly`, or any unrelated branch.

## Scope Check

The spec covers one subsystem: project-wide deterministic tests and fixture strategy. The repository already satisfies most of the spec:

- `tests/test_fixture_strategy.py` validates fixture naming, UTF-8 readability, and the under-100-row default fixture limit.
- `tests/test_no_network_default.py` verifies `live_akshare` marker registration, marker isolation under `tests/live/`, and direct source-client network blocking in default tests.
- `tests/live/test_akshare_smoke.py` is marked `live_akshare` and is skipped by default.
- Unit tests already cover CLI validation, source fetching, raw cache behavior, universe selection, dividend normalization, price normalization, dividend yield, one-year return, report assembly, and workbook writer shape.
- `uv run pytest` currently passes with `123 passed, 1 skipped`.

Remaining work:

1. Add one explicit data-quality flag coverage matrix so every required flag in `2026-05-14-10-test-and-fixture-strategy-design.md` is asserted in `dividend_rank.data_quality_flags`.
2. Add the spec-named fixture integration test that runs fixture source results through `run_scan()`, writes the workbook, and verifies workbook sheet shape and representative values.
3. Update `src/future_ledger/pipeline.py` so `run_scan()` no longer returns only raw-cache metadata and empty report rows; it must normalize, calculate metrics, assemble report tables, and preserve existing cache/error behavior.
4. Run default tests, ruff, and strict mypy.

Out of scope:

- Large-universe performance tests.
- New live AKShare contract tests beyond the existing smoke test.
- Golden workbook binary fixture comparison.
- Production monitoring or historical backfill validation.

## File Structure

- Modify `tests/test_report_assembly.py`
  - Add a compact coverage matrix that asserts all required data-quality flags are carried into assembled rank rows.
  - This is test-only coverage over completed assembly behavior.

- Modify `tests/test_pipeline.py`
  - Update the one existing "successful fetches" cache test to use a valid dividend fixture-shaped frame, because `run_scan()` will start normalizing dividends.
  - Add `test_pipeline_fixture_integration_writes_expected_report_tables`.
  - Use existing fixture CSVs:
    - `tests/fixtures/akshare/spot_a_share.csv`
    - `tests/fixtures/akshare/dividend_detail_600000.csv`
    - `tests/fixtures/prices/600000_daily_20250630_20260417.csv`
  - Monkeypatch source functions instead of calling AKShare.
  - Call `write_workbook()` with a fixed workbook timestamp and inspect workbook headers and values with `openpyxl`.

- Modify `src/future_ledger/pipeline.py`
  - Keep raw cache write-through and cache rollback behavior.
  - Import and call `normalize_dividend_detail`, `normalize_price_history`, `resolve_reference_price`, `calculate_dividend_yield`, `calculate_trailing_one_year_return`, and `assemble_report_tables`.
  - Convert metric results into `DividendMetricInput` and `ReturnMetricInput`.
  - Preserve recoverable `SourceErrorRow` collection from source fetches, normalization, cache writes, universe selection, metrics, and assembly.
  - Generate deterministic report metadata from source metadata by using the max fetched-at timestamp already returned by monkeypatched fixtures.

No new fixture files are required for this plan. Existing fixture files are intentionally small and already match the naming convention.

---

### Task 1: Required Data-Quality Flag Coverage Matrix

**Files:**
- Modify: `tests/test_report_assembly.py`

- [ ] **Step 1: Add the flag coverage test**

Add this test in `tests/test_report_assembly.py`, after `test_assemble_report_tables_carries_source_errors_metadata_and_used_prices`:

```python
def test_assemble_report_tables_covers_required_data_quality_flags() -> None:
    stocks = [
        _stock("600000", "浦发银行", "SH"),
        _stock("000001", "平安银行", "SZ"),
    ]
    dividends = [
        DividendRecord(
            stock_code="000001",
            stock_name="平安银行",
            market="SZ",
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
    ]
    source_errors = [
        SourceErrorRow(
            stock_code="600000",
            stage="dividend_fetch",
            message="empty upstream frame",
            raw_detail=None,
        ),
        SourceErrorRow(
            stock_code="000001",
            stage="dividend_normalize",
            message="duplicate report period",
            raw_detail="{'报告期': '2025-12-31'}",
        ),
    ]

    tables = assemble_report_tables(
        config=_config(),
        stocks=stocks,
        dividends=dividends,
        prices=[],
        dividend_metrics=[
            DividendMetricInput(
                stock_code="000001",
                report_period="2025-12-31",
                reference_price=None,
                reference_price_date=None,
                dividend_yield_pct=None,
                dividend_yield_source="calculated_ex_dividend_close",
                data_quality_flags=("missing_reference_price",),
            )
        ],
        return_metrics=[
            ReturnMetricInput(
                stock_code="000001",
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
        source_errors=source_errors,
        source_metadata=[_source_metadata("600000"), _source_metadata("000001")],
        generated_at="2026-04-20T08:30:00+08:00",
    )

    observed_flags = {
        flag
        for row in tables.dividend_rank
        for flag in row.data_quality_flags
    }

    assert observed_flags >= {
        "no_valid_dividend_records",
        "has_missing_years_5y",
        "missing_cash_dividend",
        "missing_ex_dividend_date",
        "missing_reference_price",
        "missing_return_price",
        "uncertain_dividend_window",
        "invalid_return_start_price",
        "duplicate_report_period",
        "empty_dividend_detail",
    }
```

- [ ] **Step 2: Run the focused report assembly test**

Run:

```bash
uv run pytest tests/test_report_assembly.py::test_assemble_report_tables_covers_required_data_quality_flags -q
```

Expected: PASS. This confirms the already-completed report assembly module carries every required flag into rank rows.

- [ ] **Step 3: Commit the coverage-only test**

```bash
git add tests/test_report_assembly.py
git commit -m "test: cover required data quality flags"
```

---

### Task 2: Fixture-Based Pipeline and Workbook Integration Test

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Extend imports in the pipeline test**

Update the imports at the top of `tests/test_pipeline.py` to include `datetime`, `Decimal`, and `load_workbook`:

```python
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pytest
from openpyxl import load_workbook  # type: ignore[import-untyped]
```

Add this import near the existing pipeline import:

```python
from future_ledger.workbook_writer import write_workbook
```

- [ ] **Step 2: Update the existing successful-fetch cache test dividend frame**

In `test_run_scan_writes_raw_cache_snapshots_for_successful_fetches`, replace the `dividend_frame` assignment with a fixture-shaped frame that normalizes cleanly:

```python
    dividend_frame = pd.DataFrame(
        [
            {
                "报告期": "2025-12-31",
                "每10股派息": "4.10",
                "除权除息日": "2026-07-01",
                "股权登记日": "2026-06-30",
                "方案进度": "实施",
                "每股收益": "2.10",
                "每股净资产": "18.50",
                "净利润同比增长": "5.30",
                "现金分红-股息率": "4.00",
            }
        ]
    )
```

Also replace the cached dividend assertion in the same test with:

```python
    assert cached_dividend.astype(str).to_dict(orient="records") == [
        {
            "报告期": "2025-12-31",
            "每10股派息": "4.10",
            "除权除息日": "2026-07-01",
            "股权登记日": "2026-06-30",
            "方案进度": "实施",
            "每股收益": "2.10",
            "每股净资产": "18.50",
            "净利润同比增长": "5.30",
            "现金分红-股息率": "4.00",
        }
    ]
```

- [ ] **Step 3: Add the fixture integration test**

Add this test after `test_run_scan_writes_raw_cache_snapshots_for_successful_fetches`:

```python
def test_pipeline_fixture_integration_writes_expected_report_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spot_frame = pd.read_csv(Path("tests/fixtures/akshare/spot_a_share.csv"))
    dividend_frame = pd.read_csv(Path("tests/fixtures/akshare/dividend_detail_600000.csv"))
    price_frame = pd.read_csv(Path("tests/fixtures/prices/600000_daily_20250630_20260417.csv"))

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
        output=tmp_path / "report.xlsx",
        limit=1,
        cache_dir=tmp_path / "cache",
    )

    tables = run_scan(config)
    output = write_workbook(
        tables,
        config.output,
        workbook_timestamp=datetime(2026, 5, 14, 8, 30, 0),
    )

    assert tables.source_errors == []
    assert len(tables.dividend_rank) == 1
    rank_row = tables.dividend_rank[0]
    assert rank_row.stock_code == "600000"
    assert rank_row.stock_name == "浦发银行"
    assert rank_row.latest_report_year == 2025
    assert rank_row.latest_cash_dividend_per_share == Decimal("0.41")
    assert rank_row.reference_price == Decimal("10.80")
    assert rank_row.reference_price_date == date(2026, 4, 17)
    assert rank_row.latest_dividend_yield_pct == Decimal("3.80")
    assert rank_row.dividend_year_count_5y == 2
    assert rank_row.continuous_dividend_5y is True
    assert rank_row.data_quality_flags == ()

    assert [row.report_year for row in tables.dividend_long] == [2025, 2024]
    assert [(point.stock_code, point.date) for point in tables.price_points] == [
        ("600000", date(2025, 6, 30)),
        ("600000", date(2026, 4, 17)),
    ]

    workbook = load_workbook(output)
    assert workbook.sheetnames == [
        "dividend_rank",
        "dividend_long",
        "price_points",
        "source_errors",
        "metadata",
    ]
    rank_sheet = workbook["dividend_rank"]
    assert rank_sheet["B2"].value == "600000"
    assert rank_sheet["C2"].value == "浦发银行"
    assert rank_sheet["F2"].value == 4.1
    assert rank_sheet["J2"].value == 3.8
    assert workbook["dividend_long"].max_row == 3
    assert workbook["price_points"].max_row == 3
    assert workbook["source_errors"].max_row == 1
```

- [ ] **Step 4: Run the new integration test and verify it fails**

Run:

```bash
uv run pytest tests/test_pipeline.py::test_pipeline_fixture_integration_writes_expected_report_tables -q
```

Expected: FAIL because `run_scan()` currently returns empty `dividend_rank`, `dividend_long`, and `price_points` rows after cache write-through.

- [ ] **Step 5: Commit the failing integration test**

```bash
git add tests/test_pipeline.py
git commit -m "test: add fixture pipeline workbook integration"
```

---

### Task 3: Wire `run_scan()` Through Normalization, Metrics, and Assembly

**Files:**
- Modify: `src/future_ledger/pipeline.py`

- [ ] **Step 1: Replace the pipeline implementation with the assembled scan flow**

Replace `src/future_ledger/pipeline.py` with:

```python
"""Pipeline orchestration for the dividend scan."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from future_ledger.cache import cache_key, cache_snapshot_paths, write_cache, write_metadata
from future_ledger.domain import (
    DividendRecord,
    PricePoint,
    ReportTables,
    RunConfig,
    SourceErrorRow,
    SourceFetchResult,
    SourceMetadata,
)
from future_ledger.metrics.dividend_yield import (
    DIVIDEND_YIELD_SOURCE,
    calculate_dividend_yield,
    resolve_reference_price,
)
from future_ledger.metrics.returns import calculate_trailing_one_year_return
from future_ledger.normalize.dividends import normalize_dividend_detail
from future_ledger.normalize.prices import normalize_price_history
from future_ledger.report_assembly import (
    DividendMetricInput,
    ReturnMetricInput,
    assemble_report_tables,
)
from future_ledger.sources.akshare_client import (
    fetch_a_share_spot,
    fetch_dividend_detail,
    fetch_price_history,
)
from future_ledger.sources.universe import build_universe


def run_scan(config: RunConfig) -> ReportTables:
    """Fetch, cache, normalize, score, and assemble the v0 dividend report."""
    source_errors: list[SourceErrorRow] = []
    source_metadata: list[SourceMetadata] = []

    spot_result = fetch_a_share_spot()
    source_metadata.append(spot_result.metadata)
    source_errors.extend(_source_errors_from_result(spot_result))
    source_errors.extend(
        _write_raw_cache_snapshot(
            config=config,
            key=cache_key("spot", "all_a"),
            result=spot_result,
        )
    )

    if spot_result.frame.empty:
        return assemble_report_tables(
            config=config,
            stocks=[],
            dividends=[],
            prices=[],
            dividend_metrics=[],
            return_metrics=[],
            source_errors=source_errors,
            source_metadata=source_metadata,
            generated_at=_generated_at(source_metadata),
        )

    stocks, universe_errors = build_universe(
        spot_result.frame,
        universe=config.universe,
        limit=config.limit,
    )
    source_errors.extend(universe_errors)

    all_dividends: list[DividendRecord] = []
    all_prices: list[PricePoint] = []
    dividend_metrics: list[DividendMetricInput] = []
    return_metrics: list[ReturnMetricInput] = []

    start_date, end_date = _price_window(config.as_of, config.years)
    for stock in stocks:
        dividend_result = fetch_dividend_detail(stock.code)
        source_metadata.append(dividend_result.metadata)
        source_errors.extend(_source_errors_from_result(dividend_result))
        source_errors.extend(
            _write_raw_cache_snapshot(
                config=config,
                key=cache_key("dividend_detail", stock.code),
                result=dividend_result,
            )
        )
        dividend_records, dividend_errors = normalize_dividend_detail(
            stock,
            dividend_result.frame,
        )
        source_errors.extend(dividend_errors)
        all_dividends.extend(dividend_records)

        price_result = fetch_price_history(stock.code, start_date, end_date)
        source_metadata.append(price_result.metadata)
        source_errors.extend(_source_errors_from_result(price_result))
        source_errors.extend(
            _write_raw_cache_snapshot(
                config=config,
                key=cache_key(
                    "price_history",
                    stock.code,
                    start_date=start_date,
                    end_date=end_date,
                ),
                result=price_result,
            )
        )
        price_points, price_errors = normalize_price_history(
            stock.code,
            price_result.frame,
            price_result.metadata,
        )
        source_errors.extend(price_errors)
        all_prices.extend(price_points)

        dividend_metrics.extend(_dividend_metrics(dividend_records, price_points))
        return_metrics.append(
            _return_metric(
                stock_code=stock.code,
                as_of=config.as_of,
                prices=price_points,
                dividends=dividend_records,
            )
        )

    return assemble_report_tables(
        config=config,
        stocks=stocks,
        dividends=all_dividends,
        prices=all_prices,
        dividend_metrics=dividend_metrics,
        return_metrics=return_metrics,
        source_errors=source_errors,
        source_metadata=source_metadata,
        generated_at=_generated_at(source_metadata),
    )


def _dividend_metrics(
    dividends: Sequence[DividendRecord],
    prices: Sequence[PricePoint],
) -> list[DividendMetricInput]:
    metrics: list[DividendMetricInput] = []
    price_points = list(prices)
    for record in dividends:
        reference = resolve_reference_price(price_points, record.ex_dividend_date)
        yield_result = calculate_dividend_yield(
            cash_dividend_per_share=record.cash_dividend_per_share,
            reference_price=reference.reference_price,
        )
        metrics.append(
            DividendMetricInput(
                stock_code=record.stock_code,
                report_period=record.report_period,
                reference_price=reference.reference_price,
                reference_price_date=reference.reference_price_date,
                dividend_yield_pct=yield_result.dividend_yield_pct,
                dividend_yield_source=DIVIDEND_YIELD_SOURCE,
                data_quality_flags=yield_result.data_quality_flags,
            )
        )
    return metrics


def _return_metric(
    *,
    stock_code: str,
    as_of: date,
    prices: Sequence[PricePoint],
    dividends: Sequence[DividendRecord],
) -> ReturnMetricInput:
    result = calculate_trailing_one_year_return(
        stock_code=stock_code,
        as_of=as_of,
        prices=list(prices),
        dividends=list(dividends),
    )
    return ReturnMetricInput(
        stock_code=stock_code,
        start_price_date=result.start_price_date,
        end_price_date=result.end_price_date,
        cash_dividends_1y=result.cash_dividends_1y,
        total_return_1y_pct=result.total_return_1y_pct,
        annualized_return_1y_pct=result.annualized_return_1y_pct,
        data_quality_flags=result.return_data_quality_flags,
    )


def _write_raw_cache_snapshot(
    *,
    config: RunConfig,
    key: str,
    result: SourceFetchResult,
) -> list[SourceErrorRow]:
    if not _is_cacheable(result):
        return []

    cache_path, metadata_path = cache_snapshot_paths(config.cache_dir, key)
    try:
        original_cache = _read_existing_bytes(cache_path)
        original_metadata = _read_existing_bytes(metadata_path)
    except OSError as exc:
        return [_cache_write_error(result, key, exc)]

    try:
        write_cache(config.cache_dir, key, result.frame)
        write_metadata(config.cache_dir, key, result.metadata, empty=result.frame.empty)
    except OSError as exc:
        _restore_cache_file(cache_path, original_cache)
        _restore_cache_file(metadata_path, original_metadata)
        return [_cache_write_error(result, key, exc)]
    return []


def _read_existing_bytes(path: Path) -> bytes | None:
    if not path.exists():
        return None
    return path.read_bytes()


def _restore_cache_file(path: Path, content: bytes | None) -> None:
    try:
        if content is None:
            path.unlink(missing_ok=True)
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    except OSError:
        return


def _cache_write_error(result: SourceFetchResult, key: str, exc: OSError) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=result.metadata.symbol,
        stage="cache_write",
        message=f"{exc.__class__.__name__}: {exc}",
        raw_detail=key,
    )


def _is_cacheable(result: SourceFetchResult) -> bool:
    if result.error is None:
        return True
    return result.error.message == "empty upstream frame"


def _source_errors_from_result(result: SourceFetchResult) -> list[SourceErrorRow]:
    if result.error is None:
        return []
    return [result.error]


def _price_window(as_of: date, years: int) -> tuple[str, str]:
    start = _replace_year_with_feb_28_fallback(as_of, as_of.year - years)
    return _yyyymmdd(start), _yyyymmdd(as_of)


def _replace_year_with_feb_28_fallback(value: date, year: int) -> date:
    try:
        return value.replace(year=year)
    except ValueError:
        return value.replace(year=year, day=28)


def _yyyymmdd(value: date) -> str:
    return value.strftime("%Y%m%d")


def _generated_at(source_metadata: Sequence[SourceMetadata]) -> str:
    if not source_metadata:
        return ""
    return max(metadata.fetched_at for metadata in source_metadata)
```

- [ ] **Step 2: Run the new integration test and verify it passes**

Run:

```bash
uv run pytest tests/test_pipeline.py::test_pipeline_fixture_integration_writes_expected_report_tables -q
```

Expected: PASS.

- [ ] **Step 3: Run all pipeline tests**

Run:

```bash
uv run pytest tests/test_pipeline.py -q
```

Expected: PASS. The cache rollback and per-stock continuation tests must keep passing while `run_scan()` now returns populated report tables when input frames are valid.

- [ ] **Step 4: Commit the pipeline integration implementation**

```bash
git add src/future_ledger/pipeline.py tests/test_pipeline.py
git commit -m "feat: assemble report tables in pipeline"
```

---

### Task 4: Full Deterministic Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run the default offline test suite**

Run:

```bash
uv run pytest
```

Expected: PASS with the existing live AKShare smoke test skipped by default.

- [ ] **Step 2: Run fixture and no-network tests explicitly**

Run:

```bash
uv run pytest tests/test_fixture_strategy.py tests/test_no_network_default.py -q
```

Expected: PASS.

- [ ] **Step 3: Run the optional live command shape without enabling live endpoints**

Run:

```bash
uv run pytest tests/live -m live_akshare --collect-only -q
```

Expected: collection succeeds and reports `tests/live/test_akshare_smoke.py::test_live_fetch_a_share_spot_smoke`. Do not run the live test during default CI verification.

- [ ] **Step 4: Run ruff**

Run:

```bash
uv run ruff check .
```

Expected: PASS.

- [ ] **Step 5: Run strict mypy**

Run:

```bash
uv run mypy src tests
```

Expected: PASS.

- [ ] **Step 6: Commit verification notes only if files changed**

If no files changed during verification, do not create a commit. If a formatter or type fix changed files, stage only those files and commit:

```bash
git add src/future_ledger/pipeline.py tests/test_pipeline.py tests/test_report_assembly.py
git commit -m "chore: satisfy deterministic verification"
```

---

## Self-Review

Spec coverage:

- Deterministic default test suite: covered by Task 4 `uv run pytest`.
- Fixture naming conventions: already covered by `tests/test_fixture_strategy.py`; explicitly rerun in Task 4.
- Live AKShare smoke tests excluded from default CI: already covered by `tests/test_no_network_default.py`; explicitly rerun in Task 4.
- Static analysis expectations: Task 4 runs `ruff` and strict `mypy`.
- Data quality flags: Task 1 asserts all required flags.
- Integration from fixture source results to workbook shape: Task 2 writes the failing integration test; Task 3 implements the pipeline path.
- Known review risks from module index: cache rollback, per-stock continuation, source errors, flags, workbook shape, and no-network defaults remain covered by existing tests plus the new integration test.

Placeholder scan:

- No placeholder markers or vague edge-case steps are present.
- Every code-changing step includes concrete code.
- Commands include expected outcomes.

Type consistency:

- `DividendMetricInput` and `ReturnMetricInput` field names match `src/future_ledger/report_assembly.py`.
- Metric result field names match `src/future_ledger/metrics/dividend_yield.py` and `src/future_ledger/metrics/returns.py`.
- Source result and metadata field names match `src/future_ledger/domain.py`.
