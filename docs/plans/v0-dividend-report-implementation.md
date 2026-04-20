# FutureLedger v0 Dividend Report Implementation Plan

Status: READY FOR IMPLEMENTATION
Generated: 2026-04-20
Source design: `docs/designs/v0-dividend-report.md`

## Objective

Build FutureLedger v0 as a local Python CLI that generates a reproducible A-share dividend research workbook.

The first usable command is:

```bash
future-ledger dividends scan \
  --years 5 \
  --as-of 2026-04-20 \
  --universe all-a-excluding-st \
  --output reports/dividend_rank.xlsx
```

The product is not a portfolio manager, not investment advice, and not a web app. v0 earns trust by making data lineage, calculation rules, source failures, and missing history visible.

## Bottom-Up Technical Choices

| Layer | Choice | Why |
|---|---|---|
| Runtime | Python 3.11 | Matches the design doc, stable for data tooling, avoids newest-version dependency churn. |
| Project manager | `uv` | Official docs position it as a Python package/project manager with lockfiles, Python version management, and build support. |
| CLI | `Typer` | Official Typer docs emphasize type-hint-driven CLIs, automatic help, completion, and simple subcommand trees. |
| Data source | `akshare` | Design requires AKShare. Official AKShare docs expose `stock_fhps_detail_em`, `stock_zh_a_spot_em`, and `stock_zh_a_hist`. |
| Tabular processing | `pandas` | AKShare returns pandas DataFrames. Keeping pandas avoids a conversion layer for v0. |
| Excel output | `pandas.ExcelWriter` with `openpyxl` engine | openpyxl is a direct xlsx read/write library and also lets tests verify workbook shape. |
| Schema/config | stdlib `dataclasses` first, Pydantic deferred | v0 has narrow local inputs. Explicit dataclasses are enough until config expands. |
| Retries | `tenacity` | Simple retry policy around upstream calls, no custom retry framework. |
| Progress/logging | `rich` through Typer dependency, stdlib `logging` for files | Clean terminal UX without inventing a TUI. |
| Tests | `pytest`, fixture-first | Default CI must not depend on live financial endpoints. |
| Lint/format | `ruff` | Official Ruff docs position it as fast linting and formatting with pyproject support. |
| CI | GitHub Actions | Run lint and deterministic tests. Live AKShare smoke test stays manual/optional. |

Primary references:
- AKShare stock docs: https://akshare.akfamily.xyz/data/stock/stock.html
- uv docs: https://docs.astral.sh/uv/
- Typer docs: https://typer.tiangolo.com/
- Ruff docs: https://docs.astral.sh/ruff/
- openpyxl docs: https://openpyxl.readthedocs.io/

## What Already Exists

- `docs/designs/v0-dividend-report.md`: source of truth for v0 product boundary, command, workbook shape, calculation rules, and failure modes. Reuse it.
- `TODOS.md`: already defers bank fixed-deposit scraping to v2. Keep it deferred.
- No Python package, tests, CI, or README exist yet.
- No commits exist on `main` yet. Treat the first implementation as the foundation commit.

## Scope Challenge

Minimum complete v0:

1. Scaffold a Python package.
2. Implement only the dividend CLI.
3. Use AKShare Eastmoney dividend detail as the primary source.
4. Use AKShare A-share spot list to build the stock universe and exclude ST.
5. Use AKShare historical daily prices for reference prices and one-year returns.
6. Cache raw source outputs.
7. Generate the five required workbook sheets.
8. Add deterministic fixture tests for every branch in the design doc.

Deferred:

- Bank fixed-deposit scanner, already tracked in `TODOS.md`.
- Web dashboard.
- Multi-source dividend reconciliation.
- Provider fallback hierarchy beyond v0 primary source.
- Investment screening or recommendation language.
- PyPI publication. Source install is enough for v0.

Complexity check: this plan intentionally creates more than 8 files, but they are narrow package foundation files. That is acceptable because the repo currently has no implementation. The smell would be adding abstractions like plugin systems, async orchestration, or source reconciliation now. Do not.

## Architecture

Package layout:

```text
FutureLedger/
  pyproject.toml
  README.md
  src/future_ledger/
    __init__.py
    cli.py
    domain.py
    pipeline.py
    sources/
      __init__.py
      akshare_client.py
    normalize/
      __init__.py
      dividends.py
    metrics/
      __init__.py
      dividends.py
      prices.py
    reports/
      __init__.py
      excel.py
    cache.py
    errors.py
  tests/
    fixtures/
      akshare/
    test_cli.py
    test_normalize_dividends.py
    test_metrics_dividends.py
    test_metrics_prices.py
    test_excel_report.py
```

Data flow:

