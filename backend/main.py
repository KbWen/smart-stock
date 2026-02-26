from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import threading
import time
from typing import Optional, List, Any

# Add parent directory to path - MUST BE FIRST for core imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config

# Setup Logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from core.data import (
    fetch_stock_data, get_all_tw_stocks, save_score_to_db, 
    get_top_scores_from_db, get_db_connection,
    save_indicators_to_db, load_indicators_from_db, load_indicators_for_tickers, load_from_db,
    get_stock_name, init_db, get_latest_score_for_ticker
)
from core.analysis import generate_analysis_report
from core.rise_score_v2 import calculate_rise_score_v2
from core.features import compute_all_indicators
from core.ai import predict_prob, get_model_version
from core.alerts import check_smart_conditions
from core.market import get_market_status
from backend.backtest import run_time_machine

from fastapi.responses import FileResponse, JSONResponse
from fastapi import Request
from core.utils import safe_float, parse_date
from core.logger import setup_logger

logger = setup_logger("backend")

app = FastAPI(title="Smart Stock Selector")

# Global Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Error Catch: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"Server Side Error: {str(exc)}", "path": request.url.path}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if not os.path.exists(frontend_path):
    os.makedirs(frontend_path)

@app.get("/")
async def read_index():
    candidates = [
        os.path.join(frontend_path, "index.html"),
        os.path.join(frontend_path, "index_legacy.html"),
        os.path.join(frontend_path, "v4", "dist", "index.html"),
        os.path.join(frontend_path, "v4", "index.html"),
    ]
    for entry in candidates:
        if os.path.exists(entry):
            return FileResponse(entry)
    raise HTTPException(status_code=404, detail="Frontend entry file not found")

app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="static")

# -- Global Cache Removed: Uses get_all_tw_stocks() with @lru_cache now --


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


def _sync_status_snapshot() -> dict[str, Any]:
    with sync_status_lock:
        return dict(sync_status)


def _sync_status_update(**kwargs) -> None:
    with sync_status_lock:
        sync_status.update(kwargs)


def _sync_status_increment_current() -> None:
    with sync_status_lock:
        sync_status["current"] += 1


def _try_start_sync() -> bool:
    """Atomically mark sync as running.

    Returns True if the caller successfully acquired the sync run slot.
    """
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

# -- Lightweight API Cache (TTL) --
API_CACHE_TTL_SECONDS = 60
_api_cache: dict[str, dict[str, Any]] = {}
_api_cache_lock = threading.Lock()


def _read_api_cache(key: str):
    now = time.time()
    with _api_cache_lock:
        item = _api_cache.get(key)
        if not item:
            return None
        if item["expires_at"] <= now:
            _api_cache.pop(key, None)
            return None
        return item["value"]


def _write_api_cache(key: str, value, ttl_seconds: int = API_CACHE_TTL_SECONDS):
    with _api_cache_lock:
        _api_cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }


def clear_api_caches():
    with _api_cache_lock:
        _api_cache.clear()

