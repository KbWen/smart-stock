from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Optional

from fastapi import APIRouter, BackgroundTasks

from core import config
from core.ai import get_model_version, predict_prob
from core.data import (
    fetch_stock_data,
    get_all_tw_stocks,
    load_indicators_from_db,
    save_indicators_to_db,
    save_score_to_db,
)
from core.logger import setup_logger

router = APIRouter()
logger = setup_logger("backend.sync")

sync_status = {
    "is_syncing": False,
    "total": 0,
    "current": 0,
    "current_ticker": "",
    "last_updated": None,
    "sync_epoch": 0,
}
sync_status_lock = Lock()

_cache_clearers: list[Callable[[], None]] = []
_cache_clearers_lock = Lock()


def register_cache_clearer(clearer: Callable[[], None]) -> None:
    with _cache_clearers_lock:
        if clearer not in _cache_clearers:
            _cache_clearers.append(clearer)


def _run_cache_clearers() -> None:
    with _cache_clearers_lock:
        clearers = list(_cache_clearers)
    for clearer in clearers:
        try:
            clearer()
        except Exception:
            logger.exception("Failed to clear registered API cache")


def get_sync_status_snapshot() -> dict[str, Any]:
    with sync_status_lock:
        return dict(sync_status)


def _sync_status_update(**kwargs) -> None:
    with sync_status_lock:
        sync_status.update(kwargs)


def _sync_status_increment_current() -> None:
    with sync_status_lock:
        sync_status["current"] += 1


def _try_start_sync() -> bool:
    with sync_status_lock:
        if sync_status["is_syncing"]:
            return False
        sync_status["is_syncing"] = True
        return True


def _mark_sync_completed() -> None:
    with sync_status_lock:
        sync_status["is_syncing"] = False
        sync_status["last_updated"] = datetime.now().isoformat(timespec="seconds")
        sync_status["sync_epoch"] += 1


def run_sync_task() -> None:
    if not _try_start_sync():
        logger.warning("Sync task triggered but already running.")
        return

    logger.info("Starting background sync task...")

    try:
        all_stocks = get_all_tw_stocks()
        _sync_status_update(total=len(all_stocks), current=0)

        def process_stock(stock: dict[str, Any]) -> None:
            ticker = stock["code"]
            name = stock["name"]

            _sync_status_update(current_ticker=f"{ticker} {name}")

            try:
                cached = load_indicators_from_db(ticker)
                current_model_version = get_model_version()

                should_skip = False
                if cached and cached.get("model_version") == current_model_version:
                    updated_at = cached["updated_at"]
                    if isinstance(updated_at, str):
                        if "Z" in updated_at:
                            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        else:
                            updated_at = datetime.fromisoformat(updated_at)

                    now = datetime.now(updated_at.tzinfo) if updated_at.tzinfo else datetime.now()
                    if (now - updated_at).total_seconds() < 21600:
                        should_skip = True

                if should_skip:
                    _sync_status_increment_current()
                    return

                df = fetch_stock_data(ticker, days=730, force_download=False)
                if not df.empty and len(df) >= 60:
                    from core.indicators_v2 import compute_v4_indicators
                    from core.rise_score_v2 import calculate_rise_score_v2

                    df = compute_v4_indicators(df)
                    df = calculate_rise_score_v2(df)
                    last_row = df.iloc[-1]
                    prev_close = float(df.iloc[-2].get("close", 0) or 0) if len(df) > 1 else 0
                    last_close = float(last_row.get("close", 0) or 0)
                    change_percent = ((last_close - prev_close) / prev_close * 100) if prev_close else 0

                    score = {
                        "total_score": last_row.get("total_score_v2", 0),
                        "trend_score": last_row.get("trend_score_v2", 0),
                        "momentum_score": last_row.get("momentum_score_v2", 0),
                        "volatility_score": last_row.get("volatility_score_v2", 0),
                        "last_price": last_close,
                        "change_percent": change_percent,
                    }

                    ai_result = predict_prob(df)
                    ai_prob = 0.0
                    if isinstance(ai_result, dict):
                        ai_prob = ai_result.get("prob", 0.0)
                        score["ai_details"] = ai_result.get("details", {})
                    else:
                        ai_prob = ai_result

                    save_score_to_db(ticker, score, ai_prob, model_version=current_model_version)
                    save_indicators_to_db(ticker, df, model_version=current_model_version)

            except Exception:
                logger.exception("Sync error for %s", ticker)

            _sync_status_increment_current()

        num_workers = min(config.CONCURRENCY_WORKERS, len(all_stocks))
        logger.info("Syncing %s stocks with %s workers.", len(all_stocks), num_workers)
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(process_stock, all_stocks)

        logger.info("Sync task completed successfully.")

    except Exception:
        logger.exception("Fatal error in run_sync_task")
    finally:
        _run_cache_clearers()
        _mark_sync_completed()


@router.post("/api/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    current_status = get_sync_status_snapshot()
    if current_status["is_syncing"]:
        return {"message": "Sync already in progress"}

    background_tasks.add_task(run_sync_task)
    return {"message": "Sync started in background"}


@router.get("/api/sync/status")
def get_sync_status():
    return get_sync_status_snapshot()
