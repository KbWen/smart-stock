# System Architecture - Sniper V4.2

## Overview

Smart Stock Selector (Sniper V4.2) is a specialized decision support system for the Taiwan Stock Market, integrating both TWSE (上市) and TPEX/OTC (上櫃) stock universes. It combines advanced technical analysis, a robust machine learning ensemble (GB + RF + MLP), and a modern React-based frontend featuring optimized scrolling and glassmorphism styling.

## High-Level Architecture

The system is organized into four main layers, including a newly introduced **Constitution Layer** for AI-human alignment.

```mermaid
graph TD
    User[User / Trader] --> Frontend[Frontend (React/Vite)]
    Frontend --> API[Backend API (FastAPI)]
    
    subgraph "Backend Core (Python)"
        API --> Engine[Factor Engine (core/analysis.py)]
        API --> AI[AI Engine (core/ai/)]
        API --> DB[(SQLite DB)]
        API --> Log[Logger (core/logger.py)]
        
        Engine --> DB
        AI --> DB
        
        Sync[Daily Sync (scripts)] --> Data[Data Layer (core/data.py)]
        FastSync[scripts/fast_backfill.py] --> Bulk[core/bulk_history.py]
        Data --> DB
        Bulk --> DB
    end
    
    subgraph "Governance (Constitution Layer)"
        Rules[.agent/rules/]
        Superpowers[.agent/superpowers/]
        Rules --> AI
        Superpowers --> User
    end

    subgraph "External"
        Data --> Yahoo[Yahoo Finance API per-stock]
        Data --> TWSE[TWSE / TPEX universe list]
        Bulk --> TWSEBulk[TWSE/TPEX per-day bulk]
    end
```

## Directory Structure & Responsibilities

### `backend/` - The API Layer

* **Role**: Serves data to the frontend, handles long-running tasks (backtests), and manages process lifecycles.
* **Runtime State Safety**: Sync progress state is protected by a lock in `backend/routes/sync.py` and exposed via snapshot reads (`/api/sync/status`) to avoid concurrent mutation leaks.
* **Key Files**:
  * `main.py`: FastAPI entry point. Defines routes (`/api/v4/...`).
  * `backtest.py`: The "Time Machine" simulation logic.
  * `recalculate.py`: Batch processing script to update scores and indicators.

### `core/` - The Intelligence Layer

* **Role**: Contains all business logic, math, and AI models. This layer is framework-agnostic (could be used by CLI or Web).
* **Key Files**:
  * `data.py`: Per-stock data fetching (yfinance/twstock) and database I/O.
  * `bulk_history.py`: Accelerated full-universe history via TWSE/TPEX per-day bulk endpoints (raw prices); used by `scripts/fast_backfill.py`.
  * `analysis.py`: Technical analysis (SMA, RSI, MACD, Bollinger Bands) and Rise Score logic.
  * `ai/`: Feature engineering, model training, and prediction package.
  * `logger.py`: Centralized logging with file rotation and alert triggers.
  * `indicators_v2.py`: The V4.1 optimized indicator library.
  * `rise_score_v2.py`: The V4.1 scoring rules engine.

### `frontend/v4/` - The Presentation Layer

* **Role**: A modern, responsive SPA (Single Page Application) built with React, TypeScript, and Tailwind CSS.
* **Key Design**:
  * **Glassmorphism**: Dark mode with translucent panels.
  * **Component-Based**: Reusable widgets like `SniperCard`, `StockList`.
  * **State Management**: React Hooks (`useState`, `useEffect`) for localized state.

## Data Flow

1. **Ingestion (Daily)**:
    * `daily_run.bat` (or Unix `daily_run.sh`) triggers `backend/main.py --sync`.
    * Market data (OHLCV) is fetched for both TWSE (.TW) and TPEX/OTC (.TWO) stocks using a cached suffix mapper and defensive suffix-alternating retry logic, then stored in `storage.db`.
    * **Accelerated alternative**: `scripts/fast_backfill.py` (via `core/bulk_history.py`) backfills the whole universe from official TWSE/TPEX per-day bulk endpoints — far fewer calls than the per-stock yfinance crawl. Those prices are **raw** (not dividend-adjusted), so keep a DB to one source.