def run_sync_task():
    if not _try_start_sync():
        logger.warning("Sync task triggered but already running.")
        return

    logger.info("Starting background sync task...")
    
    try:
        all_stocks = get_all_tw_stocks()
        _sync_status_update(total=len(all_stocks), current=0)
        
        def process_stock(stock):
            ticker = stock["code"]
            name = stock["name"]
            
            _sync_status_update(current_ticker=f"{ticker} {name}")
                
            try:
                # Smart Sync: Check version AND timestamp
                cached = load_indicators_from_db(ticker)
                current_model_version = get_model_version()
                
                should_skip = False
                if cached:
                    # 1. Check Model Version (MUST match)
                    if cached.get('model_version') == current_model_version:
                        # 2. Check Timestamp (SQLite might return string)
                        updated_at = cached['updated_at']
                        if isinstance(updated_at, str):
                            try:
                                updated_at = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                updated_at = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')

                        # Skip if updated within last 6 hours
                        if datetime.now() - updated_at < timedelta(hours=6):
                            should_skip = True

                if should_skip:
                    _sync_status_increment_current()
                    return
                
                # Fetch and Process
                df = fetch_stock_data(ticker, days=730, force_download=False)
                if not df.empty and len(df) >= 60:
                    from core.indicators_v2 import compute_v4_indicators
                    df = compute_v4_indicators(df)
                    # V2 returns the dataframe with scores added but we need the dict for save_score_to_db
                    # Oh wait, V2 returns the dataframe. We should extract the last row.
                    from core.rise_score_v2 import calculate_rise_score_v2
                    df = calculate_rise_score_v2(df)
                    last_row = df.iloc[-1]
                    prev_close = float(df.iloc[-2].get('close', 0) or 0) if len(df) > 1 else 0
                    last_close = float(last_row.get('close', 0) or 0)
                    change_percent = ((last_close - prev_close) / prev_close * 100) if prev_close else 0

                    score = {
                        'total_score': last_row.get('total_score_v2', 0),
                        'trend_score': last_row.get('trend_score_v2', 0),
                        'momentum_score': last_row.get('momentum_score_v2', 0),
                        'volatility_score': last_row.get('volatility_score_v2', 0),
                        'last_price': last_close,
                        'change_percent': change_percent,
                    }
                    
                    ai_result = predict_prob(df)
                    ai_prob = 0.0
                    if isinstance(ai_result, dict):
                        ai_prob = ai_result.get('prob', 0.0)
                        score['ai_details'] = ai_result.get('details', {})
                    else:
                        ai_prob = ai_result
                        
                    save_score_to_db(ticker, score, ai_prob, model_version=current_model_version)
                    save_indicators_to_db(ticker, df, model_version=current_model_version)

            except Exception:
                logger.exception(f"Sync error for {ticker}")
                
            _sync_status_increment_current()

        # Dynamic workers based on load and config
        num_workers = min(config.CONCURRENCY_WORKERS, len(all_stocks))
        logger.info(f"Syncing {len(all_stocks)} stocks with {num_workers} workers.")
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            executor.map(process_stock, all_stocks)
            
        logger.info("Sync task completed successfully.")
            
    except Exception:
        logger.exception("Fatal error in run_sync_task")
    finally:
        clear_api_caches()
        _mark_sync_completed()

