# Source Fetching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap all live AKShare calls in a source-client boundary that returns raw frames, deterministic source metadata, and recoverable source errors.

**Architecture:** Add small immutable source result models to `future_ledger.domain`, then rewrite `future_ledger.sources.akshare_client` as the only AKShare call boundary. The client validates request inputs before live calls, retries upstream exceptions with tenacity, and converts empty, malformed, or failed responses into `SourceFetchResult` values that downstream cache and normalization code can consume.

**Tech Stack:** Python 3.11, pandas, AKShare, tenacity, dataclasses, pytest, uv, ruff, mypy.

---

## Scope Check

The spec covers one subsystem: live source fetching through AKShare. It can be implemented and tested independently from raw cache persistence, normalization, report assembly, and CLI pipeline orchestration.

## File Structure

- Modify `src/future_ledger/domain.py`
  - Adds `SourceMetadata`.
  - Adds `SourceFetchResult`.
  - Uses `TYPE_CHECKING` for the pandas frame annotation so domain models do not import pandas at runtime.

- Modify `tests/test_domain_models.py`
  - Documents construction and immutability of `SourceMetadata`.
  - Documents that `SourceFetchResult` carries a raw frame and optional `SourceErrorRow`.

- Create `tests/sources/test_akshare_client.py`
  - Uses monkeypatched AKShare functions only.
  - Verifies spot, dividend detail, and price history success metadata.
  - Verifies invalid symbols, invalid date ranges, empty frames, malformed responses, and retry-exhausted exceptions.
  - Patches tenacity wait to zero in retry tests so default tests stay fast.

- Modify `src/future_ledger/sources/akshare_client.py`
  - Owns all direct AKShare calls.
  - Exposes `fetch_a_share_spot()`, `fetch_dividend_detail()`, and `fetch_price_history()`.
  - Returns `SourceFetchResult` from every fetch function.
  - Keeps raw AKShare column names unchanged in returned frames.

- Modify `tests/test_no_network_default.py`
  - Updates the default no-network assertion for the new recoverable source-error contract.
  - Keeps the guarantee that default tests do not depend on live AKShare endpoints.

- Modify `tests/live/test_akshare_smoke.py`
  - Updates the optional smoke test to inspect `SourceFetchResult.frame`.
  - Keeps the `live_akshare` marker and default skip behavior.

---

### Task 1: Add Source Result Domain Models

**Files:**
- Modify: `tests/test_domain_models.py`
- Modify: `src/future_ledger/domain.py`

- [ ] **Step 1: Write failing domain model tests**

In `tests/test_domain_models.py`, replace the import block:

```python
from future_ledger.domain import (
    DividendLongRow,
    DividendRankRow,
    DividendYearDetail,
    MetadataRow,
    RunConfig,
)
```

with:

```python
from future_ledger.domain import (
    DividendLongRow,
    DividendRankRow,
    DividendYearDetail,
    MetadataRow,
    RunConfig,
    SourceErrorRow,
    SourceFetchResult,
    SourceMetadata,
)
```

Then append this test class to the end of `tests/test_domain_models.py`:

```python
class TestSourceFetchResult:
    def test_source_metadata_construction(self) -> None:
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

        assert metadata.source_name == "akshare"
        assert metadata.stage == "price_fetch"
        assert metadata.symbol == "600000"
        assert metadata.row_count == 2
        assert metadata.request_start_date == "20250420"
        assert metadata.request_end_date == "20260420"
        assert metadata.upstream_function == "stock_zh_a_hist"

    def test_source_fetch_result_carries_frame_metadata_and_error(self) -> None:
        frame = pd.DataFrame([{"代码": "600000", "名称": "浦发银行"}])
        metadata = SourceMetadata(
            source_name="akshare",
            stage="spot_fetch",
            symbol="all_a",
            fetched_at="2026-05-14T08:30:00+00:00",
            akshare_version="1.17.0",
            row_count=1,
            upstream_function="stock_zh_a_spot_em",
        )
        error = SourceErrorRow(
            stock_code="all_a",
            stage="spot_fetch",
            message="empty upstream frame",
            raw_detail=None,
        )

        result = SourceFetchResult(frame=frame, metadata=metadata, error=error)

        assert result.frame.equals(frame)
        assert result.metadata == metadata
        assert result.error == error

    def test_source_metadata_is_frozen(self) -> None:
        metadata = SourceMetadata(
            source_name="akshare",
            stage="dividend_fetch",
            symbol="600000",
            fetched_at="2026-05-14T08:30:00+00:00",
            akshare_version="1.17.0",
            row_count=0,
            upstream_function="stock_fhps_detail_em",
        )

        with pytest.raises(AttributeError):
            metadata.row_count = 1  # type: ignore[misc]
```

