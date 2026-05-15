from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]
import pytest

from future_ledger.errors import SourceError
from future_ledger.sources.universe import build_universe


def test_build_universe_excludes_st_names() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "600001", "名称": "*ST 示例"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )

    stocks, errors = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert [stock.code for stock in stocks] == ["600000", "000001"]
    assert errors == []


def test_build_universe_applies_limit_after_filtering() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600001", "名称": "*ST 示例"},
            {"代码": "900001", "名称": "未知市场"},
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )

    stocks, errors = build_universe(frame, universe="all-a-excluding-st", limit=1)

    assert [stock.code for stock in stocks] == ["600000"]
    assert [error.stock_code for error in errors] == ["900001"]


def test_build_universe_assigns_market_by_code_prefix() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "000001", "名称": "平安银行"},
            {"代码": "300750", "名称": "宁德时代"},
            {"代码": "830799", "名称": "艾融软件"},
            {"代码": "430047", "名称": "诺思兰德"},
        ]
    )

    stocks, errors = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert {stock.code: stock.market for stock in stocks} == {
        "600000": "SH",
        "000001": "SZ",
        "300750": "SZ",
        "830799": "BJ",
        "430047": "BJ",
    }
    assert errors == []


def test_build_universe_skips_unknown_prefix_with_source_error() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "900001", "名称": "未知市场"},
            {"代码": "600000", "名称": "浦发银行"},
        ]
    )

    stocks, errors = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert [stock.code for stock in stocks] == ["600000"]
    assert len(errors) == 1
    assert errors[0].stock_code == "900001"
    assert errors[0].stage == "universe"
    assert errors[0].message == "unsupported stock code prefix"
    assert "900001" in (errors[0].raw_detail or "")


def test_build_universe_rejects_missing_required_columns() -> None:
    frame = pd.DataFrame([{"代码": "600000"}])

    with pytest.raises(SourceError, match="spot frame missing required columns: 代码, 名称"):
        build_universe(frame, universe="all-a-excluding-st", limit=None)


def test_build_universe_returns_source_error_for_empty_spot_frame() -> None:
    frame = pd.DataFrame(columns=["代码", "名称"])

    stocks, errors = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert stocks == []
    assert len(errors) == 1
    assert errors[0].stock_code == ""
    assert errors[0].stage == "universe"
    assert errors[0].message == "empty spot frame"
    assert errors[0].raw_detail is None


def test_build_universe_zero_pads_integer_like_stock_codes() -> None:
    frame = pd.DataFrame(
        [
            {"代码": 1, "名称": "平安银行"},
            {"代码": "600000", "名称": "浦发银行"},
        ]
    )

    stocks, errors = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert [stock.code for stock in stocks] == ["000001", "600000"]
    assert [stock.market for stock in stocks] == ["SZ", "SH"]
    assert errors == []


def test_build_universe_skips_missing_stock_name_with_source_error() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": ""},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )

    stocks, errors = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert [stock.code for stock in stocks] == ["000001"]
    assert len(errors) == 1
    assert errors[0].stock_code == "600000"
    assert errors[0].stage == "universe"
    assert errors[0].message == "missing stock name"
    assert "600000" in (errors[0].raw_detail or "")


def test_build_universe_rejects_unsupported_universe() -> None:
    frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])

    with pytest.raises(ValueError, match="Unsupported universe: hs300"):
        build_universe(frame, universe="hs300", limit=None)


def test_build_universe_rejects_non_positive_limit() -> None:
    frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])

    with pytest.raises(ValueError, match="limit must be >= 1"):
        build_universe(frame, universe="all-a-excluding-st", limit=-1)
