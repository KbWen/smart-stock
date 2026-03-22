# API Contract

Base URL: `http://localhost:8000` (dev) / your production host

All responses are JSON. Errors follow the shape:
```json
{ "status": "error", "message": "...", "path": "/api/..." }
```

---

## System

### `GET /`
Serve frontend `index.html`. Falls back through 4 candidate paths.

### `GET /api/health`
Returns system health and sync status.

**Response:**
```json
{
  "status": "ok",
  "db_connected": true,
  "last_sync": "2026-03-19T08:00:00",
  "model_version": "v4.20260319_0800"
}
```

### `GET /api/init`
Consolidated startup payload (market + top picks + models + sync status). Use this to avoid waterfall fetches.

**Response:**
```json
{
  "market": { ... },
  "top_picks": [ ... ],
  "models": [ ... ],
  "sync": { ... },
  "perf_ms": 120
}
```

---

## Market

### `GET /api/market_status`
Current market status (bull/bear ratio, index, model version) + 30-day history.

**Response:**
```json
{
  "status": "open",
  "bull_ratio": 0.62,
  "model_version": "v4.20260319_0800",
  "history": [ { "date": "2026-03-19", "bull_ratio": 0.62 } ]
}
```

---

## Stocks

### `GET /api/stocks`
List all TW stocks, optionally filtered by query.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | No | Filter by code or name (case-insensitive) |

**Response:** Array of `{ code, name }` objects (max 50 unfiltered, 20 filtered).

---

### `GET /api/search`
Global stock search.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | Yes | Search term (min 1 char) |

---

### `GET /api/top_picks`
Top-scoring stocks ranked by composite score or AI probability.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `sort` | `score` \| `ai` | `score` | Sort order |
| `version` | string | `latest` | Model version tag |

**Response:** Array of stock score objects (max 50).

---

### `GET /api/stock/{ticker}`
Legacy stock detail with indicators and analysis.

| Path Param | Validation |
|-----------|-----------|
| `ticker` | `^[A-Z0-9.\^\-]{1,15}$` |

---

### `GET /api/stock/{ticker}/verify`
Re-fetch and verify stock data from source.

| Query Param | Type | Default | Description |
|------------|------|---------|-------------|
| `refresh_db` | bool | `false` | Force DB refresh |

---

### `POST /api/smart_scan`
Run custom filter criteria against all stocks.

**Required header:** `X-Requested-With: XMLHttpRequest`

**Request body:** `["criteria1", "criteria2"]` (JSON array of strings)

**Rate limit:** None (POST, single operation)

---

### `GET /api/backtest`
Run time-machine simulation over past N days.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | `30` | Look-back window |
| `version` | string | `latest` | Model version tag |

**Rate limit:** 20 req/min per IP

**Response:**
```json
{
  "summary": {
    "total_signals": 12,
    "wins": 8,
    "win_rate": 0.667,
    "profit_factor": 2.1
  },
  "signals": [ ... ]
}
```

---

## V4 Sniper API

### `GET /api/v4/sniper/candidates`
Primary endpoint: returns ranked stock candidates with scores and AI probability.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | `50` | Max results |
| `sort` | `score` \| `ai` | `score` | Sort order |
| `version` | string | `latest` | Model version tag |

**Rate limit:** 60 req/min per IP

**Response:**
```json
{
  "candidates": [
    {
      "ticker": "2330",
      "name": "台積電",
      "total_score": 87.5,
      "ai_prob": 0.74,
      "last_price": 1000.0,
      "change_percent": 1.2
    }
  ],
  "model_version": "v4.20260319_0800",
  "cached": true
}
```

---

### `GET /api/v4/stock/{ticker}`
V4 stock detail: scores, indicators, signals.

| Path Param | Validation |
|-----------|-----------|
| `ticker` | `^[A-Z0-9.\^\-]{1,15}$` |

**Response:**
```json
{
  "ticker": "2330",
  "scores": { "total_score": 87.5, "trend_score": 70.0, ... },
  "signals": { "squeeze": false, "golden_cross": true, ... },
  "ai_prob": 0.74,
  "model_version": "v4.20260319_0800"
}
```

---

### `GET /api/v4/meta`
Bulk meta payload for multiple tickers.

| Param | Type | Required | Validation |
|-------|------|----------|-----------|
| `tickers` | string | Yes | Comma-separated. Max 100. Each: `^[A-Z0-9.\^\-]{1,15}$` |

**Rate limit:** 30 req/min per IP

**Response:**
```json
{
  "data": {
    "2330": {
      "total_score": 87.5,
      "trend_score": 70.0,
      "momentum_score": 60.0,
      "volatility_score": 50.0,
      "last_price": 1000.0,
      "change_percent": 1.2,
      "ai_prob": 0.74,
      "signals": {
        "squeeze": false,
        "golden_cross": true,
        "volume_spike": false,
        "rsi": 58.3,
        "macd_diff": 2.1,
        "rel_vol": 1.3
      },
      "updated_at": "2026-03-19T08:00:00",
      "model_version": "v4.20260319_0800",
      "name": "台積電"
    }
  }
}
```

---

## Models

### `GET /api/models`
List all trained model versions with metrics.

**Response:**
```json
[
  {
    "version": "v4.20260319_0800",
    "timestamp": "20260319_0800",
    "samples": 12000,
    "oos_metrics": { "accuracy": 0.821, "precision_strong": 0.76 },
    "backtest_30d": { "profit_factor": 2.1, "win_rate": 0.667 }
  }
]
```

---

## Sync

### `GET /api/sync/status`
Current sync job status.

### `POST /api/sync/trigger`
Trigger a background data sync (non-blocking).

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 403 | Forbidden (missing required header) |
| 404 | Not found |
| 422 | Validation error (invalid ticker, out-of-range param) |
| 429 | Rate limit exceeded |
| 500 | Internal server error (details logged server-side, not returned) |