- [ ] **Step 2: Run the focused domain tests and verify they fail**

Run:

```bash
uv run pytest tests/test_domain_models.py -q
```

Expected: FAIL with an import error for `SourceFetchResult` or `SourceMetadata`.

- [ ] **Step 3: Add the domain dataclasses**

In `src/future_ledger/domain.py`, add this import after the existing imports:

```python
from typing import TYPE_CHECKING
```

Then add this block after the `Path` import:

```python
if TYPE_CHECKING:
    import pandas as pd
```

Then insert these dataclasses immediately after `SourceErrorRow` and before `ReportTables`:

```python
@dataclass(frozen=True)
class SourceMetadata:
    """Lineage metadata for one upstream source fetch."""

    source_name: str
    stage: str
    symbol: str
    fetched_at: str
    akshare_version: str
    row_count: int
    upstream_function: str
    request_start_date: str | None = None
    request_end_date: str | None = None


@dataclass(frozen=True)
class SourceFetchResult:
    """A raw upstream frame with lineage metadata and an optional source error."""

    frame: pd.DataFrame
    metadata: SourceMetadata
    error: SourceErrorRow | None = None
```

- [ ] **Step 4: Run the focused domain tests and verify they pass**

Run:

```bash
uv run pytest tests/test_domain_models.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the domain models**

Run:

```bash
git add src/future_ledger/domain.py tests/test_domain_models.py
git commit -m "feat: add source fetch result models"
```

Expected: commit succeeds with only the domain model changes staged.

---

### Task 2: Implement Successful AKShare Fetch Results

**Files:**
- Create: `tests/sources/test_akshare_client.py`
- Modify: `src/future_ledger/sources/akshare_client.py`

- [ ] **Step 1: Write failing source-client success tests**

Create `tests/sources/test_akshare_client.py` with:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

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
```

- [ ] **Step 2: Run the source-client tests and verify they fail**

Run:

```bash
uv run pytest tests/sources/test_akshare_client.py -q
```

Expected: FAIL because the existing fetch functions return raw `DataFrame` objects and do not accept `clock=`.

- [ ] **Step 3: Implement successful result wrapping**

Replace `src/future_ledger/sources/akshare_client.py` with:

```python
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
```

- [ ] **Step 4: Run the source-client tests and verify they pass**

Run:

```bash
uv run pytest tests/sources/test_akshare_client.py -q
```

Expected: PASS for the three success-path tests.

- [ ] **Step 5: Commit the success-path source client**

Run:

```bash
git add src/future_ledger/sources/akshare_client.py tests/sources/test_akshare_client.py
git commit -m "feat: wrap akshare fetches with source metadata"
```

Expected: commit succeeds with only the source client and its tests staged.

---

### Task 3: Add Validation, Empty Frames, Malformed Responses, And Retry Errors

**Files:**
- Modify: `tests/sources/test_akshare_client.py`
- Modify: `tests/test_no_network_default.py`
- Modify: `src/future_ledger/sources/akshare_client.py`

- [ ] **Step 1: Extend source-client tests for validation and source errors**

In `tests/sources/test_akshare_client.py`, add these imports:

```python
import pytest
from tenacity import wait_none
```

Then append these tests to the end of `tests/sources/test_akshare_client.py`:

```python
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


def test_fetch_dividend_detail_validates_symbol_before_live_call(monkeypatch: Any) -> None:
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


def test_fetch_source_exception_returns_source_error_after_retries(monkeypatch: Any) -> None:
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
    monkeypatch.setattr(akshare_client.ak, "stock_zh_a_spot_em", lambda: [{"代码": "600000"}])

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
```

In `tests/test_no_network_default.py`, add this import:

```python
from tenacity import wait_none
```

Then replace:

```python
from future_ledger.sources.akshare_client import fetch_a_share_spot
```

with:

```python
from future_ledger.sources import akshare_client
from future_ledger.sources.akshare_client import fetch_a_share_spot
```

Then replace `test_default_tests_block_directly_imported_akshare_source_client` with:

