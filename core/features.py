import pandas as pd
from core.analysis import (
    calculate_rsi,
    calculate_macd,
    calculate_smas,
    calculate_emas,
    calculate_kd,
    calculate_bollinger,
    calculate_atr
)

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes all technical indicators used by the AI model and strategy.
    Centralized function to avoid duplication and ensure consistency.
    
    Includes:
    - RSI, MACD (Line, Signal, Hist)
    - SMAs (5, 20, 60)
    - EMAs (20, 50)
    - KD (Stochastics)
    - Bollinger Bands (Upper, Lower, Width, Percent)
    - ATR
    - Volume MA (20)
    """
    if df.empty:
        return df

    # Create a copy to avoid SettingWithCopy warnings on slices
    df = df.copy()

    # 1. Basic Indicators
    df['rsi'] = calculate_rsi(df)
    df['macd'], df['macd_signal'] = calculate_macd(df)
    df = calculate_smas(df)
    df = calculate_emas(df)
    df = calculate_kd(df)
    df = calculate_bollinger(df)
    df['atr'] = calculate_atr(df)

    # 2. Volume Moving Average (Critical for Volatility Score and Setup)
    df['vol_ma20'] = df['volume'].rolling(window=20).mean()

    return df
