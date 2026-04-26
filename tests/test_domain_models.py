"""Tests for expanded domain models matching the workbook contract."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from future_ledger.domain import (
    DividendLongRow,
    DividendRankRow,
    DividendYearDetail,
    MetadataRow,
    RunConfig,
)


class TestRunConfig:
    def test_cache_dir_default(self) -> None:
        config = RunConfig(
            years=5,
            as_of=date(2026, 4, 20),
            universe="all-a-excluding-st",
            output=Path("reports/dividend_rank.xlsx"),
        )
        assert config.cache_dir == Path(".future_ledger/cache")

    def test_cache_dir_custom(self) -> None:
        config = RunConfig(
            years=5,
            as_of=date(2026, 4, 20),
            universe="all-a-excluding-st",
            output=Path("reports/dividend_rank.xlsx"),
            cache_dir=Path("/tmp/cache"),  # noqa: S108
        )
        assert config.cache_dir == Path("/tmp/cache")  # noqa: S108


class TestDividendYearDetail:
    def test_full_construction(self) -> None:
        detail = DividendYearDetail(
            report_year=2025,
            report_period="2025年报",
            cash_dividend_per_10_shares=Decimal("4.10"),
            cash_dividend_per_share=Decimal("0.41"),
            reference_price=Decimal("10.25"),
            reference_price_date=date(2025, 7, 1),
            dividend_yield_pct=Decimal("4.00"),
            registration_date=date(2025, 6, 28),
            ex_dividend_date=date(2025, 6, 29),
            plan_status="实施",
            eps=Decimal("2.10"),
            net_asset_per_share=Decimal("18.50"),
            profit_growth_yoy_pct=Decimal("5.30"),
            source="akshare.stock_fhps_detail_em",
        )
        assert detail.report_year == 2025
        assert detail.cash_dividend_per_share == Decimal("0.41")
        assert detail.source == "akshare.stock_fhps_detail_em"

    def test_optional_fields_default_none(self) -> None:
        detail = DividendYearDetail(
            report_year=2024,
            report_period="2024年报",
            cash_dividend_per_10_shares=None,
            cash_dividend_per_share=None,
            reference_price=None,
            reference_price_date=None,
            dividend_yield_pct=None,
            registration_date=None,
            ex_dividend_date=None,
            plan_status=None,
            eps=None,
            net_asset_per_share=None,
            profit_growth_yoy_pct=None,
            source="akshare.stock_fhps_detail_em",
        )
        assert detail.eps is None
        assert detail.reference_price is None

    def test_frozen(self) -> None:
        detail = DividendYearDetail(
            report_year=2024,
            report_period="2024年报",
            cash_dividend_per_10_shares=Decimal("3.00"),
            cash_dividend_per_share=Decimal("0.30"),
            reference_price=Decimal("9.00"),
            reference_price_date=date(2024, 7, 1),
            dividend_yield_pct=Decimal("3.33"),
            registration_date=None,
            ex_dividend_date=None,
            plan_status="实施",
            eps=Decimal("1.80"),
            net_asset_per_share=Decimal("16.00"),
            profit_growth_yoy_pct=Decimal("4.00"),
            source="akshare.stock_fhps_detail_em",
        )
        with pytest.raises(AttributeError):
            detail.report_year = 2023  # type: ignore[misc]


class TestDividendRankRow:
    def test_full_construction(self) -> None:
        row = DividendRankRow(
            rank_latest_yield=1,
            stock_code="600000",
            stock_name="浦发银行",
            market="SH",
            latest_report_year=2025,
            latest_cash_dividend_per_10_shares=Decimal("4.10"),
            latest_cash_dividend_per_share=Decimal("0.41"),
            reference_price=Decimal("10.25"),
            reference_price_date=date(2025, 7, 1),
            latest_dividend_yield_pct=Decimal("4.00"),
            dividend_yield_source="calculated_ex_dividend_close",
            dividend_year_count_5y=5,
            continuous_dividend_5y=True,
            avg_dividend_yield_pct_5y=Decimal("3.80"),
            min_dividend_yield_pct_5y=Decimal("3.10"),
            max_dividend_yield_pct_5y=Decimal("4.20"),
            as_of_date=date(2026, 4, 20),
            cash_dividends_1y=Decimal("0.41"),
            total_return_1y_pct=Decimal("6.50"),
            annualized_return_1y_pct=Decimal("6.50"),
            has_missing_years_5y=False,
            data_quality_flags=("none",),
            source_priority_used="akshare.stock_fhps_detail_em",
            fetched_at="2026-04-20T08:30:00+08:00",
            annual_fields={"2025_plan_status": "实施"},
        )
        assert row.stock_code == "600000"
        assert row.annual_fields["2025_plan_status"] == "实施"
        assert row.rank_latest_yield == 1

    def test_optional_rank_is_none(self) -> None:
        row = DividendRankRow(
            rank_latest_yield=None,
            stock_code="000001",
            stock_name="平安银行",
            market="SZ",
            latest_report_year=2025,
            latest_cash_dividend_per_10_shares=Decimal("2.00"),
            latest_cash_dividend_per_share=Decimal("0.20"),
            reference_price=Decimal("12.00"),
            reference_price_date=date(2025, 6, 15),
            latest_dividend_yield_pct=Decimal("1.67"),
            dividend_yield_source="calculated_ex_dividend_close",
            dividend_year_count_5y=5,
            continuous_dividend_5y=True,
            avg_dividend_yield_pct_5y=Decimal("2.00"),
            min_dividend_yield_pct_5y=Decimal("1.50"),
            max_dividend_yield_pct_5y=Decimal("2.50"),
            as_of_date=date(2026, 4, 20),
            cash_dividends_1y=Decimal("0.20"),
            total_return_1y_pct=Decimal("5.00"),
            annualized_return_1y_pct=Decimal("5.00"),
            has_missing_years_5y=False,
            data_quality_flags=(),
            source_priority_used="akshare.stock_fhps_detail_em",
            fetched_at="2026-04-20T08:30:00+08:00",
            annual_fields={},
        )
        assert row.rank_latest_yield is None

    def test_frozen(self) -> None:
        row = DividendRankRow(
            rank_latest_yield=None,
            stock_code="000001",
            stock_name="平安银行",
            market="SZ",
            latest_report_year=2024,
            latest_cash_dividend_per_10_shares=None,
            latest_cash_dividend_per_share=None,
            reference_price=None,
            reference_price_date=None,
            latest_dividend_yield_pct=None,
            dividend_yield_source="none",
            dividend_year_count_5y=0,
            continuous_dividend_5y=False,
            avg_dividend_yield_pct_5y=None,
            min_dividend_yield_pct_5y=None,
            max_dividend_yield_pct_5y=None,
            as_of_date=date(2026, 4, 20),
            cash_dividends_1y=None,
            total_return_1y_pct=None,
            annualized_return_1y_pct=None,
            has_missing_years_5y=True,
            data_quality_flags=("no_data",),
            source_priority_used="none",
            fetched_at="",
            annual_fields={},
        )
        with pytest.raises(AttributeError):
            row.stock_code = "600000"  # type: ignore[misc]


class TestDividendLongRow:
    def test_full_construction(self) -> None:
        row = DividendLongRow(
            stock_code="600000",
            stock_name="浦发银行",
            market="SH",
            report_year=2025,
            report_period="2025年报",
            cash_dividend_per_10_shares=Decimal("4.10"),
            cash_dividend_per_share=Decimal("0.41"),
            ex_dividend_date=date(2025, 6, 29),
            registration_date=date(2025, 6, 28),
            plan_status="实施",
            eps=Decimal("2.10"),
            net_asset_per_share=Decimal("18.50"),
            profit_growth_yoy_pct=Decimal("5.30"),
            dividend_yield_pct=Decimal("4.00"),
            source="akshare.stock_fhps_detail_em",
        )
        assert row.stock_code == "600000"
        assert row.report_year == 2025

    def test_optional_fields_none(self) -> None:
        row = DividendLongRow(
            stock_code="000001",
            stock_name="平安银行",
            market="SZ",
            report_year=2023,
            report_period="2023年报",
            cash_dividend_per_10_shares=None,
            cash_dividend_per_share=None,
            ex_dividend_date=None,
            registration_date=None,
            plan_status=None,
            eps=None,
            net_asset_per_share=None,
            profit_growth_yoy_pct=None,
            dividend_yield_pct=None,
            source="akshare.stock_fhps_detail_em",
        )
        assert row.cash_dividend_per_share is None
        assert row.eps is None

    def test_frozen(self) -> None:
        row = DividendLongRow(
            stock_code="000001",
            stock_name="平安银行",
            market="SZ",
            report_year=2023,
            report_period="2023年报",
            cash_dividend_per_10_shares=Decimal("2.00"),
            cash_dividend_per_share=Decimal("0.20"),
            ex_dividend_date=None,
            registration_date=None,
            plan_status="实施",
            eps=Decimal("1.50"),
            net_asset_per_share=Decimal("15.00"),
            profit_growth_yoy_pct=Decimal("3.00"),
            dividend_yield_pct=Decimal("2.00"),
            source="akshare.stock_fhps_detail_em",
        )
        with pytest.raises(AttributeError):
            row.report_year = 2024  # type: ignore[misc]


class TestMetadataRow:
    def test_construction(self) -> None:
        row = MetadataRow(key="run_date", value="2026-04-20")
        assert row.key == "run_date"
        assert row.value == "2026-04-20"

    def test_frozen(self) -> None:
        row = MetadataRow(key="version", value="0.1.0")
        with pytest.raises(AttributeError):
            row.key = "changed"  # type: ignore[misc]