@app.post("/api/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    current_status = _sync_status_snapshot()
    if current_status["is_syncing"]:
        return {"message": "Sync already in progress"}
    
    background_tasks.add_task(run_sync_task)
    return {"message": "Sync started in background"}

@app.get("/api/sync/status")
def get_sync_status():
    return _sync_status_snapshot()

@app.get("/api/stocks")
def search_stocks(q: Optional[str] = None):
    all_stocks = get_all_tw_stocks()
    if not q:
        return all_stocks[:50]
    
    q = q.lower()
    filtered = [
        s for s in all_stocks 
        if q in s["code"].lower() or q in s["name"].lower()
    ]
    return filtered[:20]

@app.get("/api/models")
def get_model_history_list():
    """Returns list of available trained model versions."""
    from core.ai import list_available_models
    return list_available_models()

@app.get("/api/search")
def search_stocks_global_api(q: str = Query(..., min_length=1)):
    """Universal search for any stock ticker or name."""
    from core.data import search_stocks_global
    return search_stocks_global(q)

@app.get("/api/init")
def get_init_data():
    """Consolidated endpoint for homepage initialization to reduce round-trips."""
    t0 = time.time()
    
    # 1. Market Status
    from core.market import get_market_status
    market = get_market_status()
    
    # 2. Top Picks (Latest Technical)
    picks = get_top_picks(sort="score")
    
    # 3. Models
    from core.ai import list_available_models
    models = list_available_models()
    
    # 4. Sync Status
    curr_sync = _sync_status_snapshot()
    
    total_time = time.time() - t0
    logger.info(f"Consolidated Init took {total_time:.4f}s")
    
    return {
        "market": market,
        "top_picks": picks,
        "models": models,
        "sync": curr_sync,
        "perf_ms": int(total_time * 1000)
    }

@app.get("/api/top_picks")
def get_top_picks(sort: str = "score", version: Optional[str] = None):
    picks = get_top_scores_from_db(limit=50, sort_by=sort, version=version)
    
    if picks:
        # Optimized with name_map cache internally
        result = []
        for p in picks:
            last_price = p.get('last_price', 0) or 0
            ai_prob = p.get('ai_probability') or 0
            
            result.append({
                "ticker": p['ticker'],
                "name": get_stock_name(p['ticker']),
                "ai_probability": ai_prob,
                "model_version": p.get('model_version', 'legacy'),
                "last_sync": p.get('last_sync'),
                "ai_target_price": round(last_price * 1.15, 2) if last_price else 0,
                "ai_stop_price": round(last_price * 0.95, 2) if last_price else 0,
                "score": {
                    "total_score": p['total_score'],
                    "trend_score": p['trend_score'],
                    "momentum_score": p['momentum_score'],
                    "volatility_score": p['volatility_score'],
                    "last_price": last_price,
                    "change_percent": p.get('change_percent', 0) or 0
                }
            })
        return result
    else:
        return []

@app.get("/api/stock/{ticker}")
def get_stock_detail(ticker: str):
    # Fast path for UI responsiveness: use local DB snapshot first (even if not same-day).
    # This avoids blocking the card on remote provider retries when data is slightly stale.
    df = load_from_db(ticker)
    if df.empty:
        # Fallback only when there is no local data at all.
        df = fetch_stock_data(ticker)
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Compute V4 indicators
    from core.indicators_v2 import compute_v4_indicators
    from core.rise_score_v2 import calculate_rise_score_v2
    df = compute_v4_indicators(df)
    
    df = calculate_rise_score_v2(df)
    df = df.fillna(0)
    last_row = df.iloc[-1]
    score = {
        'total_score': safe_float(last_row.get('total_score_v2', 0)),
        'trend_score': safe_float(last_row.get('trend_score_v2', 0)),
        'momentum_score': safe_float(last_row.get('momentum_score_v2', 0)),
        'volatility_score': safe_float(last_row.get('volatility_score_v2', 0))
    }
    
    # --- Text Analysis ---
    prev_row = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    analysis_report = generate_analysis_report(
        df.iloc[-1], prev_row, 
        score['trend_score'], score['momentum_score'], score['volatility_score']
    )
    score['analysis'] = analysis_report
    
    ai_result = predict_prob(df)
    
    ai_prob = 0.0
    ai_details = {}
    
    if isinstance(ai_result, dict):
        ai_prob = ai_result.get('prob', 0.0)
        ai_details = ai_result.get('details', {})
    elif isinstance(ai_result, float):
        ai_prob = ai_result
        
    score['ai_details'] = ai_details
    
    last_price = float(last_row.get('close', 0) or 0)
    
    history = df.tail(30)[['date', 'close', 'volume']].to_dict('records')
    for h in history:
        if hasattr(h['date'], 'strftime'):
            h['date'] = h['date'].strftime('%Y-%m-%d')
    
    change_percent = 0.0
    if len(df) > 1 and float(df.iloc[-2].get('close', 0) or 0) != 0:
        prev_close = float(df.iloc[-2]['close'])
        change_percent = ((last_price - prev_close) / prev_close) * 100

    score['last_price'] = round(last_price, 4)
    score['change_percent'] = round(change_percent, 4)

    db_score = get_latest_score_for_ticker(ticker)
    db_updated_at = db_score.get('updated_at') if db_score else None

    return {
        "ticker": ticker,
        "last_price": round(last_price, 4),
        "change_percent": round(change_percent, 4),
        "updated_at": db_updated_at,
        "score": score,
        "ai_probability": ai_prob,
        "ai_target_price": round(last_price * 1.15, 2) if last_price else 0,
        "ai_stop_price": round(last_price * 0.95, 2) if last_price else 0,
        "history": history
    }


@app.get("/api/stock/{ticker}/verify")
def verify_stock_detail(ticker: str, refresh_db: bool = False):
    """Fetch real-time quote and compare against cached DB score snapshot."""
    db_score = get_latest_score_for_ticker(ticker)
    if not db_score:
        raise HTTPException(status_code=404, detail="Stock score not found in DB")

    realtime_df = fetch_stock_data(ticker, days=30, force_download=True)
    if realtime_df.empty:
        raise HTTPException(status_code=404, detail="Unable to fetch realtime stock data")

    realtime_last = float(realtime_df.iloc[-1].get('close', 0) or 0)
    realtime_change = 0.0
    if len(realtime_df) > 1 and float(realtime_df.iloc[-2].get('close', 0) or 0) != 0:
        prev_close = float(realtime_df.iloc[-2].get('close', 0) or 0)
        realtime_change = ((realtime_last - prev_close) / prev_close) * 100

    db_last = float(db_score.get('last_price', 0) or 0)
    db_change = float(db_score.get('change_percent', 0) or 0)

    last_price_diff_pct = abs((db_last - realtime_last) / realtime_last * 100) if realtime_last else 0
    change_diff_abs = abs(db_change - realtime_change)

    tolerance_percent = 0.5
    within_tolerance = last_price_diff_pct <= tolerance_percent and change_diff_abs <= tolerance_percent

    if refresh_db:
        model_version = db_score.get('model_version')
        refresh_score_payload = {
            'total_score': db_score.get('total_score', 0),
            'trend_score': db_score.get('trend_score', 0),
            'momentum_score': db_score.get('momentum_score', 0),
            'volatility_score': db_score.get('volatility_score', 0),
            'last_price': realtime_last,
            'change_percent': realtime_change,
        }
        save_score_to_db(ticker, refresh_score_payload, ai_prob=db_score.get('ai_probability', 0), model_version=model_version)
        db_score = get_latest_score_for_ticker(ticker, model_version=model_version)

    return {
        "ticker": ticker,
        "within_tolerance": within_tolerance,
        "tolerance_percent": tolerance_percent,
        "database": {
            "last_price": db_last,
            "change_percent": db_change,
            "updated_at": db_score.get('updated_at') if db_score else None,
            "model_version": db_score.get('model_version') if db_score else None,
        },
        "realtime": {
            "last_price": round(realtime_last, 4),
            "change_percent": round(realtime_change, 4),
        },
        "diff": {
            "last_price_pct": round(last_price_diff_pct, 4),
            "change_percent_abs": round(change_diff_abs, 4),
        }
    }

@app.get("/api/backtest")
def run_backtest_simulation(days: int = 30, version: Optional[str] = None):
    """
    Run 'Time Machine' backtest. Supports specific model version.
    """
    try:
        # Pass version to run_time_machine
        result = run_time_machine(days_ago=days, limit=100, version=version)
        return result
    except Exception as e:
        logger.error(f"Backtest API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market_status")
def market_status():
    """
    Returns market-wide risk metrics (Bull/Bear Ratio, Temp, Sentiment) + History.
    """
    from core.market import save_market_history, get_market_history
    status = get_market_status()
    status["model_version"] = get_model_version()
    
    # Save snapshot to history
    if status.get("bull_ratio") is not None:
        save_market_history(status)
        
    status["history"] = get_market_history()
    return status

@app.post("/api/smart_scan")
def smart_scan(criteria: List[str] = []):
    """
    Scans Top 100 stocks for composite conditions using CACHED indicators where possible.
    """
    candidates = get_top_scores_from_db(limit=100, sort_by="score")
    all_stocks = get_all_tw_stocks()
    name_map = {s['code']: s['name'] for s in all_stocks}
    
    results = []
    
    for c in candidates:
        ticker = c['ticker']
        try:
            # 1. Try to load from CACHE first (Super Fast)
            cached_indicators = load_indicators_from_db(ticker)
            
            if cached_indicators:
                # check_smart_conditions expects a DataFrame or enough info to calculate
                # Let's adjust check_smart_conditions to handle cached data if possible,
                # or just fetch if cache is missing.
                
                # OPTIMIZATION: Use load_from_db instead of fetch_stock_data to avoid network calls.
                # If data is stale, it's better to scan stale data than hang.
                df = load_from_db(ticker) 
                
                if df.empty or len(df) < 60: continue
                
                # Slicing: Only compute indicators for recent history (last 300 days is enough)
                # calculating indicators on 20 years of data is slow and unnecessary.
                if len(df) > 300:
                    df = df.tail(300).copy()
                    
                # We skip compute_all_indicators if we have cache? 
                # Actually check_smart_conditions needs indicators in columns.
                # load_from_db returns OHLCV only. We must compute indicators.
                df = compute_all_indicators(df) 
                
                # Ensure 'c' has required keys before accessing
                if not isinstance(c, dict): continue
                
                ai_prob = c.get('ai_probability', 0)
                if check_smart_conditions(df, ai_prob, criteria):
                    results.append({
                        "ticker": ticker,
                        "name": name_map.get(ticker, ticker),
                        "ai_probability": ai_prob,
                        "model_version": c.get('model_version', 'legacy'),
                        "last_sync": c.get('last_sync'),
                        "score": c, # Return full object for frontend compatibility
                        "price": c.get('last_price', 0),
                        "ai_target_price": round(c.get('last_price', 0) * 1.15, 2),
                        "ai_stop_price": round(c.get('last_price', 0) * 0.95, 2),
                        "matches": criteria
                    })
        except:
            continue
            
    return results

@app.get("/api/health")
def health_check():
    """System Health Check Endpoint"""
    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "db": "disconnected",
        "model_version": get_model_version(),
        "concurrency_workers": config.CONCURRENCY_WORKERS
    }
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        health_status["db"] = "connected"
    except Exception as e:
        health_status["status"] = "error"
        health_status["db"] = str(e)
        
    return health_status

