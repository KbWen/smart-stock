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
    monkeypatch.setattr(data, "_live_universe", lambda: [])  # no network in tests
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


def test_get_ticker_suffix_us_crypto():
    """Verify get_ticker_suffix returns empty string for US/Crypto stocks."""
    from core import data
    assert data.get_ticker_suffix("AAPL") == ""
    assert data.get_ticker_suffix("BTC-USD") == ""
    assert data.get_ticker_suffix("MSFT") == ""
    assert data.get_ticker_suffix("2330") in (".TW", ".TWO")


# --- Universe completeness (feature/data-universe-completeness) -------------

def test_get_all_tw_stocks_uses_live_source(monkeypatch, tmp_path):
    """Live source is the primary universe; entries carry market + kind (incl. ETF)."""
    from core import data
    import core.config

    monkeypatch.setattr(core.config, "STOCK_LIST_CACHE", str(tmp_path / "cache.json"))
    data._tw_stocks_cache.update({"data": None, "last_updated": 0, "name_map": None})

    live = [
        {"code": "2330", "name": "台積電", "market": "上市", "kind": "股票"},
        {"code": "0050", "name": "元大台灣50", "market": "上市", "kind": "ETF"},
    ]
    monkeypatch.setattr(data, "_live_universe", lambda: live)

    out = data.get_all_tw_stocks()
    by = {s["code"]: s for s in out}
    assert by["0050"]["kind"] == "ETF"
    assert by["2330"]["market"] == "上市"
    assert data.get_stock_name("2330.TW") == "台積電"


def test_get_all_tw_stocks_fallback_to_twstock_includes_etf(monkeypatch, tmp_path):
    """When live returns nothing, twstock fallback is used and ETFs are included."""
    import types
    from core import data
    import core.config

    monkeypatch.setattr(core.config, "STOCK_LIST_CACHE", str(tmp_path / "cache.json"))
    data._tw_stocks_cache.update({"data": None, "last_updated": 0, "name_map": None})
    monkeypatch.setattr(data, "_live_universe", lambda: [])

    fake_codes = {
        "2330": types.SimpleNamespace(type="股票", market="上市", name="台積電"),
        "0050": types.SimpleNamespace(type="ETF", market="上市", name="元大台灣50"),
        "6488": types.SimpleNamespace(type="股票", market="上櫃", name="環球晶"),
        "1234": types.SimpleNamespace(type="特別股", market="上市", name="排除我"),
    }
    monkeypatch.setattr(data, "twstock", types.SimpleNamespace(codes=fake_codes))

    out = data.get_all_tw_stocks()
    by = {s["code"]: s for s in out}
    assert by["0050"]["kind"] == "ETF"
    assert by["6488"]["market"] == "上櫃"
    assert "1234" not in by  # neither 股票 nor ETF -> excluded


def test_get_all_tw_stocks_never_overwrites_good_cache_with_empty(monkeypatch, tmp_path):
    """A failed live fetch + no twstock must not blank out a populated in-memory list."""
    from core import data
    import core.config

    monkeypatch.setattr(core.config, "STOCK_LIST_CACHE", str(tmp_path / "cache.json"))
    good = [{"code": "2330", "name": "台積電", "market": "上市", "kind": "股票"}]
    data._tw_stocks_cache.update({"data": good, "last_updated": 0, "name_map": None})  # stale
    monkeypatch.setattr(data, "_live_universe", lambda: [])
    monkeypatch.setattr(data, "twstock", None)

    out = data.get_all_tw_stocks()
    assert out == good


def test_normalize_loaded_drops_phantom_codes():
    """Corrupted cache rows (None / 'None' / empty code) must not leak phantom tickers."""
    from core import data
    out = data._normalize_loaded([
        {"code": "2330", "name": "台積電", "market": "上市", "kind": "股票"},
        {"code": None, "name": "x"},
        {"code": "None", "name": "y"},
        {"code": "", "name": "z"},
    ])
    assert [s["code"] for s in out] == ["2330"]


def test_refresh_stock_universe_force_refetches(monkeypatch, tmp_path):
    """AC3: force=True bypasses the fresh in-memory cache and re-fetches live."""
    import time as _time
    from core import data
    import core.config

    monkeypatch.setattr(core.config, "STOCK_LIST_CACHE", str(tmp_path / "cache.json"))
    data._tw_stocks_cache.update({
        "data": [{"code": "9999", "name": "old", "market": "上市", "kind": "股票"}],
        "last_updated": _time.time(),  # deliberately fresh
        "name_map": None,
    })
    calls = {"n": 0}

    def fake_live():
        calls["n"] += 1
        return [{"code": "2330", "name": "台積電", "market": "上市", "kind": "股票"}]

    monkeypatch.setattr(data, "_live_universe", fake_live)
    out = data.refresh_stock_universe(force=True)
    assert calls["n"] == 1  # refetched despite fresh memory cache
    assert {s["code"] for s in out} == {"2330"}


def test_backfill_history_invokes_fetch_for_short(monkeypatch):
    """AC4: backfill derives short tickers and reuses fetch_stock_data, counting hits."""
    from core import data

    monkeypatch.setattr(data, "report_history_coverage", lambda *a, **k: {"short": ["1111", "2222"]})
    fetched = []

    def fake_fetch(code, days=730, force_download=False):
        fetched.append(code)
        return pd.DataFrame({"close": [1]}) if code == "1111" else pd.DataFrame()

    monkeypatch.setattr(data, "fetch_stock_data", fake_fetch)
    res = data.backfill_history(limit=5)
    assert res["attempted"] == 2
    assert res["fetched"] == 1  # only 1111 returned data
    assert fetched == ["1111", "2222"]


def test_report_history_coverage_counts(mock_db, monkeypatch, tmp_path):
    """Coverage report classifies tickers by available history depth."""
    from core import data
    import core.config

    monkeypatch.setattr(core.config, "DB_PATH", str(tmp_path / "test_stocks.db"))
    conn = data.get_db_connection()

    def seed(ticker, n):
        dates = pd.date_range("2018-01-01", periods=n, freq="D").strftime("%Y-%m-%d")
        rows = [(ticker, d, 1.0, 1.0, 1.0, 1.0, 100) for d in dates]
        conn.executemany(
            "INSERT OR REPLACE INTO stock_history (ticker,date,open,high,low,close,volume)"
            " VALUES (?,?,?,?,?,?,?)",
            rows,
        )

    seed("1111", 130)  # >= MIN_PREDICT(120), < MIN_TRAIN(260)
    seed("2222", 300)  # >= both
    seed("3333", 50)   # short
    conn.commit()
    conn.close()

    cov = data.report_history_coverage(["1111", "2222", "3333"])
    assert cov["universe"] == 3
    assert cov["with_predict_rows"] == 2
    assert cov["with_train_rows"] == 1
    assert "3333" in cov["short"]
    assert "2222" not in cov["short"]
