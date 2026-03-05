import sqlite3
import os

db_path = 'storage.db'
conn = sqlite3.connect(db_path)
try:
    tickers = ['2330', '2317']
    for ticker in tickers:
        # Update stock_scores with v1 (which backend currently queries)
        conn.execute("""
            INSERT OR REPLACE INTO stock_scores 
            (ticker, total_score, trend_score, momentum_score, volatility_score, last_price, change_percent, ai_probability, model_version, updated_at)
            VALUES (?, 85.5, 38.0, 25.5, 22.0, 580.0, 1.5, 0.72, 'v1', datetime('now'))
        """, (ticker,))
        
        # Update stock_indicators
        conn.execute("""
            INSERT OR REPLACE INTO stock_indicators 
            (ticker, is_squeeze, kd_cross_flag, rel_vol, rsi, macd, macd_signal, model_version, updated_at)
            VALUES (?, 1, 1, 1.8, 62.5, 2.1, 1.5, 'v1', datetime('now'))
        """, (ticker,))

    conn.commit()
    print("Success: Database updated with v1 model data.")
finally:
    conn.close()
