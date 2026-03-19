import pandas as pd
from core.logger import setup_logger
from core.data import get_db_connection

logger = setup_logger(__name__)

def get_market_status():
    """
    Derives market insights purely from existing stock_scores.
    No new data sources.
    """
    conn = get_db_connection()
    try:
        # Fetch all scores for the latest model version ONLY
        df = pd.read_sql(
            "SELECT trend_score, momentum_score, ai_probability FROM stock_scores "
            "WHERE model_version = (SELECT model_version FROM stock_scores ORDER BY updated_at DESC LIMIT 1)",
            conn
        )
        
        if df.empty:
            return {
                "bull_ratio": 0,
                "market_temp": 0,
                "ai_sentiment": 0,
                "risk_level": "unknown",
                "total_stocks": 0
            }
            
        total_stocks = len(df)
        
        # 1. Bull/Bear Ratio (Trend Score > 20 out of 40)
        # Assuming Trend Score is roughly 0-40 from V2 logic
        # Let's use > 20 as the threshold for positive trend
        bull_count = len(df[df['trend_score'] > 20])
        bull_ratio = bull_count / total_stocks if total_stocks > 0 else 0
        
        # 2. Market Temperature (Avg Momentum of Top 100)
        # High momentum = Hot
        top_100_momt = df.nlargest(100, 'momentum_score')
        market_temp = top_100_momt['momentum_score'].mean()
        
        # 3. AI Sentiment (Avg Prob of Top 50 AI picks)
        # Are the machines bullish?
        top_50_ai = df.nlargest(50, 'ai_probability')
        ai_sentiment = top_50_ai['ai_probability'].mean()
        
        # 4. Risk Level
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
            "total_stocks": total_stocks
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
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save market history: {e}")

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
