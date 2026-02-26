import pytest
import pandas as pd
import numpy as np

# We'll assume the implementation will be in core/signals.py
# For now, this will fail because core/signals.py doesn't exist or doesn't have these functions.

def test_sma20_breakout_detection():
    """Verify that a price crossing SMA20 from below triggers a BREAKOUT signal."""
    # Data where price crosses SMA20 at the last row
    df = pd.DataFrame({
        'close': [90, 95, 105],
        'sma_20': [100, 100, 100]
    })
    
    from core.signals import get_technical_signals
    signals = get_technical_signals(df)
    
    assert 'SMA20 突破' in signals

def test_volume_surge_detection():
    """Verify that relative volume > 2.0 with price rise triggers a VOLUME_SURGE signal."""
    df = pd.DataFrame({
        'close': [100, 105],
        'volume': [1000, 3000],
        'vol_ma20': [1000, 1000]
    })
    
    from core.signals import get_technical_signals
    # We expect rel_vol = 3.0 here
    signals = get_technical_signals(df)
    
    assert '量能激增' in signals

def test_data_rounding_accuracy():
    """Verify that the signal extraction logic returns correctly rounded data points for the API."""
    # This is more of a helper test to ensure core.signals handles rounding
    from core.signals import format_api_data
    
    raw_data = {
        'price': 123.45678,
        'change': 0.012345
    }
    
    formatted = format_api_data(raw_data)
    
    assert formatted['price'] == 123.46
    assert formatted['change_percent'] == 1.23
