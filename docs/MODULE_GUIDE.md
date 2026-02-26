# Module Guide

This document provides a detailed breakdown of the key Python modules in the system.

## Core Modules (`core/`)

### `core/data.py`

**Purpose**: Handles data acquisition and database interactions.

* `ensure_db_initialized()`: Performs thread-safe, lazy schema/migration bootstrap once per `DB_PATH` before DB usage.
* `get_db_connection()`: Returns a SQLite connection after confirming initialization has run for the active DB path.
* `fetch_stock_data(ticker, days)`: Downloads OHLCV data from yfinance or twstock.
* `load_from_db(ticker)`: Retrieves DataFrame from SQLite.
* `save_score_to_db(...)`: Persists V2 scores and AI probabilities.

### `core/analysis.py`

**Purpose**: Core calculation functions for indicators and report generation.

* `compute_all_indicators(df)`: Calculates base indicators (SMA, RSI, MACD, BB).
* `generate_analysis_report(...)`: Generates human-readable market context from indicator states.

### `core/indicators_v2.py` (New in V4.1)

**Purpose**: The optimized V2 indicator library.

* `compute_v4_indicators(df)`: High-performance calculation of Trend, Momentum, and Volatility factors.

### `core/ai/` (Package)

**Purpose**: The AI brain and data preparation pipeline, modularized for specialized training and prediction.

* `core/ai/common.py`: Universal features and threshold constants.
* `core/ai/trainer.py`: Model training logic (GB + RF + MLP Ensemble).
* `core/ai/predictor.py`: Probabilistic inference with model version caching.

### `core/logger.py`

**Purpose**: Centralized observability.

* `setup_logger(name)`: Configures rotating file logs (10MB) and console output.
* `AlertHandler`: Triggers `send_alert()` notifications on `ERROR` or `CRITICAL` events.

## Backend Modules (`backend/`)

### `backend/main.py`

**Purpose**: The FastAPI application entry point.

* `GET /api/v4/sniper/candidates`: Returns top-ranked stocks using persistent scores.
* `GET /api/backtest`: Runs the simulation engine.

### `backend/backtest.py`

**Purpose**: Historical simulation logic with True Sniper Exit constraints.

* `run_time_machine(days_ago, version)`: Reconstructs the market state from exact trading days ago and evaluates strategy performance. Includes immediate take-profit/stop-loss early exit mechanism to correctly mirror trade discipline.

### `backend/recalculate.py`

**Purpose**: Batch processing script.

* Iterates through all 1000+ stocks in the DB.
* Computes V2 indicators and scores.
* Updates the `stock_scores` table.
