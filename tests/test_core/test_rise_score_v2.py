import pytest
import pandas as pd
import numpy as np
from core.rise_score_v2 import calculate_rise_score_v2

def test_calculate_rise_score_v2_perfect_score():
    """Verify that a stock matching all 'Sniper' criteria gets a high score."""
    data = {
        'trend_alignment': [1],
        'sma20_slope': [0.01],
        'sma60_slope': [0.005],
        'rsi': [50],
        'norm_macd_hist': [0.01],
        'kd_cross_flag': [1],
        'is_squeeze': [1],
        'rel_vol': [2.0],
        'bb_percent': [0.15]
    }
    df = pd.DataFrame(data)
    df = calculate_rise_score_v2(df)
    
    # Expected: 
    # Trend: 20 (align) + 10 (slope20) + 10 (slope60) = 40
    # Momentum: 15 (rsi zone) + 5 (macd_hist>0) + 10 (kd flag) = 30
    # Volatility: 15 (squeeze) + 10 (rel_vol) + 5 (bb_percent) = 30
    # Total: 100
    assert df.loc[0, 'total_score_v2'] == 100

def test_calculate_rise_score_v2_bad_stock():
    """Verify that a poorly performing stock gets a low score."""
    data = {
        'trend_alignment': [0],
        'sma20_slope': [-0.01],
        'sma60_slope': [-0.005],
        'rsi': [20],
        'norm_macd_hist': [-0.01],
        'kd_cross_flag': [0],
        'is_squeeze': [0],
        'rel_vol': [0.5],
        'bb_percent': [0.9]
    }
    df = pd.DataFrame(data)
    df = calculate_rise_score_v2(df)
    
    assert df.loc[0, 'total_score_v2'] == 0

def test_score_v2_empty_df():
    """Ensure it handles empty DataFrames gracefully."""
    df = pd.DataFrame()
    result = calculate_rise_score_v2(df)
    assert result.empty


def test_volatility_uses_bb_width_rank_threshold():
    """Squeeze points should be based on bb_width_rank < 0.2 threshold."""
    df = pd.DataFrame({
        'trend_alignment': [0, 0],
        'sma20_slope': [0.0, 0.0],
        'sma60_slope': [0.0, 0.0],
        'rsi': [50, 50],
        'norm_macd_hist': [0, 0],
        'kd_cross_flag': [0, 0],
        'bb_width_rank': [0.19, 0.2],
        'rel_vol': [1.0, 1.0],
        'bb_percent': [0.5, 0.5]
    })
    out = calculate_rise_score_v2(df)
    assert out.loc[0, 'volatility_score_v2'] == 15
    assert out.loc[1, 'volatility_score_v2'] == 0
