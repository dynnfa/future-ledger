# FutureLedger v0 Module Spec Index Design

Status: DRAFT
Generated: 2026-04-28

## Purpose

This document is the module-spec index for FutureLedger v0. It decomposes the
existing A-share dividend research workbook design into a sequence of smaller
specs that can be implemented and tested independently.

The index is not a replacement for `docs/designs/v0-dividend-report.md`. That
document defines the v0 product boundary and report behavior. This index defines
the engineering spec queue needed to deliver that behavior without letting
module contracts drift.

## Product Boundary

The indexed specs cover only the v0 local Python CLI workflow:

```bash
future-ledger dividends scan
```

In scope:

- A-share stock universe selection.
- AKShare-backed dividend and price data fetching.
- Raw source caching for reproducibility.
- Dividend and price normalization into domain models.
- Dividend-yield and trailing one-year return metrics.
- Report table assembly.
- Excel workbook writing.
- CLI orchestration and validation.
- Deterministic fixture-based tests plus optional live smoke tests.

Out of scope:

- Bank fixed-deposit rate scraping.
- Web dashboard or service API.
- Portfolio management.
- Investment advice or allocation logic.
- Multi-source reconciliation beyond the primary v0 AKShare source.

## Success Criteria

The module specs are complete when:

- Every v0 module has a named spec with clear inputs, outputs, contracts,
  errors, flags, acceptance criteria, and tests.
- `pipeline.run_scan()` can be implemented by following the dependency order in
  this index.
- AKShare raw column names remain confined to source and normalization modules.
- Downstream modules communicate through `future_ledger.domain` types.
- Each module can be implemented and verified without requiring live financial
  endpoints in default CI.
- Known review risks are assigned to the module specs that should resolve them.

## Module Dependency Order

The module dependency order follows the runtime data flow:

```text
01-universe-selection
  -> 02-source-fetching
  -> 03-raw-cache
  -> 04-dividend-normalization
  -> 05-price-normalization
  -> 06-metrics
  -> 07-report-assembly
  -> 08-workbook-writer
  -> 09-cli-pipeline
  -> 10-test-and-fixture-strategy
```

`10-test-and-fixture-strategy` is a cross-cutting spec. It appears last because
it summarizes the project-wide verification strategy, but each module spec must
also define its own focused tests.

## Standard Module Spec Template

Each module spec must use this structure:

1. Purpose
2. Current State
3. Inputs
4. Outputs
5. Domain Contracts
6. Error Handling
7. Data Quality Flags
8. Acceptance Criteria
9. Tests
10. Out of Scope
11. Dependencies

The template keeps module decisions local while preserving a common review
shape. A reader should be able to understand what a module does, how to call it,
what it returns, and how it fails without reading implementation internals.

## Module Specs

### 01-universe-selection

Purpose: build a deterministic list of `StockIdentity` rows from the A-share
spot market frame.

Primary code area:

- `src/future_ledger/sources/universe.py`
- `future_ledger.domain.StockIdentity`

The spec must define:

- Supported universe names, starting with `all-a-excluding-st`.
- ST filtering rules.
- `limit` semantics for development runs.
- Market inference for SH, SZ, and BJ codes.
- Behavior for unsupported or unexpected code prefixes.
- Whether universe-level errors fail the scan or become source errors.

Known risks assigned here:

- Unknown stock-code prefixes can currently raise `ValueError` and halt a batch.

### 02-source-fetching

Purpose: isolate live AKShare calls behind a small source client boundary.

Primary code area:

- `src/future_ledger/sources/akshare_client.py`
- `src/future_ledger/errors.py`

The spec must define:

- Fetch functions for spot data, dividend detail, and price history.
- Fetch-stage names used in `source_errors`.
- Retry, timeout, and transient failure behavior.
- How empty or malformed upstream frames are represented.
- What metadata is captured for source lineage.
- The boundary between default fixture tests and optional live AKShare smoke
  tests.

Known risks assigned here:

- Live endpoint instability must not make default CI flaky.

### 03-raw-cache

Purpose: persist raw upstream frames and source metadata so a report run can be
audited and reproduced.

Primary code area:

- `src/future_ledger/cache.py`
- `.future_ledger/cache`

The spec must define:

- Cache key format by stage and symbol.
- CSV snapshot format.
- JSON metadata sidecar format.
- Recorded metadata such as source name, symbol, fetched timestamp, AKShare
  version, row count, and request date range.
- Read-through versus write-only behavior for v0.
- Cache behavior when live fetch succeeds, returns empty data, or fails.

Known risks assigned here:

- `read_cache()` and `write_cache()` are currently not implemented.

### 04-dividend-normalization

Purpose: convert AKShare dividend-detail frames into normalized
`DividendRecord` instances and normalization errors.

Primary code area:

- `src/future_ledger/normalize/dividends.py`
- `future_ledger.domain.DividendRecord`
- `future_ledger.domain.SourceErrorRow`

The spec must define:

- AKShare column-to-domain field mapping.
- Date parsing rules.
- Decimal parsing rules for cash dividend, EPS, net assets, growth, and
  provider yield.
- Duplicate report-period behavior.
- Plan-status priority, including preference for finalized implementation rows.
- Missing field handling and normalization error rows.
- Source name lineage.

Known risks assigned here:

- Duplicate report periods currently use first-seen wins.
- Unknown market prefixes can currently halt normalization.
- Percent parsing and non-percent decimal parsing need explicit field-specific
  semantics.

### 05-price-normalization

Purpose: convert AKShare daily price frames into sorted `PricePoint` instances.

Primary code area:

- `src/future_ledger/normalize/prices.py`
- `future_ledger.domain.PricePoint`