```text
CLI args
  |
  v
RunConfig(years, as_of, universe, output)
  |
  v
Universe fetch: stock_zh_a_spot_em()
  |       \
  |        -> filter ST, normalize market/code/name
  v
For each stock
  |
  +--> dividend source: stock_fhps_detail_em(symbol)
  |        |
  |        +--> raw cache
  |        +--> normalize annual dividend records
  |
  +--> price source: stock_zh_a_hist(symbol, adjust="")
           |
           +--> raw cache
           +--> reference prices for ex-dividend and 1y return windows

Normalized records + price points
  |
  +--> dividend yield metrics
  +--> 1y return metrics
  +--> data quality flags
  |
  v
Workbook
  +--> dividend_rank
  +--> dividend_long
  +--> price_points
  +--> source_errors
  +--> metadata
```

Key boundary rule: AKShare-specific column names must not leak past `sources/` and `normalize/`. Everything after normalization uses FutureLedger English field names from the design doc.

## Step-by-Step Implementation

### Step 1: Scaffold Project

Create:

- `pyproject.toml`
- `.python-version`
- `.gitignore`
- `README.md`
- `src/future_ledger/`
- `tests/`

Initial commands:

```bash
uv init --package
uv add akshare pandas openpyxl typer tenacity
uv add --dev pytest ruff
uv lock
```

Acceptance:

- `uv run future-ledger --help` works.
- `uv run pytest` runs with at least a placeholder test.
- `uv run ruff check .` passes.

### Step 2: Define Domain Contracts

Add `src/future_ledger/domain.py`.

Define dataclasses:

- `RunConfig`
- `StockIdentity`
- `DividendRecord`
- `PricePoint`
- `DividendRankRow`
- `SourceError`
- `ReportTables`

Use `Decimal` for dividend and price calculations internally, then convert to floats only when writing Excel.

Acceptance:

- Tests validate date parsing and default config.
- Tests validate output field names match the design doc.

### Step 3: CLI Skeleton

Add `src/future_ledger/cli.py`.

Commands:

```text
future-ledger
  dividends
    scan
```

Options:

- `--years`, default `5`
- `--as-of`, default current local date
- `--universe`, default `all-a-excluding-st`
- `--output`, default `reports/dividend_rank.xlsx`
- `--limit`, hidden/dev option for fixture and sample runs
- `--cache-dir`, default `.future_ledger/cache`

Acceptance:

- Default args produce the expected `RunConfig`.
- Invalid `--years 0` exits with a clear CLI error.
- Output parent directory is created if missing.

### Step 4: AKShare Client Wrapper

Add `src/future_ledger/sources/akshare_client.py`.

Functions:

- `fetch_a_share_spot()`
- `fetch_dividend_detail(symbol)`
- `fetch_daily_prices(symbol, start_date, end_date)`

Rules:

- Wrap AKShare calls with retries and timeout-adjacent error handling where possible.
- Convert exceptions into `SourceError`.
- Cache raw DataFrames as CSV plus JSON metadata.
- Do not silently fallback to another dividend source.

Acceptance:

- Unit tests mock AKShare calls.
- Timeout/exception returns `SourceError`, not a crashed full scan.
- Empty DataFrame is recorded as a source/data-quality issue.

### Step 5: Universe Builder

Implement universe normalization in the source layer or a small helper in `pipeline.py`.

Rules:

- Use AKShare A-share spot data.
- Exclude ST by default.
- Preserve rows with missing optional fields, but flag missing stock code/name as source error.

Acceptance:

- Fixture with ST names excludes them.
- Non-ST A-share rows become `StockIdentity`.
- Missing required identity fields become `SourceError`.

### Step 6: Dividend Normalization

Add `src/future_ledger/normalize/dividends.py`.

Map AKShare Eastmoney columns:

- `报告期` -> `report_period`
- `现金分红-现金分红比例` -> `cash_dividend_per_10_shares`
- `现金分红-股息率` -> raw provider yield reference only
- `股权登记日` -> `registration_date`
- `除权除息日` -> `ex_dividend_date`
- `方案进度` or equivalent -> `plan_status`, if present
- EPS/net asset/profit growth fields as optional metrics

Rules:

- Derive `report_year` from `报告期`.
- Convert per-10-share cash dividend to per-share.
- Missing report period is a source error.
- Duplicate report period is kept but flagged; choose the latest plan status/date deterministically for rank rows.

Acceptance:

- Fixture tests cover normal rows, missing period, duplicate period, empty source, and partial metrics.

### Step 7: Price Lookup Rules

Add `src/future_ledger/metrics/prices.py`.

Functions:

- `close_on_or_before(prices, target_date)`
- `close_on_or_after(prices, target_date)`
- `reference_price_for_ex_dividend(prices, ex_dividend_date)`

