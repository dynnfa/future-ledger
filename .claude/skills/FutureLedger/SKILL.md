```markdown
# FutureLedger Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill introduces the core development patterns and conventions used in the FutureLedger Python codebase. It covers file organization, import/export styles, commit message standards, and testing patterns, providing practical examples and command suggestions to streamline your workflow.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `transaction_manager.py`, `user_profile.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import calculate_hash
    from ..models import LedgerEntry
    ```

### Export Style
- Use **named exports** by explicitly listing public objects in `__all__`.
  - Example:
    ```python
    __all__ = ['Ledger', 'Transaction']
    ```

### Commit Messages
- Follow **conventional commit** format.
- Use the `feat` prefix for new features.
  - Example: `feat: add transaction validation logic`
- Keep commit messages concise (average ~40 characters).

## Workflows

### Adding a New Feature
**Trigger:** When implementing a new capability or module  
**Command:** `/add-feature`

1. Create a new Python file using snake_case.
2. Implement the feature using relative imports for dependencies.
3. Add named exports in the module's `__all__` list.
4. Write or update corresponding test files (see Testing Patterns).
5. Commit changes using the conventional format:
    ```
    feat: <short description of the feature>
    ```

### Refactoring Code
**Trigger:** When improving code structure or readability  
**Command:** `/refactor`

1. Update file and function names to follow snake_case if needed.
2. Adjust import statements to use relative paths.
3. Ensure public interfaces are listed in `__all__`.
4. Run all relevant tests to confirm no regressions.
5. Commit with a clear message:
    ```
    feat: refactor <module/component> for clarity
    ```

### Writing Tests
**Trigger:** When adding or updating functionality  
**Command:** `/write-test`

1. Create or update test files using the `*.test.*` pattern.
    - Example: `ledger.test.py`
2. Write test functions for each public method or class.
3. Use assertions to validate expected behavior.
4. Run tests using your preferred Python test runner.
5. Commit with a message:
    ```
    feat: add tests for <module/component>
    ```

## Testing Patterns

- Test files follow the `*.test.*` naming convention.
  - Example: `transaction_manager.test.py`
- Each test file targets a specific module or component.
- Testing framework is unspecified; use standard Python testing tools (e.g., `unittest`, `pytest`).
- Example test structure:
    ```python
    def test_calculate_hash():
        result = calculate_hash('input')
        assert result == 'expected_hash'
    ```

## Commands
| Command        | Purpose                                    |
|----------------|--------------------------------------------|
| /add-feature   | Start workflow for adding a new feature    |
| /refactor      | Begin code refactoring process             |
| /write-test    | Guide for writing or updating tests        |
```
