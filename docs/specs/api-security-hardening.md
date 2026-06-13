---
status: frozen
created: 2026-03-19
branch: claude/fervent-poincare
classification: quick-win
---

# Spec: API Security Hardening

## Problem

The API layer lacked several baseline defenses:

1. Path traversal via unchecked `version` parameter in `predict_prob()` and CLI commands.
2. Internal error messages (`str(exc)`) leaked in HTTP 500 responses.
3. `POST /api/smart_scan` had no CSRF defense (no cookie auth mitigates full token requirement, but header check blocks naive browser form submissions).
4. High-cost endpoints (`/api/backtest`, `/api/v4/sniper/candidates`, `/api/v4/meta`) had no rate limiting.
5. `{ticker}` path parameters were not validated, allowing arbitrary strings to reach service layer.
6. Bare `except:` clauses silently swallowed all exceptions including `KeyboardInterrupt`/`SystemExit`.
7. Health endpoint leaked DB connection error details via `str(e)` in the response body.
8. Model files loaded without integrity verification — a tampered `.pkl` could cause arbitrary code execution via pickle deserialization.

## Acceptance Criteria

| # | Criterion | Status |
|---|---|---|
| AC1 | `version` param in `predict_prob()` validated with `VERSION_RE` before constructing file path | ✅ |
| AC2 | CLI `cmd_activate()` and `cmd_delete()` validate version string before `.split('.')` | ✅ |
| AC3 | All HTTP 500 responses return `"Internal server error"` (no `str(exc)` leakage) | ✅ |
| AC4 | `POST /api/smart_scan` requires `X-Requested-With: XMLHttpRequest` header | ✅ |
| AC5 | `GET /api/backtest` rate-limited to 20/minute per IP | ✅ |
| AC6 | `GET /api/v4/sniper/candidates` rate-limited to 60/minute per IP | ✅ |
| AC7 | `GET /api/v4/meta` rate-limited to 30/minute per IP | ✅ |
| AC8 | All `{ticker}` path params validated against `r'^[A-Z0-9.^-]{1,15}$'` before service layer | ✅ |
| AC9 | `days` param on `/api/backtest` bounded `ge=1, le=365`; `limit` on candidates bounded `ge=1, le=500` | ✅ |
| AC10 | All bare `except:` replaced with `except Exception:` across changed files | ✅ |
| AC11 | Health endpoint returns `"disconnected"` (not `str(e)`) on DB failure | ✅ |
| AC12 | `_verify_checksum()` validates SHA256 sidecar before `joblib.load()`; legacy models (no sidecar) pass through | ✅ |

## Design

### Rate Limiting (`backend/limiter.py`)

Shared `Limiter` instance extracted to `backend/limiter.py` to avoid the circular import that would arise if defined in `main.py` and imported by `routes/stock.py`.

```
backend/limiter.py  ←  backend/main.py (app.state.limiter, exception handler)
                    ←  backend/routes/stock.py (@limiter.limit decorators)
```

### Version String Validation

`VERSION_RE = re.compile(r'^v\d+\.\d{8}_\d{4}$')` defined in `core/ai/common.py` and used by:
- `core/ai/predictor.py` — `predict_prob(version=...)` path construction
- `backend/manage_models.py` — `cmd_activate()`, `cmd_delete()` CLI commands

The regex is anchored (`^...$`) and only allows the canonical format (`v4.20260319_0800`). Any deviation returns `None` / prints error before the `.split('.')[-1]` path component is used.

### SHA256 Integrity Check

`_verify_checksum(path)` in `core/ai/predictor.py`:
- Reads `<model>.pkl.sha256` sidecar.
- If sidecar absent → allow load (legacy model support).
- If sidecar present but hash mismatches → refuse load, log warning.
- `_read_sidecar(path)` centralises sidecar I/O with explicit `encoding='utf-8'`.

### Ticker Regex

`_TICKER_RE = re.compile(r'^[A-Z0-9.^-]{1,15}$')` covers:
- TW market: `2330.TW`
- US market: `AAPL`
- Indices: `^TWII`
- Crypto: `BTC-USD`

Applied to: `GET /api/stock/{ticker}`, `GET /api/stock/{ticker}/verify`, `GET /api/v4/stock/{ticker}`, and all tickers in `GET /api/v4/meta`.

### Shared Utilities (`core/ai/common.py`)

Three new exports to eliminate duplication:
- `MAX_PREDICTION_CACHE_SIZE = 3` — LRU cap for in-process model cache
- `validate_version_string(version: str) -> bool` — wraps `VERSION_RE`
- `profit_factor_sort_key(h: dict) -> float` — `None`-safe sort key for model rotation

## Known Limitations / Follow-up

- Legacy endpoints (`/api/stocks`, `/api/search`, `/api/top_picks`, `/api/init`) still have no rate limits. Tracked as follow-up (low-urgency, read-only endpoints with DB-level caching).
- `MODEL_SIGNING_KEY` in `config.py` is reserved for future HMAC signing of model files. Currently unused — SHA256 checksum only provides integrity, not authenticity.
- `smart_scan` CSRF check assumes no frontend caller exists that does not already send `X-Requested-With`. Confirm before enabling in production.