Rules:

- Ex-dividend reference price uses close on ex-dividend date, else nearest previous trading day.
- One-year start price uses nearest later trading day.
- One-year end price uses nearest previous trading day.
- Missing prices return a flagged empty result, not zero.

Acceptance:

- Tests cover exact trading day, weekend/holiday fallback, missing before/after data, and empty prices.

### Step 8: Dividend and Return Metrics

Add `src/future_ledger/metrics/dividends.py`.

Functions:

- `calculate_dividend_yield(record, reference_price)`
- `calculate_5y_summary(records, price_points, years, as_of)`
- `calculate_trailing_1y_return(records, prices, as_of)`

Rules:

- Ranking uses locally calculated `cash_dividend_per_share / reference_close_price * 100`.
- Provider yield is included only as a raw reference field if useful.
- Missing dividend history is not zero.
- Include dividends whose ex-dividend date is within `[window_start, window_end]`.
- If source cannot determine dividend window, flag `uncertain_dividend_window`.

Acceptance:

- Tests cover positive dividend, zero dividend, missing price, missing ex-dividend date, missing history, and 1-year return with dividends.

### Step 9: Pipeline Orchestration

Add `src/future_ledger/pipeline.py`.

Pipeline behavior:

- Build universe.
- Iterate stock by stock.
- Record per-stock errors and continue.
- Produce `ReportTables`.
- Sort `dividend_rank` by latest calculated annual dividend yield descending, with missing yield last.

Failure threshold:

- If more than 30% of universe rows fail source fetch, finish workbook but add a metadata warning.
- CLI exits non-zero only for configuration errors or unwritable output, not per-stock upstream failures.

Acceptance:

- Pipeline fixture test with mixed success/failure still writes rows and source errors.
- Sorting puts missing yield last.

### Step 10: Excel Writer

Add `src/future_ledger/reports/excel.py`.

Sheets:

- `dividend_rank`
- `dividend_long`
- `price_points`
- `source_errors`
- `metadata`

Rules:

- Stable column order from the design doc.
- Freeze top row.
- Add autofilter.
- Format percent and currency-like numeric fields.
- Metadata includes command args, AKShare version, generated timestamp, source priority, disclaimer.

Acceptance:

- openpyxl test loads generated workbook.
- Required sheets exist.
- Required columns exist.
- Metadata includes non-investment-advice disclaimer.
- Unwritable output path test produces clear CLI error.

### Step 11: README and Compliance Copy

README must include:

- What FutureLedger v0 does.
- Install/dev commands.
- Example CLI command.
- Explanation of workbook sheets.
- Data source and reproducibility notes.
- Disclaimer from the design doc.

Acceptance:

- README does not contain buy/sell recommendation language.
- Metadata sheet contains the same disclaimer.

### Step 12: CI

Add `.github/workflows/ci.yml`.

Run:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Live AKShare smoke test:

- Add later as a manual workflow or `pytest -m live`.
- Do not run it in default CI.

## Code Path Coverage Plan

```text
CODE PATH COVERAGE
==================
[+] cli.py
    |
    +-- dividends scan
        +-- [GAP] default args -> RunConfig
        +-- [GAP] invalid years
        +-- [GAP] custom as-of/output
        +-- [GAP] unwritable output path

[+] sources/akshare_client.py
    |
    +-- fetch_a_share_spot()
    |   +-- [GAP] success DataFrame
    |   +-- [GAP] empty DataFrame
    |   +-- [GAP] exception/timeout
    |
    +-- fetch_dividend_detail(symbol)
    |   +-- [GAP] success DataFrame cached
    |   +-- [GAP] exception creates SourceError
    |
    +-- fetch_daily_prices(symbol, start, end)
        +-- [GAP] exact date range
        +-- [GAP] missing price rows

[+] normalize/dividends.py
    |
    +-- normalize_dividend_records()
        +-- [GAP] valid annual rows
        +-- [GAP] missing report period
        +-- [GAP] duplicate report period
        +-- [GAP] missing optional metrics

[+] metrics/prices.py
    |
    +-- close_on_or_before()
    |   +-- [GAP] exact date
    |   +-- [GAP] nearest previous trading date
    |   +-- [GAP] no available previous price
    |
    +-- close_on_or_after()
        +-- [GAP] exact date
        +-- [GAP] nearest later trading date
        +-- [GAP] no available later price

[+] metrics/dividends.py
    |
    +-- calculate_dividend_yield()
    |   +-- [GAP] normal calculation
    |   +-- [GAP] missing price
    |   +-- [GAP] zero/empty dividend
    |
    +-- calculate_trailing_1y_return()
        +-- [GAP] normal one-year window
        +-- [GAP] missing start price
        +-- [GAP] missing end price
        +-- [GAP] uncertain dividend window

[+] reports/excel.py
    |
    +-- write_workbook()
        +-- [GAP] all required sheets
        +-- [GAP] required column order
        +-- [GAP] metadata/disclaimer
        +-- [GAP] source_errors sheet populated

USER FLOW COVERAGE
==================
[+] Generate default report
    +-- [GAP] [->E2E] future-ledger dividends scan writes xlsx

[+] Generate sample report
    +-- [GAP] [->E2E] --limit 5 writes xlsx quickly

[+] Upstream partial failure
    +-- [GAP] [->E2E] one failed stock appears in source_errors, scan continues

COVERAGE TARGET
===============
Initial implementation starts at 0/N.
No implementation step is done until its listed gaps have tests.
```

