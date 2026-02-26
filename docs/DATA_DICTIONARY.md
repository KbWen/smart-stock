# Data Dictionary & API Contract

## 1. Database Schema (`storage.db`)

### Table: `stock_history` (Daily OHLCV)

Stores raw daily price data fetched from Yahoo Finance (TW/TWO).

| Column | Type | Description |
| :--- | :--- | :--- |
| `ticker` | TEXT (PK) | Stock symbol (e.g., `2330.TW`) |
| `date` | DATE (PK) | Trading date (YYYY-MM-DD) |
| `open` | REAL | Opening price |
| `high` | REAL | Highest price |
| `low` | REAL | Lowest price |
| `close` | REAL | Closing price (Adjusted Close) |
| `volume` | INTEGER | Trading volume |

### Table: `stock_scores` (Analysis Results)

Stores the latest analysis scores, AI predictions, and strategy signals.

| Column | Type | Description |
| :--- | :--- | :--- |
| `ticker` | TEXT (PK) | Stock symbol |
| `total_score` | REAL | Composite Rise Score (0-100) |
| `trend_score` | REAL | Trend component (max 40) |
| `momentum_score` | REAL | Momentum component (max 30) |
| `volatility_score` | REAL | Volatility/Setup component (max 30) |
| `last_price` | REAL | Latest closing price |
| `change_percent` | REAL | Daily percentage change |
| `ai_probability` | REAL | Ensemble AI Win Probability (0.0 - 1.0) |
| `model_version` | TEXT (PK) | Version of the model used (Part of Composite PK) |
| `updated_at` | TIMESTAMP | Last calculation timestamp |

### Table: `stock_indicators` (Cached Features)

Stores the latest calculated technical indicators to speed up scanning.

| Column | Type | Description |
| :--- | :--- | :--- |
| `ticker` | TEXT (PK) | Stock symbol |
| `rsi` | REAL | Relative Strength Index (14) |
| `macd` | REAL | MACD Line (12, 26) |
| `macd_signal` | REAL | MACD Signal Line (9) |
| `ema_20` | REAL | 20-day Exponential Moving Average |
| `ema_50` | REAL | 50-day Exponential Moving Average |
| `sma_20` | REAL | 20-day Simple Moving Average |
| `sma_60` | REAL | 60-day Simple Moving Average |
| `k_val` | REAL | Stochastic K (9, 3) |
| `d_val` | REAL | Stochastic D (9, 3) |
| `atr` | REAL | Average True Range (14) |
| `bb_width` | REAL | Bollinger Band Width |
| `model_version` | TEXT | Version of the model used |
| `updated_at` | TIMESTAMP | Last calculation timestamp |

---

## 2. Technical Indicators & Rise Score

### Indicators

- **RSI**: 14-period Relative Strength Index. >75 Overbought, <25 Oversold.
- **MACD**: EMA(12) - EMA(26). Bullish when MACD > Signal.
- **KD**: Stochastic Oscillator (9,3,3). Golden Cross when K > D.
- **Bollinger Bands**: 20-period SMA +/- 2 STD.
  - `bb_width`: (Upper - Lower) / SMA. < 0.10 indicates Squeeze.
  - `bb_percent`: Position within bands (0=Lower, 1=Upper).
- **ATR**: 14-period Average True Range. Volatility measure.
- **Vol MA**: 20-period Volume Moving Average.

### Rise Score (0-100)

A heuristic score combining three factors:

1. **Trend (40pts)**
    - Price > SMA20 > SMA60 (+40)
    - Price > SMA20 only (+20)
    - SMA60 Sloping Up (+10)
2. **Momentum (30pts)**
    - RSI 55-75 (+15), RSI > 80 (-10)
    - MACD Bullish (+10)
    - KD Golden Cross (+15/+5)
3. **Volatility (30pts)**
    - Volume > 1.5x MA20 (+15)
    - BB Squeeze (<0.10) (+10)
    - BB Support Bounce (+10)

---

## 3. API Metrics & Contracts

### Enpoints

#### `GET /api/top_picks?sort=score|ai`

Returns sorted list of stocks.

**Response JSON:**

```json
[
  {
    "ticker": "2330.TW",
    "name": "台積電",
    "total_score": 85.5,
    "ai_probability": 0.72,
    "last_price": 580.0,
    "change_percent": 1.5,
    "last_sync": "2023-10-27 13:30:00"
  }
]
```

#### `GET /api/stock/{ticker}`

Returns detailed analysis.

**Response JSON:**

```json
{
  "ticker": "2330.TW",
  "name": "台積電",
  "price": 580.0,
  "change": 1.5,
  "score": {
      "total_score": 85,
      "trend_score": 40,
      "momentum_score": 30,
      "analysis": { "trend": "...", "setup": "..." }
  },
  "ai_probability": 0.72,
  "indicators": {
      "rsi": 65.4,
      "macd": 2.1,
      "k": 78,
      "d": 72
  }
}
```

#### `POST /api/smart_scan`

Body: `["high_ai", "vol_surge"]`

**Response JSON:**

```json
[
  {
    "ticker": "2330.TW",
    "name": "台積電",
    "ai_probability": 0.75,
    "matches": ["high_ai"]
  }
]
```
