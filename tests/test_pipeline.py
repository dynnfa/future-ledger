from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pytest

from future_ledger.cache import cache_key, read_cache, read_metadata, write_cache, write_metadata
from future_ledger.domain import (
    DividendRecord,
    PricePoint,
    ReportTables,
    RunConfig,
    SourceErrorRow,
    SourceFetchResult,
    SourceMetadata,
    StockIdentity,
)
from future_ledger.pipeline import run_scan


def test_run_scan_writes_raw_cache_snapshots_for_successful_fetches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spot_frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])
    dividend_frame = pd.DataFrame([{"报告期": "2025-12-31", "每10股派息": "4.10"}])
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
        {"报告期": "2025-12-31", "每10股派息": "4.10"}
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


def test_run_scan_sequences_source_cache_normalize_metrics_and_assembly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stages: list[str] = []
    stock = StockIdentity(code="600000", name="浦发银行", market="SH")
    dividend_record = DividendRecord(
        stock_code="600000",
        stock_name="浦发银行",
        market="SH",
        report_year=2025,
        report_period="2025-12-31",
        cash_dividend_per_10_shares=Decimal("4.10"),
        cash_dividend_per_share=Decimal("0.41"),
        ex_dividend_date=date(2025, 7, 1),
        source="akshare.stock_fhps_detail_em",
    )
    price_point = PricePoint(
        stock_code="600000",
        date=date(2025, 7, 1),
        close=Decimal("10.00"),
    )

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _stage_result(stages, "fetch_spot", "spot_fetch", "all_a"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.build_universe",
        lambda frame, universe, limit: (stages.append("build_universe") or [stock], []),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_dividend_detail",
        lambda symbol: _stage_result(stages, "fetch_dividend", "dividend_fetch", symbol),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_price_history",
        lambda symbol, start_date, end_date: _stage_result(
            stages,
            "fetch_price",
            "price_fetch",
            symbol,
            request_start_date=start_date,
            request_end_date=end_date,
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.write_cache",
        lambda cache_dir, key, frame: stages.append(f"cache:{key.split('/')[0]}"),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.write_metadata",
        lambda cache_dir, key, metadata, empty: None,
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.normalize_dividend_detail",
        lambda received_stock, frame: (
            stages.append("normalize_dividend") or [dividend_record],
            [],
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.normalize_price_history",
        lambda stock_code, frame, metadata: (
            stages.append("normalize_price") or [price_point],
            [],
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.resolve_reference_price",
        lambda points, ex_dividend_date: _reference_price(stages),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.calculate_dividend_yield",
        lambda cash_dividend_per_share, reference_price: _dividend_yield(stages),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.calculate_trailing_one_year_return",
        lambda stock_code, as_of, prices, dividends: _return_result(stages, as_of),
    )

    def fake_assemble_report_tables(**kwargs: object) -> ReportTables:
        stages.append("assemble")
        assert kwargs["stocks"] == [stock]
        assert kwargs["dividends"] == [dividend_record]
        assert kwargs["prices"] == [price_point]
        return ReportTables.empty()

    monkeypatch.setattr(
        "future_ledger.pipeline.assemble_report_tables",
        fake_assemble_report_tables,
    )

    run_scan(_config(tmp_path))

    assert stages == [
        "fetch_spot",
        "build_universe",
        "cache:spot",
        "fetch_dividend",
        "fetch_price",
        "cache:dividend_detail",
        "cache:price_history",
        "normalize_dividend",
        "normalize_price",
        "resolve_reference_price",
        "calculate_dividend_yield",
        "calculate_return",
        "assemble",
    ]


def test_run_scan_continues_after_per_stock_source_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stocks = [
        StockIdentity(code="600000", name="浦发银行", market="SH"),
        StockIdentity(code="000001", name="平安银行", market="SZ"),
    ]
    calls: list[str] = []

    monkeypatch.setattr(
        "future_ledger.pipeline.fetch_a_share_spot",
        lambda: _result(
            pd.DataFrame([{"代码": "600000"}, {"代码": "000001"}]),
            "spot_fetch",
            "all_a",
            "stock_zh_a_spot_em",
        ),
    )
    monkeypatch.setattr(
        "future_ledger.pipeline.build_universe",
        lambda frame, universe, limit: (stocks, []),
    )

    def fake_dividend(symbol: str) -> SourceFetchResult:
        calls.append(f"dividend:{symbol}")
        if symbol == "600000":
            return _result(
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
            )
        return _result(
            pd.DataFrame([{"报告期": "2025-12-31", "每10股派息": "4.10"}]),
            "dividend_fetch",
            symbol,
            "stock_fhps_detail_em",
        )

    def fake_price(symbol: str, start_date: str, end_date: str) -> SourceFetchResult:
        calls.append(f"price:{symbol}")
        return _result(
            pd.DataFrame([{"日期": "2025-07-01", "收盘": "10.00"}]),
            "price_fetch",
            symbol,
            "stock_zh_a_hist",
            request_start_date=start_date,
            request_end_date=end_date,
        )

    monkeypatch.setattr("future_ledger.pipeline.fetch_dividend_detail", fake_dividend)
    monkeypatch.setattr("future_ledger.pipeline.fetch_price_history", fake_price)

    tables = run_scan(_config(tmp_path))

    assert calls == [
        "dividend:600000",
        "price:600000",
        "dividend:000001",
        "price:000001",
    ]
    assert any(
        row.stock_code == "600000"
        and row.stage == "dividend_fetch"
        and "upstream unavailable" in row.message
        for row in tables.source_errors
    )
    assert any(row.stock_code == "000001" for row in tables.dividend_rank)


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


def _stage_result(
    stages: list[str],
    stage_name: str,
    source_stage: str,
    symbol: str,
    *,
    request_start_date: str | None = None,
    request_end_date: str | None = None,
) -> SourceFetchResult:
    stages.append(stage_name)
    return _result(
        pd.DataFrame([{"value": symbol}]),
        source_stage,
        symbol,
        source_stage,
        request_start_date=request_start_date,
        request_end_date=request_end_date,
    )


def _reference_price(stages: list[str]) -> object:
    stages.append("resolve_reference_price")
    return type(
        "ReferencePrice",
        (),
        {
            "reference_price": Decimal("10.00"),
            "reference_price_date": date(2025, 7, 1),
        },
    )()


def _dividend_yield(stages: list[str]) -> object:
    stages.append("calculate_dividend_yield")
    return type(
        "DividendYield",
        (),
        {
            "dividend_yield_pct": Decimal("4.10"),
            "data_quality_flags": (),
        },
    )()


def _return_result(stages: list[str], as_of: date) -> object:
    stages.append("calculate_return")
    return type(
        "ReturnResult",
        (),
        {
            "as_of_date": as_of,
            "return_window_start": date(as_of.year - 1, as_of.month, as_of.day),
            "return_window_end": as_of,
            "start_close_price": Decimal("10.00"),
            "start_price_date": date(2025, 4, 20),
            "end_close_price": Decimal("10.65"),
            "end_price_date": as_of,
            "cash_dividends_1y": Decimal("0.41"),
            "total_return_1y_pct": Decimal("10.60"),
            "annualized_return_1y_pct": Decimal("10.60"),
            "return_data_quality_flags": (),
        },
    )()
