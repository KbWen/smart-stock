import threading
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.backtest import run_time_machine
from backend.routes.sync import get_sync_status_snapshot, register_cache_clearer
from core import config
from core.ai import get_model_version, predict_prob
from core.alerts import check_smart_conditions
from core.analysis import generate_analysis_report
from core.data import (
    fetch_stock_data,
    get_all_tw_stocks,
    get_db_connection,
    get_latest_score_for_ticker,
    get_stock_name,
    get_top_scores_from_db,
    load_from_db,
    load_indicators_for_tickers,
    load_indicators_from_db,
    save_score_to_db,
    standardize_ticker,
)
from core.features import compute_all_indicators
from core.logger import setup_logger
from core.utils import safe_float

router = APIRouter()
logger = setup_logger("backend.stock")

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


def _write_api_cache(key: str, value: Any, ttl_seconds: int = API_CACHE_TTL_SECONDS) -> None:
    with _api_cache_lock:
        _api_cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds,
        }


def clear_api_caches() -> None:
    with _api_cache_lock:
        _api_cache.clear()


register_cache_clearer(clear_api_caches)


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _parse_db_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _load_latest_scores_for_tickers(tickers: list[str]) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}

    conn = get_db_connection()
    try:
        placeholders = ",".join(["?"] * len(tickers))
        query = f"""
            SELECT s.*
            FROM stock_scores s
            WHERE s.ticker IN ({placeholders})
              AND s.updated_at = (
                SELECT MAX(s2.updated_at)
                FROM stock_scores s2
                WHERE s2.ticker = s.ticker
              )
        """
        rows = conn.execute(query, tickers).fetchall()
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            row_dict = dict(row)
            ticker = row_dict.get("ticker")
            if ticker and ticker not in result:
                result[ticker] = row_dict
        return result
    finally:
        conn.close()


@router.get("/api/stocks")
def search_stocks(q: Optional[str] = None):
    all_stocks = get_all_tw_stocks()
    if not q:
        return all_stocks[:50]

    q = q.lower()
    filtered = [s for s in all_stocks if q in s["code"].lower() or q in s["name"].lower()]
    return filtered[:20]


@router.get("/api/models")
def get_model_history_list():
    from core.ai import list_available_models

    return list_available_models()


@router.get("/api/search")
def search_stocks_global_api(q: str = Query(..., min_length=1)):
    from core.data import search_stocks_global

    return search_stocks_global(q)


@router.get("/api/init")
def get_init_data():
    t0 = time.time()

    from core.market import get_market_status
    from core.ai import list_available_models

    market = get_market_status()
    picks = get_top_picks(sort="score")
    models = list_available_models()
    curr_sync = get_sync_status_snapshot()

    total_time = time.time() - t0
    logger.info("Consolidated Init took %.4fs", total_time)

    return {
        "market": market,
        "top_picks": picks,
        "models": models,
        "sync": curr_sync,
        "perf_ms": int(total_time * 1000),
    }


@router.get("/api/top_picks")
def get_top_picks(sort: str = "score", version: Optional[str] = None):
    picks = get_top_scores_from_db(limit=50, sort_by=sort, version=version)

    if not picks:
        return []

    result = []
    for p in picks:
        last_price = p.get("last_price", 0) or 0
        ai_prob = p.get("ai_probability") or 0

        result.append(
            {
                "ticker": p["ticker"],
                "name": get_stock_name(p["ticker"]),
                "ai_probability": ai_prob,
                "model_version": p.get("model_version", "legacy"),
                "last_sync": p.get("last_sync"),
                "ai_target_price": round(last_price * 1.15, 2) if last_price else 0,
                "ai_stop_price": round(last_price * 0.95, 2) if last_price else 0,
                "score": {
                    "total_score": p["total_score"],
                    "trend_score": p["trend_score"],
                    "momentum_score": p["momentum_score"],
                    "volatility_score": p["volatility_score"],
                    "last_price": last_price,
                    "change_percent": p.get("change_percent", 0) or 0,
                },
            }
        )
    return result


