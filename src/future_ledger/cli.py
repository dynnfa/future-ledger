from datetime import date
from pathlib import Path

import typer

from future_ledger.domain import RunConfig
from future_ledger.pipeline import run_scan
from future_ledger.workbook_writer import write_workbook

app = typer.Typer(name="future-ledger", help="A-share dividend research workbook generator")
dividends_app = typer.Typer(help="Dividend analysis commands")
app.add_typer(dividends_app, name="dividends")


def _parse_as_of(as_of: str | None) -> date:
    """Parse --as-of into a date, raising BadParameter on invalid input."""
    if as_of is None:
        return date.today()
    try:
        return date.fromisoformat(as_of)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date format: {as_of!r}. Expected YYYY-MM-DD.") from exc


def _validate_years(years: int) -> int:
    """Validate that --years is a positive integer."""
    if years < 1:
        raise typer.BadParameter("--years must be >= 1")
    return years


def _validate_limit(limit: int | None) -> int | None:
    """Validate that --limit is positive when supplied."""
    if limit is not None and limit < 1:
        raise typer.BadParameter("--limit must be >= 1")
    return limit


@dividends_app.command("scan")
def scan(
    years: int = typer.Option(5, "--years", help="Lookback window in years"),
    as_of: str | None = typer.Option(
        None, "--as-of", help="Reference date YYYY-MM-DD (default: today)"
    ),
    universe: str = typer.Option("all-a-excluding-st", "--universe", help="Stock universe filter"),
    output: Path = typer.Option(
        "reports/dividend_rank.xlsx", "--output", help="Output workbook path"
    ),
    limit: int | None = typer.Option(None, "--limit", help="Dev: limit stocks to process"),
    cache_dir: Path = typer.Option(
        ".future_ledger/cache", "--cache-dir", help="Raw data cache directory"
    ),
) -> None:
    """Scan A-share dividend data and generate a ranked workbook."""
    validated_years = _validate_years(years)
    validated_limit = _validate_limit(limit)
    as_of_date = _parse_as_of(as_of)
    config = RunConfig(
        years=validated_years,
        as_of=as_of_date,
        universe=universe,
        output=output,
        limit=validated_limit,
        cache_dir=cache_dir,
    )
    tables = run_scan(config)
    written_path = write_workbook(tables, config.output)
    typer.echo(f"Workbook written: {written_path}")
    typer.echo(f"Rows ranked: {len(tables.dividend_rank)}")
