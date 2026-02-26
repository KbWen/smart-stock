import pandas as pd
import numpy as np

def calculate_rise_score_v2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Implements Rise Score 2.0 (V4.1 Sniper logic).
    Adds 'trend_score', 'momentum_score', 'volatility_score', and 'total_score' to DF.
    Each branch is capped at its theoretical max weight.
    """
    if df.empty:
        return df
        
    # --- Ensure factors are present ---
    # Only fallback to full indicator computation when base OHLCV columns exist.
    required_factors = ['trend_alignment', 'rel_vol', 'bb_percent', 'sma20_slope', 'sma60_slope', 'rsi', 'kd_cross_flag', 'norm_macd_hist']
    has_base_ohlcv = all(col in df.columns for col in ['close', 'high', 'low', 'volume'])
    if any(col not in df.columns for col in required_factors) and has_base_ohlcv:
        from core.indicators_v2 import compute_v4_indicators
        df = compute_v4_indicators(df)

    df = df.copy()
    if 'bb_width_rank' not in df.columns:
        # Backward compatibility for tests / lightweight callers that only pass is_squeeze.
        if 'is_squeeze' in df.columns:
            df['bb_width_rank'] = np.where(df['is_squeeze'] == 1, 0.0, 1.0)
        else:
            df['bb_width_rank'] = 1.0
    
    # Weights (0-100 scale)
    W_TREND = 40
    W_MOMENTUM = 30
    W_VOLATILITY = 30

    # 1. Trend Score (Max 40)
    trend_score = df.get('trend_alignment', 0) * 20
    trend_score = trend_score + np.where(df.get('sma20_slope', 0) > 0, 10, 0)
    trend_score = trend_score + np.where(df.get('sma60_slope', 0) > 0, 10, 0)
    df['trend_score_v2'] = pd.Series(trend_score).fillna(0).clip(0, W_TREND).values

    # 2. Momentum Score (Max 30)
    rsi = df.get('rsi', 50) # Neutral RSI if missing
    momentum_score = np.where((rsi >= 40) & (rsi <= 70), 15, 0)
    momentum_score = momentum_score + np.where((rsi > 70) & (rsi <= 80), 7, 0)
    momentum_score = momentum_score + np.where(df.get('norm_macd_hist', 0) > 0, 5, 0)
    momentum_score = momentum_score + (df.get('kd_cross_flag', 0) * 10)
    df['momentum_score_v2'] = pd.Series(momentum_score).fillna(0).clip(0, W_MOMENTUM).values

    # 3. Volatility / Setup Score (Max 30)
    vol_score = np.where(df.get('bb_width_rank', 1.0) < 0.2, 15, 0)
    vol_score = vol_score + np.where(df.get('rel_vol', 0) > 1.5, 10, 0)
    bbp = df.get('bb_percent', 0.5)
    vol_score = vol_score + np.where((bbp >= 0) & (bbp <= 0.3), 5, 0)
    df['volatility_score_v2'] = pd.Series(vol_score).fillna(0).clip(0, W_VOLATILITY).values

    # Total Score
    df['total_score_v2'] = df['trend_score_v2'] + df['momentum_score_v2'] + df['volatility_score_v2']
    
    return df