2. **Processing**:
    * `recalculate.py` runs immediately after sync.
    * It computes V2 Indicators and V2 Rise Scores for all stocks.
    * Results are **persisted** to the `stock_scores` table to ensure <100ms API response.
3. **Consumption**:
    * User opens Dashboard.
    * `GET /api/v4/sniper/candidates` queries `stock_scores` (filtered by top rank).
    * Frontend renders the list.
4. **AI Prediction & Ensemble**:
    * The system loads the latest `model_sniper.pkl` (containing GB, RF, and MLP models).
    * Class probabilities are resolved dynamically based on `classes_` array mapping.
    * MLP Classifier is trained on a resampled training set via deterministic random oversampling (`np.random.default_rng(42)`) to handle class imbalance.
    * Generates an ensemble probability ($P_{win}$) for each candidate based on technical features.

## Strategy Parameters (Single Source of Truth)

> [!IMPORTANT]
> All strategy parameters **MUST** be defined in `core/config.py` and re-exported via `core/ai/common.py`.
> Training (`core/ai/trainer.py`) and Backtest (`backend/backtest.py`) import from `common.py`.
> **DO NOT** hardcode magic numbers for targets, stops, thresholds, or data lengths in downstream files.

| Parameter | Config Key | Default | Used By |
|-----------|-----------|---------|---------|
| Profit Target | `TARGET_GAIN` | +15% | trainer, backtest |
| Stop Loss | `STOP_LOSS` | -5% | trainer, backtest |
| Buy Target (Class 1) | `BUY_TARGET` | +10% | trainer |
| Look-ahead Window | `PRED_DAYS` | 20 days | trainer, backtest |
| Backtest AI Filter | `BACKTEST_AI_THRESHOLD` | 0.35 | backtest |
| Min Training Rows | `MIN_TRAIN_ROWS` | 260 | trainer |
| Min Prediction Rows | `MIN_PREDICT_ROWS` | 120 | trainer, predictor |

**Workflow**: When modifying strategy → change `config.py` → retrain model → run backtest to validate.

> **Data Integrity Note**: To understand how the system prevents **Look-Ahead Bias** (偷看未來資料) during feature engineering, training, and backtesting, please refer to [DATA_INTEGRITY.md](./DATA_INTEGRITY.md).

## Design Patterns

* **Repository Pattern**: `core/data.py` abstracts all DB interactions.
* **Strategy Pattern**: `core/ai/` supports multiple model versions and legacy/ensemble switching.
* **Observer Pattern**: `core/logger.py` uses custom handlers to "observe" high-level errors and trigger alerts.
* **Lazy Loading**: The frontend initializes non-critical data asynchronously.


## API Performance Notes

- **Candidates API (`/api/v4/sniper/candidates`)** returns summary fields optimized for ranking lists and excludes per-ticker signal expansion to avoid N+1 work.
- **Detail API (`/api/v4/stock/{ticker}`)** computes richer analysis only when the user drills into a single ticker.
- **History API (`/api/v4/stock/{ticker}/history`)** returns 90-day OHLC + signal array for charting. Uses an independent 60s in-memory cache (key: `history:{ticker}`) separate from the main 300s detail cache. Route registered before the `{ticker}` wildcard to prevent path shadowing.
- Server-side cache keys include `limit`, `sort`, and `version` dimensions to avoid cross-query cache pollution.

## Frontend Performance Notes

- **SVG Sparkline Area Charts**: Replaced DOM-heavy, ResizeObserver-listener-bound Recharts widgets in CandidateRow list cells with lightweight, raw SVG inline charts. Scale values are mapped mathematically inside a `viewBox="0 0 100 24"`. 
- **Taiwan-Harmonious Color Gradients**: Gradients transition from red/green to transparent based on change percentage, and scrolling maintains 60 FPS under virtualization by avoiding CSS layout reflow.
- **Glassmorphism Transitions**: Micro-animations and hover transitions (hover scale zoom, amber gold/emerald green borders, left-side indicator borders) use smooth, hardware-accelerated CSS transitions (`transition-all duration-200 ease-out`).
