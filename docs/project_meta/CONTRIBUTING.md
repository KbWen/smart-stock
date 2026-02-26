# Contributing to Smart Stock Selector

Thank you for your interest in contributing to the Smart Stock Selector (Sniper V4.1)! This document outlines the process for contributing code and the standards we expect.

## Development Workflow

1. **Fork & Clone**: Fork the repository and clone it locally.
2. **Branching Strategy**:
    * `master`: The stable production branch.
    * `feature/<name>`: For new features (e.g., `feature/add-macd-filter`).
    * `bugfix/<name>`: For bug fixes (e.g., `bugfix/fix-api-crash`).
    * `hotfix/<name>`: For urgent production fixes.
3. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    cd frontend/v4 && npm install
    ```

4. **Make Changes**: Implement your feature or fix.
5. **Test**: Run relevant tests (see `TESTING.md`).
6. **Commit**: Use descriptive commit messages.
    * Format: `[Type]: Description`
    * Types: `Feat`, `Fix`, `Docs`, `Refactor`, `Perf`, `Test`.
    * Example: `Feat: Add support for MACD histogram in core/analysis.py`
7. **Push & PR**: Push to your fork and submit a Pull Request to `master`.

## Pull Request Process

* **Description**: clearly describe what the PR does. Link to any related issues.
* **Screenshots**: For UI changes, attach before/after screenshots.
* **Review**: Wait for a maintains to review your code. Address any feedback.
* **Merge**: Once approved, your code will be merged.

## Code Standards

Please refer to `CODE_STYLE.md` for detailed coding conventions.

## Reporting Issues

* Check existing issues before creating a new one.
* Use the Issue Templates provided (Bug Report / Feature Request).
* Include reproduction steps for bugs.
