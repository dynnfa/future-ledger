from __future__ import annotations

import pytest

from future_ledger.cache import cache_key


def test_cache_key_uses_stage_and_symbol() -> None:
    assert cache_key("dividend_detail", "600000") == "dividend_detail/600000.csv"


def test_spot_cache_key_uses_all_a_symbol() -> None:
    assert cache_key("spot", "all_a") == "spot/all_a.csv"


def test_price_history_cache_key_includes_date_range() -> None:
    assert (
        cache_key(
            "price_history",
            "600000",
            start_date="20250420",
            end_date="20260420",
        )
        == "price_history/600000_20250420_20260420.csv"
    )


@pytest.mark.parametrize("symbol", ["", "../600000", "600000/evil", r"600000\evil", ".."])
def test_cache_key_rejects_path_traversal(symbol: str) -> None:
    with pytest.raises(ValueError, match="symbol must be all_a or a six-digit stock code"):
        cache_key("dividend_detail", symbol)


def test_cache_key_rejects_unknown_stage() -> None:
    with pytest.raises(ValueError, match="unsupported cache stage: raw"):
        cache_key("raw", "600000")


def test_price_history_cache_key_requires_both_dates() -> None:
    with pytest.raises(ValueError, match="price_history cache keys require start_date and end_date"):
        cache_key("price_history", "600000", start_date="20250420")


def test_non_price_cache_key_rejects_date_range() -> None:
    with pytest.raises(ValueError, match="spot cache keys do not accept start_date or end_date"):
        cache_key("spot", "all_a", start_date="20250420", end_date="20260420")
