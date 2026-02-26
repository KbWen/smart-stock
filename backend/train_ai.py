import sys
import os
import pandas as pd
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add parent directory to path to find 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from core import config

from core.data import get_db_connection, load_from_db, init_db
from core.indicators_v2 import compute_v4_indicators
from core.ai import train_and_save

# Setup Logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def process_single_stock(ticker: str) -> pd.DataFrame:
    """Helper function to load data and compute indicators for a single stock."""
    df = load_from_db(ticker)
    if df.empty or len(df) < config.MIN_TRAIN_ROWS:
        return pd.DataFrame()
    return compute_v4_indicators(df)

def main():
    start_time = time.perf_counter()
    init_db()  # Ensure tables exist
    logger.info("Loading stock data for AI training...")
    conn = get_db_connection()
    tickers = pd.read_sql("SELECT DISTINCT ticker FROM stock_history", conn)['ticker'].tolist()
    conn.close()
    
    logger.info(f"Found {len(tickers)} stocks. Using {config.TRAINING_WORKERS} workers for parallel processing.")
    
    all_dfs = []
    
    with ProcessPoolExecutor(max_workers=config.TRAINING_WORKERS) as executor:
        future_to_ticker = {executor.submit(process_single_stock, t): t for t in tickers}
        
        for i, future in enumerate(as_completed(future_to_ticker), 1):
            try:
                df = future.result()
                if not df.empty:
                    all_dfs.append(df)
            except Exception as e:
                ticker = future_to_ticker[future]
                logger.error(f"Error processing {ticker}: {e}")
                
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(tickers)} stocks...")
    
    load_time = time.perf_counter() - start_time
    logger.info(f"Total stocks with sufficient data: {len(all_dfs)} (Prepared in {load_time:.2f}s)")
    
    train_and_save(all_dfs)
    
    total_time = time.perf_counter() - start_time
    logger.info(f"Training pipeline complete in {total_time:.2f}s!")

if __name__ == "__main__":
    main()