@router.get("/api/stock/{ticker}")
def get_stock_detail(ticker: str):
    df = load_from_db(ticker)
    if df.empty:
        df = fetch_stock_data(ticker)
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock not found")

    from core.indicators_v2 import compute_v4_indicators
    from core.rise_score_v2 import calculate_rise_score_v2

    df = compute_v4_indicators(df)
    df = calculate_rise_score_v2(df)
    df = df.fillna(0)
    last_row = df.iloc[-1]
    score = {
        "total_score": safe_float(last_row.get("total_score_v2", 0)),
        "trend_score": safe_float(last_row.get("trend_score_v2", 0)),
        "momentum_score": safe_float(last_row.get("momentum_score_v2", 0)),
        "volatility_score": safe_float(last_row.get("volatility_score_v2", 0)),
    }

    prev_row = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    analysis_report = generate_analysis_report(
        df.iloc[-1],
        prev_row,
        score["trend_score"],
        score["momentum_score"],
        score["volatility_score"],
    )
    score["analysis"] = analysis_report

    ai_result = predict_prob(df)

    ai_prob = 0.0
    ai_details = {}

    if isinstance(ai_result, dict):
        ai_prob = ai_result.get("prob", 0.0)
        ai_details = ai_result.get("details", {})
    elif isinstance(ai_result, float):
        ai_prob = ai_result

    score["ai_details"] = ai_details

    last_price = float(last_row.get("close", 0) or 0)

    history = df.tail(30)[["date", "close", "volume"]].to_dict("records")
    for h in history:
        if hasattr(h["date"], "strftime"):
            h["date"] = h["date"].strftime("%Y-%m-%d")

    change_percent = 0.0
    if len(df) > 1 and float(df.iloc[-2].get("close", 0) or 0) != 0:
        prev_close = float(df.iloc[-2]["close"])
        change_percent = ((last_price - prev_close) / prev_close) * 100

    score["last_price"] = round(last_price, 4)
    score["change_percent"] = round(change_percent, 4)

    db_score = get_latest_score_for_ticker(ticker)
    db_updated_at = db_score.get("updated_at") if db_score else None

    return {
        "ticker": ticker,
        "last_price": round(last_price, 4),
        "change_percent": round(change_percent, 4),
        "updated_at": db_updated_at,
        "score": score,
        "ai_probability": ai_prob,
        "ai_target_price": round(last_price * 1.15, 2) if last_price else 0,
        "ai_stop_price": round(last_price * 0.95, 2) if last_price else 0,
        "history": history,
    }


@router.get("/api/stock/{ticker}/verify")
def verify_stock_detail(ticker: str, refresh_db: bool = False):
    db_score = get_latest_score_for_ticker(ticker)
    if not db_score:
        raise HTTPException(status_code=404, detail="Stock score not found in DB")

    realtime_df = fetch_stock_data(ticker, days=30, force_download=True)
    if realtime_df.empty:
        raise HTTPException(status_code=404, detail="Unable to fetch realtime stock data")

    realtime_last = float(realtime_df.iloc[-1].get("close", 0) or 0)
    realtime_change = 0.0
    if len(realtime_df) > 1 and float(realtime_df.iloc[-2].get("close", 0) or 0) != 0:
        prev_close = float(realtime_df.iloc[-2].get("close", 0) or 0)
        realtime_change = ((realtime_last - prev_close) / prev_close) * 100

    db_last = float(db_score.get("last_price", 0) or 0)
    db_change = float(db_score.get("change_percent", 0) or 0)

    last_price_diff_pct = abs((db_last - realtime_last) / realtime_last * 100) if realtime_last else 0
    change_diff_abs = abs(db_change - realtime_change)

    tolerance_percent = 0.5
    within_tolerance = last_price_diff_pct <= tolerance_percent and change_diff_abs <= tolerance_percent

    if refresh_db:
        model_version = db_score.get("model_version")
        refresh_score_payload = {
            "total_score": db_score.get("total_score", 0),
            "trend_score": db_score.get("trend_score", 0),
            "momentum_score": db_score.get("momentum_score", 0),
            "volatility_score": db_score.get("volatility_score", 0),
            "last_price": realtime_last,
            "change_percent": realtime_change,
        }
        save_score_to_db(
            ticker,
            refresh_score_payload,
            ai_prob=db_score.get("ai_probability", 0),
            model_version=model_version,
        )
        db_score = get_latest_score_for_ticker(ticker, model_version=model_version)

    return {
        "ticker": ticker,
        "within_tolerance": within_tolerance,
        "tolerance_percent": tolerance_percent,
        "database": {
            "last_price": db_last,
            "change_percent": db_change,
            "updated_at": db_score.get("updated_at") if db_score else None,
            "model_version": db_score.get("model_version") if db_score else None,
        },
        "realtime": {
            "last_price": round(realtime_last, 4),
            "change_percent": round(realtime_change, 4),
        },
        "diff": {
            "last_price_pct": round(last_price_diff_pct, 4),
            "change_percent_abs": round(change_diff_abs, 4),
        },
    }


