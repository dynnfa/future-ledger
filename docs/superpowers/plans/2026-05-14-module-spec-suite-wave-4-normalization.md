# FutureLedger Module Spec Suite Wave 4: Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the dividend and price normalization specs that convert raw source frames into domain objects.

**Architecture:** Wave 4 can run Tasks 6 and 7 in parallel. Dividend normalization and price normalization own separate module contracts, but they should align on `SourceErrorRow` stage naming and invalid-row semantics.

**Tech Stack:** Python 3.11, Typer, pandas, AKShare, openpyxl, tenacity, pytest, ruff, mypy, Markdown specs under `docs/superpowers/specs/`.

---

## Source Context

This plan is split from `docs/superpowers/plans/2026-05-14-module-spec-suite.md`. It preserves the original task numbers so commits, reviews, and cross-module references line up with the master plan.

## Execution Rules

- Use one fresh agent per task.
- Keep each agent scoped to the files listed in its task.
- Do not combine task ownership across spec files.
- Run each task's verification commands before committing that task.
- After all tasks in this wave finish, run a quick consistency pass for names, stages, flags, and dependencies introduced inside this wave.

## Wave Task Order

Dispatch both tasks in parallel after Wave 3 has clarified source and universe boundary semantics.

```text
Task 6: 04-dividend-normalization
Task 7: 05-price-normalization
```

### Task 6: 04 Dividend Normalization Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the dividend normalization spec**

Create `docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 04 Dividend Normalization Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Convert AKShare dividend-detail frames into normalized `DividendRecord` instances and normalization errors.

## Current State

- `src/future_ledger/normalize/dividends.py` maps AKShare columns into `DividendRecord`.
- Duplicate report years currently use first-seen wins.
- The normalizer infers market from stock code and can raise `ValueError` for unknown prefixes.
- Percent and non-percent numeric fields use the same parser.

## Inputs

- `StockIdentity` with `code`, `name`, and `market`.
- Raw AKShare dividend-detail pandas `DataFrame`.
- Source metadata containing source name and fetched timestamp.

## Outputs

- `list[DividendRecord]` sorted by `report_year` descending.
- `list[SourceErrorRow]` for skipped rows, duplicate rows, malformed fields, and stock-level normalization failures.

## Domain Contracts

- Raw AKShare column mapping:
  - `报告期` -> `DividendRecord.report_period` and derived `report_year`.
  - `每10股派息` -> `cash_dividend_per_10_shares`.
  - `除权除息日` -> `ex_dividend_date`.
  - `股权登记日` -> `registration_date`.
  - `方案进度` -> `plan_status`.
  - `每股收益` -> `eps`.
  - `每股净资产` -> `net_asset_per_share`.
  - `净利润同比增长` -> `profit_growth_yoy_pct`.
  - `现金分红-股息率` -> `provider_yield_pct`.
- `cash_dividend_per_share` equals `cash_dividend_per_10_shares / Decimal("10")`.
- Percent fields keep percent units: `"5.30%"` becomes `Decimal("5.30")`, not `Decimal("0.053")`.
- Non-percent decimal fields reject values with a percent sign.
- Date parsing accepts `YYYY-MM-DD`, `YYYY/MM/DD`, and timestamp strings whose first 10 characters form a date.
- Missing optional numeric/date fields become `None`.
- The normalizer uses `StockIdentity.market`; it must not infer market from code.
- `source` is `akshare.stock_fhps_detail_em` for v0.

## Error Handling

- Missing or unparsable `报告期` skips the row and emits `SourceErrorRow(stage="dividend_normalize", message="missing report period")` or `message="invalid report period"`.
- Duplicate report periods are resolved by plan-status priority and emit `SourceErrorRow(stage="dividend_normalize", message="duplicate report period")`.
- Plan-status priority is `实施` > `股东大会通过` > `董事会预案` > `预案` > any other non-empty status > missing status.
- When two duplicate rows have the same plan-status priority, keep the row that appears later in the raw frame and emit the duplicate error.
- Malformed optional decimals become `None` and emit `SourceErrorRow(stage="dividend_normalize", message="invalid decimal field: <field_name>")`.
- Unknown stock-code prefixes are handled by universe selection; dividend normalization receives a `StockIdentity` and does not raise for prefixes.

## Data Quality Flags

- The normalizer emits source errors, not final report flags.
- Report assembly converts duplicate-period errors into `duplicate_report_period`.
- Report assembly converts empty normalized record sets into `no_valid_dividend_records`.

## Acceptance Criteria

- Fixture dividend frames normalize into deterministic `DividendRecord` values.
- Duplicate report periods prefer finalized implementation rows.
- Percent fields and non-percent decimal fields use field-specific parsing rules.
- Missing report period rows are skipped with source errors.
- Unknown code prefixes cannot halt dividend normalization because market is supplied by `StockIdentity`.

## Tests

- `tests/normalize/test_dividends.py::test_normalize_dividend_detail_maps_required_fields_from_fixture` remains the fixture mapping test.
- `tests/normalize/test_dividends.py::test_normalize_dividend_detail_prefers_implemented_duplicate_report_period` verifies plan-status priority.
- `tests/normalize/test_dividends.py::test_normalize_dividend_detail_uses_stock_identity_market` passes a nonstandard code with `market="BJ"` and expects no prefix inference.
- `tests/normalize/test_dividends.py::test_percent_fields_keep_percent_units` verifies `5.30%` becomes `Decimal("5.30")`.
- `tests/normalize/test_dividends.py::test_non_percent_decimal_rejects_percent_sign` expects a source error for `每股收益="2.10%"`.
- Run `uv run pytest tests/normalize/test_dividends.py -q`.

## Out of Scope

- Fetching raw dividend frames.
- Calculating dividend yield.
- Ranking stocks.
- Parsing non-AKShare dividend providers.

## Dependencies

- Depends on `future_ledger.domain.StockIdentity`, `DividendRecord`, and `SourceErrorRow`.
- Consumes output from source fetching.
- Feeds metrics and report assembly.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify normalization risk coverage**

Run:

```bash
rg -n "duplicate report period|plan-status priority|Percent fields|StockIdentity.market|invalid decimal field" docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md
```

Expected: output includes duplicate resolution, plan-status priority, percent parsing, market source, and invalid decimal behavior.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-04-dividend-normalization-design.md
git commit -m "docs: specify dividend normalization module"
```

