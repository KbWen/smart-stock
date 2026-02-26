# Configuration Guide - Sniper V4.1

This document outlines the available configuration variables and how to tune the system's performance and scoring behavior.

## Environment Variables

Configuration is managed in `core/config.py`. You can override these defaults by setting environment variables in your OS or a `.env` file (if supported).

### Core Database & System

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `storage.db` | Path to the SQLite database file. |
| `DB_TIMEOUT` | `30.0` | Timeout in seconds for DB locks. |
| `CONCURRENCY_WORKERS` | `5` | Number of parallel threads for data synchronization. |
| `CACHE_DURATION` | `3600` | Expiry time for stock list and indicator cache (seconds). |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

### AI Model Strategy

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `model_sniper.pkl` | Path to the active AI model file. |
| `PRED_DAYS` | `20` | Look-ahead window for training labels (days). |
| `TARGET_GAIN` | `0.15` (15%) | Minimum gain required to classify as a "Win". |
| `STOP_LOSS` | `0.05` (5%) | Maximum loss allowed before improved as "Loss". |

### Rise Score Weights (V1 Logic)
>
> [!NOTE]
> These weights apply to the legacy scoring system. V4.1 uses `core/rise_score_v2.py` which may implement dynamic weighting.

| Variable | Default | Description |
|----------|---------|-------------|
| `WEIGHT_TREND` | `0.40` | Importance of Moving Average alignment. |
| `WEIGHT_MOMENTUM` | `0.30` | Importance of RSI/MACD/KD strength. |
| `WEIGHT_VOLATILITY` | `0.30` | Importance of BB Squeeze and Volume. |

## File Locations

* **Database**: `storage.db` (Root)
* **AI Models**: `models/*.pkl`
* **Logs**: Console output (Stdout).
* **Cache**: `stock_list_cache.json`, `market_history.json`.

## Tuning for Performance

* **High-Spec Machine**: Increase `CONCURRENCY_WORKERS` to 10 or 20 for faster sync.
* **Low-Spec / Raspberry Pi**: Decrease `CONCURRENCY_WORKERS` to 2 to prevent database locks.
