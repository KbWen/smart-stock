import sys
import os
import types

# Ensure project root is in sys.path for core imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide lightweight twstock stub for test environments without full parser deps.
if "twstock" not in sys.modules:
    twstock_stub = types.ModuleType("twstock")
    twstock_stub.codes = {}
    sys.modules["twstock"] = twstock_stub

import pytest
import pandas as pd
import numpy as np
import sqlite3
from unittest.mock import MagicMock


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as a live-market integration test (deselect with -m 'not integration')",
    )


@pytest.fixture
def sample_stock_data():
    """Generates 300 days of synthetic stock data with a slight upward trend."""
    periods = 300
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods)
    data = {
        'date': dates,
        'open': np.linspace(100, 110, periods) + np.random.normal(0, 1, periods),
        'high': np.linspace(102, 112, periods) + np.random.normal(0, 1, periods),
        'low': np.linspace(98, 108, periods) + np.random.normal(0, 1, periods),
        'close': np.linspace(101, 111, periods) + np.random.normal(0, 1, periods),
        'volume': np.random.randint(1000, 5000, periods)
    }
    df = pd.DataFrame(data)
    # Ensure high is highest and low is lowest
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    return df

@pytest.fixture
def mock_db(tmp_path):
    """Creates a temporary in-memory SQLite database for testing."""
    db_file = tmp_path / "test_stocks.db"
    conn = sqlite3.connect(db_file)
    # Create required tables
    conn.execute("CREATE TABLE stock_history (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER, PRIMARY KEY (ticker, date))")
    conn.execute("CREATE TABLE stock_scores (ticker TEXT, total_score REAL, trend_score REAL, momentum_score REAL, volatility_score REAL, last_price REAL, change_percent REAL, ai_probability REAL, model_version TEXT, updated_at TIMESTAMP, PRIMARY KEY (ticker, model_version))")
    conn.execute("CREATE TABLE stock_indicators (ticker TEXT PRIMARY KEY, rsi REAL, macd REAL, macd_signal REAL, ema_20 REAL, ema_50 REAL, sma_20 REAL, sma_60 REAL, k_val REAL, d_val REAL, atr REAL, bb_width REAL, model_version TEXT, updated_at TIMESTAMP)")
    conn.commit()
    yield conn
    conn.close()
