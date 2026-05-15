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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd  # type: ignore[import-untyped]


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
    market: str  # e.g. "SH", "SZ", "BJ"


@dataclass(frozen=True)
class DividendRecord:
    """One normalized annual dividend record for a stock."""

    stock_code: str
    stock_name: str
    market: str
    report_year: int
    report_period: str
    cash_dividend_per_10_shares: Decimal | None
    cash_dividend_per_share: Decimal | None
    ex_dividend_date: date | None = None
    registration_date: date | None = None
    plan_status: str | None = None
    eps: Decimal | None = None
    net_asset_per_share: Decimal | None = None
    profit_growth_yoy_pct: Decimal | None = None
    provider_yield_pct: Decimal | None = None
    source: str = ""


@dataclass(frozen=True)
class PricePoint:
    """A single daily price close for a stock."""

    stock_code: str
    date: date
    close: Decimal


@dataclass(frozen=True)
class DividendYearDetail:
    """Per-year detail used in the dividend_long sheet."""

    report_year: int
    report_period: str
    cash_dividend_per_10_shares: Decimal | None
    cash_dividend_per_share: Decimal | None
    reference_price: Decimal | None
    reference_price_date: date | None
    dividend_yield_pct: Decimal | None
    registration_date: date | None
    ex_dividend_date: date | None
    plan_status: str | None
    eps: Decimal | None
    net_asset_per_share: Decimal | None
    profit_growth_yoy_pct: Decimal | None
    source: str


@dataclass(frozen=True)
class DividendRankRow:
    """One row in the dividend_rank output sheet."""

    rank_latest_yield: int | None
    stock_code: str
    stock_name: str
    market: str
    latest_report_year: int | None
    latest_cash_dividend_per_10_shares: Decimal | None
    latest_cash_dividend_per_share: Decimal | None
    reference_price: Decimal | None
    reference_price_date: date | None
    latest_dividend_yield_pct: Decimal | None
    dividend_yield_source: str
    dividend_year_count_5y: int
    continuous_dividend_5y: bool
    avg_dividend_yield_pct_5y: Decimal | None
    min_dividend_yield_pct_5y: Decimal | None
    max_dividend_yield_pct_5y: Decimal | None
    as_of_date: date
    cash_dividends_1y: Decimal | None
    total_return_1y_pct: Decimal | None
    annualized_return_1y_pct: Decimal | None
    has_missing_years_5y: bool
    data_quality_flags: tuple[str, ...]
    source_priority_used: str
    fetched_at: str
    annual_fields: dict[str, object]


@dataclass(frozen=True)
class DividendLongRow:
    """One row in the dividend_long output sheet."""

    stock_code: str
    stock_name: str
    market: str
    report_year: int
    report_period: str
    cash_dividend_per_10_shares: Decimal | None
    cash_dividend_per_share: Decimal | None
    ex_dividend_date: date | None
    registration_date: date | None
    plan_status: str | None
    eps: Decimal | None
    net_asset_per_share: Decimal | None
    profit_growth_yoy_pct: Decimal | None
    dividend_yield_pct: Decimal | None
    source: str


@dataclass(frozen=True)
class MetadataRow:
    """A key-value row in the metadata output sheet."""

    key: str
    value: str


@dataclass(frozen=True)
class SourceErrorRow:
    """A row in the source_errors output sheet."""

    stock_code: str
    stage: str  # e.g. "dividend_fetch", "price_fetch", "normalize"
    message: str
    raw_detail: str | None = None


@dataclass(frozen=True)
class SourceMetadata:
    """Lineage metadata for one upstream source fetch."""

    source_name: str
    stage: str
    symbol: str
    fetched_at: str
    akshare_version: str
    row_count: int
    upstream_function: str
    request_start_date: str | None = None
    request_end_date: str | None = None


@dataclass(frozen=True)
class SourceFetchResult:
    """A raw upstream frame with lineage metadata and an optional source error."""

    frame: pd.DataFrame
    metadata: SourceMetadata
    error: SourceErrorRow | None = None


@dataclass(frozen=True)
class ReportTables:
    """All tables that make up the output workbook."""

    dividend_rank: list[DividendRankRow]
    dividend_long: list[DividendLongRow]
    price_points: list[PricePoint]
    source_errors: list[SourceErrorRow]
    metadata: list[MetadataRow]

    @classmethod
    def empty(cls) -> ReportTables:
        """Return an empty report with no rows in any table."""
        return cls(
            dividend_rank=[],
            dividend_long=[],
            price_points=[],
            source_errors=[],
            metadata=[],
        )
