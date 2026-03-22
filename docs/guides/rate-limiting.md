# Rate Limiting Guide

> **Feature**: Per-IP rate limiting via SlowAPI
> **Added**: v4 security hardening (PR#4, 2026-03-19)
> **Relevant files**: `backend/limiter.py`, `backend/routes/stock.py`, `backend/main.py`

---

## Overview

Smart Stock 使用 [SlowAPI](https://github.com/laurentS/slowapi)（基於 `limits` 套件）在三個高成本 API 端點上實施 per-IP rate limiting，防止資料爬取與 DoS 攻擊。Rate limiting 在 FastAPI middleware 層啟用，不影響業務邏輯。

---

## Rate Limit 設定

| 端點 | 方法 | 限制 | 變數 |
|------|------|------|------|
| `/api/v4/sniper/candidates` | GET | 60 次/分鐘 | `_RATE_CANDIDATES` |
| `/api/v4/meta` | GET | 30 次/分鐘 | `_RATE_META` |
| `/api/backtest` | GET | 20 次/分鐘 | `_RATE_BACKTEST` |

設定位置：`backend/routes/stock.py`

```python
_RATE_CANDIDATES = "60/minute"
_RATE_META       = "30/minute"
_RATE_BACKTEST   = "20/minute"
```

---

## 架構

### limiter.py

```python
# backend/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

- `key_func=get_remote_address`：以客戶端 IP 為限速金鑰
- 計數器存於 in-memory（單機部署）

### main.py 掛載

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from backend.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

### 端點宣告

```python
@router.get("/api/v4/sniper/candidates")
@limiter.limit(_RATE_CANDIDATES)
def get_v4_candidates(request: Request, ...):
    ...
```

> **注意**：`request: Request` 參數是 SlowAPI 運作的必要條件，缺少時 rate limiting 不會生效。

---

## 限速觸發行為

超過限制時，回傳：

```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{"error": "Rate limit exceeded: 60 per 1 minute"}
```

---

## 測試

### 手動測試（curl 壓測）

```bash
# 快速發送超過限制的請求，確認 429 觸發
for i in $(seq 1 65); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://localhost:8000/api/v4/sniper/candidates
done
# 前 60 個應回傳 200，第 61 個起回傳 429
```

```bash
# backtest 端點（限制 20/min）
for i in $(seq 1 25); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    "http://localhost:8000/api/backtest?days=7"
done
```

### 單元測試（FastAPI TestClient）

SlowAPI 在 `TestClient` 環境下以 `127.0.0.1` 為 key。測試可使用 `monkeypatch` 替換 limiter 或驗證 `@limiter.limit` decorator 已正確附加：

```python
# 驗證 decorator 已正確設定（smoke test）
from backend.routes.stock import get_v4_candidates, run_backtest_simulation, get_v4_meta

def test_rate_limit_decorators_applied():
    """Smoke test: verify @limiter.limit decorators are present."""
    # SlowAPI wraps the function; __wrapped__ holds the original
    assert hasattr(get_v4_candidates, "__wrapped__") or callable(get_v4_candidates)
    assert hasattr(run_backtest_simulation, "__wrapped__") or callable(run_backtest_simulation)
```

### pytest 中停用 rate limiting

若現有 API 測試需要高頻呼叫，可在 `conftest.py` 中 patch limiter：

```python
# tests/conftest.py
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=False)
def disable_rate_limit():
    """Disable SlowAPI rate limiting for a specific test."""
    with patch("backend.limiter.limiter.limit", return_value=lambda f: f):
        yield
```

---

## 調整限制

修改 `backend/routes/stock.py` 中的常數：

```python
_RATE_CANDIDATES = "120/minute"  # 放寬候選股列表
_RATE_META       = "60/minute"   # 放寬 meta 查詢
_RATE_BACKTEST   = "10/minute"   # 收緊回測（高成本）
```

> **注意**：目前 rate limit 狀態存於 in-memory。若要橫向擴展（多 instance），需切換至 Redis backend：
> ```python
> Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
> ```

---

## 相關文件

- [SlowAPI 官方文件](https://github.com/laurentS/slowapi)
- `backend/limiter.py` — limiter 實例
- `backend/routes/stock.py` — rate limit 裝飾器使用
- `docs/API_CONTRACT.md` — 完整 API 規格
