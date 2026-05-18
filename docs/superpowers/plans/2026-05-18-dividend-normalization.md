# Dividend Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert AKShare dividend-detail frames into deterministic `DividendRecord` rows and recoverable `SourceErrorRow` normalization errors.

**Architecture:** Keep all AKShare dividend column knowledge inside `src/future_ledger/normalize/dividends.py`. The normalizer accepts a `StockIdentity` so universe selection owns market inference, validates report periods before selecting rows, resolves duplicate report periods by plan-status priority, then maps only selected rows into `DividendRecord` instances with field-specific decimal parsing.

**Tech Stack:** Python 3.11, pandas, dataclasses from `future_ledger.domain`, `Decimal`, `datetime.date`, pytest, uv.

---

## Execution Prerequisite: Independent Branch

Development for this plan must happen on an isolated branch or worktree before any code edits.

- Branch name: `feature/dividend-normalization`
- If using the main workspace directly, run:

```bash
git switch -c feature/dividend-normalization
```

- If using an isolated worktree, use the `superpowers:using-git-worktrees` skill at execution time and create a worktree from `feature/dividend-normalization`.
- Do not implement this plan on `main` or on an unrelated feature branch.

## Scope Check

The spec covers one subsystem: dividend detail normalization. This plan updates `src/future_ledger/normalize/dividends.py` and its focused tests in `tests/normalize/test_dividends.py`.

Report assembly flags are intentionally not implemented here because there is no report assembly module in the current codebase. This plan preserves the source-error messages that later report assembly can convert into `duplicate_report_period` and `no_valid_dividend_records`.

## File Structure

- Modify `src/future_ledger/normalize/dividends.py`
  - Public API becomes `normalize_dividend_detail(stock: StockIdentity, frame: pd.DataFrame) -> tuple[list[DividendRecord], list[SourceErrorRow]]`.
  - Uses `stock.code`, `stock.name`, and `stock.market`; removes `_market_for_code()`.
  - Emits `SourceErrorRow(stage="dividend_normalize", ...)` for missing report periods, invalid report periods, duplicate report periods, and malformed optional decimal fields.
  - Keeps `SOURCE_NAME = "akshare.stock_fhps_detail_em"`.
  - Owns plan-status priority, report-period parsing, date parsing, percent decimal parsing, and non-percent decimal parsing.

- Modify `tests/normalize/test_dividends.py`
  - Imports `StockIdentity`.
  - Keeps `test_normalize_dividend_detail_maps_required_fields_from_fixture`.
  - Replaces the old duplicate-year test with `test_normalize_dividend_detail_prefers_implemented_duplicate_report_period`.
  - Adds `test_normalize_dividend_detail_uses_stock_identity_market`.
  - Adds `test_percent_fields_keep_percent_units`.
  - Adds `test_non_percent_decimal_rejects_percent_sign`.
  - Adds focused tests for invalid report periods and malformed optional decimal fields so the implementation is pinned down.

No domain model changes are needed. `DividendRecord`, `StockIdentity`, and `SourceErrorRow` already contain the fields required by this spec.

---

### Task 1: Public Contract Uses StockIdentity

**Files:**
- Modify: `tests/normalize/test_dividends.py`
- Modify: `src/future_ledger/normalize/dividends.py`

- [ ] **Step 1: Replace the dividend normalization tests with the new contract tests**

Replace `tests/normalize/test_dividends.py` with:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import StockIdentity
from future_ledger.normalize.dividends import normalize_dividend_detail