```python
def test_default_tests_block_directly_imported_akshare_source_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(akshare_client, "_RETRY_WAIT", wait_none())

    result = fetch_a_share_spot()

    assert result.frame.empty
    assert result.metadata.stage == "spot_fetch"
    assert result.metadata.symbol == "all_a"
    assert result.error is not None
    assert result.error.stage == "spot_fetch"
    assert result.error.stock_code == "all_a"
    assert result.error.message.startswith("RuntimeError: Network access disabled")
```

- [ ] **Step 2: Run the extended source-client and no-network tests and verify they fail**

Run:

```bash
uv run pytest tests/sources/test_akshare_client.py tests/test_no_network_default.py -q
```

Expected: FAIL because invalid inputs are not validated, exceptions still raise, empty frames have no source error, and malformed responses are not converted to empty frames.

- [ ] **Step 3: Implement validation and source-error conversion**

Replace `src/future_ledger/sources/akshare_client.py` with:

```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import re

import akshare as ak  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from future_ledger.domain import SourceErrorRow, SourceFetchResult, SourceMetadata

SOURCE_NAME = "akshare"
SPOT_STAGE = "spot_fetch"
DIVIDEND_STAGE = "dividend_fetch"
PRICE_STAGE = "price_fetch"
ALL_A_SYMBOL = "all_a"
_SYMBOL_RE = re.compile(r"^\d{6}$")
_RETRY_WAIT = wait_exponential(multiplier=0.5, min=0.5, max=4)

Clock = Callable[[], datetime]
FrameCall = Callable[[], object]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def fetch_a_share_spot(*, clock: Clock = _utc_now) -> SourceFetchResult:
    return _fetch(
        stage=SPOT_STAGE,
        symbol=ALL_A_SYMBOL,
        upstream_function="stock_zh_a_spot_em",
        clock=clock,
        call=lambda: ak.stock_zh_a_spot_em(),
    )


def fetch_dividend_detail(symbol: str, *, clock: Clock = _utc_now) -> SourceFetchResult:
    _validate_symbol(symbol)
    return _fetch(
        stage=DIVIDEND_STAGE,
        symbol=symbol,
        upstream_function="stock_fhps_detail_em",
        clock=clock,
        call=lambda: ak.stock_fhps_detail_em(symbol=symbol),
    )


def fetch_price_history(
    symbol: str,
    start_date: str,
    end_date: str,
    *,
    clock: Clock = _utc_now,
) -> SourceFetchResult:
    _validate_symbol(symbol)
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")

    return _fetch(
        stage=PRICE_STAGE,
        symbol=symbol,
        upstream_function="stock_zh_a_hist",
        clock=clock,
        request_start_date=start_date,
        request_end_date=end_date,
        call=lambda: ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
        ),
    )


def _fetch(
    *,
    stage: str,
    symbol: str,
    upstream_function: str,
    clock: Clock,
    call: FrameCall,
    request_start_date: str | None = None,
    request_end_date: str | None = None,
) -> SourceFetchResult:
    try:
        response = _call_with_retries(call)
    except Exception as exc:
        return _build_result(
            frame=pd.DataFrame(),
            stage=stage,
            symbol=symbol,
            upstream_function=upstream_function,
            clock=clock,
            request_start_date=request_start_date,
            request_end_date=request_end_date,
            error_message=f"{exc.__class__.__name__}: {exc}",
        )

    if not isinstance(response, pd.DataFrame):
        return _build_result(
            frame=pd.DataFrame(),
            stage=stage,
            symbol=symbol,
            upstream_function=upstream_function,
            clock=clock,
            request_start_date=request_start_date,
            request_end_date=request_end_date,
            error_message="malformed upstream response",
            raw_detail=repr(type(response)),
        )

    if response.empty:
        return _build_result(
            frame=response,
            stage=stage,
            symbol=symbol,
            upstream_function=upstream_function,
            clock=clock,
            request_start_date=request_start_date,
            request_end_date=request_end_date,
            error_message="empty upstream frame",
        )

    return _build_result(
        frame=response,
        stage=stage,
        symbol=symbol,
        upstream_function=upstream_function,
        clock=clock,
        request_start_date=request_start_date,
        request_end_date=request_end_date,
    )


def _call_with_retries(call: FrameCall) -> object:
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
    error_message: str | None = None,
    raw_detail: str | None = None,
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
    error = (
        None
        if error_message is None
        else SourceErrorRow(
            stock_code=symbol,
            stage=stage,
            message=error_message,
            raw_detail=raw_detail,
        )
    )
    return SourceFetchResult(frame=frame, metadata=metadata, error=error)


def _validate_symbol(symbol: str) -> None:
    if _SYMBOL_RE.fullmatch(symbol) is None:
        raise ValueError("symbol must be a six-digit A-share code")


def _akshare_version() -> str:
    return str(getattr(ak, "__version__", "unknown"))
```

