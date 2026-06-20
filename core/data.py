import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import os
import time
import json
try:
    import twstock
except Exception:  # optional dependency used only for ticker universe refresh
    twstock = None
try:
    from core import universe_source as _universe_source
except Exception:  # keep data layer importable even if live-source deps are missing
    _universe_source = None
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
from threading import Lock
from core import config
from core.utils import safe_float
from core.logger import setup_logger

logger = setup_logger(__name__)

_DB_INIT_LOCK = Lock()
_DB_READY = False
_DB_READY_PATH = None

_ticker_suffix_map = {}
_ticker_suffix_lock = Lock()

def get_ticker_suffix(ticker: str) -> str:
    """Returns '.TWO' for TPEX/OTC stocks, '.TW' for TWSE/Listed stocks."""
    code = standardize_ticker(ticker)
    import re
    if not re.match(r'^\d+$', code):
        return ""
    global _ticker_suffix_map
    with _ticker_suffix_lock:
        if not _ticker_suffix_map and twstock is not None:
            try:
                _ticker_suffix_map = {
                    c: (".TWO" if info.market == '上櫃' else ".TW")
                    for c, info in twstock.codes.items()
                    if info.type == '股票'
                }
            except Exception:
                pass
        return _ticker_suffix_map.get(code, ".TW")



def _create_db_connection():
    conn = sqlite3.connect(config.DB_PATH, timeout=config.DB_TIMEOUT)
    conn.row_factory = sqlite3.Row  # Return dict-like rows
    return conn

def ensure_db_initialized():
    """Initialize DB schema/migrations once per process per DB path before usage."""
    global _DB_READY, _DB_READY_PATH
    db_path = config.DB_PATH

    if _DB_READY and _DB_READY_PATH == db_path:
        return

    with _DB_INIT_LOCK:
        db_path = config.DB_PATH
        if _DB_READY and _DB_READY_PATH == db_path:
            return
        init_db()
        _DB_READY = True
        _DB_READY_PATH = db_path

def get_db_connection():
    ensure_db_initialized()
    return _create_db_connection()

def standardize_ticker(ticker: str) -> str:
    """Standardizes Taiwan stock tickers to numeric codes (e.g., 2454.TW -> 2454)."""
    if not ticker: return ticker
    # Strip common Taiwan suffixes
    for suffix in ['.TW', '.TWO']:
        if ticker.upper().endswith(suffix):
            return ticker[:-len(suffix)]
    return ticker