def test_normalize_dividend_detail_maps_required_fields_from_fixture() -> None:
    frame = pd.read_csv(Path("tests/fixtures/akshare/dividend_detail_600000.csv"))

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert errors == []
    assert len(records) == 2
    assert records[0].stock_code == "600000"
    assert records[0].stock_name == "浦发银行"
    assert records[0].market == "SH"
    assert records[0].report_year == 2025
    assert records[0].report_period == "2025-12-31"
    assert records[0].cash_dividend_per_10_shares == Decimal("4.10")
    assert records[0].cash_dividend_per_share == Decimal("0.41")
    assert records[0].ex_dividend_date == date(2026, 7, 1)
    assert records[0].registration_date == date(2026, 6, 30)
    assert records[0].plan_status == "实施"
    assert records[0].eps == Decimal("2.10")
    assert records[0].net_asset_per_share == Decimal("18.50")
    assert records[0].profit_growth_yoy_pct == Decimal("5.30")
    assert records[0].provider_yield_pct == Decimal("4.00")
    assert records[0].source == "akshare.stock_fhps_detail_em"


def test_normalize_dividend_detail_uses_stock_identity_market() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "2024-12-31", "每10股派息": "4.0", "方案进度": "实施"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("900001", "北交示例", "BJ"), frame)

    assert errors == []
    assert len(records) == 1
    assert records[0].stock_code == "900001"
    assert records[0].market == "BJ"


def test_normalize_dividend_detail_skips_missing_report_period() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "", "每10股派息": "4.0"},
            {"报告期": None, "每10股派息": "4.2"},
            {"报告期": "2024-12-31", "每10股派息": "3.80"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("000001", "平安银行", "SZ"), frame)

    assert [record.report_year for record in records] == [2024]
    assert records[0].market == "SZ"
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "missing report period"),
        ("dividend_normalize", "missing report period"),
    ]


def _stock(code: str, name: str, market: str) -> StockIdentity:
    return StockIdentity(code=code, name=name, market=market)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
