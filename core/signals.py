import pandas as pd
from typing import List, Dict, Any, Optional

def get_technical_signals(df: pd.DataFrame) -> List[str]:
    """Analyze technical data to produce concise human-readable signals.
    
    Args:
        df: DataFrame containing at least 'close' and 'sma_20' (and optional 'volume'/'vol_ma20').
        
    Returns:
        List[str]: List of active technical signals.
    """
    if df.empty or len(df) < 2:
        return []
        
    signals = []
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 1. SMA20 Breakout (Price crossing SMA from below)
    if 'close' in df.columns and 'sma_20' in df.columns:
        if prev_row['close'] <= prev_row['sma_20'] and last_row['close'] > last_row['sma_20']:
            signals.append('SMA20 突破')
            
    # 2. Volume Surge
    if all(col in df.columns for col in ['volume', 'vol_ma20']):
        rel_vol = last_row['volume'] / last_row['vol_ma20'] if last_row['vol_ma20'] > 0 else 1.0
        # If volume is 2x average AND price is not falling
        if rel_vol >= 2.0 and last_row['close'] >= prev_row['close']:
            signals.append('量能激增')
            
    return signals

def get_signals_from_indicators(ind: Dict[str, Any]) -> List[str]:
    """Generate signals from a dictionary of indicators (typically from DB)."""
    signals = []
    
    rsi = ind.get('rsi')
    sma20 = ind.get('sma_20')
    sma60 = ind.get('sma_60')
    close = ind.get('close')
    bb_width = ind.get('bb_width')
    k = ind.get('k_val') or ind.get('k')
    d = ind.get('d_val') or ind.get('d')
    macd = ind.get('macd')
    macd_signal = ind.get('macd_signal')
    
    if rsi is not None:
        if float(rsi) < 30: signals.append('RSI 超賣')
        elif float(rsi) > 70: signals.append('RSI 過熱')

    if macd is not None and macd_signal is not None:
        macd = float(macd)
        macd_signal = float(macd_signal)
        diff = macd - macd_signal
        if diff >= 1.0:
            signals.append('MACD 多頭')
        elif diff > 0:
            signals.append('MACD 黃金交叉')
        elif diff < 0:
            signals.append('MACD 死亡交叉')
        
    if sma20 is not None and sma60 is not None:
        if float(sma20) > float(sma60): signals.append('均線多頭排列')
        elif float(sma20) < float(sma60): signals.append('均線空頭排列')
        
    if k is not None and d is not None:
        k = float(k)
        d = float(d)
        if k > d and k < 30:
            signals.append('KD 低檔黃金交叉')
        elif k < d and k > 70:
            signals.append('KD 高檔死叉')
        
    if bb_width is not None:
        bb_width = float(bb_width)
        if bb_width < 0.05:
            signals.append('布林收斂')
        elif bb_width > 0.15:
            signals.append('布林擴張')
        
    # Standard Signal Logic
    if any(col in ind for col in ['volume', 'vol_ma20']):
        vol = float(ind.get('volume', 0))
        ma_vol = float(ind.get('vol_ma20', 1))
        if ma_vol > 0 and vol / ma_vol >= 2.0:
            signals.append('量能激增')
            
    return signals[0:3]

def format_api_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Standards-compliant data rounding for the web API to ensure readable and accurate display.
    
    Args:
        raw_data: Dictionary with numeric values.
        
    Returns:
        Dict[str, Any]: Rounded and formatted dictionary.
    """
    formatted = {}
    
    # Precise rounding for price
    if 'price' in raw_data:
        formatted['price'] = round(float(raw_data['price']), 2)
        
    # Standard rounding for percent (e.g., 0.0123 -> 1.23)
    if 'change' in raw_data:
        formatted['change_percent'] = round(float(raw_data['change']) * 100, 2)
        
    return formatted
