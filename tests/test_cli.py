from __future__ import annotations

import pytest
from typer.testing import CliRunner

from future_ledger.cli import app
from future_ledger.domain import ReportTables, RunConfig


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

    def fake_run_scan(config: RunConfig) -> ReportTables:
        captured["config"] = config
        return ReportTables.empty()

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
    result = runner.invoke(app, ["dividends", "scan", "--as-of", "2026-01-15"])

    assert result.exit_code == 0
    assert str(captured["config"].as_of) == "2026-01-15"
    assert "workbook writing not yet implemented" in result.output
    assert "Rows ranked: 0" in result.output


def test_scan_uses_default_arguments(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, RunConfig] = {}

    def fake_run_scan(config: RunConfig) -> ReportTables:
        captured["config"] = config
        return ReportTables.empty()

    monkeypatch.setattr("future_ledger.cli.run_scan", fake_run_scan)
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
