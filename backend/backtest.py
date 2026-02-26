import sys
import os
import random
import threading
import pandas as pd
import time
# Add parent dir
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data import get_all_tw_stocks, load_from_db as _load_from_db
from core.ai import predict_prob

from core import config
from core.ai.common import PRED_DAYS, TARGET_GAIN, STOP_LOSS, BACKTEST_AI_THRESHOLD

MODEL_PATH = config.MODEL_PATH
if not os.path.exists(MODEL_PATH):
    print(f"⚠️ WARNING: AI model not found at {MODEL_PATH}")

from typing import Optional

# IMPORTANT: Strategy parameters are centralized in core/config.py → core/ai/common.py.
# DO NOT hardcode target/stop/threshold values here. Any change should go through config.
BACKTEST_HORIZON_DAYS = PRED_DAYS  # Must match training look-ahead window

def _passes_liquidity_filter(df: pd.DataFrame, min_avg_volume: int) -> bool:
    if min_avg_volume <= 0:
        return True
    if df.empty or 'volume' not in df.columns:
        return False
    avg_vol = float(df['volume'].tail(min(20, len(df))).mean() or 0)
    return avg_vol >= float(min_avg_volume)


def run_time_machine(days_ago=30, limit=20, version: Optional[str] = None, candidate_pool_limit: Optional[int] = None):
    """
    Simulates Top Picks from 'days_ago' and calculates their actual return until now.
    Supports specific model version analysis.
    """
    print(f"⏳ Time Machine Started (Version: {version or 'latest'}): Traveling back {days_ago} days...")
    start_time = time.perf_counter()

    if days_ago <= 0:
        return {"error": "days_ago must be > 0"}
    if limit <= 0:
        return {"error": "limit must be > 0"}
    
    # --- FIX LOOK-AHEAD BIAS ---
    # Instead of picking top candidates FROM THE FUTURE, we pick a random sample from the pool.
    all_stocks = get_all_tw_stocks()
    if not all_stocks:
        # Fallback to DB list (but without future sorting bias)
        from core.data import get_db_connection
        conn = get_db_connection()
        tickers = [row[0] for row in conn.execute("SELECT ticker FROM stock_scores").fetchall()]
        all_stocks = [{"code": t} for t in tickers]
        conn.close()

    if not all_stocks:
        return {"error": "Failed to load stock list"}
    
    # We use a random sample to avoid hitting just ETFs at the start of the list.
    random.seed(42) # Deterministic for consistent backtests
    configured_pool_limit = candidate_pool_limit or int(os.getenv("BACKTEST_CANDIDATE_POOL", "300"))
    sample_size = min(len(all_stocks), configured_pool_limit)
    candidates = random.sample(all_stocks, sample_size)

    # We increase the padding to 450 to ensure at least 300+ trading days 
    # are available for indicators (SMA240) even when traveling back 60 days.
    lookback_days = max(days_ago + 450, 730)
    frame_cache = {}
    inflight_loads = {}
    cache_lock = threading.Lock()

    def get_stock_frame(ticker: str) -> pd.DataFrame:
        while True:
            with cache_lock:
                if ticker in frame_cache:
                    return frame_cache[ticker]

                loading_event = inflight_loads.get(ticker)
                if loading_event is None:
                    loading_event = threading.Event()
                    inflight_loads[ticker] = loading_event
                    is_loader = True
                else:
                    is_loader = False

            if is_loader:
                df = pd.DataFrame()
                try:
                    df = _load_from_db(ticker, days=lookback_days)
                finally:
                    with cache_lock:
                        frame_cache[ticker] = df
                        inflight_loads.pop(ticker, None)
                        loading_event.set()
                return df

            loading_event.wait()

    min_avg_volume = int(os.getenv("BACKTEST_MIN_AVG_VOLUME", "0"))
    if min_avg_volume > 0:
        prefiltered = []
        for s in candidates:
            t = s.get("ticker") or s.get("code")
            if not t:
                continue
            df_full = get_stock_frame(t)
            if _passes_liquidity_filter(df_full, min_avg_volume=min_avg_volume):
                prefiltered.append(s)
        candidates = prefiltered
    
    print(f"🔍 Analyzing {len(candidates)} random candidates (No look-ahead bias)...")
    
    from concurrent.futures import ThreadPoolExecutor
    
    def process_stock(stock):
        ticker = stock["ticker"] if "ticker" in stock else stock["code"]
        try:
            # 1. Name Lookup (Improved)
            name = stock.get("name") or ticker
            
            # 2. Fetch/Load Data (bounded window for speed)
            df_full = get_stock_frame(ticker)
            if df_full.empty:
                return None
            
            # 3. Time Machine Slicing
            if len(df_full) <= days_ago:
                return None
                
            entry_idx = len(df_full) - days_ago
            if entry_idx < 0 or entry_idx >= len(df_full):
                return None

            simulated_date = df_full.iloc[entry_idx]['date']
            entry_price = float(df_full.iloc[entry_idx]['close'])
            current_price = float(df_full.iloc[-1]['close'])
            
            # Use data up to entry day for signal generation, and strictly after entry for outcomes.
            df_past = df_full.iloc[:entry_idx + 1].copy()
            df_future = df_full.iloc[entry_idx + 1: entry_idx + 1 + BACKTEST_HORIZON_DAYS].copy()
            
            if df_past.empty:
                return None
                
            # Verify score calculation
            from core.indicators_v2 import compute_v4_indicators
            from core.rise_score_v2 import calculate_rise_score_v2
            df_past = compute_v4_indicators(df_past)
            df_past = calculate_rise_score_v2(df_past)
            
            if 'total_score_v2' not in df_past.columns:
                return None
                
            total_score = float(df_past.iloc[-1]['total_score_v2'])
            
            # AI Probability (with version support)
            ai_result = predict_prob(df_past, version=version)
            ai_prob = ai_result.get('prob', 0.0) if isinstance(ai_result, dict) else (ai_result or 0.0)
            
            # --- STRATEGY FILTER ---
            # Threshold sourced from config.BACKTEST_AI_THRESHOLD (currently {BACKTEST_AI_THRESHOLD})
            if ai_prob < BACKTEST_AI_THRESHOLD: 
                return None
            
            last_observed_close = float(df_future.iloc[-1]['close']) if not df_future.empty else current_price
            roi = (last_observed_close - entry_price) / entry_price if entry_price > 0 else 0.0
            
            # --- SNIPER HIT/MISS ANALYSIS ---
            # Check if price hit +15% (target) before -5% (stop) within the 20-day backtest window
            sniper_result = 'PENDING'
            max_drawdown_pct = 0.0
            max_gain_pct = 0.0
            
            # Default holding days and exit date if no target or stop is hit
            actual_holding_days = max(len(df_future), 0)
            default_exit_row = df_future.iloc[-1] if not df_future.empty else df_full.iloc[-1]
            exit_date_actual = default_exit_row['date'].strftime('%Y-%m-%d') if hasattr(default_exit_row['date'], 'strftime') else str(default_exit_row['date'])
            locked_roi = roi # Default to final day ROI
            
            for i in range(len(df_future)):
                row = df_future.iloc[i]
                day_high_pct = (row['high'] - entry_price) / entry_price
                day_low_pct = (row['low'] - entry_price) / entry_price
                day_close_pct = (row['close'] - entry_price) / entry_price

                max_gain_pct = max(max_gain_pct, day_high_pct)
                max_drawdown_pct = min(max_drawdown_pct, day_low_pct)

                # Conservative same-day ordering: stop has precedence over target.
                if day_low_pct <= -STOP_LOSS:  # Hit stop loss
                    sniper_result = 'STOP'
                    locked_roi = day_low_pct
                    actual_holding_days = i + 1
                    exit_date_actual = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                    break
                if day_high_pct >= TARGET_GAIN:  # Hit target
                    sniper_result = 'HIT'
                    locked_roi = day_high_pct
                    actual_holding_days = i + 1
                    exit_date_actual = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                    break
                locked_roi = day_close_pct
            
            return {
                "ticker": ticker,
                "name": name,
                "entry_date": simulated_date,
                "entry_price": entry_price,
                "current_price": current_price,
                "ai_prob_at_entry": ai_prob,
                "rise_score_at_entry": total_score,
                "actual_return": locked_roi,
                "sniper_result": sniper_result,
                "max_gain": max_gain_pct,
                "max_drawdown": max_drawdown_pct,
                "holding_days": actual_holding_days,
                "exit_date": exit_date_actual
            }
        except Exception as e:
            # print(f"❌ Error processing {ticker}: {e}")
            return None

    results = []
    # Optimize workers based on CPU count (I/O reading DB + CPU processing indicators)
    max_threads = min(config.CPU_COUNT * 2, len(candidates), 20)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(process_stock, s) for s in candidates]
        for f in futures:
            res = f.result()
            if res: results.append(res)

    # 4. RANKING
    df_res = pd.DataFrame(results)
    
    if df_res.empty:
        return {"error": "No stocks met requirements", "summary": {"avg_return": 0, "win_rate": 0, "sniper_hit_rate": 0}}
        
    df_res = df_res.sort_values(by="ai_prob_at_entry", ascending=False)
    
    # Top N for Concentrated Strategy
    top_n = max(1, int(limit)) if limit else 10
    top_picks = df_res.head(top_n).to_dict('records')
    
    # Summary Stats for Top Picks
    top_df = df_res.head(top_n)
    avg_return = top_df['actual_return'].mean()
    win_count = len(top_df[top_df['actual_return'] > 0])
    
    # Sniper-specific stats
    sniper_hits = len(top_df[top_df['sniper_result'] == 'HIT'])
    sniper_stops = len(top_df[top_df['sniper_result'] == 'STOP'])
    sniper_total = sniper_hits + sniper_stops
    sniper_hit_rate = sniper_hits / sniper_total if sniper_total > 0 else 0
    
    # Max drawdown across all top picks
    avg_max_drawdown = top_df['max_drawdown'].mean() if 'max_drawdown' in top_df.columns else 0
    
    # Profit factor: total gains / total losses
    gains = top_df[top_df['actual_return'] > 0]['actual_return'].sum()
    losses = abs(top_df[top_df['actual_return'] < 0]['actual_return'].sum())
    profit_factor = gains / losses if losses > 0 else float('inf')

    best_pick = None
    if not top_df.empty:
        best_idx = top_df['actual_return'].idxmax()
        if pd.notna(best_idx):
            best_pick = top_df.loc[best_idx]
    
    return {
        "days_ago": days_ago,
        "model_version": version or "latest",
        "simulated_date": top_picks[0]['entry_date'] if top_picks else "N/A",
        "candidate_pool_size": len(results),
        "top_picks": top_picks,
        "summary": {
            "holding_days": top_picks[0]['holding_days'] if top_picks else max(days_ago - 1, 0),
            "exit_date_actual": top_picks[0]['exit_date'] if top_picks else "今日",
            "avg_return": avg_return,
            "win_rate": win_count / len(top_picks) if top_picks else 0,
            "sniper_hit_rate": sniper_hit_rate,
            "sniper_hits": sniper_hits,
            "sniper_stops": sniper_stops,
            "profit_factor": round(profit_factor, 2),
            "avg_max_drawdown": round(avg_max_drawdown * 100, 2),
            "best_stock": best_pick['name'] if best_pick is not None else "N/A",
            "best_return": float(best_pick['actual_return']) if best_pick is not None else 0,
            "execution_time_sec": round(time.perf_counter() - start_time, 2)
        }
    }

if __name__ == "__main__":
    # Test run
    print("Running test backtest (10 days ago)...")
    result = run_time_machine(days_ago=10)
    print(result['summary'])
