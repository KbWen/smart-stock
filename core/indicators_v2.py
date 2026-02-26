import pandas as pd
import numpy as np
from core.analysis import (
    calculate_rsi,
    calculate_macd,
    calculate_smas,
    calculate_emas,
    calculate_kd,
    calculate_bollinger,
    calculate_atr
)

def compute_v4_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes all technical factors for V4.1 Sniper strategy.
    Centralized and normalized for AI and Rule Engine consumption.
    """
    if df.empty:
        return df

    df = df.copy()
    
    # 1. Base technical indicators (reusing existing optimized logic)
    df = calculate_smas(df)
    df = calculate_emas(df)
    df['rsi'] = calculate_rsi(df)
    macd, signal = calculate_macd(df)
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_hist'] = macd - signal
    df = calculate_kd(df)
    df = calculate_bollinger(df)
    df['atr'] = calculate_atr(df)
    df['vol_ma20'] = df['volume'].rolling(window=20).mean()
    
    # 2. Factor Groups (Normalized/Relative)
    df = calculate_trend_factors(df)
    df = calculate_momentum_factors(df)
    df = calculate_volatility_factors(df)
    
    return df

def calculate_trend_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Trend (40% Weight): SMA Alignments & Slopes"""
    # Relative Distance from MAs
    df['dist_sma20'] = (df['close'] - df['sma_20']) / (df['sma_20'] + 1e-9)
    df['dist_sma60'] = (df['close'] - df['sma_60']) / (df['sma_60'] + 1e-9)
    df['dist_sma120'] = (df['close'] - df['sma_120']) / (df['sma_120'] + 1e-9)
    df['dist_sma240'] = (df['close'] - df['sma_240']) / (df['sma_240'] + 1e-9)
    
    # MA Spread (Normalized by price)
    df['ma_spread'] = (df['sma_20'] - df['sma_60']) / (df['close'] + 1e-9)
    
    # Slopes (5-day pct change of MAs)
    df['sma20_slope'] = df['sma_20'].pct_change(5)
    df['sma60_slope'] = df['sma_60'].pct_change(5)
    # Slopes (Longer term 10-day pct change for 120 and 240)
    df['sma120_slope'] = df['sma_120'].pct_change(10)
    df['sma240_slope'] = df['sma_240'].pct_change(10)
    
    # Alignment Flag (1 if Price > SMA20 > SMA60, else 0)
    df['trend_alignment'] = ((df['close'] > df['sma_20']) & (df['sma_20'] > df['sma_60'])).astype(int)
    
    # 52-week position (Relative to high/low)
    # Using available data window as proxy if 252 days not available
    rolling_window = min(len(df), 252)
    df['high_52w'] = df['high'].rolling(window=rolling_window).max()
    df['low_52w'] = df['low'].rolling(window=rolling_window).min()
    df['pos_52w'] = (df['close'] - df['low_52w']) / (df['high_52w'] - df['low_52w'] + 1e-9)
    
    return df

def calculate_momentum_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Momentum (30% Weight): RSI, KD, MACD Normalized"""
    # RSI is already 0-100, we normalize to 0.0-1.0
    df['norm_rsi'] = df['rsi'] / 100.0
    
    # MACD Histogram normalized by price
    df['norm_macd_hist'] = df['macd_hist'] / df['close']
    
    # KD Golden Cross proxy used by Rise Score 2.0
    # 1 if K > D and K < 80 (fresh momentum zone, avoids overheat)
    kd_cross = (df['k'] > df['d']) & (df['k'] < 80)
    df['kd_cross_flag'] = kd_cross.astype(int)
    
    return df

def calculate_volatility_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Volatility & Setup (30% Weight): BB Squeeze, Rel Vol, ATR%"""
    # BB Width is already normalized in calculate_bollinger (BB Width / SMA)
    # Relative Volume
    df['rel_vol'] = df['volume'] / (df['vol_ma20'] + 1e-9)
    
    # 60-day Volume Trend (Long-term volume breakout proxy)
    df['vol_ma60'] = df['volume'].rolling(window=60).mean()
    df['vol_trend_60d'] = (df['vol_ma20'] - df['vol_ma60']) / (df['vol_ma60'] + 1e-9)
    
    # ATR% (Normalize ATR by price)
    df['atr_percent'] = df['atr'] / df['close']
    
    # Squeeze & Bandwidth Rank (fully vectorized)
    rolling_window = 60
    squeeze_threshold = df['bb_width'].rolling(window=rolling_window, min_periods=20).quantile(0.2)
    df['is_squeeze'] = (df['bb_width'] <= squeeze_threshold).astype(int)

    # Percentile rank of the latest bb_width inside each 60-day window (0~1)
    # Uses pandas vectorized rolling rank instead of Python lambda apply.
    df['bb_width_rank'] = df['bb_width'].rolling(window=rolling_window, min_periods=20).rank(pct=True)

    return df
