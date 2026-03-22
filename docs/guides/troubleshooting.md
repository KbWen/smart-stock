# Troubleshooting Guide

---

## Backend

### Server won't start

**Symptom:** `python backend/main.py` exits immediately or crashes.

**Checks:**
1. Python version: `python --version` → must be ≥ 3.11
2. Dependencies: `pip install -r requirements.txt`
3. Port conflict: `netstat -an | grep 8000` — if in use, kill the process or change the port
4. DB path: ensure `DB_PATH` directory exists and is writable
5. Model path: `MODEL_PATH` directory must exist (model file is optional at startup)

---

### Sync hangs or never completes

**Symptom:** `/api/sync/status` shows `is_syncing: true` for more than 30 minutes.

**Cause:** Network timeout fetching from `yfinance` or `twstock`, or a deadlocked DB write.

**Fix:**
1. Restart the server — the sync lock resets on startup
2. Check logs: `logs/backend.log` for the last error before hang
3. Test connectivity: `python -c "import yfinance; print(yfinance.download('2330.TW', period='1d'))"`
4. If `twstock` fails: `python -c "import twstock; print(twstock.codes.get('2330'))"`
5. Reduce concurrency: set `CONCURRENCY_WORKERS=2` and retry

---

### `database is locked` errors

See **DB Runbook → Common Issues → DB Locked** (`docs/guides/db-operations.md`).

---

### API returns 500 "Internal server error"

**Cause:** Unhandled exception in a route handler. Details are logged server-side.

**Fix:**
1. Check `logs/backend.log` for the full traceback
2. Set `LOG_LEVEL=DEBUG` to get more context
3. Common causes: DB locked, model file missing, malformed data in DB

---

### Model loading fails silently (predictions all return null)

**Symptom:** `GET /api/v4/sniper/candidates` returns empty or `ai_prob: 0` for all tickers.

**Causes and fixes:**

| Cause | Check | Fix |
|-------|-------|-----|
| Model file missing | `ls $MODEL_PATH` | Run `python backend/train_ai.py` |
| Checksum mismatch | Log: `"Checksum mismatch for ..."` | Re-train or restore from backup |
| HMAC sig mismatch | Log: `"HMAC signature mismatch for ..."` | Verify `MODEL_SIGNING_KEY` env var is set correctly |
| Corrupt pkl | Log: exception from `joblib.load` | Delete the corrupt file; run `python backend/train_ai.py` |
| Invalid version string | Log: `"Rejected invalid version string"` | Use correct format: `v4.YYYYMMDD_HHMM` |

---

### Rate limit errors (429)

**Symptom:** API returns `429 Too Many Requests`.

**Limits:**
| Endpoint | Limit |
|---------|-------|
| `/api/v4/sniper/candidates` | 60 req/min |
| `/api/v4/meta` | 30 req/min |
| `/api/backtest` | 20 req/min |

**Fix:** Reduce request frequency, or for local dev set `RATE_LIMIT_DISABLED=true` (not implemented in production builds — restart server with slowapi removed for local stress testing).

---

### `/api/smart_scan` returns 403

**Cause:** Missing `X-Requested-With: XMLHttpRequest` header on POST request.

**Fix (curl):**
```bash
curl -X POST http://localhost:8000/api/smart_scan \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d '["criteria1"]'
```

---

## Frontend

### Frontend shows blank page

**Symptom:** `http://localhost:8000` returns 404 or blank.

**Causes:**
1. Frontend not built: `cd frontend/v4 && npm run build`
2. Dist not in expected path: backend looks for `frontend/v4/dist/index.html`
3. Backend serving wrong directory: check `frontend_path` in `backend/main.py`

---

### API calls fail from frontend (CORS errors)

**Symptom:** Browser console shows `CORS policy: No 'Access-Control-Allow-Origin'`.

**Fix:**
1. Ensure frontend origin is in `CORS_ORIGINS` env var
2. Default dev origins: `http://localhost:5173`, `http://localhost:5174`, `http://localhost:3000`
3. If running on a different port: `CORS_ORIGINS=http://localhost:YOUR_PORT`

---

### Frontend dev server shows stale data

**Symptom:** Dev server (`npm run dev`) shows old API responses.

**Fix:** The Vite dev server proxies API calls to `http://127.0.0.1:8000`. Make sure the backend is running. Hard-refresh with `Ctrl+Shift+R`.

---

## AI / Model

### Training fails with insufficient data

**Symptom:** `python backend/train_ai.py` exits with "Not enough rows for training".

**Fix:**
1. Ensure you have at least `MIN_TRAIN_ROWS=260` days of price history per ticker
2. Run a full sync first: `python backend/main.py --sync`
3. Check which tickers have enough data:
   ```bash
   sqlite3 storage.db "SELECT ticker, COUNT(*) as rows FROM stock_history GROUP BY ticker HAVING rows < 260 LIMIT 20;"
   ```

### Model rotation deleting too many versions

**Symptom:** Old good models disappearing after training a bad new model.

**Cause:** Pre-fix issue — now resolved by `profit_factor_sort_key` in common.py (always protects the active model and freshly trained model).

**Check:** `python backend/manage_models.py list` — the active model (`*`) should never be pruned.

---

## Docker

### Container exits immediately

```bash
docker-compose logs app
```

Common causes: volume mount path doesn't exist, `DB_PATH` not writable inside container.

**Fix:**
```bash
mkdir -p ./data ./logs
docker-compose up --build
```

### Data not persisting between restarts

Ensure volumes are mounted:
```yaml
volumes:
  - ./data:/app/data
  - ./logs:/app/logs
```

The `./data` directory on the host maps to `/app/data` inside the container where `DB_PATH` and `MODEL_PATH` are set.

---

## Logs

| Log File | Content |
|---------|---------|
| `logs/backend.log` | API server, sync, scoring errors |
| `logs/core.log` | Data fetch, analysis, AI model load |
| stdout | Training progress, manage_models CLI output |

Set `LOG_LEVEL=DEBUG` for verbose output.
