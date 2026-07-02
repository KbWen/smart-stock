"""Transparency Panel backend (docs/specs/transparency-panel.md v1.0.0).

Read-only aggregation of EXISTING honest primitives:
  - core.ai.get_model_health() / get_model_version() / list_available_models()
  - core.data.report_history_coverage() / get_history_context()

No new data, no ML change, no persistence (AC1). The endpoint's aggregate is
server-side cached with a short TTL and rate-limited (AC2) since the coverage
+ history scans are full-ish table scans on a full-universe DB.
"""
import threading
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from backend.limiter import limiter
from core import config as _cfg
from core.ai import get_model_health, list_available_models
from core.data import get_history_context, report_history_coverage
from core.logger import setup_logger

router = APIRouter()
logger = setup_logger("backend.transparency")

_RATE_TRANSPARENCY = "10/minute"

_CACHE_TTL_SECONDS = 60.0

# --- Server-side TTL cache (double-checked locking) -------------------------
# A lock + (timestamp, value) pair. A request within TTL returns the cached
# value with no recompute. On a miss, recompute happens under the lock so
# concurrent misses do not each rescan the DB.
_cache_lock = threading.Lock()
_cache_timestamp: Optional[float] = None
_cache_value: Optional[dict] = None


def _reset_transparency_cache() -> None:
    """Test helper: clear the module-level cache so tests don't leak state."""
    global _cache_timestamp, _cache_value
    with _cache_lock:
        _cache_timestamp = None
        _cache_value = None


def _active_model_entry(version: str) -> Optional[dict]:
    """Return the models_history.json entry for the active version.

    Mirrors the exact lookup get_model_health() uses internally (same
    fallback-to-latest behavior) so the extra fields we surface here are
    consistent with the status/message get_model_health already returned.
    """
    history = list_available_models()
    entry = next((h for h in history if h.get("version") == version), None)
    if entry is None and history:
        entry = history[-1]
    return entry


def _compute_transparency() -> dict:
    """The heavy aggregation: full-ish table scans + model metadata lookup.

    Wrapped by the TTL cache below — never call this directly per-request.
    """
    coverage = report_history_coverage()
    history_ctx = get_history_context()

    data: dict[str, Any] = {
        "universe_size": coverage["universe"],
        "tickers_with_history": history_ctx["sample_size"] if history_ctx else None,
        "date_range": history_ctx["date_range"] if history_ctx else None,
        "coverage": {
            "with_predict_rows": coverage["with_predict_rows"],
            "with_train_rows": coverage["with_train_rows"],
            "short_count": len(coverage["short"]),
            "min_predict_rows": _cfg.MIN_PREDICT_ROWS,
            "min_train_rows": _cfg.MIN_TRAIN_ROWS,
        },
    }

    health = get_model_health()
    entry = _active_model_entry(health["version"]) or {}

    model: dict[str, Any] = {
        "status": health["status"],
        "version": health["version"],
        "message": health["message"],
        "trained_at": entry.get("trained_at") or entry.get("timestamp"),
        "samples": entry.get("samples"),
        "test_samples": entry.get("test_samples"),
        "class_distribution": entry.get("class_distribution"),
        "oos_metrics": entry.get("oos_metrics") or None,
    }

    return {"data": data, "model": model}


def _get_transparency_cached() -> dict:
    """Return the cached aggregate, recomputing once per TTL window.

    Double-checked locking: fast path reads under the lock; on a stale/absent
    cache, recompute happens while still holding the lock so concurrent
    misses serialize onto a single recompute rather than each rescanning.
    """
    global _cache_timestamp, _cache_value
    now = time.time()
    with _cache_lock:
        if _cache_value is not None and _cache_timestamp is not None and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
            return _cache_value
        value = _compute_transparency()
        _cache_value = value
        _cache_timestamp = time.time()
        return value


@router.get("/api/transparency")
@limiter.limit(_RATE_TRANSPARENCY)
def get_transparency(request: Request):
    try:
        return _get_transparency_cached()
    except Exception as e:
        logger.error("Transparency aggregation error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
