import pytest
from typer.testing import CliRunner

from future_ledger.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_root_help(runner: CliRunner):
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "future-ledger" in result.output.lower() or "Future Ledger" in result.output


def test_dividends_scan_help(runner: CliRunner):
    result = runner.invoke(app, ["dividends", "scan", "--help"])
    assert result.exit_code == 0
    assert "--years" in result.output
    assert "--output" in result.output


def test_scan_invalid_as_of(runner: CliRunner):
    result = runner.invoke(app, ["dividends", "scan", "--as-of", "not-a-date"])
    assert result.exit_code != 0
    assert "Invalid date format" in result.output


def test_scan_valid_as_of(runner: CliRunner):
    result = runner.invoke(app, ["dividends", "scan", "--as-of", "2026-01-15"])
    assert result.exit_code == 0
    assert "2026-01-15" in result.output
