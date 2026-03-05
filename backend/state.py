import threading
import time
from datetime import datetime
from typing import Any

# -- Global State for Sync Progress --
sync_status = {
    "is_syncing": False,
    "total": 0,
    "current": 0,
    "current_ticker": "",
    "last_updated": None,
    "sync_epoch": 0,
}
sync_status_lock = threading.Lock()

def sync_status_snapshot() -> dict[str, Any]:
    with sync_status_lock:
        return dict(sync_status)

def sync_status_update(**kwargs) -> None:
    with sync_status_lock:
        sync_status.update(kwargs)

def sync_status_increment_current() -> None:
    with sync_status_lock:
        sync_status["current"] += 1

def try_start_sync() -> bool:
    with sync_status_lock:
        if sync_status["is_syncing"]:
            return False
        sync_status["is_syncing"] = True
        return True

def mark_sync_completed() -> None:
    with sync_status_lock:
        sync_status["is_syncing"] = False
        sync_status["last_updated"] = datetime.now().isoformat(timespec="seconds")
        sync_status["sync_epoch"] += 1

# -- Lightweight API Cache (TTL) --
API_CACHE_TTL_SECONDS = 60
_api_cache: dict[str, dict[str, Any]] = {}
_api_cache_lock = threading.Lock()

def read_api_cache(key: str):
    now = time.time()
    with _api_cache_lock:
        item = _api_cache.get(key)
        if not item:
            return None
        if item["expires_at"] <= now:
            _api_cache.pop(key, None)
            return None
        return item["value"]

def write_api_cache(key: str, value, ttl_seconds: int = API_CACHE_TTL_SECONDS):
    with _api_cache_lock:
        _api_cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }

def clear_api_caches():
    with _api_cache_lock:
        _api_cache.clear()