uv run pytest tests/normalize/test_dividends.py -q
```

Expected: FAIL because `normalize_dividend_detail()` still accepts `stock_code, stock_name, frame`, still infers market from the stock-code prefix, and still emits `stage="normalize"`.

- [ ] **Step 3: Update the normalizer to accept StockIdentity and use the new error stage**

Replace `src/future_ledger/normalize/dividends.py` with:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import DividendRecord, SourceErrorRow, StockIdentity

SOURCE_NAME = "akshare.stock_fhps_detail_em"
NORMALIZE_STAGE = "dividend_normalize"


def normalize_dividend_detail(
    stock: StockIdentity, frame: pd.DataFrame
) -> tuple[list[DividendRecord], list[SourceErrorRow]]:
    records: list[DividendRecord] = []
    errors: list[SourceErrorRow] = []
    seen_periods: set[str] = set()

    for row in frame.to_dict(orient="records"):
        report_period = _string_or_none(row.get("报告期"))
        if report_period is None:
            errors.append(_error(stock.code, "missing report period", row))
            continue

        report_year = _report_year_or_none(report_period)
        if report_year is None:
            errors.append(_error(stock.code, "invalid report period", row))
            continue

        if report_period in seen_periods:
            errors.append(_error(stock.code, "duplicate report period", row))
            continue

        cash_dividend_per_10_shares = _decimal_or_none(row.get("每10股派息"))
        seen_periods.add(report_period)
        records.append(
            DividendRecord(
                stock_code=stock.code,
                stock_name=stock.name,
                market=stock.market,
                report_year=report_year,
                report_period=report_period,
                cash_dividend_per_10_shares=cash_dividend_per_10_shares,
                cash_dividend_per_share=_per_share(cash_dividend_per_10_shares),
                ex_dividend_date=_date_or_none(row.get("除权除息日")),
                registration_date=_date_or_none(row.get("股权登记日")),
                plan_status=_string_or_none(row.get("方案进度")),
                eps=_decimal_or_none(row.get("每股收益")),
                net_asset_per_share=_decimal_or_none(row.get("每股净资产")),
                profit_growth_yoy_pct=_decimal_or_none(row.get("净利润同比增长")),
                provider_yield_pct=_decimal_or_none(row.get("现金分红-股息率")),
                source=SOURCE_NAME,
            )
        )

    return sorted(records, key=lambda item: item.report_year, reverse=True), errors


def _report_year_or_none(report_period: str) -> int | None:
    try:
        return int(report_period[:4])
    except ValueError:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    text = _string_or_none(value)
    if text is None:
        return None

    normalized = text.replace(",", "").removesuffix("%").strip()
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _per_share(per_10_shares: Decimal | None) -> Decimal | None:
    if per_10_shares is None:
        return None
    return per_10_shares / Decimal("10")


def _date_or_none(value: Any) -> date | None:
    text = _string_or_none(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10].replace("/", "-"))
    except ValueError:
        return None


def _string_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    return text


def _error(stock_code: str, message: str, row: dict[str, Any]) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=stock_code,
        stage=NORMALIZE_STAGE,
        message=message,
        raw_detail=str(row),
    )
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```bash
uv run pytest tests/normalize/test_dividends.py -q
```

Expected: PASS for the current three tests.

- [ ] **Step 5: Commit the public contract change**

Run:

```bash
git add src/future_ledger/normalize/dividends.py tests/normalize/test_dividends.py
git commit -m "feat: normalize dividends from stock identity"
```

Expected: commit succeeds with only the normalizer and its focused test file staged.

---

### Task 2: Duplicate Report Period Priority

**Files:**
- Modify: `tests/normalize/test_dividends.py`
- Modify: `src/future_ledger/normalize/dividends.py`

- [ ] **Step 1: Add the failing duplicate-priority test**

Insert this test in `tests/normalize/test_dividends.py` above `_stock()`:

```python
def test_normalize_dividend_detail_prefers_implemented_duplicate_report_period() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "每10股派息": "3.50",
                "除权除息日": "2025-07-01",
                "方案进度": "董事会预案",
            },
            {
                "报告期": "2024-12-31",
                "每10股派息": "4.20",
                "除权除息日": "2025-07-02",
                "方案进度": "实施",
            },
            {
                "报告期": "2023-12-31",
                "每10股派息": "2.80",
                "除权除息日": "2024/07/01",
                "方案进度": "实施",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert [record.report_year for record in records] == [2024, 2023]
    assert records[0].report_period == "2024-12-31"
    assert records[0].cash_dividend_per_10_shares == Decimal("4.20")
    assert records[0].cash_dividend_per_share == Decimal("0.42")
    assert records[0].ex_dividend_date == date(2025, 7, 2)
    assert records[0].plan_status == "实施"
    assert len(errors) == 1
    assert errors[0].stock_code == "600000"
    assert errors[0].stage == "dividend_normalize"
    assert errors[0].message == "duplicate report period"
    assert "实施" in (errors[0].raw_detail or "")
```

- [ ] **Step 2: Add the failing same-priority-later-row test**

Insert this test below the duplicate-priority test:

```python
def test_normalize_dividend_detail_prefers_later_duplicate_when_priority_ties() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "2024-12-31", "每10股派息": "3.50", "方案进度": "实施"},
            {"报告期": "2024-12-31", "每10股派息": "4.20", "方案进度": "实施"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert len(records) == 1
    assert records[0].cash_dividend_per_10_shares == Decimal("4.20")
    assert len(errors) == 1
    assert errors[0].message == "duplicate report period"
```

- [ ] **Step 3: Run the focused tests and verify they fail**

Run:

```bash
uv run pytest tests/normalize/test_dividends.py::test_normalize_dividend_detail_prefers_implemented_duplicate_report_period tests/normalize/test_dividends.py::test_normalize_dividend_detail_prefers_later_duplicate_when_priority_ties -q
```

Expected: FAIL because the current implementation keeps the first row for a duplicate period.

- [ ] **Step 4: Implement duplicate selection before record creation**

Replace `src/future_ledger/normalize/dividends.py` with:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import DividendRecord, SourceErrorRow, StockIdentity

SOURCE_NAME = "akshare.stock_fhps_detail_em"
NORMALIZE_STAGE = "dividend_normalize"
PLAN_STATUS_PRIORITY = {
    "实施": 5,
    "股东大会通过": 4,
    "董事会预案": 3,
    "预案": 2,
}


def normalize_dividend_detail(
    stock: StockIdentity, frame: pd.DataFrame
) -> tuple[list[DividendRecord], list[SourceErrorRow]]:
    errors: list[SourceErrorRow] = []
    selected_rows: dict[str, tuple[int, int, int, dict[str, Any]]] = {}

    for index, row in enumerate(frame.to_dict(orient="records")):
        report_period = _string_or_none(row.get("报告期"))
        if report_period is None:
            errors.append(_error(stock.code, "missing report period", row))
            continue

        report_year = _report_year_or_none(report_period)
        if report_year is None:
            errors.append(_error(stock.code, "invalid report period", row))
            continue

        priority = _plan_status_priority(row.get("方案进度"))
        existing = selected_rows.get(report_period)
        if existing is not None:
            errors.append(_error(stock.code, "duplicate report period", row))
            existing_priority, existing_index, _, _ = existing
            if priority < existing_priority:
                continue
            if priority == existing_priority and index < existing_index:
                continue

        selected_rows[report_period] = (priority, index, report_year, row)

    records = [
        _record_from_row(stock, report_year, report_period, row)
        for report_period, (_, _, report_year, row) in selected_rows.items()
    ]
    return sorted(records, key=lambda item: item.report_year, reverse=True), errors


def _record_from_row(
    stock: StockIdentity,
    report_year: int,
    report_period: str,
    row: dict[str, Any],
) -> DividendRecord:
    cash_dividend_per_10_shares = _decimal_or_none(row.get("每10股派息"))
    return DividendRecord(
        stock_code=stock.code,
        stock_name=stock.name,
        market=stock.market,
        report_year=report_year,
        report_period=report_period,
        cash_dividend_per_10_shares=cash_dividend_per_10_shares,
        cash_dividend_per_share=_per_share(cash_dividend_per_10_shares),
        ex_dividend_date=_date_or_none(row.get("除权除息日")),
        registration_date=_date_or_none(row.get("股权登记日")),
        plan_status=_string_or_none(row.get("方案进度")),
        eps=_decimal_or_none(row.get("每股收益")),
        net_asset_per_share=_decimal_or_none(row.get("每股净资产")),
        profit_growth_yoy_pct=_decimal_or_none(row.get("净利润同比增长")),
        provider_yield_pct=_decimal_or_none(row.get("现金分红-股息率")),
        source=SOURCE_NAME,
    )


def _plan_status_priority(value: Any) -> int:
    status = _string_or_none(value)
    if status is None:
        return 0
    return PLAN_STATUS_PRIORITY.get(status, 1)


def _report_year_or_none(report_period: str) -> int | None:
    try:
        return int(report_period[:4])
    except ValueError:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    text = _string_or_none(value)
    if text is None:
        return None

    normalized = text.replace(",", "").removesuffix("%").strip()
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _per_share(per_10_shares: Decimal | None) -> Decimal | None:
    if per_10_shares is None:
        return None
    return per_10_shares / Decimal("10")


def _date_or_none(value: Any) -> date | None:
    text = _string_or_none(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10].replace("/", "-"))
    except ValueError:
        return None


def _string_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    return text


def _error(stock_code: str, message: str, row: dict[str, Any]) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=stock_code,
        stage=NORMALIZE_STAGE,
        message=message,
        raw_detail=str(row),
    )
```

- [ ] **Step 5: Run the focused tests and verify they pass**

Run:

```bash
uv run pytest tests/normalize/test_dividends.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit duplicate priority behavior**

Run:

```bash
git add src/future_ledger/normalize/dividends.py tests/normalize/test_dividends.py
git commit -m "feat: resolve duplicate dividend report periods"
```

Expected: commit succeeds with only the normalizer and its focused test file staged.

---

### Task 3: Field-Specific Decimal And Report-Period Errors

**Files:**
- Modify: `tests/normalize/test_dividends.py`
- Modify: `src/future_ledger/normalize/dividends.py`

- [ ] **Step 1: Add percent and non-percent decimal tests**

Insert these tests in `tests/normalize/test_dividends.py` above `_stock()`:

```python
def test_percent_fields_keep_percent_units() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "净利润同比增长": "5.30%",
                "现金分红-股息率": "4.00%",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert errors == []
    assert records[0].profit_growth_yoy_pct == Decimal("5.30")
    assert records[0].provider_yield_pct == Decimal("4.00")


def test_non_percent_decimal_rejects_percent_sign() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "每10股派息": "4.20",
                "每股收益": "2.10%",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert len(records) == 1
    assert records[0].cash_dividend_per_10_shares == Decimal("4.20")
    assert records[0].eps is None
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "invalid decimal field: eps"),
    ]
