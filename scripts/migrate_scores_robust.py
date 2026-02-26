import sqlite3
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "storage.db")

def blob_to_float(blob):
    if blob is None:
        return 0.0
    if not isinstance(blob, bytes):
        return float(blob)
    try:
        if len(blob) == 8:
            return float(np.frombuffer(blob, dtype=np.float64)[0])
        elif len(blob) == 4:
            return float(np.frombuffer(blob, dtype=np.float32)[0])
    except Exception:
        pass
    return 0.0

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Migrating stock_scores...")
    rows = cursor.execute("SELECT * FROM stock_scores").fetchall()
    for row in rows:
        ticker = row['ticker']
        mv = row['model_version']
        
        updates = {
            'total_score': blob_to_float(row['total_score']),
            'trend_score': blob_to_float(row['trend_score']),
            'momentum_score': blob_to_float(row['momentum_score']),
            'volatility_score': blob_to_float(row['volatility_score']),
            'last_price': blob_to_float(row['last_price']),
            'change_percent': blob_to_float(row['change_percent']),
            'ai_probability': blob_to_float(row['ai_probability'])
        }
        
        cursor.execute('''
            UPDATE stock_scores 
            SET total_score=?, trend_score=?, momentum_score=?, volatility_score=?, last_price=?, change_percent=?, ai_probability=?
            WHERE ticker=? AND model_version=?
        ''', (
            updates['total_score'], updates['trend_score'], updates['momentum_score'],
            updates['volatility_score'], updates['last_price'], updates['change_percent'],
            updates['ai_probability'], ticker, mv
        ))

    print("Migrating stock_indicators...")
    indicator_rows = cursor.execute("SELECT * FROM stock_indicators").fetchall()
    for row in indicator_rows:
        ticker = row['ticker']
        cols = ['rsi', 'macd', 'macd_signal', 'ema_20', 'ema_50', 'sma_20', 'sma_60', 'k_val', 'd_val', 'atr', 'bb_width']
        update_vals = [blob_to_float(row[c]) for c in cols]
        
        sql = f"UPDATE stock_indicators SET {', '.join([c+'=?' for c in cols])} WHERE ticker=?"
        cursor.execute(sql, (*update_vals, ticker))

    conn.commit()
    conn.close()
    print("Migration completed successfully with numpy decoding.")

if __name__ == "__main__":
    migrate_db()
