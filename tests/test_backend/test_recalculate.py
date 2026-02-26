import importlib
import sys

import pandas as pd

# test_backtest injects a fake core.data module; ensure we load the real one here.
if 'core.data' in sys.modules and not hasattr(sys.modules['core.data'], 'get_db_connection'):
    del sys.modules['core.data']

recalculate = importlib.import_module('backend.recalculate')


class DummyConn:
    def close(self):
        return None


def test_load_target_tickers_full(monkeypatch):
    calls = []

    def fake_read_sql(query, conn, params=None):
        calls.append((query, params))
        return pd.DataFrame({'ticker': ['2330', '2317']})

    monkeypatch.setattr(recalculate, 'get_db_connection', lambda: DummyConn())
    monkeypatch.setattr(pd, 'read_sql', fake_read_sql)

    out = recalculate._load_target_tickers(incremental=False, stale_hours=6, model_version='v4.1')
    assert out == ['2330', '2317']
    assert len(calls) == 1


def test_load_target_tickers_incremental(monkeypatch):
    def fake_read_sql(query, conn, params=None):
        if 'SELECT DISTINCT ticker FROM stock_history' in query:
            return pd.DataFrame({'ticker': ['2330', '2317', '1301']})
        return pd.DataFrame({'ticker': ['2317']})

    monkeypatch.setattr(recalculate, 'get_db_connection', lambda: DummyConn())
    monkeypatch.setattr(pd, 'read_sql', fake_read_sql)

    out = recalculate._load_target_tickers(incremental=True, stale_hours=6, model_version='v4.1')
    assert out == ['2317']


def test_load_target_tickers_incremental_considers_new_trading_date(monkeypatch):
    seen = {"query": ""}

    def fake_read_sql(query, conn, params=None):
        seen["query"] = query
        return pd.DataFrame({'ticker': ['2330']})

    monkeypatch.setattr(recalculate, 'get_db_connection', lambda: DummyConn())
    monkeypatch.setattr(pd, 'read_sql', fake_read_sql)

    out = recalculate._load_target_tickers(incremental=True, stale_hours=6, model_version='v4.1')
    assert out == ['2330']
    assert 'MAX(h.date) > DATE(s.updated_at)' in seen["query"]


def test_recalculate_uses_bounded_lookback_window(monkeypatch):
    import pandas as pd

    captured = {"days": None}

    monkeypatch.setattr(recalculate, "_load_target_tickers", lambda **_kwargs: ["2330"])
    monkeypatch.setattr(recalculate, "get_model_version", lambda: "v4.1")

    def fake_load_from_db(ticker, days=730):
        captured["days"] = days
        return pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=80, freq="D"),
                "close": [100.0 + i for i in range(80)],
            }
        )

    monkeypatch.setattr(recalculate, "load_from_db", fake_load_from_db)
    import core.indicators_v2 as indicators_v2
    import core.rise_score_v2 as rise_score_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda df: df)
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda df: df.assign(total_score_v2=1, trend_score_v2=1, momentum_score_v2=1, volatility_score_v2=1))
    monkeypatch.setattr(recalculate, "generate_analysis_report", lambda *_args, **_kwargs: "ok")
    monkeypatch.setattr(recalculate, "predict_prob", lambda _df: {"prob": 0.5})
    monkeypatch.setattr(recalculate, "save_score_to_db", lambda *_args, **_kwargs: None)

    recalculate.recalculate_all(incremental=True, stale_hours=6)

    assert captured["days"] == recalculate.RECALC_LOOKBACK_DAYS