The spec must define:

- AKShare price column mapping.
- Date parsing rules.
- Decimal close-price parsing rules.
- Sorting guarantee.
- Handling for missing, zero, negative, duplicate, or malformed prices.
- Whether invalid rows are skipped with errors or fail the stock.

Known risks assigned here:

- Metric fallback behavior depends on normalized prices being sorted and valid.

### 06-metrics

Purpose: calculate dividend-yield and trailing one-year return metrics from
normalized dividends and prices.

Primary code area:

- `src/future_ledger/metrics/dividend_yield.py`
- `src/future_ledger/metrics/returns.py`

The spec must define:

- Reference-price rule for dividend yield.
- Whether the ex-dividend date close itself is eligible.
- Previous or nearest trading-day fallback behavior.
- Yield precision and rounding.
- One-year return window rules.
- Leap-year handling for February 29.
- Start and end price fallback behavior.
- Dividend inclusion rule for the return window.
- Data quality flags for missing or uncertain metric inputs.

Known risks assigned here:

- February 29 can currently crash the return calculation.
- Reference price currently includes the ex-dividend date close.
- Dividend yield precision is not yet quantized.
- Price lookup should avoid unnecessary full-list sorting per lookup.

### 07-report-assembly

Purpose: assemble normalized records, metrics, source errors, and metadata into
`ReportTables`.

Primary code area:

- `src/future_ledger/domain.py`
- `src/future_ledger/pipeline.py`

The spec must define:

- Construction of `DividendRankRow`, `DividendLongRow`, `PricePoint`,
  `SourceErrorRow`, and `MetadataRow` outputs.
- Ranking behavior when latest yield is missing.
- Annual expansion field names and ordering.
- Aggregated data quality flags.
- Metadata rows for run parameters, source versions, source priority, generated
  timestamp, and disclaimer.
- Whether `annual_fields` should remain mutable or become a mapping.

Known risks assigned here:

- `pipeline.run_scan()` currently returns empty tables.
- `DividendRankRow.annual_fields` is mutable despite the frozen dataclass.

### 08-workbook-writer

Purpose: write `ReportTables` to the v0 Excel workbook.

Primary code area:

- A new writer module under `src/future_ledger/`.
- `openpyxl` and `pandas` integration as appropriate.

The spec must define:

- Required sheets and order:
  `dividend_rank`, `dividend_long`, `price_points`, `source_errors`,
  `metadata`.
- Required columns and column order.
- Formatting for decimals, percentages, dates, booleans, and empty values.
- Output directory creation behavior.
- Failure behavior for unwritable output paths.
- Workbook shape tests.

Known risks assigned here:

- Workbook writing is not implemented yet.

### 09-cli-pipeline

Purpose: connect Typer CLI inputs to the pipeline and workbook writer.

Primary code area:

- `src/future_ledger/cli.py`
- `src/future_ledger/pipeline.py`

The spec must define:

- CLI arguments and defaults.
- Validation for `--years`, `--as-of`, `--universe`, `--output`,
  `--limit`, and `--cache-dir`.
- User-visible progress and completion messages.
- Exit behavior for recoverable per-stock failures versus fatal configuration
  failures.
- How `run_scan()` sequences universe, fetch, cache, normalize, metrics,
  assembly, and workbook writing.

Known risks assigned here:

- The CLI currently reports that workbook writing is not implemented.
- `run_scan()` is not yet a real orchestration path.

### 10-test-and-fixture-strategy

Purpose: define the project-wide verification strategy for v0.

Primary code area:

- `tests/`
- `tests/fixtures/`
- `pyproject.toml`

The spec must define:

- Fixture naming conventions.
- Unit test expectations for each module.
- Integration test expectations for pipeline and workbook shape.
- Optional live AKShare smoke tests excluded from default CI.
- Test data size constraints.
- Coverage expectations for known failure modes.
- Static analysis expectations for `ruff` and strict `mypy`.

Known risks assigned here:

- Default verification must stay deterministic and not depend on live financial
  endpoints.

## Recommended Spec Writing Order

The runtime dependency order is not the best writing order. The current codebase
already has useful lower-level modules and tests, but the user-facing v0 loop is
not closed. Write specs in this order to close the workbook flow first:

1. `07-report-assembly`
2. `08-workbook-writer`
3. `09-cli-pipeline`
4. `03-raw-cache`
5. `02-source-fetching`
6. `04-dividend-normalization`
7. `05-price-normalization`
8. `06-metrics`
9. `01-universe-selection`
10. `10-test-and-fixture-strategy`

This order gives the project an executable spine before tightening lower-level
edge cases.

## Shared Cross-Module Rules

### Domain Boundary

AKShare-specific column names must not appear downstream of `sources/` and
`normalize/`. Downstream modules should use `future_ledger.domain` types and
module-specific result objects.

### Error Semantics

Recoverable per-stock failures should produce `SourceErrorRow` entries and
allow the scan to continue. Fatal configuration, validation, and output-path
errors should fail the CLI with a non-zero exit.

### Data Quality Flags

Flags should be stable string identifiers suitable for filtering in Excel. A
module spec that introduces a flag must define the exact condition that emits
it.

### Reproducibility

Every workbook must include enough metadata to identify run parameters, source
priority, source package version, generated timestamp, and the research-only
disclaimer.

### Testing

Default tests must use fixtures and must not require network access. Live
AKShare checks can exist only as explicit smoke tests that are skipped by
default.

## Next Step

After this index is accepted, the next spec should be
`07-report-assembly-design.md`, because it defines the report tables that the
workbook writer and CLI pipeline need to complete the v0 loop.