```

- [ ] **Step 2: Add invalid report-period and malformed optional decimal tests**

Insert these tests below the decimal tests:

```python
def test_invalid_report_period_is_skipped_with_source_error() -> None:
    frame = pd.DataFrame(
        [
            {"报告期": "not-a-date", "每10股派息": "4.20"},
            {"报告期": "2024-12-31", "每10股派息": "3.80"},
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert [record.report_year for record in records] == [2024]
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "invalid report period"),
    ]


def test_malformed_optional_decimal_becomes_none_with_source_error() -> None:
    frame = pd.DataFrame(
        [
            {
                "报告期": "2024-12-31",
                "每10股派息": "bad-value",
                "每股净资产": "18.50",
            },
        ]
    )

    records, errors = normalize_dividend_detail(_stock("600000", "浦发银行", "SH"), frame)

    assert len(records) == 1
    assert records[0].cash_dividend_per_10_shares is None
    assert records[0].cash_dividend_per_share is None
    assert records[0].net_asset_per_share == Decimal("18.50")
    assert [(error.stage, error.message) for error in errors] == [
        ("dividend_normalize", "invalid decimal field: cash_dividend_per_10_shares"),
    ]
```

- [ ] **Step 3: Run the focused tests and verify they fail**

Run:

```bash
uv run pytest tests/normalize/test_dividends.py::test_percent_fields_keep_percent_units tests/normalize/test_dividends.py::test_non_percent_decimal_rejects_percent_sign tests/normalize/test_dividends.py::test_invalid_report_period_is_skipped_with_source_error tests/normalize/test_dividends.py::test_malformed_optional_decimal_becomes_none_with_source_error -q
```

Expected: FAIL because non-percent decimals still accept percent signs and malformed decimals do not emit source errors.

- [ ] **Step 4: Implement field-specific parsing and selected-row decimal errors**

Replace `src/future_ledger/normalize/dividends.py` with:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import DividendRecord, SourceErrorRow, StockIdentity

SOURCE_NAME = "akshare.stock_fhps_detail_em"
NORMALIZE_STAGE = "dividend_normalize"
PLAN_STATUS_PRIORITY = {
    "实施": 5,
    "股东大会通过": 4,
    "董事会预案": 3,
    "预案": 2,
}


def normalize_dividend_detail(
    stock: StockIdentity, frame: pd.DataFrame
) -> tuple[list[DividendRecord], list[SourceErrorRow]]:
    errors: list[SourceErrorRow] = []
    selected_rows: dict[str, tuple[int, int, int, dict[str, Any]]] = {}

    for index, row in enumerate(frame.to_dict(orient="records")):
        report_period = _string_or_none(row.get("报告期"))
        if report_period is None:
            errors.append(_error(stock.code, "missing report period", row))
            continue

        report_year = _report_year_or_none(report_period)
        if report_year is None:
            errors.append(_error(stock.code, "invalid report period", row))
            continue

        priority = _plan_status_priority(row.get("方案进度"))
        existing = selected_rows.get(report_period)
        if existing is not None:
            errors.append(_error(stock.code, "duplicate report period", row))
            existing_priority, existing_index, _, _ = existing
            if priority < existing_priority:
                continue
            if priority == existing_priority and index < existing_index:
                continue

        selected_rows[report_period] = (priority, index, report_year, row)

    records = [
        _record_from_row(stock, report_year, report_period, row, errors)
        for report_period, (_, _, report_year, row) in selected_rows.items()
    ]
    return sorted(records, key=lambda item: item.report_year, reverse=True), errors


def _record_from_row(
    stock: StockIdentity,
    report_year: int,
    report_period: str,
    row: dict[str, Any],
    errors: list[SourceErrorRow],
) -> DividendRecord:
    cash_dividend_per_10_shares = _decimal_or_none(
        row.get("每10股派息"),
        field_name="cash_dividend_per_10_shares",
        stock_code=stock.code,
        row=row,
        errors=errors,
        allow_percent=False,
    )
    return DividendRecord(
        stock_code=stock.code,
        stock_name=stock.name,
        market=stock.market,
        report_year=report_year,
        report_period=report_period,
        cash_dividend_per_10_shares=cash_dividend_per_10_shares,
        cash_dividend_per_share=_per_share(cash_dividend_per_10_shares),
        ex_dividend_date=_date_or_none(row.get("除权除息日")),
        registration_date=_date_or_none(row.get("股权登记日")),
        plan_status=_string_or_none(row.get("方案进度")),
        eps=_decimal_or_none(
            row.get("每股收益"),
            field_name="eps",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=False,
        ),
        net_asset_per_share=_decimal_or_none(
            row.get("每股净资产"),
            field_name="net_asset_per_share",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=False,
        ),
        profit_growth_yoy_pct=_decimal_or_none(
            row.get("净利润同比增长"),
            field_name="profit_growth_yoy_pct",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=True,
        ),
        provider_yield_pct=_decimal_or_none(
            row.get("现金分红-股息率"),
            field_name="provider_yield_pct",
            stock_code=stock.code,
            row=row,
            errors=errors,
            allow_percent=True,
        ),
        source=SOURCE_NAME,
    )


def _plan_status_priority(value: Any) -> int:
    status = _string_or_none(value)
    if status is None:
        return 0
    return PLAN_STATUS_PRIORITY.get(status, 1)


def _report_year_or_none(report_period: str) -> int | None:
    if len(report_period) < 4 or not report_period[:4].isdigit():
        return None
    try:
        _date_or_none_required(report_period)
    except ValueError:
        return None
    return int(report_period[:4])


def _decimal_or_none(
    value: Any,
    *,
    field_name: str,
    stock_code: str,
    row: dict[str, Any],
    errors: list[SourceErrorRow],
    allow_percent: bool,
) -> Decimal | None:
    text = _string_or_none(value)
    if text is None:
        return None

    normalized = text.replace(",", "").strip()
    if normalized.endswith("%"):
        if not allow_percent:
            errors.append(_error(stock_code, f"invalid decimal field: {field_name}", row))
            return None
        normalized = normalized.removesuffix("%").strip()
    elif "%" in normalized:
        errors.append(_error(stock_code, f"invalid decimal field: {field_name}", row))
        return None

    try:
        return Decimal(normalized)
    except InvalidOperation:
        errors.append(_error(stock_code, f"invalid decimal field: {field_name}", row))
        return None


def _per_share(per_10_shares: Decimal | None) -> Decimal | None:
    if per_10_shares is None:
        return None
    return per_10_shares / Decimal("10")


def _date_or_none(value: Any) -> date | None:
    text = _string_or_none(value)
    if text is None:
        return None
    try:
        return _date_or_none_required(text)
    except ValueError:
        return None


def _date_or_none_required(text: str) -> date:
    return date.fromisoformat(text[:10].replace("/", "-"))


def _string_or_none(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    return text


def _error(stock_code: str, message: str, row: dict[str, Any]) -> SourceErrorRow:
    return SourceErrorRow(
        stock_code=stock_code,
        stage=NORMALIZE_STAGE,
        message=message,
        raw_detail=str(row),
    )
```

