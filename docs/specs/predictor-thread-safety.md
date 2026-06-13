---
status: frozen
module: core-ai
---
# Spec: Thread-Safe Model Version Tracking in predictor.py

## Problem

`core/ai/predictor.py` tracks the currently-loaded model version in a module-level global:

```python
CURRENT_MODEL_VERSION = "unknown"   # line 11

def predict_prob(df, version=None):
    global CURRENT_MODEL_VERSION
    # ...
    CURRENT_MODEL_VERSION = model_data_all.get('version', 'unknown')   # mutated here
```

FastAPI runs synchronous route handlers in a thread pool. Concurrent calls to `predict_prob`
with different model versions will race to overwrite `CURRENT_MODEL_VERSION`, causing
`get_model_version()` to return a stale or wrong version to other callers.

Additionally, the `_model_cache` dict has no size limit. Each versioned model (.pkl) is
~50–100 MB. Comparing multiple backtest versions via `/api/backtest?version=...` loads
all of them into memory permanently.

## Goal

1. Make model version tracking thread-safe using a `threading.Lock`.
2. Cap `_model_cache` at `_MAX_CACHED_MODELS = 3` with LRU eviction via `OrderedDict`.

## Proposed Changes

### 1. Replace bare global with lock-protected state

```python
import threading
from collections import OrderedDict

_version_lock = threading.Lock()
_current_model_version = "unknown"   # private; accessed only through helpers
_cache_lock = threading.Lock()
_model_cache: OrderedDict = OrderedDict()
_MAX_CACHED_MODELS = 3

def _get_model_version_unsafe() -> str:   # call only while holding _version_lock
    return _current_model_version

def _set_model_version(version: str) -> None:
    global _current_model_version
    with _version_lock:
        _current_model_version = version

def get_model_version() -> str:
    with _version_lock:
        if _current_model_version != "unknown":
            return _current_model_version
    # load outside the lock (expensive I/O)
    if os.path.exists(MODEL_PATH):
        try:
            data = joblib.load(MODEL_PATH)
            v = data.get('version', 'legacy') if isinstance(data, dict) else 'legacy'
            _set_model_version(v)
        except Exception:
            pass
    with _version_lock:
        return _current_model_version
```

### 2. LRU cache helpers

```python
def _cache_get(path: str):
    with _cache_lock:
        if path in _model_cache:
            _model_cache.move_to_end(path)
            return _model_cache[path]
    return None

def _cache_put(path: str, model_data) -> None:
    with _cache_lock:
        _model_cache[path] = model_data
        _model_cache.move_to_end(path)
        while len(_model_cache) > _MAX_CACHED_MODELS:
            _model_cache.popitem(last=False)
```

### 3. Update `predict_prob` to use helpers

Replace `global CURRENT_MODEL_VERSION` and all mutations with `_set_model_version(...)`.
Replace direct `_model_cache` dict access with `_cache_get` / `_cache_put`.

## Acceptance Criteria (AC)

- [x] **AC1 – Thread-safe version**: `_current_model_version` protected by `_version_lock`; `_set_model_version()` helper wraps all writes. No bare `global CURRENT_MODEL_VERSION` remains. _(code-verified 2026-03-18)_
- [x] **AC2 – LRU eviction**: `_model_cache` is `OrderedDict` capped at `_MAX_CACHED_MODELS=3` via `_cache_put()` with `popitem(last=False)`. _(code-verified 2026-03-18)_
- [x] **AC3 – Backward compat**: All 124 tests pass including existing `test_ai.py` which uses `_model_cache.clear()`. _(2026-03-18)_

## Non-goals

- Adding async/await to the prediction pipeline.
- Changing ensemble weights or model architecture.
