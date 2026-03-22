# Environment Setup Guide

This guide explains how to configure Smart Stock Selector for local development and production.

## Quick Start

```bash
cp .env.example .env
# Edit .env — uncomment and set any values you want to override
```

The app reads all configuration from environment variables at startup. Every variable has a sane default, so `.env` is optional for local development.

## Variable Reference

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `<repo>/storage.db` | Absolute path to SQLite database |
| `DB_TIMEOUT` | `30.0` | SQLite busy-wait timeout (seconds) |

### AI Model

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `<repo>/model_sniper.pkl` | Active model file path |
| `PRED_DAYS` | `20` | Look-ahead window for labels (trading days) |
| `TARGET_GAIN` | `0.15` | Profit target (+15%) |
| `STOP_LOSS` | `0.05` | Stop-loss threshold (-5%) |
| `BUY_TARGET` | `0.10` | Buy-signal threshold (+10%) |

### Backtest / Strategy

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKTEST_AI_THRESHOLD` | `0.35` | Min AI probability to count as a buy signal |
| `MIN_TRAIN_ROWS` | `260` | Min OHLCV rows required for training |
| `MIN_PREDICT_ROWS` | `120` | Min OHLCV rows required for prediction |

### Backend / System

| Variable | Default | Description |
|----------|---------|-------------|
| `CONCURRENCY_WORKERS` | `5` | Concurrent workers for scoring pipeline |
| `TRAINING_WORKERS` | `CPU_COUNT - 1` | Workers for model training |
| `USE_GPU` | `auto` | GPU acceleration: `true` / `false` / `auto` |
| `CACHE_DURATION` | `3600` | API cache TTL (seconds) |
| `LOG_LEVEL` | `INFO` | Log verbosity: `DEBUG` / `INFO` / `WARNING` / `ERROR` |

### CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | localhost:5173/5174/3000 | Comma-separated list of allowed frontend origins |

**Production**: always set `CORS_ORIGINS` explicitly:
```
CORS_ORIGINS=https://your-frontend.example.com
```

## Security Notes

- **Never commit `.env`** — it is in `.gitignore`
- **`MODEL_PATH`** should point to a directory with restricted write access in production
- **`CORS_ORIGINS`** wildcard (`*`) is intentionally unsupported — set explicit origins
- Model files (`.pkl`) are integrity-checked via SHA256 sidecar files (`.pkl.sha256`) — do not modify them manually

## Loading `.env` in Development

The app does **not** auto-load `.env` files. Use one of these approaches:

**Option A — export before running:**
```bash
export $(cat .env | grep -v '^#' | xargs)
python backend/main.py
```

**Option B — use `python-dotenv` (install separately):**
```bash
pip install python-dotenv
```
Then add to the top of `backend/main.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

**Option C — shell profile:**
Add `export VAR=value` lines to `~/.bashrc` or `~/.zshrc` for persistent local config.

## Production Checklist

- [ ] `DB_PATH` points to a persistent, backed-up location
- [ ] `MODEL_PATH` points to a directory with restricted write access
- [ ] `CORS_ORIGINS` set to actual frontend domain(s) — no localhost
- [ ] `LOG_LEVEL=WARNING` or `ERROR` (reduce noise)
- [ ] `.env` file has `chmod 600` permissions
- [ ] `.env` is excluded from any Docker image or deployment artifact
