from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pytest
from tenacity import wait_none

from future_ledger.sources import akshare_client
from future_ledger.sources.akshare_client import (
    fetch_a_share_spot,
    fetch_dividend_detail,
    fetch_price_history,
)

FIXED_NOW = datetime(2026, 5, 14, 8, 30, tzinfo=timezone.utc)


def fixed_clock() -> datetime:
    return FIXED_NOW


def test_fetch_a_share_spot_returns_frame_and_metadata(monkeypatch: Any) -> None:
    frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])

    monkeypatch.setattr(akshare_client.ak, "__version__", "1.17.0", raising=False)
    monkeypatch.setattr(akshare_client.ak, "stock_zh_a_spot_em", lambda: frame)

    result = fetch_a_share_spot(clock=fixed_clock)

    assert result.frame.equals(frame)
    assert result.error is None
    assert result.metadata.source_name == "akshare"
    assert result.metadata.stage == "spot_fetch"
    assert result.metadata.symbol == "all_a"
    assert result.metadata.fetched_at == "2026-05-14T08:30:00+00:00"
    assert result.metadata.akshare_version == "1.17.0"
    assert result.metadata.row_count == 1
    assert result.metadata.upstream_function == "stock_zh_a_spot_em"
    assert result.metadata.request_start_date is None
    assert result.metadata.request_end_date is None


def test_fetch_dividend_detail_returns_frame_and_metadata(monkeypatch: Any) -> None:
    frame = pd.DataFrame([{"代码": "600000", "分红年度": "2025"}])

    monkeypatch.setattr(akshare_client.ak, "__version__", "1.17.0", raising=False)
    monkeypatch.setattr(
        akshare_client.ak,
        "stock_fhps_detail_em",
        lambda symbol: frame if symbol == "600000" else pd.DataFrame(),
    )

    result = fetch_dividend_detail("600000", clock=fixed_clock)

    assert result.frame.equals(frame)
    assert result.error is None
    assert result.metadata.source_name == "akshare"
    assert result.metadata.stage == "dividend_fetch"
    assert result.metadata.symbol == "600000"
    assert result.metadata.fetched_at == "2026-05-14T08:30:00+00:00"
    assert result.metadata.akshare_version == "1.17.0"
    assert result.metadata.row_count == 1
    assert result.metadata.upstream_function == "stock_fhps_detail_em"


def test_fetch_price_history_passes_daily_request_and_metadata(monkeypatch: Any) -> None:
    frame = pd.DataFrame([{"日期": "2026-04-17", "收盘": "10.25"}])
    calls: list[dict[str, str]] = []

    def fake_hist(**kwargs: str) -> pd.DataFrame:
        calls.append(kwargs)
        return frame

    monkeypatch.setattr(akshare_client.ak, "__version__", "1.17.0", raising=False)
    monkeypatch.setattr(akshare_client.ak, "stock_zh_a_hist", fake_hist)

    result = fetch_price_history(
        "600000",
        start_date="20250420",
        end_date="20260420",
        clock=fixed_clock,
    )

    assert calls == [
        {
            "symbol": "600000",
            "period": "daily",
            "start_date": "20250420",
            "end_date": "20260420",
        }
    ]
    assert result.frame.equals(frame)
    assert result.error is None
    assert result.metadata.source_name == "akshare"
    assert result.metadata.stage == "price_fetch"
    assert result.metadata.symbol == "600000"
    assert result.metadata.fetched_at == "2026-05-14T08:30:00+00:00"
    assert result.metadata.akshare_version == "1.17.0"
    assert result.metadata.row_count == 1
    assert result.metadata.upstream_function == "stock_zh_a_hist"
    assert result.metadata.request_start_date == "20250420"
    assert result.metadata.request_end_date == "20260420"


