# Universe Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic `StockIdentity` universe from an A-share spot frame while reporting recoverable malformed rows through `SourceErrorRow`.

**Architecture:** Keep universe selection isolated in `src/future_ledger/sources/universe.py`. The public `build_universe()` function validates fatal frame-level inputs first, then iterates raw spot rows into `(list[StockIdentity], list[SourceErrorRow])`, using small private helpers for code normalization, name normalization, and market inference.

**Tech Stack:** Python 3.11, pandas, dataclasses from `future_ledger.domain`, pytest, uv.

---

## Scope Check

The spec covers one subsystem: A-share universe selection. It can be implemented and tested independently in `src/future_ledger/sources/universe.py` and `tests/sources/test_universe.py`.

## File Structure

- Modify `src/future_ledger/sources/universe.py`
  - Owns the `build_universe(frame, universe, limit)` contract.
  - Imports `SourceError` for fatal source-frame errors.
  - Imports `SourceErrorRow` for recoverable row-level errors.
  - Keeps `_market_for_code()` private to source universe selection.
  - Adds `_normalize_code()`, `_string_or_none()`, and `_universe_error()` private helpers.

- Modify `tests/sources/test_universe.py`
  - Documents the return contract by destructuring `stocks, errors`.
  - Keeps existing ST, limit, and market inference tests.
  - Adds tests for unknown prefixes, missing required columns, empty frames, integer-like stock codes, missing stock names, unsupported universe names, and non-positive limits.

No domain model changes are needed because `StockIdentity`, `SourceErrorRow`, and `SourceError` already exist.

---

### Task 1: Update Universe Tests For The New Contract

**Files:**
- Modify: `tests/sources/test_universe.py`

- [ ] **Step 1: Replace the universe test file with failing tests**

Replace `tests/sources/test_universe.py` with:

```python
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
```

- [ ] **Step 2: Run the focused test file and verify it fails**

Run:

```bash
uv run pytest tests/sources/test_universe.py -q
```

Expected: FAIL. The existing implementation still returns only `list[StockIdentity]`, raises `ValueError` for unknown prefixes, and does not raise `SourceError` for missing required columns.

- [ ] **Step 3: Commit the failing tests**

Run:

```bash
git add tests/sources/test_universe.py
git commit -m "test: define universe source error contract"
```

Expected: commit succeeds with only `tests/sources/test_universe.py` staged.

---

### Task 2: Implement Universe Selection Errors And Normalization

**Files:**
- Modify: `src/future_ledger/sources/universe.py`
- Test: `tests/sources/test_universe.py`

- [ ] **Step 1: Replace the universe implementation**

Replace `src/future_ledger/sources/universe.py` with:

```python
from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import SourceErrorRow, StockIdentity
from future_ledger.errors import SourceError

REQUIRED_COLUMNS = ("代码", "名称")
SUPPORTED_UNIVERSE = "all-a-excluding-st"


def build_universe(
    frame: pd.DataFrame, universe: str, limit: int | None
) -> tuple[list[StockIdentity], list[SourceErrorRow]]:
    if universe != SUPPORTED_UNIVERSE:
        raise ValueError(f"Unsupported universe: {universe}")
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise SourceError("spot frame missing required columns: 代码, 名称")

    if frame.empty:
        return [], [
            SourceErrorRow(
                stock_code="",
                stage="universe",
                message="empty spot frame",
                raw_detail=None,
            )
        ]

    stocks: list[StockIdentity] = []
    errors: list[SourceErrorRow] = []

    for row in frame.to_dict(orient="records"):
        code = _normalize_code(row.get("代码"))
        raw_detail = str(row)
        if code is None:
            errors.append(_universe_error("", "missing stock code", raw_detail))
            continue

        name = _string_or_none(row.get("名称"))
        if name is None:
            errors.append(_universe_error(code, "missing stock name", raw_detail))
            continue

        if "ST" in name.upper():
            continue

        try:
            market = _market_for_code(code)
        except ValueError:
            errors.append(_universe_error(code, "unsupported stock code prefix", raw_detail))
            continue

        stocks.append(StockIdentity(code=code, name=name, market=market))

    if limit is not None:
        stocks = stocks[:limit]
    return stocks, errors


def _market_for_code(code: str) -> str:
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    raise ValueError(f"Unsupported A-share stock code prefix: {code!r}")


def _normalize_code(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    if isinstance(value, float):
        if not value.is_integer():
            return None
        text = str(int(value))
    elif isinstance(value, int):
        text = str(value)
    else:
        text = str(value).strip()
        if text.endswith(".0") and text.removesuffix(".0").isdigit():
            text = text.removesuffix(".0")

    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    if not text.isdigit():
        return None
    if len(text) <= 6:
        return text.zfill(6)
    return text


def _string_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    return text


def _universe_error(stock_code: str, message: str, raw_detail: str | None) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=stock_code,
        stage="universe",
        message=message,
        raw_detail=raw_detail,
    )
```

- [ ] **Step 2: Run the focused universe tests**

Run:

```bash
uv run pytest tests/sources/test_universe.py -q
```

Expected: PASS with all tests in `tests/sources/test_universe.py` passing.

- [ ] **Step 3: Run lint on touched Python files**

Run:

```bash
uv run ruff check src/future_ledger/sources/universe.py tests/sources/test_universe.py
```

Expected: PASS with no lint violations.

- [ ] **Step 4: Commit the implementation**

Run:

```bash
git add src/future_ledger/sources/universe.py tests/sources/test_universe.py
git commit -m "feat: report recoverable universe row errors"
```

Expected: commit succeeds with the implementation and updated tests staged.

---

### Task 3: Final Verification

**Files:**
- Verify: `src/future_ledger/sources/universe.py`
- Verify: `tests/sources/test_universe.py`

- [ ] **Step 1: Run the spec acceptance test command**

Run:

```bash
uv run pytest tests/sources/test_universe.py -q
```

Expected: PASS. This directly satisfies the spec test command.

- [ ] **Step 2: Run the default test suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS. Default tests do not require live AKShare data.

- [ ] **Step 3: Run type checking**

Run:

```bash
uv run mypy src tests
```

Expected: PASS. `build_universe()` has a precise tuple return type and no strict-mode type errors are introduced.

- [ ] **Step 4: Inspect git status**

Run:

```bash
git status --short
```

Expected: no unstaged changes from this implementation. If unrelated pre-existing changes appear, leave them untouched and mention them in the handoff.

---

## Self-Review

- Spec coverage: The plan covers supported universe validation, non-positive limits, required raw columns, empty spot frames, ST filtering, integer-like code normalization, SH/SZ/BJ market inference, unknown-prefix source errors, missing-name source errors, post-filter limit behavior, and default non-live tests.
- Placeholder scan: The plan contains concrete file paths, code, commands, and expected outcomes. It does not rely on unspecified validation or unnamed tests.
- Type consistency: `build_universe()` consistently returns `tuple[list[StockIdentity], list[SourceErrorRow]]`; tests destructure `stocks, errors`; row-level errors consistently use `stage="universe"`.
