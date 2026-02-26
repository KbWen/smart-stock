# System Architecture - Sniper V4.2

## Overview

Smart Stock Selector (Sniper V4.1) is a specialized decision support system for the Taiwan Stock Market (TWSE). It combines technical analysis, machine learning (Ensemble V4), and a modern React-based frontend to identify high-probability "Sniper" setups.

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
        Data --> DB
    end
    
    subgraph "Governance (Constitution Layer)"
        Rules[.agent/rules/]
        Superpowers[.agent/superpowers/]
        Rules --> AI
        Superpowers --> User
    end

    subgraph "External"
        Data --> TWSE[TWSE / TPEX]
        Data --> Yahoo[Yahoo Finance API]
    end
```

## Directory Structure & Responsibilities

### `backend/` - The API Layer

* **Role**: Serves data to the frontend, handles long-running tasks (backtests), and manages process lifecycles.
* **Runtime State Safety**: Sync progress state is protected by a lock in `backend/main.py` and exposed via snapshot reads (`/api/sync/status`) to avoid concurrent mutation leaks.
* **Key Files**:
  * `main.py`: FastAPI entry point. Defines routes (`/api/v4/...`).
  * `backtest.py`: The "Time Machine" simulation logic.
  * `recalculate.py`: Batch processing script to update scores and indicators.

### `core/` - The Intelligence Layer

* **Role**: Contains all business logic, math, and AI models. This layer is framework-agnostic (could be used by CLI or Web).
* **Key Files**:
  * `data.py`: Data fetching (yfinance/twstock) and database I/O.
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
    * `daily_run.bat` triggers `backend/main.py --sync`.
    * Market data (OHLCV) is fetched for 1000+ tickers and stored in `storage.db`.
2. **Processing**:
    * `recalculate.py` runs immediately after sync.
    * It computes V2 Indicators and V2 Rise Scores for all stocks.
    * Results are **persisted** to the `stock_scores` table to ensure <100ms API response.
3. **Consumption**:
    * User opens Dashboard.
    * `GET /api/v4/sniper/candidates` queries `stock_scores` (filtered by top rank).
    * Frontend renders the list.
4. **AI Prediction**:
    * The system loads the latest `model_sniper.pkl`.
    * It generates a probability ($P_{win}$) for each candidate based on technical features.

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
- Server-side cache keys include `limit`, `sort`, and `version` dimensions to avoid cross-query cache pollution.
