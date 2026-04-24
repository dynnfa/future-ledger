"""Core domain types for the dividend analysis pipeline.

All AKShare-specific column names must not leak past the sources/ and
normalize/ layers.  Everything downstream uses the field names defined
here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class RunConfig:
    """Resolved CLI configuration passed to the pipeline."""

    years: int
    as_of: date
    universe: str
    output: Path
    limit: int | None = None
    cache_dir: Path = field(default=Path(".future_ledger/cache"))


@dataclass(frozen=True)
class StockIdentity:
    """A single A-share stock after universe filtering."""

    code: str
    name: str
    market: str  # e.g. "SH", "SZ"


@dataclass(frozen=True)
class DividendRecord:
    """One normalized annual dividend record for a stock."""

    stock_code: str
    report_year: int
    cash_dividend_per_share: Decimal
    ex_dividend_date: date | None = None
    registration_date: date | None = None
    plan_status: str | None = None
    provider_yield_pct: Decimal | None = None


@dataclass(frozen=True)
class PricePoint:
    """A single daily price close for a stock."""

    stock_code: str
    date: date
    close: Decimal


@dataclass(frozen=True)
class DividendRankRow:
    """One row in the dividend_rank output sheet."""

    stock_code: str
    stock_name: str
    latest_annual_yield_pct: Decimal | None = None
    avg_annual_yield_pct: Decimal | None = None
    dividend_count_in_window: int = 0
    trailing_1y_return_pct: Decimal | None = None
    data_quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceErrorRow:
    """A row in the source_errors output sheet."""

    stock_code: str
    stage: str  # e.g. "dividend_fetch", "price_fetch", "normalize"
    message: str
    raw_detail: str | None = None


@dataclass(frozen=True)
class ReportTables:
    """All tables that make up the output workbook."""

    dividend_rank: list[DividendRankRow]
    dividend_long: list[DividendRecord]
    price_points: list[PricePoint]
    source_errors: list[SourceErrorRow]
    metadata: dict[str, str]