@router.get("/api/backtest")
def run_backtest_simulation(days: int = 30, version: Optional[str] = None):
    try:
        return run_time_machine(days_ago=days, limit=100, version=version)
    except Exception as e:
        logger.error("Backtest API Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/smart_scan")
def smart_scan(criteria: list[str] = []):
    candidates = get_top_scores_from_db(limit=100, sort_by="score")
    all_stocks = get_all_tw_stocks()
    name_map = {s["code"]: s["name"] for s in all_stocks}

    results = []

    for c in candidates:
        ticker = c["ticker"]
        try:
            cached_indicators = load_indicators_from_db(ticker)

            if cached_indicators:
                df = load_from_db(ticker)
                if df.empty or len(df) < 60:
                    continue
                if len(df) > 300:
                    df = df.tail(300).copy()

                df = compute_all_indicators(df)

                if not isinstance(c, dict):
                    continue

                ai_prob = c.get("ai_probability", 0)
                if check_smart_conditions(df, ai_prob, criteria):
                    results.append(
                        {
                            "ticker": ticker,
                            "name": name_map.get(ticker, ticker),
                            "ai_probability": ai_prob,
                            "model_version": c.get("model_version", "legacy"),
                            "last_sync": c.get("last_sync"),
                            "score": c,
                            "price": c.get("last_price", 0),
                            "ai_target_price": round(c.get("last_price", 0) * 1.15, 2),
                            "ai_stop_price": round(c.get("last_price", 0) * 0.95, 2),
                            "matches": criteria,
                        }
                    )
        except Exception:
            continue

    return results


@router.get("/api/health")
def health_check():
    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "db": "disconnected",
        "model_version": get_model_version(),
        "concurrency_workers": config.CONCURRENCY_WORKERS,
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


