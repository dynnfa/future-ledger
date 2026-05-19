# CLI Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect `future-ledger dividends scan` to the full local v0 dividend workflow and write the populated workbook requested by the CLI.

**Architecture:** Keep CLI responsibilities narrow: validate pre-run arguments, build `RunConfig`, call `run_scan(config)`, call `write_workbook(tables, config.output)`, and print a concise completion summary. Keep pipeline responsibilities inside `run_scan(config)`: fetch sources, build the universe, write raw cache snapshots, normalize raw frames, calculate metrics, assemble `ReportTables`, and return recoverable per-stock errors without writing the workbook.

**Tech Stack:** Python 3.11, Typer, pandas, openpyxl, dataclasses, `Decimal`, pytest, uv.

---

## Execution Prerequisite: Independent Branch

Development for this plan must happen on an isolated branch or worktree before any code edits.

- Branch name: `feature/cli-pipeline`
- The current repository may contain untracked plan files from other features. Leave unrelated untracked files untouched.
- If using the main workspace directly, run:

```bash
git switch -c feature/cli-pipeline
```

- If using an isolated worktree, use the `superpowers:using-git-worktrees` skill at execution time and create a worktree from `feature/cli-pipeline`.
- Do not implement this plan on `main`, `feature/workbook-writer`, `feature/report-assembly`, `feature/metrics`, `feature/price-normalization`, `feature/dividend-normalization`, `feature/raw-cache`, `feature/source-fetching`, or any unrelated branch.

## Dependency Prerequisite

Execute this plan only after these subsystem plans have been merged into the implementation branch or are already present in the working tree:

- `docs/superpowers/plans/2026-05-15-universe-selection.md`
- `docs/superpowers/plans/2026-05-15-source-fetching.md`
- `docs/superpowers/plans/2026-05-15-raw-cache.md`
- `docs/superpowers/plans/2026-05-18-dividend-normalization.md`
- `docs/superpowers/plans/2026-05-18-price-normalization.md`
- `docs/superpowers/plans/2026-05-18-metrics.md`
- `docs/superpowers/plans/2026-05-18-report-assembly.md`
- `docs/superpowers/plans/2026-05-18-workbook-writer.md`

Required public interfaces from those plans:

```python
from future_ledger.normalize.dividends import normalize_dividend_detail
from future_ledger.normalize.prices import normalize_price_history
from future_ledger.metrics.dividend_yield import (
    DIVIDEND_YIELD_SOURCE,
    calculate_dividend_yield,
    resolve_reference_price,
)
from future_ledger.metrics.returns import calculate_trailing_one_year_return
from future_ledger.report_assembly import (
    DividendMetricInput,
    ReturnMetricInput,
    assemble_report_tables,
)
from future_ledger.workbook_writer import write_workbook
```

## Scope Check

The spec covers one integration layer: CLI validation and pipeline orchestration. It does not reimplement universe selection, source fetching, raw cache persistence, normalization rules, metrics math, report assembly layout, or workbook serialization.

This plan intentionally adds only the glue, fatal CLI validation, progress messages, and integration tests needed to prove the existing subsystem contracts run in the declared order.

## File Structure

- Modify `src/future_ledger/cli.py`
  - Validate `--output` suffix before source fetching.
  - Validate existing `--cache-dir` paths before source fetching.
  - Reject unsupported `--universe` before source fetching.
  - Convert workbook writer `ConfigError` into a non-zero CLI failure after `run_scan()` succeeds.
  - Print universe size, processed stock count, source error count, workbook path, and ranked row count.

- Modify `tests/test_cli.py`
  - Add pre-run validation tests for non-`.xlsx` output, cache path shape, and unsupported universe.
  - Add a call-order test proving `write_workbook(tables, config.output)` happens after `run_scan(config)`.
  - Add a writer `ConfigError` test proving source fetching is not retried.
  - Update the valid scan assertion to include the concrete workbook and progress messages.