def test_fetch_dividend_detail_records_empty_frame_source_error(monkeypatch: Any) -> None:
    frame = pd.DataFrame(columns=["代码", "分红年度"])

    monkeypatch.setattr(akshare_client.ak, "__version__", "1.17.0", raising=False)
    monkeypatch.setattr(akshare_client.ak, "stock_fhps_detail_em", lambda symbol: frame)

    result = fetch_dividend_detail("600000", clock=fixed_clock)

    assert result.frame.equals(frame)
    assert result.metadata.stage == "dividend_fetch"
    assert result.metadata.symbol == "600000"
    assert result.metadata.row_count == 0
    assert result.error is not None
    assert result.error.stock_code == "600000"
    assert result.error.stage == "dividend_fetch"
    assert result.error.message == "empty upstream frame"
    assert result.error.raw_detail is None


def test_fetch_price_history_validates_date_range(monkeypatch: Any) -> None:
    called = False

    def fake_hist(**_kwargs: str) -> pd.DataFrame:
        nonlocal called
        called = True
        return pd.DataFrame()

    monkeypatch.setattr(akshare_client.ak, "stock_zh_a_hist", fake_hist)

    with pytest.raises(ValueError, match="start_date must be <= end_date"):
        fetch_price_history("600000", start_date="20260420", end_date="20250420")

    assert called is False


def test_fetch_dividend_detail_validates_symbol_before_live_call(
    monkeypatch: Any,
) -> None:
    called = False

    def fake_detail(symbol: str) -> pd.DataFrame:
        nonlocal called
        called = True
        return pd.DataFrame([{"代码": symbol}])

    monkeypatch.setattr(akshare_client.ak, "stock_fhps_detail_em", fake_detail)

    with pytest.raises(ValueError, match="symbol must be a six-digit A-share code"):
        fetch_dividend_detail("60000A")

    assert called is False


def test_fetch_price_history_validates_symbol_before_live_call(monkeypatch: Any) -> None:
    called = False

    def fake_hist(**_kwargs: str) -> pd.DataFrame:
        nonlocal called
        called = True
        return pd.DataFrame()

    monkeypatch.setattr(akshare_client.ak, "stock_zh_a_hist", fake_hist)

    with pytest.raises(ValueError, match="symbol must be a six-digit A-share code"):
        fetch_price_history("12345", start_date="20250420", end_date="20260420")

    assert called is False


def test_fetch_source_exception_returns_source_error_after_retries(
    monkeypatch: Any,
) -> None:
    attempts = 0

    def raising_spot() -> pd.DataFrame:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(akshare_client, "_RETRY_WAIT", wait_none())
    monkeypatch.setattr(akshare_client.ak, "__version__", "1.17.0", raising=False)
    monkeypatch.setattr(akshare_client.ak, "stock_zh_a_spot_em", raising_spot)

    result = fetch_a_share_spot(clock=fixed_clock)

    assert attempts == 3
    assert result.frame.empty
    assert result.metadata.stage == "spot_fetch"
    assert result.metadata.symbol == "all_a"
    assert result.metadata.row_count == 0
    assert result.error is not None
    assert result.error.stock_code == "all_a"
    assert result.error.stage == "spot_fetch"
    assert result.error.message == "RuntimeError: upstream unavailable"
    assert result.error.raw_detail is None


def test_fetch_malformed_response_returns_source_error(monkeypatch: Any) -> None:
    monkeypatch.setattr(akshare_client.ak, "__version__", "1.17.0", raising=False)
    monkeypatch.setattr(
        akshare_client.ak,
        "stock_zh_a_spot_em",
        lambda: [{"代码": "600000"}],
    )

    result = fetch_a_share_spot(clock=fixed_clock)

    assert result.frame.empty
    assert result.metadata.stage == "spot_fetch"
    assert result.metadata.symbol == "all_a"
    assert result.metadata.row_count == 0
    assert result.error is not None
    assert result.error.stock_code == "all_a"
    assert result.error.stage == "spot_fetch"
    assert result.error.message == "malformed upstream response"
    assert result.error.raw_detail == "<class 'list'>"
