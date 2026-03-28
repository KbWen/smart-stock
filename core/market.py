from core.logger import setup_logger
from core.data import get_db_connection

logger = setup_logger(__name__)

def get_market_status():
    """
    Derives market insights purely from existing stock_scores.
    No new data sources.

    Uses SQL aggregates instead of loading the full table into Pandas, and
    selects the model_version with the most records (same strategy as
    get_top_scores_from_db) to keep market status and candidate list in sync.
    """
    conn = get_db_connection()
    try:
        # Use the most-represented model version so market status aligns with
        # the candidate list (which also picks by record count, not recency).
        mv_row = conn.execute(
            "SELECT model_version FROM stock_scores "
            "GROUP BY model_version ORDER BY count(*) DESC LIMIT 1"
        ).fetchone()
        if not mv_row:
            return {
                "bull_ratio": 0,
                "market_temp": 0,
                "ai_sentiment": 0,
                "risk_level": "unknown",
                "total_stocks": 0,
            }
        model_version = mv_row[0]

        # Aggregate metrics in SQL — avoids loading ~1000 rows into Python.
        agg = conn.execute(
            """
            SELECT
                COUNT(*)                                    AS total_stocks,
                SUM(CASE WHEN trend_score > 20 THEN 1 ELSE 0 END) AS bull_count,
                (SELECT AVG(momentum_score)
                 FROM (SELECT momentum_score FROM stock_scores
                       WHERE model_version = ?
                       ORDER BY momentum_score DESC LIMIT 100))  AS market_temp,
                (SELECT AVG(ai_probability)
                 FROM (SELECT ai_probability FROM stock_scores
                       WHERE model_version = ?
                       ORDER BY ai_probability DESC LIMIT 50))   AS ai_sentiment
            FROM stock_scores
            WHERE model_version = ?
            """,
            (model_version, model_version, model_version),
        ).fetchone()

        total_stocks = agg[0] or 0
        if total_stocks == 0:
            return {
                "bull_ratio": 0,
                "market_temp": 0,
                "ai_sentiment": 0,
                "risk_level": "unknown",
                "total_stocks": 0,
            }

        bull_count = agg[1] or 0
        market_temp = agg[2] or 0.0
        ai_sentiment = agg[3] or 0.0
        bull_ratio = bull_count / total_stocks

        risk_level = "NEUTRAL"
        if bull_ratio < 0.30:
            risk_level = "HIGH RISK (BEAR)"
        elif bull_ratio > 0.60:
            risk_level = "LOW RISK (BULL)"

        return {
            "bull_ratio": round(bull_ratio * 100, 1),
            "market_temp": round(market_temp, 1),
            "ai_sentiment": round(ai_sentiment * 100, 1),
            "risk_level": risk_level,
            "total_stocks": total_stocks,
        }

    finally:
        conn.close()

def save_market_history(status):
    """
    Saves a snapshot of market status to market_history.json for charting.
    Keeps last 30 entries.
    """
    import os
    import json
    from datetime import datetime
    from core import config
    
    history_path = os.path.join(config.BASE_DIR, "market_history.json")
    history = []
    
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
        except Exception:
            history = []
            
    # Append current
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "bull_ratio": status.get("bull_ratio", 0),
        "market_temp": status.get("market_temp", 0),
        "ai_sentiment": status.get("ai_sentiment", 0)
    }
    
    # Check if we already have today's entry (to avoid duplicates on same-day runs)
    if history and history[-1]["timestamp"] == entry["timestamp"]:
        history[-1] = entry # Update
    else:
        history.append(entry)
        
    # Rotate (keep 30)
    if len(history) > 30:
        history = history[-30:]
        
    try:
        import tempfile
        dir_name = os.path.dirname(history_path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(history, f, indent=2)
            os.replace(tmp_path, history_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        logger.error("Failed to save market history: %s", e)

def get_market_history():
    """Returns the market history from JSON."""
    import os
    import json
    from core import config
    history_path = os.path.join(config.BASE_DIR, "market_history.json")
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []
