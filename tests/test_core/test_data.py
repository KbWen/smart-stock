import pytest
import sqlite3
import pandas as pd
from core import data

def test_standardize_ticker():
    """Verify ticker standardization correctly strips TW and TWO suffixes."""
    assert data.standardize_ticker("2330.TW") == "2330"
    assert data.standardize_ticker("6510.TWO") == "6510"
    assert data.standardize_ticker("2330") == "2330"
    assert data.standardize_ticker("") == ""
    assert data.standardize_ticker(None) is None

def test_init_db_creates_tables(mock_db):
    """Verify init_db correctly creates schema (mock_db runs init equivalent)."""
    # Note: mock_db fixture in conftest.py already creates our tables.
    # Let's verify the tables exist with the right columns.
    cursor = mock_db.cursor()
    
    # Check if stock_scores exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_scores'")
    assert cursor.fetchone() is not None
    
    # Check structure matches data.py requirements
    cursor.execute("PRAGMA table_info(stock_scores)")
    columns = {row[1] for row in cursor.fetchall()}
    
    expected = {'ticker', 'total_score', 'trend_score', 'momentum_score', 
                'volatility_score', 'last_price', 'change_percent', 
                'ai_probability', 'model_version', 'updated_at'}
    assert expected.issubset(columns)

def test_save_and_load_from_db(mock_db, monkeypatch, tmp_path):
    """Verify we can save and read scores."""
    from core import data
    import core.config
    
    # mock_db creates test_stocks.db in tmp_path
    monkeypatch.setattr(core.config, "DB_PATH", str(tmp_path / "test_stocks.db"))
    
    scores = {
        'total_score_v2': 85.0,
        'trend_score_v2': 30.0,
        'momentum_score_v2': 25.0,
        'volatility_score_v2': 30.0,
        'last_price': 100.0,
        'change_percent': 2.5
    }
    
    # Call save score
    data.save_score_to_db("2330", scores, ai_prob=80.0, model_version="v4.test")
                     
    # Fetch it
    df = data.get_top_scores_from_db(limit=10)
    
    assert len(df) == 1
    assert df[0]['ticker'] == "2330"
    assert df[0]['total_score'] == 85.0
    assert df[0]['model_version'] == "v4.test"
    assert df[0]['ai_probability'] == 80.0


def test_get_stock_name_auto_initializes_cache(monkeypatch):
    from core import data

    data._tw_stocks_cache["name_map"] = {}

    def fake_all_stocks():
        data._tw_stocks_cache["name_map"] = {"2330": "TSMC"}
        data._tw_stocks_cache["data"] = [{"code": "2330", "name": "TSMC"}]
        return data._tw_stocks_cache["data"]

    monkeypatch.setattr(data, "get_all_tw_stocks", fake_all_stocks)

    assert data.get_stock_name("2330.TW") == "TSMC"


def test_fetch_stock_data_calls_yfinance_without_timeout(monkeypatch):
    from core import data

    monkeypatch.setattr(data, "load_from_db", lambda *_args, **_kwargs: pd.DataFrame())
    monkeypatch.setattr(data, "save_to_db", lambda *_args, **_kwargs: None)

    call_kwargs = {}

    class FakeTicker:
        def history(self, **kwargs):
            call_kwargs.update(kwargs)
            return pd.DataFrame(
                {
                    "Date": pd.date_range("2024-01-01", periods=3, freq="D"),
                    "Open": [1, 1, 1],
                    "High": [1, 1, 1],
                    "Low": [1, 1, 1],
                    "Close": [1, 1, 1],
                    "Volume": [100, 100, 100],
                }
            )

    monkeypatch.setattr(data.yf, "Ticker", lambda _ticker: FakeTicker())

    out = data.fetch_stock_data("2330", days=10, force_download=True)

    assert not out.empty
    assert call_kwargs.get("period") == "10d"
    assert call_kwargs.get("auto_adjust") is True
    assert "timeout" not in call_kwargs


