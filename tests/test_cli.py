from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from future_ledger.cli import app
from future_ledger.domain import DividendRankRow, ReportTables, RunConfig, SourceErrorRow
from future_ledger.errors import ConfigError


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_root_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "future-ledger" in result.output.lower() or "Future Ledger" in result.output


def test_dividends_scan_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["dividends", "scan", "--help"])
    assert result.exit_code == 0
    assert "--years" in result.output
    assert "--output" in result.output


def test_scan_invalid_as_of(runner: CliRunner) -> None:
    result = runner.invoke(app, ["dividends", "scan", "--as-of", "not-a-date"])
    assert result.exit_code != 0
    assert "Invalid date format" in result.output


def test_scan_valid_as_of(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, RunConfig] = {}
    written: dict[str, Path] = {}

    def fake_run_scan(config: RunConfig) -> ReportTables:
        captured["config"] = config
        return ReportTables.empty()

    def fake_write_workbook(tables: ReportTables, output: Path) -> Path:
        assert tables == ReportTables.empty()
        written["output"] = output
        return output

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
    monkeypatch.setattr("future_ledger.cli.write_workbook", fake_write_workbook)
    result = runner.invoke(app, ["dividends", "scan", "--as-of", "2026-01-15"])

    assert result.exit_code == 0
    assert str(captured["config"].as_of) == "2026-01-15"
    assert written["output"] == captured["config"].output
    assert "Workbook written: reports/dividend_rank.xlsx" in result.output
    assert "Rows ranked: 0" in result.output


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


def test_scan_uses_default_arguments(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, RunConfig] = {}

    def fake_run_scan(config: RunConfig) -> ReportTables:
        captured["config"] = config
        return ReportTables.empty()

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
    monkeypatch.setattr(
        "future_ledger.cli.write_workbook",
        lambda tables, output: output,
    )
    result = runner.invoke(app, ["dividends", "scan"])

    assert result.exit_code == 0
    assert captured["config"].years == 5
    assert captured["config"].universe == "all-a-excluding-st"
    assert str(captured["config"].output) == "reports/dividend_rank.xlsx"


def test_scan_rejects_non_positive_years(runner: CliRunner) -> None:
    result = runner.invoke(app, ["dividends", "scan", "--years", "0"])
    assert result.exit_code != 0
    assert "--years must be >= 1" in result.output


def test_scan_rejects_non_positive_limit(runner: CliRunner) -> None:
    result = runner.invoke(app, ["dividends", "scan", "--limit", "-1"])
    assert result.exit_code != 0
    assert "--limit must be >= 1" in result.output


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