- [ ] **Step 4: Run the source-client and no-network tests and verify they pass**

Run:

```bash
uv run pytest tests/sources/test_akshare_client.py tests/test_no_network_default.py -q
```

Expected: PASS for all source-client and default no-network tests.

- [ ] **Step 5: Commit source validation and error handling**

Run:

```bash
git add src/future_ledger/sources/akshare_client.py tests/sources/test_akshare_client.py tests/test_no_network_default.py
git commit -m "feat: handle source fetch errors"
```

Expected: commit succeeds with only the source client, its tests, and the no-network contract update staged.

---

### Task 4: Update The Optional Live Smoke Test

**Files:**
- Modify: `tests/live/test_akshare_smoke.py`

- [ ] **Step 1: Update the optional live smoke test for `SourceFetchResult`**

Replace `tests/live/test_akshare_smoke.py` with:

```python
from __future__ import annotations

import pytest

from future_ledger.sources.akshare_client import fetch_a_share_spot

pytestmark = pytest.mark.live_akshare


def test_live_fetch_a_share_spot_smoke() -> None:
    result = fetch_a_share_spot()

    assert result.error is None
    assert result.metadata.stage == "spot_fetch"
    assert result.metadata.source_name == "akshare"
    assert result.metadata.row_count == len(result.frame.index)
    assert not result.frame.empty
```

- [ ] **Step 2: Run the live test file without the marker and verify it is skipped**

Run:

```bash
uv run pytest tests/live/test_akshare_smoke.py -q
```

Expected: SKIPPED with reason `live AKShare tests require -m live_akshare`.

- [ ] **Step 3: Commit the live smoke update**

Run:

```bash
git add tests/live/test_akshare_smoke.py
git commit -m "test: update source fetch network boundaries"
```

Expected: commit succeeds with only the live smoke test change staged.

---

### Task 5: Run Full Verification

**Files:**
- Verify: `src/future_ledger/domain.py`
- Verify: `src/future_ledger/sources/akshare_client.py`
- Verify: `tests/test_domain_models.py`
- Verify: `tests/sources/test_akshare_client.py`
- Verify: `tests/test_no_network_default.py`
- Verify: `tests/live/test_akshare_smoke.py`

- [ ] **Step 1: Run the focused source-fetching suite**

Run:

```bash
uv run pytest tests/test_domain_models.py tests/sources/test_akshare_client.py tests/test_no_network_default.py tests/live/test_akshare_smoke.py -q
```

Expected: PASS with the live smoke test skipped by default.

- [ ] **Step 2: Run all default tests**

Run:

```bash
uv run pytest -q
```

Expected: PASS with live AKShare tests skipped by default.

- [ ] **Step 3: Run ruff**

Run:

```bash
uv run ruff check .
```

Expected: PASS with no lint findings.

- [ ] **Step 4: Run strict mypy**

Run:

```bash
uv run mypy src tests
```

Expected: PASS with no type errors.

- [ ] **Step 5: Confirm no uncommitted implementation changes remain**

Run:

```bash
git status --short
```

Expected: no output for the files touched by this plan.

---

## Self-Review

**Spec coverage:** Covered. Tasks implement `SourceFetchResult`, `SourceMetadata`, `SourceErrorRow` attachment, spot/dividend/price fetches, stable stages, AKShare version capture, row counts, request dates, deterministic clock injection, symbol/date validation, three-attempt tenacity retries, empty-frame source errors, malformed response source errors, recoverable live exceptions, default monkeypatched tests, and opt-in live smoke behavior.

**Placeholder scan:** Covered. The plan contains concrete file paths, code blocks, commands, expected failures, expected passes, and commit commands.

**Type consistency:** Covered. `SourceMetadata`, `SourceFetchResult`, stage strings, function names, and test expectations use the same names across all tasks.