def test_fetch_stock_data_uses_live_download_when_db_not_today(monkeypatch):
    from core import data

    stale_df = pd.DataFrame(
        {
            "date": pd.to_datetime([pd.Timestamp.now() - pd.Timedelta(days=1)]),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
            "volume": [1000],
        }
    )

    monkeypatch.setattr(data, "load_from_db", lambda *_args, **_kwargs: stale_df)
    monkeypatch.setattr(data, "save_to_db", lambda *_args, **_kwargs: None)

    class FakeTicker:
        def history(self, **_kwargs):
            return pd.DataFrame(
                {
                    "Date": pd.date_range("2024-01-01", periods=2, freq="D"),
                    "Open": [100.0, 101.0],
                    "High": [101.0, 102.0],
                    "Low": [99.0, 100.0],
                    "Close": [100.5, 101.5],
                    "Volume": [1000, 1200],
                }
            )

    monkeypatch.setattr(data.yf, "Ticker", lambda _ticker: FakeTicker())

    out = data.fetch_stock_data("2330", days=30, force_download=False)
    assert len(out) == 2


def test_get_latest_score_for_ticker_returns_latest_row(mock_db, monkeypatch, tmp_path):
    import core.config

    monkeypatch.setattr(core.config, "DB_PATH", str(tmp_path / "test_stocks.db"))

    data.save_score_to_db(
        "2330",
        {
            "total_score": 70,
            "trend_score": 20,
            "momentum_score": 25,
            "volatility_score": 25,
            "last_price": 100,
            "change_percent": 1.2,
        },
        ai_prob=0.6,
        model_version="v4.0",
    )
    data.save_score_to_db(
        "2330",
        {
            "total_score": 75,
            "trend_score": 25,
            "momentum_score": 25,
            "volatility_score": 25,
            "last_price": 101,
            "change_percent": 1.4,
        },
        ai_prob=0.7,
        model_version="v4.1",
    )

    latest = data.get_latest_score_for_ticker("2330")
    assert latest is not None
    assert latest["model_version"] == "v4.1"
    assert latest["last_price"] == 101


def test_get_all_tw_stocks_initializes_name_map_when_twstock_missing(monkeypatch):
    from core import data

    data._tw_stocks_cache["data"] = []
    data._tw_stocks_cache["last_updated"] = 0
    data._tw_stocks_cache["name_map"] = None

    monkeypatch.setattr(data, "twstock", None)
    monkeypatch.setattr(data.os.path, "exists", lambda _p: False)

    stocks = data.get_all_tw_stocks()

    assert stocks == []
    assert data._tw_stocks_cache["name_map"] == {}
    assert data.get_stock_name("2330.TW") is None


def test_load_indicators_for_tickers_returns_map(mock_db, monkeypatch, tmp_path):
    from core import data
    import core.config

    monkeypatch.setattr(core.config, "DB_PATH", str(tmp_path / "test_stocks.db"))
    conn = data.get_db_connection()
    conn.execute(
        """
        INSERT INTO stock_indicators (ticker, rsi, macd, macd_signal, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        ("2330", 55.5, 1.2, 0.8),
    )
    conn.execute(
        """
        INSERT INTO stock_indicators (ticker, rsi, macd, macd_signal, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        ("2317", 45.2, -0.3, -0.6),
    )
    conn.commit()
    conn.close()

    out = data.load_indicators_for_tickers(["2330", "2317", "9999"])

    assert set(out.keys()) == {"2330", "2317"}
    assert out["2330"]["rsi"] == 55.5
    assert out["2317"]["macd_signal"] == -0.6


def test_get_stock_name_threadsafe_missing_map(monkeypatch):
    from core import data

    data._tw_stocks_cache["name_map"] = None
    data._tw_stocks_cache["data"] = None

    monkeypatch.setattr(data, "get_all_tw_stocks", lambda: [])
    assert data.get_stock_name("2330.TW") is None
