---
name: add-module-spec-suite-plans
description: Workflow command scaffold for add-module-spec-suite-plans in future-ledger.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-module-spec-suite-plans

Use this workflow when working on **add-module-spec-suite-plans** in `future-ledger`.

## Goal

Adds a set of planning markdown files for module spec suite, typically grouped by wave or topic.

## Common Files

- `docs/superpowers/plans/*module-spec-suite*.md`
- `.gitignore`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create one or more new markdown files in docs/superpowers/plans/ with naming pattern YYYY-MM-DD-module-spec-suite-wave-<n>-<topic>.md
- Optionally update .gitignore or other related files
- Commit all new/updated files with a message like 'Add module spec suite implementation plans'

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.