import pandas as pd
import numpy as np
from core import config

def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """Standard Wilder's RSI using EWMA."""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Wilder's smoothing: alpha = 1 / window
    avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data: pd.DataFrame) -> tuple:
    exp1 = data['close'].ewm(span=12, adjust=False).mean()
    exp2 = data['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calculate_smas(data: pd.DataFrame) -> pd.DataFrame:
    data['sma_5'] = data['close'].rolling(window=5).mean()
    data['sma_20'] = data['close'].rolling(window=20).mean()
    data['sma_60'] = data['close'].rolling(window=60).mean()
    data['sma_120'] = data['close'].rolling(window=120).mean()
    data['sma_240'] = data['close'].rolling(window=240).mean()
    return data

def calculate_emas(data: pd.DataFrame) -> pd.DataFrame:
    data['ema_20'] = data['close'].ewm(span=20, adjust=False).mean()
    data['ema_50'] = data['close'].ewm(span=50, adjust=False).mean()
    return data

def calculate_kd(data: pd.DataFrame, period: int = 9) -> pd.DataFrame:
    low_min = data['low'].rolling(window=period).min()
    high_max = data['high'].rolling(window=period).max()
    
    rsv = (data['close'] - low_min) / (high_max - low_min) * 100
    
    # Calculate K and D (using EWMA equivalent)
    # K = 2/3 * PrevK + 1/3 * RSV
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    
    data['k'] = k
    data['d'] = d
    return data

def calculate_bollinger(data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    sma = data['close'].rolling(window=window).mean()
    std = data['close'].rolling(window=window).std()
    
    data['bb_upper'] = sma + (std * 2)
    data['bb_lower'] = sma - (std * 2)
    data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / sma
    data['bb_percent'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
    return data

def calculate_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    return true_range.rolling(window=window).mean()



def generate_analysis_report(last_row, prev_row, trend_score, momentum_score, volatility_score) -> dict:
    """Generates text-based analysis for the UI."""
    report = {
        'trend': 'Neutral',
        'momentum': 'Neutral',
        'setup': 'None'
    }
    
    # 1. Trend Analysis (Hardened V2 Logic)
    close = last_row['close']
    s20, s60 = last_row.get('sma_20', 0), last_row.get('sma_60', 0)
    s120, s240 = last_row.get('sma_120', 0), last_row.get('sma_240', 0)
    
    if close > s20 > s60 > s120 > s240:
        report['trend'] = "Bullish Multi-Year Alignment (Golden Cluster)."
    elif close > s20 > s60:
        report['trend'] = "Mid-term Bullish Trend."
    elif close < s20 < s60:
        report['trend'] = "Structural Bearish Downtrend."
    elif close > s120:
        report['trend'] = "Long-term Support Holding."
    else:
        report['trend'] = "Consolidation / Bottoming phase."
        
    # 2. Momentum Analysis (V2 Weights Match)
    rsi = last_row.get('rsi', 50)
    if rsi > 75:
        report['momentum'] = f"Overheated (RSI {rsi:.1f}). Overbought."
    elif rsi < 35:
        report['momentum'] = f"Weak / Oversold (RSI {rsi:.1f})."
    elif 50 <= rsi <= 70:
        report['momentum'] = "Rising Momentum (Ideal Sniper Zone)."
    else:
        report['momentum'] = "Neutral / Sideways."
        
    # 3. Setup/Volatility
    bb_width = last_row.get('bb_width', 1.0)
    vol_ma20 = last_row.get('vol_ma20', 1)
    current_vol = last_row['volume']
    
    if bb_width < 0.08:
        report['setup'] = "Extreme Volatility Squeeze (Sniper Target)."
    elif current_vol > vol_ma20 * 1.5:
        report['setup'] = "Volume Breakout Detected."
    else:
        report['setup'] = "Stability / Accumulation."
        
    return report