def init_db():
    conn = _create_db_connection()
    cursor = conn.cursor()
    
    # Enable Write-Ahead Logging for concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")

    # Ensure table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_history (
            ticker TEXT,
            date DATE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')

    # Create indexes after table creation
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_history (ticker, date)")

    # Create scores table for fast ranking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_scores (
            ticker TEXT,
            total_score REAL,
            trend_score REAL,
            momentum_score REAL,
            volatility_score REAL,
            last_price REAL,
            change_percent REAL,
            ai_probability REAL,
            model_version TEXT,
            updated_at TIMESTAMP,
            PRIMARY KEY (ticker, model_version)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_version ON stock_scores (model_version)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_updated ON stock_scores (updated_at DESC)')
    
    # Create indicators table for caching computation results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_indicators (
            ticker TEXT PRIMARY KEY,
            rsi REAL,
            macd REAL,
            macd_signal REAL,
            ema_20 REAL,
            ema_50 REAL,
            sma_20 REAL,
            sma_60 REAL,
            k_val REAL,
            d_val REAL,
            atr REAL,
            bb_width REAL,
            rel_vol REAL,
            is_squeeze INTEGER,
            kd_cross_flag INTEGER,
            model_version TEXT,
            updated_at TIMESTAMP
        )
    ''')
    
    # Migration: Check if columns exist
    try:
        cursor.execute("SELECT ai_probability FROM stock_scores LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE stock_scores ADD COLUMN ai_probability REAL")
        
    try:
        cursor.execute("SELECT model_version FROM stock_scores LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating DB: Adding model_version to stock_scores")
        cursor.execute("ALTER TABLE stock_scores ADD COLUMN model_version TEXT")

    try:
        cursor.execute("SELECT model_version FROM stock_indicators LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating DB: Adding model_version to stock_indicators")
        cursor.execute("ALTER TABLE stock_indicators ADD COLUMN model_version TEXT")

    try:
        cursor.execute("SELECT bb_width FROM stock_indicators LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating DB: Adding bb_width to stock_indicators")
        cursor.execute("ALTER TABLE stock_indicators ADD COLUMN bb_width REAL")

    try:
        cursor.execute("SELECT rel_vol FROM stock_indicators LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating DB: Adding rel_vol to stock_indicators")
        cursor.execute("ALTER TABLE stock_indicators ADD COLUMN rel_vol REAL")

    try:
        cursor.execute("SELECT is_squeeze FROM stock_indicators LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating DB: Adding is_squeeze to stock_indicators")
        cursor.execute("ALTER TABLE stock_indicators ADD COLUMN is_squeeze INTEGER")

    try:
        cursor.execute("SELECT kd_cross_flag FROM stock_indicators LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating DB: Adding kd_cross_flag to stock_indicators")
        cursor.execute("ALTER TABLE stock_indicators ADD COLUMN kd_cross_flag INTEGER")
        
    conn.commit()
    conn.close()

def save_indicators_to_db(ticker, df, **kwargs):
    """Saves the last row of indicators to DB for fast scanning."""
    if df.empty: return
    last = df.iloc[-1]
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO stock_indicators (
                ticker, rsi, macd, macd_signal, ema_20, ema_50, sma_20, sma_60, k_val, d_val, atr, bb_width, rel_vol, is_squeeze, kd_cross_flag, model_version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker, 
            safe_float(last.get('rsi')), safe_float(last.get('macd')), safe_float(last.get('macd_signal')),
            safe_float(last.get('ema_20')), safe_float(last.get('ema_50')),
            safe_float(last.get('sma_20')), safe_float(last.get('sma_60')),
            safe_float(last.get('k')), safe_float(last.get('d')),
            safe_float(last.get('atr')),
            safe_float(last.get('bb_width')),
            safe_float(last.get('rel_vol')),
            1 if bool(last.get('is_squeeze', False)) else 0,
            1 if bool(last.get('kd_cross_flag', False)) else 0,
            kwargs.get('model_version'),
            datetime.now()
        ))
        conn.commit()
    except Exception as e:
        logger.error("Error saving indicators", extra={"ticker": ticker, "error": str(e)})
    finally:
        conn.close()

def load_indicators_from_db(ticker):
    """Loads cached indicators for a specific ticker."""
    conn = get_db_connection()
    query = 'SELECT * FROM stock_indicators WHERE ticker = ?'
    try:
        df = pd.read_sql(query, conn, params=(ticker,))
        if not df.empty:
            record = df.to_dict('records')[0]
            # Sanitize for JSON
            for k, v in record.items():
                if pd.isna(v): record[k] = None
            return record
        return None
    except Exception as e:
        logger.warning("Failed to load indicator cache", extra={"ticker": ticker, "error": str(e)})
        return None
    finally:
        conn.close()


def load_indicators_for_tickers(tickers: List[str], chunk_size: int = 200) -> Dict[str, Dict]:
    """Load cached indicators for multiple tickers in batches.

    Uses chunked ``IN`` queries to avoid per-ticker DB round-trips on list endpoints.
    """
    if not tickers:
        return {}

    conn = get_db_connection()
    results: Dict[str, Dict] = {}
    try:
        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            query = f"SELECT * FROM stock_indicators WHERE ticker IN ({placeholders})"
            df = pd.read_sql(query, conn, params=chunk)
            if df.empty:
                continue
            for record in df.to_dict('records'):
                for k, v in record.items():
                    if pd.isna(v):
                        record[k] = None
                ticker = record.get("ticker")
                if ticker:
                    results[ticker] = record
        return results
    except Exception as e:
        logger.warning("Failed to load batched indicator cache", extra={"count": len(tickers), "error": str(e)})
        return {}
    finally:
        conn.close()

# Manual TTL Cache for TW Stocks
_tw_stocks_cache = {
    "data": None,
    "last_updated": 0,
    "name_map": None
}
_tw_stocks_cache_lock = Lock()

def _live_universe():
    """Fetch the universe from authoritative live TWSE/TPEX sources.

    Returns [] on any failure (network, parse, missing optional deps) so callers
    fall back to twstock / file cache. Never raises.
    """
    if _universe_source is None:
        return []
    try:
        return _universe_source.build_universe(twstock_module=twstock)
    except Exception as e:
        logger.warning("Live universe fetch failed; will fall back", extra={"error": str(e)})
        return []


def _twstock_universe():
    """Build the universe from the bundled twstock static list (offline fallback).

    Includes both 股票 and ETF across 上市/上櫃, tagged with market + kind.
    """
    stocks = []
    if twstock is None:
        return stocks
    try:
        for code, info in twstock.codes.items():
            if info.type in ('股票', 'ETF') and info.market in ('上市', '上櫃'):
                stocks.append({
                    "code": code,
                    "name": info.name,
                    "market": info.market,
                    "kind": "ETF" if info.type == 'ETF' else "股票",
                })
    except Exception as e:
        logger.warning("twstock universe build failed", extra={"error": str(e)})
    return stocks


def _normalize_loaded(stocks):
    """Ensure every entry has code/name/market/kind (back-compat for legacy caches)."""
    normalized = []
    for s in stocks or []:
        raw_code = s.get("code")
        if raw_code is None:
            continue
        code = str(raw_code).strip()
        if not code or code.lower() == "none":  # drop corrupted/phantom cache rows
            continue
        kind = s.get("kind")
        if not kind:
            if _universe_source is not None:
                kind = _universe_source.classify_kind(code, s.get("name"), twstock)
            else:
                kind = "ETF" if code.startswith("00") else "股票"
        normalized.append({
            "code": code,
            "name": str(s.get("name", "") or code).strip(),
            "market": s.get("market") or "unknown",
            "kind": kind,
        })
    return normalized


def _set_universe_cache(stocks, now):
    with _tw_stocks_cache_lock:
        _tw_stocks_cache["data"] = stocks
        _tw_stocks_cache["last_updated"] = now
        _tw_stocks_cache["name_map"] = {s['code']: s['name'] for s in stocks}


def _write_universe_file(stocks):
    if not stocks:  # never overwrite a good cache with an empty result
        return
    try:
        with open(config.STOCK_LIST_CACHE, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Failed to write stock list file cache", extra={"error": str(e)})


def get_all_tw_stocks():
    """Return the full 上市 (TWSE) + 上櫃 (TPEX) universe as {code,name,market,kind}.

    Sourcing precedence: in-memory cache → fresh file cache → live TWSE/TPEX →
    twstock static fallback → any existing/stale cache. ETFs are included. A failed
    refresh never blanks out a previously good list. Thread-safe; caches 1h in
    memory and 24h on disk.
    """
    now = time.time()

    # 1. Memory cache
    with _tw_stocks_cache_lock:
        if _tw_stocks_cache["data"] and (now - _tw_stocks_cache["last_updated"] < config.CACHE_DURATION):
            return _tw_stocks_cache["data"]

    # 2. Fresh file cache (24h TTL)
    if os.path.exists(config.STOCK_LIST_CACHE):
        try:
            mtime = os.path.getmtime(config.STOCK_LIST_CACHE)
            if now - mtime < 86400:
                with open(config.STOCK_LIST_CACHE, 'r', encoding='utf-8') as f:
                    stocks = _normalize_loaded(json.load(f))
                if stocks:
                    _set_universe_cache(stocks, now)
                    return stocks
        except Exception as e:
            logger.warning("Failed to read stock list file cache", extra={"error": str(e)})

    # 3. Live authoritative source, then 4. twstock fallback
    stocks = _normalize_loaded(_live_universe())
    if not stocks:
        stocks = _twstock_universe()

    # 5. Last resort: keep any existing/stale data instead of returning empty
    if not stocks:
        with _tw_stocks_cache_lock:
            existing = _tw_stocks_cache.get("data") or []
        if not existing and os.path.exists(config.STOCK_LIST_CACHE):
            try:
                with open(config.STOCK_LIST_CACHE, 'r', encoding='utf-8') as f:
                    existing = _normalize_loaded(json.load(f))
            except Exception:
                existing = []
        if not existing:
            logger.warning("No universe source available; returning empty list.")
        _set_universe_cache(existing, now)
        return existing

    _set_universe_cache(stocks, now)
    _write_universe_file(stocks)
    return stocks


def refresh_stock_universe(force: bool = False):
    """Force a live re-fetch of the universe and update caches.

    Returns the refreshed list. On a failed/empty live fetch, falls back to
    twstock; if that is also empty, the existing cache is preserved (not blanked).
    When ``force`` is False this is cache-first (== get_all_tw_stocks).
    """
    if not force:
        return get_all_tw_stocks()

    now = time.time()
    stocks = _normalize_loaded(_live_universe())
    if not stocks:
        stocks = _twstock_universe()
    if not stocks:
        logger.warning("refresh_stock_universe: live + twstock both empty; keeping existing cache.")
        return get_all_tw_stocks()
    _set_universe_cache(stocks, now)
    _write_universe_file(stocks)
    return stocks


def report_history_coverage(tickers=None, chunk_size: int = 500):
    """Report how many universe tickers have enough price history for predict/train.

    Returns ``{universe, with_predict_rows, with_train_rows, short}``. ``short`` lists
    tickers below MIN_PREDICT_ROWS — the backfill candidates. Counts are surfaced,
    never silent.
    """
    if tickers is None:
        tickers = [s["code"] for s in get_all_tw_stocks()]
    tickers = [standardize_ticker(t) for t in tickers]

    counts = {}
    if tickers:
        conn = get_db_connection()
        try:
            for i in range(0, len(tickers), chunk_size):
                chunk = tickers[i:i + chunk_size]
                placeholders = ",".join(["?"] * len(chunk))
                query = (
                    f"SELECT ticker, COUNT(*) AS n FROM stock_history "
                    f"WHERE ticker IN ({placeholders}) GROUP BY ticker"
                )
                for row in conn.execute(query, chunk).fetchall():
                    counts[row["ticker"]] = row["n"]
        finally:
            conn.close()

    min_predict = config.MIN_PREDICT_ROWS
    min_train = config.MIN_TRAIN_ROWS
    with_predict = sum(1 for t in tickers if counts.get(t, 0) >= min_predict)
    with_train = sum(1 for t in tickers if counts.get(t, 0) >= min_train)
    short = [t for t in tickers if counts.get(t, 0) < min_predict]
    return {
        "universe": len(tickers),
        "with_predict_rows": with_predict,
        "with_train_rows": with_train,
        "short": short,
    }


def backfill_history(tickers=None, days: int = 730, limit=None):
    """Fetch missing/short price history for backfill candidates.

    When ``tickers`` is None, derives the short list from ``report_history_coverage``.
    Returns ``{attempted, fetched}``. Reuses the rate-limited ``fetch_stock_data``.
    """
    if tickers is None:
        tickers = report_history_coverage()["short"]
    if limit is not None:
        tickers = tickers[:limit]
    fetched = 0
    for code in tickers:
        df = fetch_stock_data(code, days=days, force_download=True)
        if not df.empty:
            fetched += 1
    return {"attempted": len(tickers), "fetched": fetched}

def get_stock_name(ticker: str) -> Optional[str]:
    """Returns the stock name from cached name map, loading cache when needed."""
    with _tw_stocks_cache_lock:
        has_name_map = bool(_tw_stocks_cache.get("name_map"))
    if not has_name_map:
        get_all_tw_stocks()  # Load cache

    code_only = standardize_ticker(ticker)
    with _tw_stocks_cache_lock:
        name_map = _tw_stocks_cache.get("name_map") or {}
    return name_map.get(code_only)

def save_to_db(ticker, df):
    if df.empty: return 0
    
    conn = get_db_connection()
    try:
        df = df.reset_index() if 'date' not in df.columns else df
        if not pd.api.types.is_string_dtype(df['date']):
             df['date'] = df['date'].dt.strftime('%Y-%m-%d')
             
        # Records
        records = df[['date', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')
        # Add standardized ticker to each record
        std_ticker = standardize_ticker(ticker)
        for r in records: r['ticker'] = std_ticker
            
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO stock_history (ticker, date, open, high, low, close, volume)
            VALUES (:ticker, :date, :open, :high, :low, :close, :volume)
        ''', records)
        conn.commit()
        return len(records)
    except Exception as e:
        logger.error("DB error while saving price history", extra={"ticker": ticker, "error": str(e)})
        return 0
    finally:
        conn.close()

