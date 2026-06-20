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
* `save_to_db(ticker, df)`: Upserts OHLCV history (`INSERT OR REPLACE`); returns rows written.
* `report_history_coverage(...)`: Reports how many universe tickers have enough history for predict/train.

### `core/bulk_history.py` (New in Directly-Usable v1 #4)

**Purpose**: Accelerated full-universe history backfill via authoritative TWSE/TPEX per-day bulk endpoints (one call returns all stocks' OHLCV for a trading day). Raw (unadjusted) prices; pure, network-injectable parsers.

* `parse_twse_mi_index(payload, date)` / `parse_tpex_daily(csv, date)`: Extract per-stock OHLCV (universe-filtered).
* `backfill_bulk(days, ...)`: Iterate trading days, assemble per-ticker, persist via `save_to_db`. The yfinance per-stock path remains the fallback.

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

### `backend/services/v4_stock_detail_service.py`

**Purpose**: Per-ticker detail computation and caching.

* `get_stock_history(ticker, days=90)`: Returns a list of `{date, close, is_squeeze, golden_cross, volume_spike}` dicts for the past N days. Runs `compute_v4_indicators` + `calculate_rise_score_v2` on the raw df (no DB cache path) and stores results with a 60s TTL cache key `history:{ticker}`.
* `_write_cache(key, value, ttl=None)`: Extended with optional `ttl` parameter so individual endpoints can override the default 300s TTL.

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

## Scripts (`scripts/`)

User-facing one-command tools (Directly-Usable v1).

* `seed_demo.py`: Seed the bundled offline demo (`data/demo/demo_prices.csv`) + compute technical scores — fully offline, idempotent. Used by quickstart and the Docker entrypoint.
* `gen_demo_fixture.py`: Maintainer tool — regenerate the demo fixture with real auto-adjusted prices for ~15 large-cap TWSE tickers.
* `fast_backfill.py [--days N]`: Fast full-universe history backfill via the `core/bulk_history.py` bulk endpoints.
* `setup_real_ai.py [--days N]`: Opt-in real-AI first-run — backfill → coverage-gate → train → recalc, so AI probabilities populate (N/A stays the default; skips training on too little data, which `model_health` discloses).
