from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import StockIdentity
from future_ledger.normalize.dividends import normalize_dividend_detail


def test_normalize_dividend_detail_maps_required_fields_from_fixture() -> None:
    frame = pd.read_csv(Path("tests/fixtures/akshare/dividend_detail_600000.csv"))

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert errors == []
    assert len(records) == 2
    assert records[0].stock_code == "600000"
    assert records[0].stock_name == "浦发银行"
    assert records[0].market == "SH"
    assert records[0].report_year == 2025
    assert records[0].report_period == "2025-12-31"
    assert records[0].cash_dividend_per_10_shares == Decimal("4.10")
    assert records[0].cash_dividend_per_share == Decimal("0.41")
    assert records[0].ex_dividend_date == date(2026, 7, 1)
    assert records[0].registration_date == date(2026, 6, 30)
    assert records[0].plan_status == "实施"
    assert records[0].eps == Decimal("2.10")
    assert records[0].net_asset_per_share == Decimal("18.50")
    assert records[0].profit_growth_yoy_pct == Decimal("5.30")
    assert records[0].provider_yield_pct == Decimal("4.00")
    assert records[0].source == "akshare.stock_fhps_detail_em"


def test_normalize_dividend_detail_uses_stock_identity_market() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "2024-12-31", "每10股派息": "4.0", "方案进度": "实施"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("900001", "北交示例", "BJ"), frame)

    assert errors == []
    assert len(records) == 1
    assert records[0].stock_code == "900001"
    assert records[0].market == "BJ"


def test_normalize_dividend_detail_skips_missing_report_period() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "", "每10股派息": "4.0"},
            {"报告期": None, "每10股派息": "4.2"},
            {"报告期": "2024-12-31", "每10股派息": "3.80"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("000001", "平安银行", "SZ"), frame)

    assert [record.report_year for record in records] == [2024]
    assert records[0].market == "SZ"
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "missing report period"),
        ("dividend_normalize", "missing report period"),
    ]


def test_normalize_dividend_detail_prefers_implemented_duplicate_report_period() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "每10股派息": "3.50",
                "除权除息日": "2025-07-01",
                "方案进度": "董事会预案",
            },
            {
                "报告期": "2024-12-31",
                "每10股派息": "4.20",
                "除权除息日": "2025-07-02",
                "方案进度": "实施",
            },
            {
                "报告期": "2023-12-31",
                "每10股派息": "2.80",
                "除权除息日": "2024/07/01",
                "方案进度": "实施",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert [record.report_year for record in records] == [2024, 2023]
    assert records[0].report_period == "2024-12-31"
    assert records[0].cash_dividend_per_10_shares == Decimal("4.20")
    assert records[0].cash_dividend_per_share == Decimal("0.42")
    assert records[0].ex_dividend_date == date(2025, 7, 2)
    assert records[0].plan_status == "实施"
    assert len(errors) == 1
    assert errors[0].stock_code == "600000"
    assert errors[0].stage == "dividend_normalize"
    assert errors[0].message == "duplicate report period"
    assert "实施" in (errors[0].raw_detail or "")


def test_normalize_dividend_detail_prefers_later_duplicate_when_priority_ties() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "2024-12-31", "每10股派息": "3.50", "方案进度": "实施"},
            {"报告期": "2024-12-31", "每10股派息": "4.20", "方案进度": "实施"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert len(records) == 1
    assert records[0].cash_dividend_per_10_shares == Decimal("4.20")
    assert len(errors) == 1
    assert errors[0].message == "duplicate report period"


def test_normalize_dividend_detail_deduplicates_canonical_report_periods() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "2024/12/31", "每10股派息": "3.50", "方案进度": "董事会预案"},
            {"报告期": "2024-12-31", "每10股派息": "4.20", "方案进度": "实施"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert len(records) == 1
    assert records[0].report_period == "2024-12-31"
    assert records[0].cash_dividend_per_10_shares == Decimal("4.20")
    assert len(errors) == 1
    assert errors[0].message == "duplicate report period"


def test_percent_fields_keep_percent_units() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "净利润同比增长": "5.30%",
                "现金分红-股息率": "4.00%",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert errors == []
    assert records[0].profit_growth_yoy_pct == Decimal("5.30")
    assert records[0].provider_yield_pct == Decimal("4.00")


def test_non_percent_decimal_rejects_percent_sign() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "每10股派息": "4.20",
                "每股收益": "2.10%",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert len(records) == 1
    assert records[0].cash_dividend_per_10_shares == Decimal("4.20")
    assert records[0].eps is None
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "invalid decimal field: eps"),
    ]


def test_invalid_report_period_is_skipped_with_source_error() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "not-a-date", "每10股派息": "4.20"},
            {"报告期": "2024-12-31", "每10股派息": "3.80"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert [record.report_year for record in records] == [2024]
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "invalid report period"),
    ]


def test_malformed_optional_decimal_becomes_none_with_source_error() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "每10股派息": "bad-value",
                "每股净资产": "18.50",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert len(records) == 1
    assert records[0].cash_dividend_per_10_shares is None
    assert records[0].cash_dividend_per_share is None
    assert records[0].net_asset_per_share == Decimal("18.50")
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "invalid decimal field: cash_dividend_per_10_shares"),
    ]


def _stock(code: str, name: str, market: str) -> StockIdentity:
    return StockIdentity(code=code, name=name, market=market)