def load_from_db(ticker: str, days: int = 730) -> pd.DataFrame:
    ticker = standardize_ticker(ticker)
    conn = get_db_connection()
    
    # Optimization: Filter by date to avoid loading full history
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    query = 'SELECT * FROM stock_history WHERE ticker = ? AND date >= ? ORDER BY date ASC'
    
    try:
        df = pd.read_sql(query, conn, params=(ticker, start_date))
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def fetch_stock_data(ticker: str, days: int = 730, force_download: bool = False) -> pd.DataFrame:
    # 1. Try DB
    if not force_download:
        df = load_from_db(ticker, days)
        if not df.empty:
            last_date = pd.to_datetime(df.iloc[-1]['date'])
            # Consider cache fresh only when DB already has today's market row.
            if last_date.date() >= datetime.now().date():
                return df

    # 2. Fetch from YFinance with Retry Logic (Exponential Backoff)
    clean_code = standardize_ticker(ticker)
    
    if ticker.upper().endswith('.TW') or ticker.upper().endswith('.TWO'):
        suffix = ".TW" if ticker.upper().endswith('.TW') else ".TWO"
    else:
        suffix = get_ticker_suffix(clean_code)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            import random
            time.sleep(random.uniform(0.5, 1.5))
            yf_ticker = f"{clean_code}{suffix}"
            stock = yf.Ticker(yf_ticker)
            df = stock.history(period=f"{days}d", auto_adjust=True)
            
            if df.empty:
                alternative_suffix = ".TWO" if suffix == ".TW" else ".TW"
                yf_ticker = f"{clean_code}{alternative_suffix}"
                stock = yf.Ticker(yf_ticker)
                df = stock.history(period=f"{days}d", auto_adjust=True)
                if not df.empty:
                    suffix = alternative_suffix
                
            if not df.empty:
                df = df.reset_index()
                df.columns = [c.lower() for c in df.columns]
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date').drop_duplicates(subset=['date'], keep='last').reset_index(drop=True)
                save_to_db(ticker, df)
                return df
                
        except Exception as e:
            # Shift suffix defensively for the next retry in case of timeout/network errors
            if suffix == ".TW":
                suffix = ".TWO"
            elif suffix == ".TWO" and attempt == 0:
                suffix = ".TW"
            wait_time = (2 ** attempt)  # 1s, 2s, 4s
            logger.warning("Fetch error, retrying", extra={"ticker": ticker, "attempt": attempt + 1, "max_retries": max_retries, "wait_seconds": wait_time, "error": str(e)})
            time.sleep(wait_time)
            
    logger.error("Failed to fetch ticker after retries", extra={"ticker": ticker, "max_retries": max_retries})
    return pd.DataFrame()

