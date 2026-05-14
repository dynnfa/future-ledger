# FutureLedger Module Spec Suite Final Cross-Module Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Review all ten module specs for consistency after the wave plans have completed.

**Architecture:** This final review runs after Waves 1-6. It does not create a new functional module spec; it verifies that all module specs exist, follow the standard template, avoid placeholder language, and use consistent names, stages, flags, fixture conventions, and dependency language.

**Tech Stack:** Python 3.11, Typer, pandas, AKShare, openpyxl, tenacity, pytest, ruff, mypy, Markdown specs under `docs/superpowers/specs/`.

---

## Source Context

This plan is split from `docs/superpowers/plans/2026-05-14-module-spec-suite.md`. Run it only after all six wave plans have completed and their commits are present.

## Execution Rules

- Use one fresh reviewer agent for the final cross-module review.
- Do not rewrite module specs wholesale during final review.
- Make only targeted consistency fixes, then rerun the final verification commands.
- If fixes are needed, commit them with the commit message from the review task.

## Final Cross-Module Review

- [ ] **Step 1: Verify all ten spec files exist**

Run:

```bash
uv run python -c 'from pathlib import Path; files=["2026-05-14-01-universe-selection-design.md","2026-05-14-02-source-fetching-design.md","2026-05-14-03-raw-cache-design.md","2026-05-14-04-dividend-normalization-design.md","2026-05-14-05-price-normalization-design.md","2026-05-14-06-metrics-design.md","2026-05-14-07-report-assembly-design.md","2026-05-14-08-workbook-writer-design.md","2026-05-14-09-cli-pipeline-design.md","2026-05-14-10-test-and-fixture-strategy-design.md"]; missing=[f for f in files if not (Path("docs/superpowers/specs")/f).exists()]; assert not missing, missing; print("ok")'
```

Expected: `ok`.

- [ ] **Step 2: Scan for placeholder language**

Run:

```bash
uv run python -c 'from pathlib import Path; terms=["T"+"BD","TO"+"DO","implement "+"later","fill in "+"details","add appropriate "+"error handling","Write tests for "+"the above","Similar to "+"Task"]; hits=[];
for p in sorted(Path("docs/superpowers/specs").glob("2026-05-14-*-design.md")):
    text=p.read_text()
    for term in terms:
        if term in text:
            hits.append(f"{p}:{term}")
assert not hits, hits
print("ok")'
```

Expected: `ok`.

- [ ] **Step 3: Verify every spec has the standard template**

Run:

```bash
uv run python -c 'from pathlib import Path; headings=["## Purpose","## Current State","## Inputs","## Outputs","## Domain Contracts","## Error Handling","## Data Quality Flags","## Acceptance Criteria","## Tests","## Out of Scope","## Dependencies"]; failures={};
for p in sorted(Path("docs/superpowers/specs").glob("2026-05-14-*-design.md")):
    text=p.read_text()
    missing=[h for h in headings if h not in text]
    if missing:
        failures[str(p)]=missing
assert not failures, failures
print("ok")'
```

Expected: `ok`.

- [ ] **Step 4: Commit cross-module review fixes if any were needed**

If no fixes were needed, skip this commit. If fixes were needed, run:

```bash
git add docs/superpowers/specs/2026-05-14-*-design.md
git commit -m "docs: align module spec suite"
```
