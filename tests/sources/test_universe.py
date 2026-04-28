import pandas as pd  # type: ignore[import-untyped]
import pytest

from future_ledger.sources.universe import build_universe


def test_build_universe_excludes_st_names() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "600001", "名称": "*ST 示例"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )

    result = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert [stock.code for stock in result] == ["600000", "000001"]


def test_build_universe_applies_limit_after_filtering() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )

    result = build_universe(frame, universe="all-a-excluding-st", limit=1)

    assert len(result) == 1


def test_build_universe_assigns_market_by_code_prefix() -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "000001", "名称": "平安银行"},
            {"代码": "300750", "名称": "宁德时代"},
            {"代码": "830799", "名称": "艾融软件"},
        ]
    )

    result = build_universe(frame, universe="all-a-excluding-st", limit=None)

    assert {stock.code: stock.market for stock in result} == {
        "600000": "SH",
        "000001": "SZ",
        "300750": "SZ",
        "830799": "BJ",
    }


def test_build_universe_rejects_non_positive_limit() -> None:
    frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])

    with pytest.raises(ValueError, match="limit must be >= 1"):
        build_universe(frame, universe="all-a-excluding-st", limit=-1)
