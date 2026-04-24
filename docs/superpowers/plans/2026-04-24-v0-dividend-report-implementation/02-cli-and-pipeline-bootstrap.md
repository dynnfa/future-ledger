### Task 2: Wire CLI Validation And Pipeline Invocation

**Files:**
- Modify: `src/future_ledger/cli.py`
- Modify: `src/future_ledger/pipeline.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add failing CLI tests for defaults and pipeline invocation**

```python
from typer.testing import CliRunner

from future_ledger.cli import app


def test_scan_uses_default_arguments(monkeypatch):
    captured = {}

    def fake_run_scan(config):
        captured["config"] = config

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
    result = CliRunner().invoke(app, ["dividends", "scan"])

    assert result.exit_code == 0
    assert captured["config"].years == 5
    assert captured["config"].universe == "all-a-excluding-st"
    assert str(captured["config"].output) == "reports/dividend_rank.xlsx"


def test_scan_rejects_non_positive_years():
    result = CliRunner().invoke(app, ["dividends", "scan", "--years", "0"])
    assert result.exit_code != 0
    assert "--years must be >= 1" in result.output
```

- [ ] **Step 2: Run tests to verify the command does not call the pipeline yet**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL because `future_ledger.cli.run_scan` is not imported or invoked, and `--years` validation is missing.

- [ ] **Step 3: Update the CLI to validate and invoke the pipeline**

```python
from future_ledger.pipeline import run_scan


def _validate_years(years: int) -> int:
    if years < 1:
        raise typer.BadParameter("--years must be >= 1")
    return years


@dividends_app.command("scan")
def scan(...):
    validated_years = _validate_years(years)
    as_of_date = _parse_as_of(as_of)
    config = RunConfig(
        years=validated_years,
        as_of=as_of_date,
        universe=universe,
        output=output,
        limit=limit,
        cache_dir=cache_dir,
    )
    tables = run_scan(config)
    typer.echo(f"Wrote workbook: {config.output}")
    typer.echo(f"Rows ranked: {len(tables.dividend_rank)}")
```

- [ ] **Step 4: Replace the pipeline stub with a minimal return value**

```python
from future_ledger.domain import ReportTables


def run_scan(config: RunConfig) -> ReportTables:
    return ReportTables(
        dividend_rank=[],
        dividend_long=[],
        price_points=[],
        source_errors=[],
        metadata=[],
    )
```

- [ ] **Step 5: Run tests to verify CLI behavior passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/future_ledger/cli.py src/future_ledger/pipeline.py tests/test_cli.py
git commit -m "feat: wire dividend scan cli to pipeline"
```
