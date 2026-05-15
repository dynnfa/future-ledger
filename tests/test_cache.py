from __future__ import annotations

import json
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest

from future_ledger.cache import cache_key, read_cache, read_metadata, write_cache, write_metadata
from future_ledger.domain import SourceMetadata
from future_ledger.errors import SourceError


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


def test_write_and_read_cache_round_trips_dataframe(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )
    key = cache_key("spot", "all_a")

    write_cache(tmp_path, key, frame)
    cached = read_cache(tmp_path, key)

    assert cached is not None
    assert list(cached.columns) == ["代码", "名称"]
    assert cached.astype(str).to_dict(orient="records") == [
        {"代码": "600000", "名称": "浦发银行"},
        {"代码": "000001", "名称": "平安银行"},
    ]


def test_write_cache_creates_parent_directories(tmp_path: Path) -> None:
    frame = pd.DataFrame([{"代码": "600000", "分红年度": "2025"}])
    key = cache_key("dividend_detail", "600000")

    write_cache(tmp_path, key, frame)

    assert (tmp_path / "dividend_detail" / "600000.csv").exists()


def test_read_cache_returns_none_when_missing(tmp_path: Path) -> None:
    assert read_cache(tmp_path, cache_key("dividend_detail", "600000")) is None


def test_read_cache_wraps_malformed_csv_as_source_error(tmp_path: Path) -> None:
    path = tmp_path / "spot" / "all_a.csv"
    path.parent.mkdir(parents=True)
    path.write_text('代码,名称\n"600000,浦发银行\n', encoding="utf-8")

    with pytest.raises(SourceError) as exc_info:
        read_cache(tmp_path, cache_key("spot", "all_a"))

    assert exc_info.value.stage == "cache_read"
    assert "ParserError" in (exc_info.value.raw_detail or "")


def test_write_and_read_metadata_round_trips_json(tmp_path: Path) -> None:
    key = cache_key(
        "price_history",
        "600000",
        start_date="20250420",
        end_date="20260420",
    )
    metadata = SourceMetadata(
        source_name="akshare",
        stage="price_fetch",
        symbol="600000",
        fetched_at="2026-05-14T08:30:00+00:00",
        akshare_version="1.17.0",
        row_count=2,
        upstream_function="stock_zh_a_hist",
        request_start_date="20250420",
        request_end_date="20260420",
    )

    write_metadata(tmp_path, key, metadata, empty=False)
    payload = read_metadata(tmp_path, key)

    assert payload is not None
    assert payload["source_name"] == "akshare"
    assert payload["stage"] == "price_fetch"
    assert payload["symbol"] == "600000"
    assert payload["row_count"] == 2
    assert payload["akshare_version"] == "1.17.0"
    assert payload["request_start_date"] == "20250420"
    assert payload["request_end_date"] == "20260420"
    assert payload["upstream_function"] == "stock_zh_a_hist"
    assert payload["empty"] is False

    sidecar_path = tmp_path / "price_history" / "600000_20250420_20260420.metadata.json"
    assert sidecar_path.read_text(encoding="utf-8") == (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def test_write_metadata_marks_empty_frames(tmp_path: Path) -> None:
    key = cache_key("dividend_detail", "600000")
    metadata = SourceMetadata(
        source_name="akshare",
        stage="dividend_fetch",
        symbol="600000",
        fetched_at="2026-05-14T08:30:00+00:00",
        akshare_version="1.17.0",
        row_count=0,
        upstream_function="stock_fhps_detail_em",
    )

    write_metadata(tmp_path, key, metadata)
    payload = read_metadata(tmp_path, key)

    assert payload is not None
    assert payload["row_count"] == 0
    assert payload["empty"] is True


def test_read_metadata_returns_none_when_missing(tmp_path: Path) -> None:
    assert read_metadata(tmp_path, cache_key("dividend_detail", "600000")) is None


def test_write_metadata_rejects_non_iso_fetched_at(tmp_path: Path) -> None:
    metadata = SourceMetadata(
        source_name="akshare",
        stage="spot_fetch",
        symbol="all_a",
        fetched_at="not-a-date",
        akshare_version="1.17.0",
        row_count=1,
        upstream_function="stock_zh_a_spot_em",
    )

    with pytest.raises(ValueError, match="fetched_at must be ISO 8601"):
        write_metadata(tmp_path, cache_key("spot", "all_a"), metadata)
