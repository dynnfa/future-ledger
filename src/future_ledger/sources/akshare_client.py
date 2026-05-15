from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

import akshare as ak  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from future_ledger.domain import SourceFetchResult, SourceMetadata

SOURCE_NAME = "akshare"
SPOT_STAGE = "spot_fetch"
DIVIDEND_STAGE = "dividend_fetch"
PRICE_STAGE = "price_fetch"
ALL_A_SYMBOL = "all_a"
_RETRY_WAIT = wait_exponential(multiplier=0.5, min=0.5, max=4)

Clock = Callable[[], datetime]
FrameCall = Callable[[], pd.DataFrame]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def fetch_a_share_spot(*, clock: Clock = _utc_now) -> SourceFetchResult:
    frame = _call_with_retries(lambda: ak.stock_zh_a_spot_em())
    return _build_result(
        frame=frame,
        stage=SPOT_STAGE,
        symbol=ALL_A_SYMBOL,
        upstream_function="stock_zh_a_spot_em",
        clock=clock,
    )


def fetch_dividend_detail(symbol: str, *, clock: Clock = _utc_now) -> SourceFetchResult:
    frame = _call_with_retries(lambda: ak.stock_fhps_detail_em(symbol=symbol))
    return _build_result(
        frame=frame,
        stage=DIVIDEND_STAGE,
        symbol=symbol,
        upstream_function="stock_fhps_detail_em",
        clock=clock,
    )


def fetch_price_history(
    symbol: str,
    start_date: str,
    end_date: str,
    *,
    clock: Clock = _utc_now,
) -> SourceFetchResult:
    frame = _call_with_retries(
        lambda: ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
        )
    )
    return _build_result(
        frame=frame,
        stage=PRICE_STAGE,
        symbol=symbol,
        upstream_function="stock_zh_a_hist",
        clock=clock,
        request_start_date=start_date,
        request_end_date=end_date,
    )


def _call_with_retries(call: FrameCall) -> pd.DataFrame:
    retryer = Retrying(
        stop=stop_after_attempt(3),
        wait=_RETRY_WAIT,
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    return retryer(call)


def _build_result(
    *,
    frame: pd.DataFrame,
    stage: str,
    symbol: str,
    upstream_function: str,
    clock: Clock,
    request_start_date: str | None = None,
    request_end_date: str | None = None,
) -> SourceFetchResult:
    metadata = SourceMetadata(
        source_name=SOURCE_NAME,
        stage=stage,
        symbol=symbol,
        fetched_at=clock().isoformat(),
        akshare_version=_akshare_version(),
        row_count=len(frame.index),
        upstream_function=upstream_function,
        request_start_date=request_start_date,
        request_end_date=request_end_date,
    )
    return SourceFetchResult(frame=frame, metadata=metadata, error=None)


def _akshare_version() -> str:
    return str(getattr(ak, "__version__", "unknown"))
