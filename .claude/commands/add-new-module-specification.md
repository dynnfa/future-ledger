---
name: add-new-module-specification
description: Workflow command scaffold for add-new-module-specification in future-ledger.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-new-module-specification

Use this workflow when working on **add-new-module-specification** in `future-ledger`.

## Goal

Defines the design/specification for a new module by creating a new markdown file in the specs directory.

## Common Files

- `docs/superpowers/specs/*-design.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Create a new markdown file in docs/superpowers/specs/ with naming pattern YYYY-MM-DD-XX-module-name-design.md
- Write the module's design/specification in the file
- Commit the new file with a message like 'docs: specify <module> module'

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.