# FutureLedger Module Spec Suite Wave 6: Test and Fixtures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the cross-cutting test and fixture strategy spec after the module specs exist.

**Architecture:** Wave 6 is serial and contains only Task 10. It summarizes test expectations across Tasks 1-9, so it should run after all previous module specs have been written and reviewed.

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

Run this task after Waves 1-5 have completed.

```text
Task 10: 10-test-and-fixture-strategy
```

### Task 10: 10 Test and Fixture Strategy Spec

**Files:**
- Create: `docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md`

- [ ] **Step 1: Run missing-file check**

Run:

```bash
uv run python -c 'from pathlib import Path; assert Path("docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md").exists()'
```

Expected: FAIL with `AssertionError` because the module spec file has not been created.

- [ ] **Step 2: Create the test and fixture strategy spec**

Create `docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md` with this exact Markdown:

```markdown
# FutureLedger v0 10 Test and Fixture Strategy Design

Status: DRAFT
Generated: 2026-05-14

## Purpose

Define the project-wide verification strategy for FutureLedger v0 so default CI remains deterministic and does not depend on live financial endpoints.

## Current State

- Tests exist for CLI validation, domain model construction, universe selection, dividend normalization, price normalization, dividend yield, and one-year return.
- Fixtures exist under `tests/fixtures/akshare/` and `tests/fixtures/prices/`.
- No workbook writer, report assembly, cache, source-client, or pipeline integration tests exist.
- `pyproject.toml` configures `pytest`, `ruff`, and strict `mypy`.

## Inputs

- Module specs `01` through `09`.
- Existing fixture CSVs under `tests/fixtures/`.
- Development commands from `pyproject.toml`.

## Outputs

- A deterministic default test suite.
- Fixture naming conventions.
- Optional live AKShare smoke tests excluded from default CI.
- Static analysis expectations.
- Coverage expectations for known review risks.

## Domain Contracts

- Default verification command is `uv run pytest`.
- Static verification commands are `uv run ruff check .` and `uv run mypy src tests`.
- Default tests must not access the network.
- Fixture files use UTF-8 CSV.
- Fixture paths:
  - `tests/fixtures/akshare/spot_a_share.csv`
  - `tests/fixtures/akshare/dividend_detail_<symbol>.csv`
  - `tests/fixtures/prices/<symbol>_daily_<start_date>_<end_date>.csv`
  - `tests/fixtures/cache/<stage>/<cache_id>.csv`
  - `tests/fixtures/workbooks/` only for intentionally small golden workbooks.
- Fixture date ranges use `YYYYMMDD` in filenames.
- Live tests live under `tests/live/`, use marker `live_akshare`, and are skipped by default.
- Test data should stay small: default fixture CSVs should be under 100 rows unless a test explicitly validates large-frame behavior.

## Error Handling

- A test that would call AKShare without the `live_akshare` marker is a test-suite bug.
- Live smoke failures do not block default CI because live tests are skipped unless explicitly selected.
- Golden workbook tests compare sheet names, headers, cell types, and representative values, not volatile generated timestamps.

## Data Quality Flags

- Every data quality flag introduced by module specs must have at least one unit or integration test.
- Required tested flags: `no_valid_dividend_records`, `has_missing_years_5y`, `missing_reference_price`, `missing_return_price`, `uncertain_dividend_window`, `duplicate_report_period`, and `empty_dividend_detail`.

## Acceptance Criteria

- `uv run pytest` passes without network access.
- `uv run ruff check .` passes.
- `uv run mypy src tests` passes under strict mypy.
- Live smoke tests run only with `uv run pytest tests/live -m live_akshare`.
- Integration tests cover pipeline behavior from fixture source results to workbook shape.
- Known review risks from the module index have explicit tests.

## Tests

- `tests/test_no_network_default.py::test_default_tests_do_not_use_live_akshare_marker` verifies live tests are isolated under `tests/live/`.
- `tests/test_fixture_strategy.py::test_fixture_files_follow_naming_convention` validates fixture paths.
- `tests/test_fixture_strategy.py::test_fixture_files_stay_small` enforces the 100-row default fixture limit.
- `tests/test_pipeline.py::test_pipeline_fixture_integration_writes_expected_report_tables` uses fake source functions and fixtures.
- `tests/test_workbook_writer.py::test_workbook_shape_from_fixture_report_tables` verifies workbook sheets and headers.
- Run `uv run pytest tests/test_fixture_strategy.py tests/test_no_network_default.py -q`.

## Out of Scope

- Performance benchmarking for the full A-share universe.
- Production monitoring.
- Historical backfill validation beyond v0 fixture windows.
- External data-provider contract tests outside optional smoke tests.

## Dependencies

- Summarizes verification requirements from module specs `01` through `09`.
- Depends on `pyproject.toml` pytest, ruff, and mypy configuration.
```

- [ ] **Step 3: Verify required headings**

Run:

```bash
uv run python -c 'from pathlib import Path; p=Path("docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md"); text=p.read_text(); headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; missing=[h for h in headings if h not in text]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Verify test strategy coverage**

Run:

```bash
rg -n "uv run pytest|ruff check|mypy src tests|live_akshare|100 rows|missing_reference_price|duplicate_report_period" docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md
```

Expected: output includes default pytest, static checks, live marker, fixture size limit, and representative data quality flags.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-05-14-10-test-and-fixture-strategy-design.md
git commit -m "docs: specify test and fixture strategy"
```
