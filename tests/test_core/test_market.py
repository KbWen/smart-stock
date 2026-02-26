import pytest
import os
import tempfile
import json
import pandas as pd
from datetime import datetime

# Monkeypatch the config to use a temp dir for history
import core.config

@pytest.fixture
def mock_market_history(monkeypatch):
    from core import config
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        monkeypatch.setattr(config, "BASE_DIR", tmpdirname)
        yield tmpdirname

def test_get_market_status_empty(mock_db, monkeypatch):
    """Empty database should return all zeros and unknown risk."""
    import core.market
    monkeypatch.setattr(core.market, "get_db_connection", lambda: mock_db)
    
    status = core.market.get_market_status()
    assert status['bull_ratio'] == 0
    assert status['market_temp'] == 0
    assert status['ai_sentiment'] == 0
    assert status['risk_level'] == "unknown"
    assert status['total_stocks'] == 0

def test_get_market_status_populated(mock_db, monkeypatch):
    """Database with scores should calculate bull ratio and correct risk levels."""
    import core.market
    monkeypatch.setattr(core.market, "get_db_connection", lambda: mock_db)
    
    # Insert some dummy data with varying versions, assuming 'v4' is latest
    cursor = mock_db.cursor()
    
    # 3 Bullish, 1 Bearish
    scores = [
        ("2330", 90.0, 30.0, 25.0, 30.0, 100.0, 2.0, 0.8, "v4.latest", "2024-01-01 10:00:00"),
        ("2317", 85.0, 25.0, 20.0, 20.0, 50.0, 1.0, 0.7, "v4.latest", "2024-01-01 10:00:00"),
        ("2454", 80.0, 22.0, 15.0, 15.0, 60.0, 0.5, 0.6, "v4.latest", "2024-01-01 10:00:00"),
        ("2308", 40.0, 10.0, 5.0, 5.0, 20.0, -1.0, 0.2, "v4.latest", "2024-01-01 10:00:00"),
        # Old version, shouldn't be counted
        ("2881", 95.0, 40.0, 30.0, 30.0, 30.0, 5.0, 0.9, "v3.old", "2023-01-01 10:00:00")
    ]
    
    cursor.executemany(
        "INSERT INTO stock_scores VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        scores
    )
    mock_db.commit()
    
    status = core.market.get_market_status()
    
    assert status['total_stocks'] == 4 # Only Latest
    # 3 out of 4 have trend_score > 20
    assert status['bull_ratio'] == 75.0
    assert "LOW RISK (BULL)" in status['risk_level']
    assert status['ai_sentiment'] > 0

def test_save_market_history_rotation(mock_market_history):
    """Verify history limits to 30 entries and deduplicates same-day saves."""
    from core.market import save_market_history, get_market_history
    import json
    
    # Seed 30 days of data
    history_file = os.path.join(mock_market_history, "market_history.json")
    seed_data = []
    for i in range(30):
        seed_data.append({
            "timestamp": f"2023-01-{i+1:02d}",
            "bull_ratio": i,
            "market_temp": i,
            "ai_sentiment": i
        })
        
    with open(history_file, "w") as f:
        json.dump(seed_data, f)
        
    # Save a new status today
    today_status = {
        "bull_ratio": 99.9,
        "market_temp": 88.8,
        "ai_sentiment": 77.7
    }
    
    # Save once
    save_market_history(today_status)
    hist = get_market_history()
    
    # Should still be 30, oldest dropped, newest added
    assert len(hist) == 30
    assert hist[-1]["timestamp"] == datetime.now().strftime("%Y-%m-%d")
    assert hist[-1]["bull_ratio"] == 99.9
    
    # Save again today (should update, not append)
    today_status["bull_ratio"] = 100.0
    save_market_history(today_status)
    hist = get_market_history()
    
    assert len(hist) == 30
    assert hist[-1]["bull_ratio"] == 100.0