- Modify `src/future_ledger/pipeline.py`
  - Keep raw cache snapshot helpers.
  - Replace the empty-report return path with normalization, metrics, and report assembly.
  - Preserve recoverable fetch, parse, metric, and cache write failures as `SourceErrorRow`.
  - Let fatal universe frame errors raise out of `run_scan()`.
  - Never call `write_workbook()`.

- Modify `tests/test_pipeline.py`
  - Add an orchestration-order test with fakes for every stage.
  - Add a recoverable per-stock source-error test proving one failed stock does not prevent a successful rank row for another stock.
  - Keep existing raw cache behavior tests passing.

---

### Task 1: Tighten CLI Validation and Completion Output

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/future_ledger/cli.py`

- [ ] **Step 1: Add failing CLI validation and writer call-order tests**

Add these imports to `tests/test_cli.py`:

```python
from datetime import date
from decimal import Decimal

from future_ledger.domain import DividendRankRow, SourceErrorRow
from future_ledger.errors import ConfigError
```

Add these tests after `test_scan_valid_as_of`:

```python
def test_scan_writes_workbook_after_run_scan(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    tables = ReportTables(
        dividend_rank=[_rank_row("600000")],
        dividend_long=[],
        price_points=[],
        source_errors=[
            SourceErrorRow(
                stock_code="000001",
                stage="dividend_fetch",
                message="RuntimeError: upstream unavailable",
                raw_detail=None,
            )
        ],
        metadata=[],
    )

    def fake_run_scan(config: RunConfig) -> ReportTables:
        calls.append(f"run:{config.output}")
        return tables

    def fake_write_workbook(received_tables: ReportTables, output: Path) -> Path:
        calls.append(f"write:{output}")
        assert received_tables is tables
        return tmp_path / "written.xlsx"

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
    monkeypatch.setattr("future_ledger.cli.write_workbook", fake_write_workbook)

    result = runner.invoke(
        app,
        [
            "dividends",
            "scan",
            "--as-of",
            "2026-04-20",
            "--output",
            str(tmp_path / "report.xlsx"),
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        f"run:{tmp_path / 'report.xlsx'}",
        f"write:{tmp_path / 'report.xlsx'}",
    ]
    assert "Universe size: 1" in result.output
    assert "Processed stocks: 1" in result.output
    assert "Source errors: 1" in result.output
    assert f"Workbook written: {tmp_path / 'written.xlsx'}" in result.output
    assert "Rows ranked: 1" in result.output


def test_scan_rejects_non_xlsx_output(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called = False

    def fake_run_scan(config: RunConfig) -> ReportTables:
        nonlocal called
        called = True
        return ReportTables.empty()

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)

    result = runner.invoke(
        app,
        ["dividends", "scan", "--output", str(tmp_path / "report.csv")],
    )

    assert result.exit_code != 0
    assert "--output must end with .xlsx" in result.output
    assert called is False


def test_scan_rejects_cache_dir_that_is_file(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache_file = tmp_path / "cache-file"
    cache_file.write_text("not a directory")
    called = False

    def fake_run_scan(config: RunConfig) -> ReportTables:
        nonlocal called
        called = True
        return ReportTables.empty()

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)

    result = runner.invoke(
        app,
        ["dividends", "scan", "--cache-dir", str(cache_file)],
    )

    assert result.exit_code != 0
    assert "--cache-dir must be a directory path" in result.output
    assert called is False


def test_scan_rejects_unsupported_universe_before_run_scan(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_run_scan(config: RunConfig) -> ReportTables:
        nonlocal called
        called = True
        return ReportTables.empty()

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)

    result = runner.invoke(app, ["dividends", "scan", "--universe", "unknown"])

    assert result.exit_code != 0
    assert "Unsupported universe: unknown" in result.output
    assert called is False


def test_scan_reports_workbook_config_error_without_rerunning_scan(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_run_scan(config: RunConfig) -> ReportTables:
        calls.append("run")
        return ReportTables.empty()

    def fake_write_workbook(tables: ReportTables, output: Path) -> Path:
        calls.append("write")
        raise ConfigError("failed to write workbook")

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
    monkeypatch.setattr("future_ledger.cli.write_workbook", fake_write_workbook)

    result = runner.invoke(
        app,
        ["dividends", "scan", "--output", str(tmp_path / "report.xlsx")],
    )

    assert result.exit_code != 0
    assert "failed to write workbook" in result.output
    assert calls == ["run", "write"]
```

Add this helper at the bottom of `tests/test_cli.py`:

```python
def _rank_row(stock_code: str) -> DividendRankRow:
    return DividendRankRow(
        rank_latest_yield=1,
        stock_code=stock_code,
        stock_name="浦发银行",
        market="SH",
        latest_report_year=2025,
        latest_cash_dividend_per_10_shares=Decimal("4.10"),
        latest_cash_dividend_per_share=Decimal("0.41"),
        reference_price=Decimal("10.00"),
        reference_price_date=date(2025, 7, 1),
        latest_dividend_yield_pct=Decimal("4.10"),
        dividend_yield_source="calculated_ex_dividend_close",
        dividend_year_count_5y=1,
        continuous_dividend_5y=False,
        avg_dividend_yield_pct_5y=Decimal("4.10"),
        min_dividend_yield_pct_5y=Decimal("4.10"),
        max_dividend_yield_pct_5y=Decimal("4.10"),
        as_of_date=date(2026, 4, 20),
        cash_dividends_1y=Decimal("0.41"),
        total_return_1y_pct=Decimal("6.50"),
        annualized_return_1y_pct=Decimal("6.50"),
        has_missing_years_5y=True,
        data_quality_flags=(),
        source_priority_used="akshare.stock_fhps_detail_em",
        fetched_at="2026-05-14T08:30:00+00:00",
        annual_fields={},
    )
```

- [ ] **Step 2: Run the CLI tests and verify they fail**

Run:

```bash
uv run pytest tests/test_cli.py -q
```

Expected: FAIL because `--output`, `--cache-dir`, unsupported universe, and writer `ConfigError` are not fully handled yet.

- [ ] **Step 3: Implement CLI validation and progress output**

Update `src/future_ledger/cli.py` to include these imports:

```python
from future_ledger.errors import ConfigError
from future_ledger.sources.universe import SUPPORTED_UNIVERSE
```

Add these validation helpers after `_validate_limit`:

```python
def _validate_universe(universe: str) -> str:
    """Validate that --universe is supported before source fetching starts."""
    if universe != SUPPORTED_UNIVERSE:
        raise typer.BadParameter(f"Unsupported universe: {universe}")
    return universe


def _validate_output(output: Path) -> Path:
    """Validate the workbook output path shape before source fetching starts."""
    if output.suffix != ".xlsx":
        raise typer.BadParameter("--output must end with .xlsx")
    return output


def _validate_cache_dir(cache_dir: Path) -> Path:
    """Validate that an existing --cache-dir path is a directory."""
    if cache_dir.exists() and not cache_dir.is_dir():
        raise typer.BadParameter("--cache-dir must be a directory path")
    return cache_dir
```

Replace the body of `scan()` with:

```python
    validated_years = _validate_years(years)
    validated_limit = _validate_limit(limit)
    validated_universe = _validate_universe(universe)
    validated_output = _validate_output(output)
    validated_cache_dir = _validate_cache_dir(cache_dir)
    as_of_date = _parse_as_of(as_of)
    config = RunConfig(
        years=validated_years,
        as_of=as_of_date,
        universe=validated_universe,
        output=validated_output,
        limit=validated_limit,
        cache_dir=validated_cache_dir,
    )
    tables = run_scan(config)
    try:
        written_path = write_workbook(tables, config.output)
    except ConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc

    universe_size = len(tables.dividend_rank)
    processed_count = len(tables.dividend_rank)
    typer.echo(f"Universe size: {universe_size}")
    typer.echo(f"Processed stocks: {processed_count}")
    typer.echo(f"Source errors: {len(tables.source_errors)}")
    typer.echo(f"Workbook written: {written_path}")
    typer.echo(f"Rows ranked: {len(tables.dividend_rank)}")
```

- [ ] **Step 4: Run the CLI tests and verify they pass**

Run:

```bash
uv run pytest tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the CLI validation change**

```bash
git add src/future_ledger/cli.py tests/test_cli.py
git commit -m "feat: validate scan CLI before pipeline"
```

---

### Task 2: Add Pipeline Orchestration Tests

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add imports for pipeline integration assertions**

Add these imports to `tests/test_pipeline.py`:

```python
from datetime import date
from decimal import Decimal

from future_ledger.domain import (
    DividendRecord,
    DividendRankRow,
    PricePoint,
    ReportTables,
    StockIdentity,
)
```

If `date` is already imported in this file, keep a single combined import.

- [ ] **Step 2: Add a pipeline order test**

Add this test before the existing helper functions:

```python
def test_run_scan_sequences_source_cache_normalize_metrics_and_assembly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stages: list[str] = []
    stock = StockIdentity(code="600000", name="浦发银行", market="SH")
    dividend_record = DividendRecord(
        stock_code="600000",
        stock_name="浦发银行",
        market="SH",
        report_year=2025,
        report_period="2025-12-31",
        cash_dividend_per_10_shares=Decimal("4.10"),
        cash_dividend_per_share=Decimal("0.41"),
        ex_dividend_date=date(2025, 7, 1),
        source="akshare.stock_fhps_detail_em",
    )
    price_point = PricePoint(
        stock_code="600000",
        date=date(2025, 7, 1),
        close=Decimal("10.00"),
    )

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _stage_result(stages, "fetch_spot", "spot_fetch", "all_a"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.build_universe",
        lambda frame, universe, limit: (stages.append("build_universe") or [stock], []),
    )
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
    monkeypatch.setattr(
        "future_ledger.pipeline.write_cache",
        lambda cache_dir, key, frame: stages.append(f"cache:{key.split('/')[0]}"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.write_metadata",
        lambda cache_dir, key, metadata, empty: None,
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.normalize_dividend_detail",
        lambda received_stock, frame: (
            stages.append("normalize_dividend") or [dividend_record],
            [],
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.normalize_price_history",
        lambda stock_code, frame, metadata: (
            stages.append("normalize_price") or [price_point],
            [],
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.resolve_reference_price",
        lambda points, ex_dividend_date: _reference_price(stages),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.calculate_dividend_yield",
        lambda cash_dividend_per_share, reference_price: _dividend_yield(stages),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.calculate_trailing_one_year_return",
        lambda stock_code, as_of, prices, dividends: _return_result(stages, as_of),
    )

    def fake_assemble_report_tables(**kwargs: object) -> ReportTables:
        stages.append("assemble")
        assert kwargs["stocks"] == [stock]
        assert kwargs["dividends"] == [dividend_record]
        assert kwargs["prices"] == [price_point]
        return ReportTables.empty()

    monkeypatch.setattr(
        "future_ledger.pipeline.assemble_report_tables",
        fake_assemble_report_tables,
    )

    run_scan(_config(tmp_path))

    assert stages == [
        "fetch_spot",
        "build_universe",
        "cache:spot",
        "fetch_dividend",
        "fetch_price",
        "cache:dividend_detail",
        "cache:price_history",
        "normalize_dividend",
        "normalize_price",
        "resolve_reference_price",
        "calculate_dividend_yield",
        "calculate_return",
        "assemble",
    ]
```

- [ ] **Step 3: Add a recoverable per-stock source-error test**

Add this test after the order test:

```python
def test_run_scan_continues_after_per_stock_source_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stocks = [
        StockIdentity(code="600000", name="浦发银行", market="SH"),
        StockIdentity(code="000001", name="平安银行", market="SZ"),
    ]
    calls: list[str] = []

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(
            pd.DataFrame([{"代码": "600000"}, {"代码": "000001"}]),
            "spot_fetch",
            "all_a",
            "stock_zh_a_spot_em",
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.build_universe",
        lambda frame, universe, limit: (stocks, []),
    )

    def fake_dividend(symbol: str) -> SourceFetchResult:
        calls.append(f"dividend:{symbol}")
        if symbol == "600000":
            return _result(
                pd.DataFrame(),
                "dividend_fetch",
                symbol,
                "stock_fhps_detail_em",
                error=SourceErrorRow(
                    stock_code=symbol,
                    stage="dividend_fetch",
                    message="RuntimeError: upstream unavailable",
                    raw_detail=None,
                ),
            )
        return _result(
            pd.DataFrame([{"报告期": "2025-12-31", "每10股派息": "4.10"}]),
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
        )

    def fake_price(symbol: str, start_date: str, end_date: str) -> SourceFetchResult:
        calls.append(f"price:{symbol}")
        return _result(
            pd.DataFrame([{"日期": "2025-07-01", "收盘": "10.00"}]),
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        )

    monkeypatch.setattr("future_ledger.pipeline.fetch_dividend_detail", fake_dividend)
    monkeypatch.setattr("future_ledger.pipeline.fetch_price_history", fake_price)

    tables = run_scan(_config(tmp_path))

    assert calls == [
        "dividend:600000",
        "price:600000",
        "dividend:000001",
        "price:000001",
    ]
    assert any(
        row.stock_code == "600000"
        and row.stage == "dividend_fetch"
        and "upstream unavailable" in row.message
        for row in tables.source_errors
    )
    assert any(row.stock_code == "000001" for row in tables.dividend_rank)
```

- [ ] **Step 4: Add the pipeline test helper objects**

Add these helpers near the existing `_config` and `_result` helpers:

```python
def _stage_result(
    stages: list[str],
    stage_name: str,
    source_stage: str,
    symbol: str,
    *,
    request_start_date: str | None = None,
    request_end_date: str | None = None,
) -> SourceFetchResult:
    stages.append(stage_name)
    return _result(
        pd.DataFrame([{"value": symbol}]),
        source_stage,
        symbol,
        source_stage,
        request_start_date=request_start_date,
        request_end_date=request_end_date,
    )


def _reference_price(stages: list[str]) -> object:
    stages.append("resolve_reference_price")
    return type(
        "ReferencePrice",
        (),
        {
            "reference_price": Decimal("10.00"),
            "reference_price_date": date(2025, 7, 1),
        },
    )()


def _dividend_yield(stages: list[str]) -> object:
    stages.append("calculate_dividend_yield")
    return type(
        "DividendYield",
        (),
        {
            "dividend_yield_pct": Decimal("4.10"),
            "data_quality_flags": (),
        },
    )()


def _return_result(stages: list[str], as_of: date) -> object:
    stages.append("calculate_return")
    return type(
        "ReturnResult",
        (),
        {
            "as_of_date": as_of,
            "return_window_start": date(as_of.year - 1, as_of.month, as_of.day),
            "return_window_end": as_of,
            "start_close_price": Decimal("10.00"),
            "start_price_date": date(2025, 4, 20),
            "end_close_price": Decimal("10.65"),
            "end_price_date": as_of,
            "cash_dividends_1y": Decimal("0.41"),
            "total_return_1y_pct": Decimal("10.60"),
            "annualized_return_1y_pct": Decimal("10.60"),
            "return_data_quality_flags": (),
        },
    )()
```

- [ ] **Step 5: Run focused pipeline tests and verify they fail**

Run:

```bash
uv run pytest tests/test_pipeline.py::test_run_scan_sequences_source_cache_normalize_metrics_and_assembly tests/test_pipeline.py::test_run_scan_continues_after_per_stock_source_error -q
```

Expected: FAIL because `run_scan()` still returns empty report tables and does not normalize, calculate metrics, or assemble the report.

- [ ] **Step 6: Commit the failing pipeline tests**

```bash
git add tests/test_pipeline.py
git commit -m "test: pin full scan pipeline orchestration"
```

---

### Task 3: Wire `run_scan()` to Normalize, Calculate, and Assemble

**Files:**
- Modify: `src/future_ledger/pipeline.py`

- [ ] **Step 1: Add integration imports**

Add these imports to `src/future_ledger/pipeline.py`:

```python
from datetime import datetime, timezone

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
```

If `date` is already imported from `datetime`, combine the import:

```python
from datetime import date, datetime, timezone
```

- [ ] **Step 2: Replace `run_scan()` with the full orchestration**

Replace the existing `run_scan()` implementation with:

```python
def run_scan(config: RunConfig) -> ReportTables:
    """Execute the full local dividend scan and return assembled report tables."""
    source_errors: list[SourceErrorRow] = []
    source_metadata = []
    all_dividends = []
    all_prices = []
    dividend_metrics = []
    return_metrics = []

    spot_result = fetch_a_share_spot()
    source_errors.extend(_source_errors_from_result(spot_result))
    source_metadata.append(spot_result.metadata)

    stocks, universe_errors = build_universe(
        spot_result.frame,
        universe=config.universe,
        limit=config.limit,
    )
    source_errors.extend(universe_errors)
    source_errors.extend(
        _write_raw_cache_snapshot(
            config=config,
            key=cache_key("spot", "all_a"),
            result=spot_result,
        )
    )

    start_date, end_date = _price_window(config.as_of, config.years)
    for stock in stocks:
        dividend_result = fetch_dividend_detail(stock.code)
        price_result = fetch_price_history(stock.code, start_date, end_date)

        source_errors.extend(_source_errors_from_result(dividend_result))
        source_errors.extend(_source_errors_from_result(price_result))

        source_errors.extend(
            _write_raw_cache_snapshot(
                config=config,
                key=cache_key("dividend_detail", stock.code),
                result=dividend_result,
            )
        )
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

        source_metadata.append(dividend_result.metadata)
        source_metadata.append(price_result.metadata)

        dividend_records, dividend_errors = normalize_dividend_detail(
            stock,
            dividend_result.frame,
        )
        price_points, price_errors = normalize_price_history(
            stock.code,
            price_result.frame,
            price_result.metadata,
        )
        source_errors.extend(dividend_errors)
        source_errors.extend(price_errors)

        all_dividends.extend(dividend_records)
        all_prices.extend(price_points)

        for record in dividend_records:
            reference = resolve_reference_price(price_points, record.ex_dividend_date)
            yield_result = calculate_dividend_yield(
                record.cash_dividend_per_share,
                reference.reference_price,
            )
            dividend_metrics.append(
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

        return_result = calculate_trailing_one_year_return(
            stock.code,
            config.as_of,
            price_points,
            dividend_records,
        )
        return_metrics.append(
            ReturnMetricInput(
                stock_code=stock.code,
                start_price_date=return_result.start_price_date,
                end_price_date=return_result.end_price_date,
                cash_dividends_1y=return_result.cash_dividends_1y,
                total_return_1y_pct=return_result.total_return_1y_pct,
                annualized_return_1y_pct=return_result.annualized_return_1y_pct,
                data_quality_flags=return_result.return_data_quality_flags,
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
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
```

- [ ] **Step 3: Remove unused empty-report and metadata-row helpers**

Delete these imports from `src/future_ledger/pipeline.py` when they become unused:

```python
MetadataRow,
```

Delete these helper functions when no tests or code paths use them:

```python
def _metadata_rows_from_result(result: SourceFetchResult) -> list[MetadataRow]:
    ...


def _empty_report(
    *,
    source_errors: list[SourceErrorRow],
    metadata_rows: list[MetadataRow],
) -> ReportTables:
    ...
```

Keep these helpers because the pipeline still uses them:

```python
_write_raw_cache_snapshot
_read_existing_bytes
_restore_cache_file
_cache_write_error
_is_cacheable
_source_errors_from_result
_price_window
_replace_year_with_feb_28_fallback
_yyyymmdd
```

- [ ] **Step 4: Run the focused pipeline tests and verify they pass**

Run:

```bash
uv run pytest tests/test_pipeline.py::test_run_scan_sequences_source_cache_normalize_metrics_and_assembly tests/test_pipeline.py::test_run_scan_continues_after_per_stock_source_error -q
```

Expected: PASS.

- [ ] **Step 5: Run all pipeline tests and verify raw cache behavior still passes**

Run:

```bash
uv run pytest tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the pipeline integration**

```bash
git add src/future_ledger/pipeline.py tests/test_pipeline.py
git commit -m "feat: assemble scan pipeline report tables"
```

---

### Task 4: Verify CLI and Pipeline Together

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `tests/test_pipeline.py`
- Modify: `src/future_ledger/cli.py`
- Modify: `src/future_ledger/pipeline.py`

- [ ] **Step 1: Run the spec-required focused test command**

Run:

```bash
uv run pytest tests/test_cli.py tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the broader local suite that covers dependent contracts**

Run:

```bash
uv run pytest tests/test_cli.py tests/test_pipeline.py tests/normalize tests/metrics tests/test_workbook_writer.py tests/test_cache.py tests/sources -q
```

Expected: PASS.

- [ ] **Step 3: Run formatting and static checks if configured**

Run:

```bash
uv run ruff check src tests
uv run mypy src
```

Expected: PASS. If `mypy` is not configured for this project, record the exact command failure in the implementation notes and keep the pytest/ruff results as the required verification for this plan.

- [ ] **Step 4: Exercise the CLI with monkeypatched tests only**

Do not run live AKShare smoke tests as part of the default verification for this plan. The spec explicitly keeps live AKShare testing out of scope for default CLI tests.

- [ ] **Step 5: Commit final verification-only adjustments**

If the verification commands require only import-order, type-annotation, or lint adjustments, commit them:

```bash
git add src/future_ledger/cli.py src/future_ledger/pipeline.py tests/test_cli.py tests/test_pipeline.py
git commit -m "test: verify cli pipeline integration"
```

Skip this commit if there are no file changes after Task 3.

---

## Self-Review

- Spec coverage:
  - CLI resolves `RunConfig` before pipeline call: Task 1.
  - `run_scan(config)` returns `ReportTables` and never writes the workbook: Task 3.
  - CLI calls `write_workbook(tables, config.output)` after `run_scan(config)`: Task 1.
  - `--output`, `--cache-dir`, `--years`, `--as-of`, `--limit`, and unsupported `--universe` fail before source fetching: Task 1 plus existing tests.
  - Recoverable per-stock fetch, parse, metric, and cache failures stay in `SourceErrorRow`: Task 2 and Task 3.
  - Pipeline order is fetch universe, build universe, fetch stock sources, cache raw snapshots, normalize, calculate metrics, assemble report tables: Task 2.
  - Workbook writer `ConfigError` exits non-zero after `run_scan()` and does not retry source fetching: Task 1.
  - Completion output includes workbook path, ranked rows, source errors, universe size, and processed stocks: Task 1.

- Placeholder scan:
  - No task uses banned placeholder language or unspecified error handling.
  - Every code-changing step includes concrete code or exact function bodies.

- Type consistency:
  - `DividendMetricInput`, `ReturnMetricInput`, and `assemble_report_tables(...)` match the report assembly plan.
  - `DIVIDEND_YIELD_SOURCE`, `resolve_reference_price(...)`, and `calculate_dividend_yield(...)` match the metrics plan.
  - CLI catches `future_ledger.errors.ConfigError`, the workbook writer's configured fatal exception type.
