from datetime import date
from pathlib import Path

import typer

from future_ledger.domain import RunConfig

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
        raise typer.BadParameter(
            f"Invalid date format: {as_of!r}. Expected YYYY-MM-DD."
        ) from exc


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
    as_of_date = _parse_as_of(as_of)
    config = RunConfig(
        years=years,
        as_of=as_of_date,
        universe=universe,
        output=output,
        limit=limit,
        cache_dir=cache_dir,
    )
    typer.echo(
        f"Scanning dividends: years={config.years}, as_of={config.as_of}, "
        f"universe={config.universe}, output={config.output}"
    )
