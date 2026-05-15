```markdown
# future-ledger Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides guidance on the development patterns and workflows used in the `future-ledger` TypeScript codebase. It covers coding conventions, specification documentation workflows, and testing patterns, ensuring consistency and clarity for contributors.

## Coding Conventions

### File Naming
- Use **kebab-case** for all file names.
  - Example: `transaction-manager.ts`, `user-profile.test.ts`

### Import Style
- Use **relative imports**.
  - Example:
    ```typescript
    import { calculateBalance } from './utils/calculate-balance';
    ```

### Export Style
- Use **named exports**.
  - Example:
    ```typescript
    // In utils/calculate-balance.ts
    export function calculateBalance(...) { ... }
    ```
    ```typescript
    // In another file
    import { calculateBalance } from './utils/calculate-balance';
    ```

### Commit Messages
- Follow **conventional commit** style.
- Use prefixes like `docs:` for documentation changes.
  - Example: `docs: specify transaction module`

## Workflows

### Add New Module Specification
**Trigger:** When you want to specify the design for a new module  
**Command:** `/new-module-spec`

1. Create a new markdown file in `docs/superpowers/specs/` following the naming pattern:  
   `YYYY-MM-DD-XX-module-name-design.md`
   - Example: `2024-06-01-01-ledger-module-design.md`
2. Write the module's design/specification in the file.
3. Commit the new file with a message like:  
   `docs: specify ledger module`

### Update Existing Module Specifications
**Trigger:** When you want to clarify, update, or align the specifications of existing modules  
**Command:** `/update-module-specs`

1. Edit one or more existing markdown files in `docs/superpowers/specs/`.
2. Commit the changes with a message like:  
   `docs: clarify transaction specs`  
   or  
   `docs: align module spec suite`

### Add Module Spec Suite Plans
**Trigger:** When you want to document implementation plans for multiple modules or phases  
**Command:** `/add-spec-suite-plan`

1. Create one or more new markdown files in `docs/superpowers/plans/` using the naming pattern:  
   `YYYY-MM-DD-module-spec-suite-wave-<n>-<topic>.md`
   - Example: `2024-06-01-module-spec-suite-wave-1-ledger.md`
2. Optionally update `.gitignore` or other related files if necessary.
3. Commit all new/updated files with a message like:  
   `Add module spec suite implementation plans`

## Testing Patterns

- Test files use the pattern: `*.test.*`
  - Example: `transaction-manager.test.ts`
- Testing framework is **unknown**; check existing test files for structure.
- Place tests alongside the modules they test or in a dedicated test directory.

## Commands

| Command                | Purpose                                                    |
|------------------------|------------------------------------------------------------|
| /new-module-spec       | Start a new module design/specification document           |
| /update-module-specs   | Update or align existing module specification documents    |
| /add-spec-suite-plan   | Add planning documents for module spec suites or phases    |
```