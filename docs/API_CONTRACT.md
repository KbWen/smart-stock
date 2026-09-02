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
Current market status (breadth, model version, model health) + 30-day history.

**Response:**
```json
{
  "status": "open",
  "bull_ratio": 62.0,
  "breadth_level": "BULLISH",
  "model_version": "v4.20260319_0800",
  "model_health": { "status": "degraded", "version": "v4.20260319_0800", "message": "..." },
  "history": [ { "date": "2026-03-19", "bull_ratio": 62.0 } ]
}
```

`breadth_level` is a stable machine token — `BULLISH` (`bull_ratio > 60`), `BEARISH`
(`< 30`), `NEUTRAL`, or `UNKNOWN` when there is no data. It is **market breadth**: the share
of tracked tickers whose trend score exceeds 20, and nothing else — no volatility, index level,
drawdown or correlation. Display labels live in the frontend (`src/lib/breadth.ts`).

> Renamed from `risk_level` on 2026-09-02. The old field carried display strings
> (`"LOW RISK (BULL)"` / `"HIGH RISK (BEAR)"`) that claimed a risk assessment the computation does
> not perform. No compatibility alias is kept — see `docs/specs/docs-reality-alignment.md`.

---

### `GET /api/transparency`
What the system actually knows: data coverage, and the active model's evaluation.

**Response:** `data` carries history coverage and the date range. `model` carries `status`
(`ok` | `degraded` | `unavailable`), `reason` (a machine token for *why* — `zero_power`,
`below_baseline`, `contaminated_metrics`, `no_baseline`, `metrics_not_for_this_version`,
`not_trained`, `no_metrics`, `ok`), a user-facing zh-TW `message`, `version`, `trained_at`,
`samples`, `test_samples`, `train_class_distribution`, `test_class_distribution`,
`oos_metrics_scope`, `embargo`, and `oos_metrics`.

`oos_metrics` includes `lift_strong` / `lift_buy` — precision divided by that class's **test-split**
base rate. **1.0 means no better than guessing at the class prevalence**; `null` when the class is
absent from the test split. Read precision through the lift, never on its own.

`oos_metrics_scope: "split_model"` records that the metrics describe the 80/20-split ensemble, while
the artifact named by `version` is a full-data refit. An **absent** `embargo` key means the entry
predates 2026-09-02, when the train/test embargo was measured in pooled rows and separated the two
sides by 0 trading days — those metrics were never out-of-sample.

> Renamed on 2026-09-02: the single `class_distribution` field became
> `train_class_distribution` + `test_class_distribution`. No compatibility alias; see
> `docs/specs/oos-metric-attribution-and-lift.md`.

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
| `days` | int | `30` | Look-back window (1–365) |
| `version` | string | `latest` | Model version tag |
| `commission_rate` | float | `0.001425` | Per-side commission (0–0.05) |
| `tax_rate` | float | `0.003` | Sell-side transaction tax (0–0.05) |
| `slippage_rate` | float | `0.001` | Per-side slippage (0–0.05) |
| `target_gain` | float | `0.15` | Stop-profit target (0.01–0.50) |
| `stop_loss` | float | `0.05` | Stop-loss threshold (0.01–0.50) |
| `holding_days` | int | `20` | Max holding window (1–90) |

**Rate limit:** 20 req/min per IP

**Response:** `summary` includes `avg_return`, `avg_net_return` (after friction),
`win_rate`, `net_win_rate`, `sniper_hit_rate`, `sniper_hits`, `sniper_stops`,
`profit_factor` and `net_profit_factor` (**`null` when there are no losing trades**),
Top-level alongside `summary`: `simulated_date` (the run's single entry date — every pick is
anchored to it), `excluded_no_data_at_as_of`, `excluded_no_price_rows` and
`excluded_unscorable` (candidates dropped, so a thin cross-section is visible rather than inferred;
`excluded_unscorable` counts stocks the model refused to score because a feature could not be
computed from that window — booking them under the AI threshold would have called a refusal "the
model said 0%"), and `model_temporal_scope`
(`in_sample` | `as_of_model` | `unknown`). **`in_sample` means the model scoring the run was trained
over the window it scored** — the numbers measure recall over data it has already seen, not
predictive skill. It fails toward `in_sample` when the model's training date cannot be determined.

`summary.holding_days` and `summary.exit_date_actual` are **`null` unless every pick agrees** — they
used to be read off `top_picks[0]` and presented as the whole run's.

`sharpe_ratio` (unannualized single-period mean ÷ stddev of net returns — not a
conventional annualized Sharpe; **`null` when that stddev is undefined or exactly zero**,
i.e. a single pick, or every settled trade landing on the same barrier),
`avg_max_drawdown`, `worst_drawdown`; plus
`top_picks[]` and `history[]`.

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

`ai_prob` is **nullable** on every candidate. It is `null` when no probability exists for that
stock — no model, or a feature the model needs that could not be computed from the loaded window
(shorter than `MIN_FEATURE_ROWS`, 250 rows). It is never a fake `0.0`, which would be
indistinguishable from a genuinely low probability. Unlike the detail endpoint, the candidate list
carries **no** `ai_unavailable_reason`: it reads a stored scalar from the `scores` table, which has
nowhere to record one.


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
  "name": "台積電",
  "price": 1000.0,
  "updated_at": "2026-03-19T08:00:00",
  "rise_score_breakdown": {
    "total": 87.5,
    "trend": 70.0,
    "momentum": 60.0,
    "volatility": 50.0
  },
  "ai_probability": 74.0,
  "ai_unavailable_reason": null,
  "analyst_summary": "Strong Uptrend: Price is consistently above SMA20 & SMA60.",
  "signals": {
    "squeeze": false,
    "golden_cross": true,
    "volume_spike": false
  }
}
```

`ai_probability` is `null` whenever no prediction was made — never a fake `0.0`, which would be
indistinguishable from a genuinely low probability.

`ai_unavailable_reason` says **why**, when the cause can be attributed to this stock's data:

```
"insufficient_history" | null
```

`insufficient_history` means the price history is shorter than the longest indicator window the
feature set needs (`MIN_FEATURE_ROWS`, 250 rows = the 240-period SMA plus its 10-row slope), so at
least one model input could not be computed. The model is **not** given a substitute value; it is
not consulted at all. The technical scores are unaffected and still returned.

The reason is `null` when `ai_probability` is present, when the cause is the model rather than the
data (no model trained, load failure — `model_health` reports those and this field must not
relabel them as a data problem), and on the cached-DB branch of `/api/v4/stock/{ticker}`, which
deliberately does not load price history and therefore cannot attribute the cause.


---

### `GET /api/v4/stock/{ticker}/sparkline`
Lightweight close-only history for sparklines (last 30 days). No indicator calculations. Cached for 60 seconds.

| Path Param | Validation |
|-----------|-----------|
| `ticker` | `^[A-Z0-9.\^\-]{1,15}$` |

**Response:**
```json
[
  {
    "date": "2026-05-15",
    "close": 1000.0
  }
]
```

---

### `GET /api/v4/stock/{ticker}/history`
90-day OHLCV and signal status history for detail page charting. Cached for 60 seconds.

| Path Param | Validation |
|-----------|-----------|
| `ticker` | `^[A-Z0-9.\^\-]{1,15}$` |

**Response:**
```json
[
  {
    "date": "2026-05-15",
    "close": 1000.0,
    "is_squeeze": false,
    "golden_cross": true,
    "volume_spike": false
  }
]
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

### `POST /api/sync`
Trigger a background data sync (non-blocking). Rate limit: 5 req/min per IP.

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