def save_score_to_db(ticker, score_data, ai_prob=None, model_version=None):
    ticker = standardize_ticker(ticker)
    conn = get_db_connection()
    # v4 compatibility mapping (v2 keys -> v1 columns)
    total = score_data.get('total_score_v2') if 'total_score_v2' in score_data else score_data.get('total_score', 0)
    trend = score_data.get('trend_score_v2') if 'trend_score_v2' in score_data else score_data.get('trend_score', 0)
    momentum = score_data.get('momentum_score_v2') if 'momentum_score_v2' in score_data else score_data.get('momentum_score', 0)
    volatility = score_data.get('volatility_score_v2') if 'volatility_score_v2' in score_data else score_data.get('volatility_score', 0)
    try:
        conn.execute('''
            INSERT OR REPLACE INTO stock_scores (ticker, total_score, trend_score, momentum_score, volatility_score, last_price, change_percent, ai_probability, model_version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker,
            safe_float(total),
            safe_float(trend),
            safe_float(momentum),
            safe_float(volatility),
            safe_float(score_data.get('last_price', 0)),
            safe_float(score_data.get('change_percent', 0)),
            # Preserve NULL when the prediction is unavailable — never store a fake 0.0
            (None if ai_prob is None else safe_float(ai_prob)),
            model_version,
            datetime.now()
        ))
        conn.commit()
    finally:
        conn.close()


def get_latest_score_for_ticker(ticker: str, model_version: Optional[str] = None) -> Optional[Dict]:
    """Load latest score snapshot for a ticker.

    If model_version is omitted, returns the most recently updated row.
    """
    ticker = standardize_ticker(ticker)
    conn = get_db_connection()
    try:
        if model_version:
            row = conn.execute(
                """
                SELECT * FROM stock_scores
                WHERE ticker = ? AND model_version = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (ticker, model_version),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM stock_scores
                WHERE ticker = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()

def get_top_scores_from_db(limit=50, sort_by='score', version=None):
    conn = get_db_connection()

    order_clause = "total_score DESC"
    if sort_by == 'ai':
        order_clause = "ai_probability DESC"

    query = "SELECT *, updated_at AS last_sync FROM stock_scores"
    params = [limit]

    if version:
        query += " WHERE model_version = ?"
        params = [version, limit]
    else:
        # Default to the version that has the most records (most representative)
        query += " WHERE model_version = (SELECT model_version FROM stock_scores GROUP BY model_version ORDER BY count(*) DESC LIMIT 1)"

    query += f" ORDER BY {order_clause} LIMIT ?"

    try:
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    finally:
        conn.close()

def search_stocks_global(query: str):
    """
    Searches for any stock in the database or twstock list by ticker or name.
    """
    q = f"%{query.upper()}%"
    conn = get_db_connection()
    # Search in historical data or scores to see if we have ANY info
    sql = """
        SELECT DISTINCT ticker FROM stock_history
        WHERE ticker LIKE ?
        UNION
        SELECT ticker FROM stock_scores
        WHERE ticker LIKE ?
        LIMIT 10
    """
    try:
        tickers = [row['ticker'] for row in conn.execute(sql, (q, q)).fetchall()]
        results = []
        for t in tickers:
            name = get_stock_name(t)
            results.append({"ticker": t, "name": name or t})
        return results
    finally:
        conn.close()


def load_sparklines_from_db(tickers: List[str], days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
    """Load cached sparkline close-only histories for multiple tickers in a single SQLite query."""
    if not tickers:
        return {}

    conn = get_db_connection()
    # Filter by date to avoid loading full history
    start_date = (datetime.now() - timedelta(days=days + 15)).strftime('%Y-%m-%d')
    placeholders = ",".join(["?"] * len(tickers))
    query = f"""
        SELECT ticker, date, close FROM stock_history
        WHERE ticker IN ({placeholders}) AND date >= ?
        ORDER BY date ASC
    """
    results = {}
    try:
        cursor = conn.cursor()
        rows = cursor.execute(query, tickers + [start_date]).fetchall()
        
        # Group by ticker
        grouped = {}
        for row in rows:
            ticker = row["ticker"]
            if ticker not in grouped:
                grouped[ticker] = []
            date_val = row["date"]
            if hasattr(date_val, "strftime"):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val)[:10]
            grouped[ticker].append({
                "date": date_str,
                "close": round(safe_float(row["close"]), 2)
            })
            
        # Take the tail(days) for each ticker
        for t, points in grouped.items():
            results[t] = points[-days:]
        return results
    except Exception as e:
        logger.warning("Failed to load batched sparklines from DB", extra={"error": str(e)})
        return {}
    finally:
        conn.close()


if __name__ == "__main__":
    ensure_db_initialized()
