# Testing Guide

## Overview

We use `pytest` for unit and integration testing. All new features should be accompanied by tests.

## Running Tests

To run the full test suite:

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_data_layer.py

# Run with verbose output
pytest -v
```

## Test Structure

* `tests/`: Root directory for all tests.
* `tests/conftest.py`: Shared fixtures (e.g., mock DB, sample DataFrames).
* `tests/test_core/`: Tests for `core/` modules (logic, math).
* `tests/test_backend/`: Tests for FastAPI endpoints.

## Writing Tests

### 1. Naming Convention

* Files: `test_<module>.py`
* Functions: `test_<function_name>_<scenario>`

### 2. Mocking

Avoid hitting external APIs (Yahoo Finance, TWSE) in tests. Use `unittest.mock` or `pytest-mock` to simulate data.

```python
from unittest.mock import patch

def test_fetch_stock_data(mocker):
    mock_yfinance = mocker.patch('yfinance.Ticker')
    # ... setup mock return values ...
    df = fetch_stock_data('2330')
    assert not df.empty
```

### 3. Database Tests

For tests involving the database, use a temporary SQLite file or an in-memory database to prevent corrupting the production `storage.db`.

## Continuous Integration (CI)

 We use **GitHub Actions** to automate testing. The [Pytest CI](.github/workflows/pytest.yml) workflow triggers on every Push and Pull Request to the `master` branch.

* **Status**: Active.
* **Command**: `python -m pytest tests/`