## Failure Modes

| Codepath | Production failure | Handling required | Test |
|---|---|---|---|
| Universe fetch | AKShare endpoint changes columns | SourceError + metadata warning | fixture with missing columns |
| ST exclusion | Stock name uses unusual marker | conservative name-based filter + test cases | fixture |
| Dividend fetch | timeout or upstream exception | retry, SourceError, continue | mocked exception |
| Dividend normalization | missing report period | SourceError, row skipped | fixture |
| Dividend normalization | duplicate report year | deterministic selection + conflict flag | fixture |
| Price fetch | no price for ex-dividend date | nearest previous trading day | fixture |
| Price fetch | no price at all | empty metric + flag | fixture |
| 1y return | as_of is non-trading day | nearest previous end close | fixture |
| 1y return | start date is non-trading day | nearest later start close | fixture |
| Excel writer | output path unwritable | CLI error, non-zero exit | CLI test |

Critical gap rule: no silent failure is allowed. If a metric is blank, the row must contain a quality flag explaining why.

## Performance Plan

Expected bottleneck is network I/O, not pandas.

v0 defaults:

- Sequential first, with retries and cache. Correctness beats speed.
- Add `--limit` for development.
- Cache raw per-symbol dividend and price responses.
- Fetch price history once per symbol for the whole required date range, not per dividend row.
- Keep concurrency deferred until the sequential pipeline and cache are proven.

Optional v0.1:

- Add bounded thread pool with `--max-workers 4`.
- Keep deterministic ordering in final tables.
- Rate-limit AKShare calls to avoid self-inflicted upstream failures.

## Parallelization Strategy

Sequential implementation is safer for the first pass, but work can split after Step 2.

| Step | Modules touched | Depends on |
|---|---|---|
| Scaffold + domain | root, `src/future_ledger/` | none |
| CLI | `src/future_ledger/cli.py` | domain |
| AKShare wrapper | `src/future_ledger/sources/` | domain |
| Normalization | `src/future_ledger/normalize/` | domain |
| Metrics | `src/future_ledger/metrics/` | domain |
| Excel writer | `src/future_ledger/reports/` | domain |
| Pipeline | `src/future_ledger/pipeline.py` | sources, normalize, metrics, reports |
| CI/README | root, `.github/` | scaffold |

Parallel lanes:

- Lane A: Scaffold + domain -> pipeline integration.
- Lane B: AKShare wrapper fixtures.
- Lane C: normalization + metrics.
- Lane D: Excel writer.
- Lane E: README + CI.

Execution order: finish Lane A domain contracts first, then launch B/C/D/E in parallel, then integrate through pipeline.

Conflict flags: Lane C and pipeline both depend heavily on domain dataclasses. Freeze field names before splitting.

## NOT in Scope

- Bank fixed-deposit collection: deferred to v2 in `TODOS.md`.
- Web dashboard: data correctness comes first.
- Multi-source reconciliation: v0 uses one primary source and explicit source priority.
- Investment recommendations: forbidden by product boundary.
- Async/concurrent fetch engine: defer until source correctness and cache behavior are proven.
- PyPI release: source install is sufficient for v0.

## Review Summary

- Step 0 Scope Challenge: scope accepted as v0 dividend-only CLI.
- Architecture Review: 1 issue found, avoid leaking AKShare raw schema past normalization.
- Code Quality Review: 1 issue found, do not introduce Pydantic/config abstraction until needed.
- Test Review: coverage diagram produced, all initial paths are gaps because implementation does not exist yet.
- Performance Review: 1 issue found, network I/O is the bottleneck; solve with caching before concurrency.
- TODOs: existing v2 bank scanner TODO is valid. No new TODO needed.
- Failure modes: no critical silent gaps remain if quality flags are implemented as required.
- Outside voice: skipped.
- Lake Score: 4/4 complete recommendations chosen.
