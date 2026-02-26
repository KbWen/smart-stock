import pandas as pd
import numpy as np

def check_smart_conditions(df, ai_prob, conditions):
    """
    Checks if a stock meets a set of composite conditions.
    
    Args:
        df (pd.DataFrame): Stock history with indicators.
        ai_prob (float): The AI probability (0.0 - 1.0).
        conditions (list): List of condition strings to check.
                           e.g. ['high_ai', 'vol_surge', 'kd_gold']
    
    Returns:
        bool: True if ALL conditions are met.
    """
    if df.empty or len(df) < 2:
        return False
        
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 1. Filters (Must Match ALL selected)
    # -----------------------------------
    if 'high_ai' in conditions:
        if ai_prob < 0.60:
            return False
            
    if 'vol_surge' in conditions:
        vol_ma = df['volume'].rolling(20).mean().iloc[-1]
        if vol_ma == 0 or (latest['volume'] / vol_ma) < 1.5:
            return False

    # 2. Signals (Must Match AT LEAST ONE selected)
    # ---------------------------------------------
    signal_conditions = [c for c in conditions if c in ['kd_gold', 'macd_bull', 'sma_cross']]
    
    # If no signals selected, we are done (passed filters)
    if not signal_conditions:
        return True
        
    # Check if ANY selected signal triggers
    has_signal = False
    
    if 'kd_gold' in conditions:
        # Relaxed KD: Just Cross (K > D) and K wasn't already high (>80)
        k_now, d_now = latest.get('k', 50), latest.get('d', 50)
        k_prev, d_prev = prev.get('k', 50), prev.get('d', 50)
        
        # Cross UP
        if k_prev < d_prev and k_now > d_now and k_now < 80:
             has_signal = True
        # Or maybe just strong separation? No, user asked for cross.
            
    if not has_signal and 'macd_bull' in conditions:
        hist_now = latest.get('macd', 0) - latest.get('macd_signal', 0)
        hist_prev = prev.get('macd', 0) - prev.get('macd_signal', 0)
        if hist_prev < 0 and hist_now > 0:
            has_signal = True
            
    if not has_signal and 'sma_cross' in conditions:
        if prev['sma_20'] < prev['sma_60'] and latest['sma_20'] > latest['sma_60']:
            has_signal = True

    return has_signal