@router.get("/api/v4/sniper/candidates")
def get_v4_candidates(limit: int = 50, sort: str = "score", version: Optional[str] = None):
    try:
        if sort not in {"score", "ai"}:
            raise HTTPException(status_code=422, detail="sort must be one of: score, ai")

        cache_version = get_sync_status_snapshot().get("sync_epoch", 0)
        cache_key = f"v4_candidates:limit={limit}:sort={sort}:version={version or 'latest'}:sync={cache_version}"
        cached = _read_api_cache(cache_key)
        if cached is not None:
            return cached

        start_ts = time.time()
        raw_candidates = get_top_scores_from_db(limit=limit * 2, sort_by=sort, version=version)
        indicators_map = load_indicators_for_tickers([c["ticker"] for c in raw_candidates])

        results = []
        fallback_errors = 0
        for c in raw_candidates:
            ticker = c["ticker"]

            if c.get("model_version", "").startswith("v4"):
                cached_ind = indicators_map.get(ticker) or {}
                results.append(
                    {
                        "ticker": ticker,
                        "name": get_stock_name(ticker),
                        "price": round(safe_float(c.get("last_price", 0)), 2),
                        "change_percent": round(safe_float(c.get("change_percent", 0)), 2),
                        "rise_score": round(safe_float(c["total_score"]), 1),
                        "ai_prob": round(safe_float(c.get("ai_probability", 0)) * 100, 1),
                        "trend": round(safe_float(c["trend_score"]), 1),
                        "momentum": round(safe_float(c["momentum_score"]), 1),
                        "volatility": round(safe_float(c["volatility_score"]), 1),
                        "rsi_14": round(safe_float(cached_ind.get("rsi", 50)), 1),
                        "macd_diff": round(
                            safe_float((cached_ind.get("macd") or 0) - (cached_ind.get("macd_signal") or 0)),
                            2,
                        ),
                        "volume_ratio": round(safe_float(cached_ind.get("rel_vol", 1.0)), 2),
                        "updated_at": c.get("updated_at"),
                    }
                )
                if len(results) >= limit:
                    break
                continue

            try:
                from core.indicators_v2 import compute_v4_indicators
                from core.rise_score_v2 import calculate_rise_score_v2

                df = load_from_db(ticker)
                if df.empty or len(df) < 60:
                    continue
                df = compute_v4_indicators(df)
                df = calculate_rise_score_v2(df)
                latest = df.iloc[-1]
                ai_result = predict_prob(df)
                ai_prob = ai_result.get("prob", 0) if isinstance(ai_result, dict) else ai_result

                results.append(
                    {
                        "ticker": ticker,
                        "name": get_stock_name(ticker),
                        "price": safe_float(latest["close"]),
                        "change_percent": safe_float(
                            (latest["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100 if len(df) > 1 else 0
                        ),
                        "rise_score": round(safe_float(latest["total_score_v2"]), 1),
                        "ai_prob": round(safe_float(ai_prob) * 100, 1),
                        "trend": round(safe_float(latest["trend_score_v2"]), 1),
                        "momentum": round(safe_float(latest["momentum_score_v2"]), 1),
                        "volatility": round(safe_float(latest["volatility_score_v2"]), 1),
                        "rsi_14": round(safe_float(latest.get("rsi", 50)), 1),
                        "macd_diff": round(safe_float(latest.get("macd_hist", 0)), 2),
                        "volume_ratio": round(safe_float(latest.get("rel_vol", 1.0)), 2),
                        "updated_at": c.get("updated_at"),
                    }
                )
            except Exception as e:
                fallback_errors += 1
                if fallback_errors <= 10:
                    logger.warning("Fallback candidate recompute failed", extra={"ticker": ticker, "error": str(e)})
                continue
            if len(results) >= limit:
                break

        elapsed_ms = round((time.time() - start_ts) * 1000, 2)
        logger.info(
            "Built v4 candidates payload",
            extra={
                "requested_limit": limit,
                "selected": len(results),
                "raw_count": len(raw_candidates),
                "elapsed_ms": elapsed_ms,
            },
        )
        _write_api_cache(cache_key, results)
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API ERROR: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v4/stock/{ticker}")
def get_v4_stock_detail(ticker: str):
    cache_version = get_sync_status_snapshot().get("sync_epoch", 0)
    cache_key = f"v4_stock_detail:{ticker}:sync={cache_version}"
    cached = _read_api_cache(cache_key)
    if cached is not None:
        return cached

    db_score = get_latest_score_for_ticker(ticker)
    cached_indicators = load_indicators_from_db(ticker) or {}

    db_updated_at = _parse_db_datetime(db_score.get("updated_at")) if db_score else None
    if db_score and db_updated_at and datetime.now() - db_updated_at < timedelta(hours=6):
        price = safe_float(db_score.get("last_price", 0))
        ai_prob = safe_float(db_score.get("ai_probability", 0))
        squeeze_flag = _to_bool(cached_indicators.get("is_squeeze"))
        golden_cross_flag = _to_bool(cached_indicators.get("kd_cross_flag"))
        rel_vol = safe_float(cached_indicators.get("rel_vol", 1.0))
        volume_spike_flag = bool(rel_vol > 1.5)

        analyst_text = []
        if squeeze_flag:
            analyst_text.append("Squeeze Alert: Low volatility detected, expecting a major move.")
        if volume_spike_flag:
            analyst_text.append("Volume Spike: Heavy trading activity detected.")

        response = {
            "ticker": ticker,
            "name": get_stock_name(ticker),
            "price": price,
            "updated_at": db_score.get("updated_at"),
            "rise_score_breakdown": {
                "total": round(safe_float(db_score.get("total_score", 0)), 1),
                "trend": round(safe_float(db_score.get("trend_score", 0)), 1),
                "momentum": round(safe_float(db_score.get("momentum_score", 0)), 1),
                "volatility": round(safe_float(db_score.get("volatility_score", 0)), 1),
            },
            "ai_probability": round(safe_float(ai_prob) * 100, 1),
            "analyst_summary": " ".join(analyst_text) if analyst_text else "Market is neutral. Watch for setup signals.",
            "signals": {
                "squeeze": squeeze_flag,
                "golden_cross": golden_cross_flag,
                "volume_spike": volume_spike_flag,
            },
        }
        _write_api_cache(cache_key, response)
        return response

    from core.indicators_v2 import compute_v4_indicators
    from core.rise_score_v2 import calculate_rise_score_v2

    df = load_from_db(ticker)
    if df.empty:
        df = fetch_stock_data(ticker)
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock not found")

    df = compute_v4_indicators(df)
    df = calculate_rise_score_v2(df)
    latest = df.iloc[-1]

    ai_result = predict_prob(df)
    ai_prob = 0.0
    if isinstance(ai_result, dict):
        ai_prob = ai_result.get("prob", 0)
    elif isinstance(ai_result, float):
        ai_prob = ai_result

    squeeze_flag = _to_bool(cached_indicators.get("is_squeeze")) if cached_indicators else _to_bool(latest.get("is_squeeze", False))
    golden_cross_flag = (
        _to_bool(cached_indicators.get("kd_cross_flag")) if cached_indicators else _to_bool(latest.get("kd_cross_flag", False))
    )
    rel_vol = safe_float(cached_indicators.get("rel_vol")) if cached_indicators else safe_float(latest.get("rel_vol", 1.0))
    volume_spike_flag = bool(rel_vol > 1.5)

    analyst_text = []
    if latest["trend_alignment"] == 1:
        analyst_text.append("Strong Uptrend: Price is consistently above SMA20 & SMA60.")
    elif latest["sma20_slope"] > 0:
        analyst_text.append("Recovering: Price is building momentum above SMA20.")

    if 40 <= latest["rsi"] <= 70:
        analyst_text.append("Momentum: RSI is in the bullish zone (40-70).")
    elif latest["rsi"] > 80:
        analyst_text.append("Overheated: RSI indicates overbought territory.")

    if squeeze_flag:
        analyst_text.append("Squeeze Alert: Low volatility detected, expecting a major move.")
    elif volume_spike_flag:
        analyst_text.append("Volume Spike: Heavy trading activity detected.")

    response = {
        "ticker": ticker,
        "name": get_stock_name(ticker),
        "price": safe_float(latest["close"]),
        "updated_at": db_score.get("updated_at") if db_score else None,
        "rise_score_breakdown": {
            "total": round(safe_float(latest["total_score_v2"]), 1),
            "trend": round(safe_float(latest["trend_score_v2"]), 1),
            "momentum": round(safe_float(latest["momentum_score_v2"]), 1),
            "volatility": round(safe_float(latest["volatility_score_v2"]), 1),
        },
        "ai_probability": round(safe_float(ai_prob) * 100, 1),
        "analyst_summary": " ".join(analyst_text) if analyst_text else "Market is neutral. Watch for setup signals.",
        "signals": {
            "squeeze": squeeze_flag,
            "golden_cross": golden_cross_flag,
            "volume_spike": volume_spike_flag,
        },
    }
    _write_api_cache(cache_key, response)
    return response


@router.get("/api/v4/meta")
def get_v4_meta(tickers: str = Query(..., min_length=1, description="Comma-separated ticker list")):
    raw = [item.strip() for item in tickers.split(",")]
    requested_pairs: list[tuple[str, str]] = []
    normalized = []
    seen: set[str] = set()
    for ticker in raw:
        if not ticker:
            continue
        normalized_ticker = standardize_ticker(ticker.upper())
        requested_pairs.append((ticker, normalized_ticker))
        if normalized_ticker in seen:
            continue
        seen.add(normalized_ticker)
        normalized.append(normalized_ticker)

    if not requested_pairs:
        raise HTTPException(status_code=422, detail="At least one ticker is required")
    if len(normalized) > 100:
        raise HTTPException(status_code=422, detail="Maximum 100 tickers per request")

    indicators_map = load_indicators_for_tickers(normalized)
    latest_scores = _load_latest_scores_for_tickers(normalized)

    data: dict[str, dict[str, Any]] = {}
    for requested_ticker, normalized_ticker in requested_pairs:
        score = latest_scores.get(normalized_ticker, {})
        indicators = indicators_map.get(normalized_ticker, {})

        macd = safe_float(indicators.get("macd", 0))
        macd_signal = safe_float(indicators.get("macd_signal", 0))
        rel_vol = safe_float(indicators.get("rel_vol", 1.0))
        ai_prob = safe_float(score.get("ai_probability", 0))

        data[requested_ticker] = {
            "total_score": safe_float(score.get("total_score", 0)),
            "trend_score": safe_float(score.get("trend_score", 0)),
            "momentum_score": safe_float(score.get("momentum_score", 0)),
            "volatility_score": safe_float(score.get("volatility_score", 0)),
            "last_price": safe_float(score.get("last_price", 0)),
            "change_percent": safe_float(score.get("change_percent", 0)),
            "ai_prob": ai_prob,
            "signals": {
                "squeeze": _to_bool(indicators.get("is_squeeze")),
                "golden_cross": _to_bool(indicators.get("kd_cross_flag")),
                "volume_spike": bool(rel_vol > 1.5),
                "rsi": safe_float(indicators.get("rsi", 50)),
                "macd_diff": safe_float(macd - macd_signal),
                "rel_vol": rel_vol,
            },
            "updated_at": score.get("updated_at") or indicators.get("updated_at"),
            "model_version": score.get("model_version") or indicators.get("model_version") or get_model_version(),
            "name": get_stock_name(normalized_ticker),
        }

    return {"data": data}
