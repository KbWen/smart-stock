import sys
import os
import pandas as pd

# Add parent directory to path to find 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

from core import config
from core.data import get_db_connection, save_score_to_db, load_from_db
from core.analysis import generate_analysis_report
from core.ai import predict_prob, get_model_version

# Setup Logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

RECALC_LOOKBACK_DAYS = 420


def _load_target_tickers(incremental: bool, stale_hours: int, model_version: str) -> list[str]:
    conn = get_db_connection()
    try:
        all_tickers = pd.read_sql("SELECT DISTINCT ticker FROM stock_history", conn)['ticker'].tolist()
        if not incremental:
            return all_tickers

        stale_before = datetime.now() - timedelta(hours=stale_hours)
        stale_df = pd.read_sql(
            """
            SELECT h.ticker
            FROM stock_history h
            LEFT JOIN stock_scores s
              ON h.ticker = s.ticker AND s.model_version = ?
            GROUP BY h.ticker
            HAVING s.updated_at IS NULL
                OR s.updated_at < ?
                OR MAX(h.date) > DATE(s.updated_at)
            """,
            conn,
            params=(model_version, stale_before),
        )
        stale_tickers = stale_df['ticker'].tolist()
        return stale_tickers
    finally:
        conn.close()


def recalculate_all(incremental: bool = True, stale_hours: int = 6):
    logger.info("=" * 60)
    logger.info("Full Score & AI Recalculation")
    logger.info("=" * 60)

    from core.rise_score_v2 import calculate_rise_score_v2
    from core.indicators_v2 import compute_v4_indicators

    # Ensure model is loaded and version is set correctly
    current_model_version = get_model_version()
    is_v4 = current_model_version.startswith("v4") or current_model_version == "unknown"

    # If still unknown, try a dummy prediction to force load
    if current_model_version == "unknown":
        predict_prob(pd.DataFrame())
        current_model_version = get_model_version()
        is_v4 = current_model_version.startswith("v4")

    tickers = _load_target_tickers(
        incremental=incremental,
        stale_hours=stale_hours,
        model_version=current_model_version,
    )

    logger.info(f"Found {len(tickers)} stocks to recalculate (incremental={incremental}, stale_hours={stale_hours}).")

    lock = threading.Lock()
    sync_status = {"current": 0, "total": len(tickers), "updated": 0, "errors": 0, "skipped": 0}
    ai_cache: dict[tuple[str, str, str], float] = {}

    def process_stock(ticker):
        nonlocal sync_status
        try:
            df = load_from_db(ticker, days=RECALC_LOOKBACK_DAYS)
            if df.empty or len(df) < 60:
                with lock:
                    sync_status["skipped"] += 1
                    sync_status["current"] += 1
                return

            if is_v4:
                df = compute_v4_indicators(df)
                df = calculate_rise_score_v2(df)
                # Prevent NaN propagation to frontend/API payloads.
                df = df.fillna(0)
                last_row = df.iloc[-1]
                score = {
                    'total_score': last_row.get('total_score_v2', 0),
                    'trend_score': last_row.get('trend_score_v2', 0),
                    'momentum_score': last_row.get('momentum_score_v2', 0),
                    'volatility_score': last_row.get('volatility_score_v2', 0),
                    'last_price': last_row.get('close', 0),
                    'change_percent': ((last_row['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100) if len(df) > 1 else 0
                }
            else:
                raise ValueError("V1 Pipeline is deprecated. Please use V4.")

            prev_row = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
            analysis_report = generate_analysis_report(
                df.iloc[-1], prev_row,
                score.get('trend_score', 0),
                score.get('momentum_score', 0),
                score.get('volatility_score', 0)
            )
            score['analysis'] = analysis_report

            cache_key = (ticker, current_model_version, str(df.iloc[-1]['date'])[:10])
            if cache_key in ai_cache:
                ai_prob = ai_cache[cache_key]
            else:
                ai_result = predict_prob(df)
                ai_prob = ai_result.get('prob', 0.0) if isinstance(ai_result, dict) else (ai_result or 0.0)
                ai_cache[cache_key] = ai_prob

            save_score_to_db(ticker, score, ai_prob, model_version=current_model_version)

            with lock:
                sync_status["updated"] += 1
        except Exception as e:
            with lock:
                sync_status["errors"] += 1
            if sync_status["errors"] <= 10:
                logger.error(f"Error {ticker}: {e}")
        finally:
            with lock:
                sync_status["current"] += 1
                if sync_status["current"] % 20 == 0:
                    logger.info(
                        f"Progress: {sync_status['current']}/{sync_status['total']} "
                        f"(Updated: {sync_status['updated']}, Skipped: {sync_status['skipped']})"
                    )

    num_workers = max(1, min(config.CONCURRENCY_WORKERS, len(tickers) or 1))
    logger.info(f"Starting recalculation with {num_workers} workers...")
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        executor.map(process_stock, tickers)

    logger.info("\nRecalculation complete!")
    logger.info(f"  Processed: {sync_status['current']}")
    logger.info(f"  Updated:   {sync_status['updated']}")
    logger.info(f"  Skipped:   {sync_status['skipped']}")
    logger.info(f"  Errors:    {sync_status['errors']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    recalculate_all()