# ==========================================
# V4.1 SNIPER API ENDPOINTS
# ==========================================

from core.rise_score_v2 import calculate_rise_score_v2
from core.indicators_v2 import compute_v4_indicators
from core.ai import predict_prob

def _to_float(value: Any) -> Optional[float]:
    """Convert a value to float when possible.

    Args:
        value: Raw value loaded from DB/cache.

    Returns:
        Optional[float]: Parsed float value, or ``None`` when conversion fails.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@app.get("/api/v4/sniper/candidates")
def get_v4_candidates(
    limit: int = 50,
    sort: str = "score",
    version: Optional[str] = None,
):
    """
    Returns Top Sniper Candidates using Rise Score 2.0 & AI Lite.
    Optimized for React Frontend (StockList.tsx).
    """
    try:
        if sort not in {"score", "ai"}:
            raise HTTPException(status_code=422, detail="sort must be one of: score, ai")

        cache_version = _sync_status_snapshot().get("sync_epoch", 0)
        cache_key = f"v4_candidates:limit={limit}:sort={sort}:version={version or 'latest'}:sync={cache_version}"
        cached = _read_api_cache(cache_key)
        if cached is not None:
            return cached

        start_ts = time.time()
        # Optimized path: Fetch top 50 directly from DB if they have V4 versions
        # We fetch a bit more to handle potential filtering
        raw_candidates = get_top_scores_from_db(limit=limit * 2, sort_by=sort, version=version)
        indicators_map = load_indicators_for_tickers([c['ticker'] for c in raw_candidates])

        results = []
        fallback_errors = 0
        for c in raw_candidates:
            ticker = c['ticker']
            
            # If the score in DB is already from a V4 version, we trust it for the list view
            # This is significantly faster than re-calculating everything
            if c.get('model_version', '').startswith('v4'):
                cached_ind = indicators_map.get(ticker) or {}
                results.append({
                    "ticker": ticker,
                    "name": get_stock_name(ticker),
                    "price": round(safe_float(c.get('last_price', 0)), 2),
                    "change_percent": round(safe_float(c.get('change_percent', 0)), 2),
                    "rise_score": round(safe_float(c['total_score']), 1),
                    "ai_prob": round(safe_float(c.get('ai_probability', 0)) * 100, 1),
                    "trend": round(safe_float(c['trend_score']), 1),
                    "momentum": round(safe_float(c['momentum_score']), 1),
                    "volatility": round(safe_float(c['volatility_score']), 1),
                    "rsi_14": round(safe_float(cached_ind.get('rsi', 50)), 1),
                    "macd_diff": round(safe_float((cached_ind.get('macd') or 0) - (cached_ind.get('macd_signal') or 0)), 2),
                    "volume_ratio": round(safe_float(cached_ind.get('rel_vol', 1.0)), 2),
                    "updated_at": c.get("updated_at")
                })
                if len(results) >= limit: break
                continue

            # Fallback for old versions: On-the-fly (Slow)
            try:
                df = load_from_db(ticker)
                if df.empty or len(df) < 60: continue
                df = compute_v4_indicators(df)
                df = calculate_rise_score_v2(df)
                latest = df.iloc[-1]
                ai_result = predict_prob(df) 
                ai_prob = ai_result.get('prob', 0) if isinstance(ai_result, dict) else ai_result
                    
                results.append({
                    "ticker": ticker, "name": get_stock_name(ticker),
                    "price": safe_float(latest['close']),
                    "change_percent": safe_float((latest['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100 if len(df) > 1 else 0),
                    "rise_score": round(safe_float(latest['total_score_v2']), 1),
                    "ai_prob": round(safe_float(ai_prob) * 100, 1),
                    "trend": round(safe_float(latest['trend_score_v2']), 1),
                    "momentum": round(safe_float(latest['momentum_score_v2']), 1),
                    "volatility": round(safe_float(latest['volatility_score_v2']), 1),
                    "rsi_14": round(safe_float(latest.get('rsi', 50)), 1),
                    "macd_diff": round(safe_float(latest.get('macd_hist', 0)), 2),
                    "volume_ratio": round(safe_float(latest.get('rel_vol', 1.0)), 2),
                    "updated_at": c.get("updated_at")
                })
            except Exception as e:
                fallback_errors += 1
                if fallback_errors <= 10:
                    logger.warning("Fallback candidate recompute failed", extra={"ticker": ticker, "error": str(e)})
                continue
            if len(results) >= limit: break

        elapsed_ms = round((time.time() - start_ts) * 1000, 2)
        logger.info("Built v4 candidates payload", extra={"requested_limit": limit, "selected": len(results), "raw_count": len(raw_candidates), "elapsed_ms": elapsed_ms})
        _write_api_cache(cache_key, results)
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v4/stock/{ticker}")
def get_v4_stock_detail(ticker: str):
    """
    Returns detailed analysis for SniperCard.tsx.
    """
    # Fast path for UI responsiveness: use local DB snapshot first (even if not same-day).
    # This avoids blocking the card on remote provider retries when data is slightly stale.
    df = load_from_db(ticker)
    if df.empty:
        # Fallback only when there is no local data at all.
        df = fetch_stock_data(ticker)
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock not found")
        
    # V4 Pipeline
    df = compute_v4_indicators(df)
    df = calculate_rise_score_v2(df)
    
    latest = df.iloc[-1]
    
    # AI
    ai_result = predict_prob(df)
    ai_prob = 0.0
    if isinstance(ai_result, dict):
        ai_prob = ai_result.get('prob', 0)
    elif isinstance(ai_result, float):
        ai_prob = ai_result

    # Generate "AI Analyst" Text
    analyst_text = []
    if latest['trend_alignment'] == 1:
        analyst_text.append("✅ **Strong Uptrend**: Price is consistently above SMA20 & SMA60.")
    elif latest['sma20_slope'] > 0:
        analyst_text.append("🌤️ **Recovering**: Price is building momentum above SMA20.")
        
    if 40 <= latest['rsi'] <= 70:
        analyst_text.append("⚡ **Momentum**: RSI is in the bullish zone (40-70).")
    elif latest['rsi'] > 80:
        analyst_text.append("⚠️ **Overheated**: RSI indicates overbought territory.")
        
    if latest['is_squeeze']:
        analyst_text.append("💥 **Squeeze Alert**: Low volatility detected, expecting a major move.")
    elif latest['rel_vol'] > 1.5:
        analyst_text.append("📢 **Volume Spike**: Heavy trading activity detected.")

    db_score = get_latest_score_for_ticker(ticker)

    return {
        "ticker": ticker,
        "name": get_stock_name(ticker),
        "price": safe_float(latest['close']),
        "updated_at": db_score.get('updated_at') if db_score else None,
        "rise_score_breakdown": {
            "total": round(safe_float(latest['total_score_v2']), 1),
            "trend": round(safe_float(latest['trend_score_v2']), 1),
            "momentum": round(safe_float(latest['momentum_score_v2']), 1),
            "volatility": round(safe_float(latest['volatility_score_v2']), 1)
        },
        "ai_probability": round(safe_float(ai_prob) * 100, 1),
        "analyst_summary": " ".join(analyst_text) if analyst_text else "Market is neutral. Watch for setup signals.",
        "signals": {
            "squeeze": bool(latest.get('is_squeeze', False)),
            "golden_cross": bool(latest.get('kd_cross_flag', False)),
            "volume_spike": bool(safe_float(latest.get('rel_vol', 1.0)) > 1.5)
        }
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true", help="Run sync and exit")
    args = parser.parse_args()
    
    if args.sync:
        print("Starting Sync-Only Mode...")
        run_sync_task()
        print("Sync Complete.")
    else:
        try:
            init_db()  # Explicitly initialize DB before starting
            get_all_tw_stocks() # Pre-cache stocks
            logger.info("Stock list cached successfully.")
        except Exception as e:
            logger.error(f"Failed to cache stock list: {e}")

        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