- [ ] **Step 5: Run the focused tests and verify they pass**

Run:

```bash
uv run pytest tests/normalize/test_dividends.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit field-specific parsing**

Run:

```bash
git add src/future_ledger/normalize/dividends.py tests/normalize/test_dividends.py
git commit -m "feat: parse dividend decimals by field"
```

Expected: commit succeeds with only the normalizer and its focused test file staged.

---

### Task 4: Update Call Sites And Run Full Verification

**Files:**
- Search: `src/future_ledger/**/*.py`
- Search: `tests/**/*.py`
- Modify if needed: any file still calling `normalize_dividend_detail("600000", "浦发银行", frame)`

- [ ] **Step 1: Search for old normalizer call sites**

Run:

```bash
rg 'normalize_dividend_detail\\(' src tests
```

Expected before cleanup: only `src/future_ledger/normalize/dividends.py` and `tests/normalize/test_dividends.py` should appear. If another file still passes `stock_code, stock_name, frame`, update it to construct or pass an existing `StockIdentity`.

- [ ] **Step 2: If old call sites exist, update them**

Use this exact pattern for any remaining old call site:

```python
from future_ledger.domain import StockIdentity
from future_ledger.normalize.dividends import normalize_dividend_detail

stock = StockIdentity(code="600000", name="浦发银行", market="SH")
records, errors = normalize_dividend_detail(stock, frame)
```

Expected: no old three-argument calls remain.

- [ ] **Step 3: Run the required focused test command from the spec**

Run:

```bash
uv run pytest tests/normalize/test_dividends.py -q
```

Expected: PASS.

- [ ] **Step 4: Run static checks**

Run:

```bash
uv run ruff check src tests
```

Expected: PASS.

Run:

```bash
uv run mypy src
```

Expected: PASS.

- [ ] **Step 5: Run the full test suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit final cleanup if any files changed**

If Step 2 changed files, run:

```bash
git add src tests
git commit -m "chore: update dividend normalizer call sites"
```

Expected: commit succeeds with only files changed in this task staged. If Step 2 found no old call sites, skip this commit.

---

## Self-Review

- Spec coverage:
  - AKShare column mapping is covered by the fixture mapping test and `_record_from_row()`.
  - `cash_dividend_per_share = cash_dividend_per_10_shares / Decimal("10")` is asserted in fixture and duplicate tests.
  - Percent fields keep percent units in `test_percent_fields_keep_percent_units`.
  - Non-percent decimal rejection is covered in `test_non_percent_decimal_rejects_percent_sign`.
  - Date parsing accepts hyphen dates, slash dates, and timestamp-like first-ten-character dates through `_date_or_none()`.
  - Missing report periods and invalid report periods emit `dividend_normalize` source errors.
  - Duplicate report periods use plan-status priority and same-priority later-row selection.
  - Unknown code prefixes cannot halt normalization because the public API uses `StockIdentity.market`.
  - Later report flags remain out of scope and are preserved as source-error messages for report assembly.

- Placeholder scan:
  - No task contains placeholder markers or vague error-handling instructions.
  - Every code-editing step includes concrete code or an exact replacement pattern.

- Type consistency:
  - Public signature is consistently `normalize_dividend_detail(stock: StockIdentity, frame: pd.DataFrame)`.
  - Error stage is consistently `dividend_normalize`.
  - Decimal error field names are domain names: `cash_dividend_per_10_shares`, `eps`, `net_asset_per_share`, `profit_growth_yoy_pct`, and `provider_yield_pct`.
