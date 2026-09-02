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


def test_recalculate_hands_the_model_an_unfilled_frame(monkeypatch):
    """docs/specs/unknown-is-not-zero-ml-features.md: the display fill must not reach the model.

    `recalculate` zero-fills the frame so NaN never reaches the API payload. That fill also
    erases what predict_prob() needs in order to refuse: a feature that could not be computed
    arrives as a real number. This is the path that writes ai_prob for the whole universe, so
    a substitution here is stored, not merely displayed.

    Falsifiable: pass `df` instead of `df_for_model` and the captured frame has no NaN left.
    """
    import numpy as np
    import pandas as pd

    captured = {}

    monkeypatch.setattr(recalculate, "_load_target_tickers", lambda **_kwargs: ["2330"])
    monkeypatch.setattr(recalculate, "get_model_version", lambda: "v4.1")
    monkeypatch.setattr(
        recalculate, "load_from_db",
        lambda _ticker, days=730: pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=80, freq="D"),
            "close": [100.0 + i for i in range(80)],
        }),
    )

    import core.indicators_v2 as indicators_v2
    import core.rise_score_v2 as rise_score_v2
    # One uncomputable indicator, exactly as a short history produces.
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda df: df.assign(dist_sma240=np.nan))
    monkeypatch.setattr(
        rise_score_v2, "calculate_rise_score_v2",
        lambda df: df.assign(total_score_v2=1, trend_score_v2=1, momentum_score_v2=1, volatility_score_v2=1),
    )
    monkeypatch.setattr(recalculate, "generate_analysis_report", lambda *_a, **_k: "ok")
    monkeypatch.setattr(recalculate, "save_score_to_db", lambda *_a, **_k: None)

    def capture(df):
        captured["frame"] = df.copy()
        return None

    monkeypatch.setattr(recalculate, "predict_prob", capture)

    recalculate.recalculate_all(incremental=False)

    frame = captured["frame"]
    assert frame["dist_sma240"].isna().all(), (
        "the model was handed a display-filled frame; an uncomputable feature arrived as 0"
    )


def test_recalc_window_clears_the_feature_requirement():
    """docs/specs/unknown-is-not-zero-ml-features.md: the window must not starve the model.

    `load_from_db` anchors its window on `datetime.now()` in CALENDAR days, so the number of
    trading rows it yields shrinks as the database ages. When RECALC_LOOKBACK_DAYS was 420 the
    shipped 92-ticker DB produced ~225 rows per ticker -- below MIN_FEATURE_ROWS (250) -- and
    predict_prob correctly refused 91 of 92 tickers, wiping the AI number from the whole product.

    A calendar day is at most 5/7 of a trading day, and TW holidays take more, so 0.66 is a
    conservative upper bound on the conversion. The window must clear the requirement with real
    margin, not by two rows.
    """
    from core.ai.common import MIN_FEATURE_ROWS

    trading_rows = recalculate.RECALC_LOOKBACK_DAYS * 0.66
    assert trading_rows >= MIN_FEATURE_ROWS * 1.5, (
        f"RECALC_LOOKBACK_DAYS={recalculate.RECALC_LOOKBACK_DAYS} yields about "
        f"{trading_rows:.0f} trading rows against a {MIN_FEATURE_ROWS}-row feature requirement; "
        f"the recalculation would refuse most of the universe"
    )
