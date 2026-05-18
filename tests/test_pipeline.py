from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pytest

from future_ledger.cache import cache_key, read_cache, read_metadata, write_cache, write_metadata
from future_ledger.domain import RunConfig, SourceErrorRow, SourceFetchResult, SourceMetadata
from future_ledger.pipeline import run_scan


def test_run_scan_writes_raw_cache_snapshots_for_successful_fetches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spot_frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])
    dividend_frame = pd.DataFrame([{"代码": "600000", "分红年度": "2025"}])
    price_frame = pd.DataFrame([{"日期": "2026-04-17", "收盘": "10.25"}])

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(spot_frame, "spot_fetch", "all_a", "stock_zh_a_spot_em"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_dividend_detail",
        lambda symbol: _result(
            dividend_frame,
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_price_history",
        lambda symbol, start_date, end_date: _result(
            price_frame,
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        ),
    )

    tables = run_scan(_config(tmp_path))

    assert tables.source_errors == []

    cached_spot = read_cache(tmp_path / "cache", cache_key("spot", "all_a"))
    assert cached_spot is not None
    assert cached_spot.astype(str).to_dict(orient="records") == [
        {"代码": "600000", "名称": "浦发银行"}
    ]

    dividend_key = cache_key("dividend_detail", "600000")
    cached_dividend = read_cache(tmp_path / "cache", dividend_key)
    assert cached_dividend is not None
    assert cached_dividend.astype(str).to_dict(orient="records") == [
        {"代码": "600000", "分红年度": "2025"}
    ]

    price_key = cache_key(
        "price_history",
        "600000",
        start_date="20250420",
        end_date="20260420",
    )
    cached_price = read_cache(tmp_path / "cache", price_key)
    assert cached_price is not None
    assert cached_price.astype(str).to_dict(orient="records") == [
        {"日期": "2026-04-17", "收盘": "10.25"}
    ]

    price_metadata = read_metadata(tmp_path / "cache", price_key)
    assert price_metadata is not None
    assert price_metadata["stage"] == "price_fetch"
    assert price_metadata["request_start_date"] == "20250420"
    assert price_metadata["request_end_date"] == "20260420"
    assert price_metadata["empty"] is False


def test_run_scan_records_cache_write_error_and_continues_per_stock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spot_frame = pd.DataFrame(
        [
            {"代码": "600000", "名称": "浦发银行"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )
    calls: list[str] = []

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(spot_frame, "spot_fetch", "all_a", "stock_zh_a_spot_em"),
    )

    def fake_dividend(symbol: str) -> SourceFetchResult:
        calls.append(f"dividend:{symbol}")
        return _result(
            pd.DataFrame([{"代码": symbol, "分红年度": "2025"}]),
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
        )

    def fake_price(symbol: str, start_date: str, end_date: str) -> SourceFetchResult:
        calls.append(f"price:{symbol}:{start_date}:{end_date}")
        return _result(
            pd.DataFrame([{"日期": "2026-04-17", "收盘": "10.25"}]),
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        )

    monkeypatch.setattr("future_ledger.pipeline.fetch_dividend_detail", fake_dividend)
    monkeypatch.setattr("future_ledger.pipeline.fetch_price_history", fake_price)

    def flaky_write_cache(cache_dir: Path, key: str, df: pd.DataFrame) -> None:
        if key == cache_key("dividend_detail", "600000"):
            raise OSError("read-only cache")
        write_cache(cache_dir, key, df)

    monkeypatch.setattr("future_ledger.pipeline.write_cache", flaky_write_cache)

    tables = run_scan(_config(tmp_path))

    assert "dividend:000001" in calls
    assert "price:000001:20250420:20260420" in calls
    assert any(
        error.stock_code == "600000"
        and error.stage == "cache_write"
        and "OSError: read-only cache" in error.message
        for error in tables.source_errors
    )


def test_run_scan_records_overlong_stock_code_and_continues_per_stock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spot_frame = pd.DataFrame(
        [
            {"代码": "6000000", "名称": "过长代码"},
            {"代码": "000001", "名称": "平安银行"},
        ]
    )
    calls: list[str] = []

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(spot_frame, "spot_fetch", "all_a", "stock_zh_a_spot_em"),
    )

    def fake_dividend(symbol: str) -> SourceFetchResult:
        calls.append(f"dividend:{symbol}")
        return _result(
            pd.DataFrame([{"代码": symbol, "分红年度": "2025"}]),
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
        )

    def fake_price(symbol: str, start_date: str, end_date: str) -> SourceFetchResult:
        calls.append(f"price:{symbol}:{start_date}:{end_date}")
        return _result(
            pd.DataFrame([{"日期": "2026-04-17", "收盘": "10.25"}]),
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        )

    monkeypatch.setattr("future_ledger.pipeline.fetch_dividend_detail", fake_dividend)
    monkeypatch.setattr("future_ledger.pipeline.fetch_price_history", fake_price)

    tables = run_scan(_config(tmp_path))

    assert calls == ["dividend:000001", "price:000001:20250420:20260420"]
    assert any(
        error.stock_code == "6000000"
        and error.stage == "universe"
        and error.message == "invalid stock code length"
        for error in tables.source_errors
    )


def test_run_scan_does_not_overwrite_cache_for_failed_live_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_dir = tmp_path / "cache"
    dividend_key = cache_key("dividend_detail", "600000")
    write_cache(
        cache_dir,
        dividend_key,
        pd.DataFrame([{"代码": "600000", "分红年度": "existing"}]),
    )

    spot_frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(spot_frame, "spot_fetch", "all_a", "stock_zh_a_spot_em"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_dividend_detail",
        lambda symbol: _result(
            pd.DataFrame(),
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
            error=SourceErrorRow(
                stock_code=symbol,
                stage="dividend_fetch",
                message="RuntimeError: upstream unavailable",
                raw_detail=None,
            ),
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_price_history",
        lambda symbol, start_date, end_date: _result(
            pd.DataFrame([{"日期": "2026-04-17", "收盘": "10.25"}]),
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        ),
    )

    tables = run_scan(_config(tmp_path))

    cached_dividend = read_cache(cache_dir, dividend_key)
    assert cached_dividend is not None
    assert cached_dividend.astype(str).to_dict(orient="records") == [
        {"代码": "600000", "分红年度": "existing"}
    ]
    assert any(
        error.stock_code == "600000"
        and error.stage == "dividend_fetch"
        and error.message == "RuntimeError: upstream unavailable"
        for error in tables.source_errors
    )


def test_run_scan_restores_existing_cache_when_metadata_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_dir = tmp_path / "cache"
    dividend_key = cache_key("dividend_detail", "600000")
    write_cache(
        cache_dir,
        dividend_key,
        pd.DataFrame([{"代码": "600000", "分红年度": "existing"}]),
    )
    write_metadata(
        cache_dir,
        dividend_key,
        SourceMetadata(
            source_name="akshare",
            stage="dividend_fetch",
            symbol="600000",
            fetched_at="2026-05-14T08:30:00+00:00",
            akshare_version="1.17.0",
            row_count=1,
            upstream_function="stock_fhps_detail_em",
        ),
        empty=False,
    )

    spot_frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(spot_frame, "spot_fetch", "all_a", "stock_zh_a_spot_em"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_dividend_detail",
        lambda symbol: _result(
            pd.DataFrame([{"代码": symbol, "分红年度": "new"}]),
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_price_history",
        lambda symbol, start_date, end_date: _result(
            pd.DataFrame([{"日期": "2026-04-17", "收盘": "10.25"}]),
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        ),
    )

    original_write_text = Path.write_text

    def flaky_write_text(self: Path, data: str, *args: Any, **kwargs: Any) -> int:
        if self.parent.name == "dividend_detail" and "600000.metadata.json" in self.name:
            raise OSError("metadata disk full")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)

    tables = run_scan(_config(tmp_path))

    cached_dividend = read_cache(cache_dir, dividend_key)
    assert cached_dividend is not None
    assert cached_dividend.to_dict(orient="records") == [
        {"代码": "600000", "分红年度": "existing"}
    ]

    metadata = read_metadata(cache_dir, dividend_key)
    assert metadata is not None
    assert metadata["row_count"] == 1
    assert any(
        error.stock_code == "600000"
        and error.stage == "cache_write"
        and "OSError: metadata disk full" in error.message
        for error in tables.source_errors
    )


def _config(tmp_path: Path) -> RunConfig:
    return RunConfig(
        years=1,
        as_of=date(2026, 4, 20),
        universe="all-a-excluding-st",
        output=tmp_path / "report.xlsx",
        limit=None,
        cache_dir=tmp_path / "cache",
    )


def _result(
    frame: pd.DataFrame,
    stage: str,
    symbol: str,
    upstream_function: str,
    *,
    request_start_date: str | None = None,
    request_end_date: str | None = None,
    error: SourceErrorRow | None = None,
) -> SourceFetchResult:
    return SourceFetchResult(
        frame=frame,
        metadata=SourceMetadata(
            source_name="akshare",
            stage=stage,
            symbol=symbol,
            fetched_at="2026-05-14T08:30:00+00:00",
            akshare_version="1.17.0",
            row_count=len(frame.index),
            upstream_function=upstream_function,
            request_start_date=request_start_date,
            request_end_date=request_end_date,
        ),
        error=error,
    )