### Task 7: 05 Price Normalization Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-05-price-normalization-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-05-price-normalization-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the price normalization spec**

Create `docs/superpowers/specs/2026-05-14-05-price-normalization-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 05 Price Normalization Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Convert AKShare daily price frames into sorted, valid `PricePoint` instances for dividend-yield and one-year return calculations.

## Current State

- `src/future_ledger/normalize/prices.py` maps `日期` and `收盘` into `PricePoint`.
- The current function returns only a list of points and does not report invalid rows.
- Sorting by date exists.
- Missing, zero, negative, duplicate, and malformed prices are not specified.

## Inputs

- Six-digit stock code.
- Raw AKShare daily price pandas `DataFrame`.
- Source metadata with source name and requested date range.

## Outputs

- `list[PricePoint]` sorted by `date` ascending.
- `list[SourceErrorRow]` for skipped malformed rows and duplicate conflicts.

## Domain Contracts

- Raw AKShare column mapping:
  - `日期` -> `PricePoint.date`.
  - `收盘` -> `PricePoint.close`.
- Date parsing accepts `YYYY-MM-DD`, `YYYY/MM/DD`, and timestamp strings whose first 10 characters form a date.
- Close price parsing accepts numeric values and numeric strings.
- `PricePoint.close` must be greater than `Decimal("0")`.
- Duplicate dates with the same close keep one point and do not emit an error.
- Duplicate dates with different closes keep the later raw row and emit `SourceErrorRow(stage="price_normalize", message="duplicate price date")`.
- Returned points are always sorted ascending and contain no duplicate dates.

## Error Handling

- Missing `日期` skips the row and emits `SourceErrorRow(stage="price_normalize", message="missing price date")`.
- Invalid date skips the row and emits `SourceErrorRow(stage="price_normalize", message="invalid price date")`.
- Missing `收盘` skips the row and emits `SourceErrorRow(stage="price_normalize", message="missing close price")`.
- Zero or negative close skips the row and emits `SourceErrorRow(stage="price_normalize", message="non-positive close price")`.
- Invalid close decimal skips the row and emits `SourceErrorRow(stage="price_normalize", message="invalid close price")`.
- A frame with no valid price points returns an empty list plus row-level source errors.

## Data Quality Flags

- The normalizer emits source errors, not final report flags.
- Metrics convert missing usable prices into `missing_reference_price` or `missing_return_price`.

## Acceptance Criteria

- Fixture price frames normalize into sorted `PricePoint` rows.
- Invalid rows are skipped with deterministic source error messages.
- Duplicate conflicting dates do not create duplicate `PricePoint` rows.
- Downstream metrics can rely on sorted valid points and avoid repeated full-list sorting.

## Tests

- `tests/normalize/test_prices.py::test_normalize_price_history_sorts_by_date` remains the sorting fixture test.
- `tests/normalize/test_prices.py::test_normalize_price_history_skips_non_positive_close` expects one source error and no point for zero or negative close.
- `tests/normalize/test_prices.py::test_normalize_price_history_reports_invalid_date_and_close` expects two source errors.
- `tests/normalize/test_prices.py::test_normalize_price_history_deduplicates_same_close` expects one point and no error.
- `tests/normalize/test_prices.py::test_normalize_price_history_keeps_later_duplicate_conflict` expects the later close and source error `duplicate price date`.
- Run `uv run pytest tests/normalize/test_prices.py -q`.

## Out of Scope

- Fetching raw price history.
- Adjusted-price selection beyond the AKShare v0 daily close source.
- Filling non-trading days.
- Return calculation.

## Dependencies

- Depends on `future_ledger.domain.PricePoint` and `SourceErrorRow`.
- Consumes output from source fetching.
- Feeds dividend-yield metrics, return metrics, and report assembly.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-05-price-normalization-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify price edge-case coverage**

Run:

```bash
rg -n "non-positive close price|duplicate price date|sorted ascending|missing close price|invalid close price" docs/superpowers/specs/2026-05-14-05-price-normalization-design.md
```

Expected: output includes non-positive, duplicate, sorting, missing close, and invalid close contracts.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-05-price-normalization-design.md
git commit -m "docs: specify price normalization module"
```
