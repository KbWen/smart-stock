import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_v4_candidates_basic():
    """Test the V4 specific sniper candidates endpoint."""
    response = client.get("/api/v4/sniper/candidates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        candidate = data[0]
        assert "ticker" in candidate
        assert "rise_score" in candidate
        assert "ai_prob" in candidate

from unittest.mock import patch

def test_api_backtest_with_version():
    """Test backtest endpoint with a specific model version using mocks."""
    mock_data = {
        "days_ago": 5,
        "model_version": "latest",
        "simulated_date": "2026-02-10",
        "candidate_pool_size": 1,
        "top_picks": [{"ticker": "2330.TW", "actual_return": 0.02}],
        "summary": {"avg_return": 0.02, "win_rate": 100}
    }
    with patch("backend.main.run_time_machine", return_value=mock_data):
        response = client.get("/api/backtest?days=5&version=latest")
        assert response.status_code == 200
        data = response.json()
        assert "top_picks" in data
        assert data["model_version"] == "latest"

def test_api_models_list():
    """Verify the models listing endpoint."""
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_v4_candidates_uses_cache_within_ttl(monkeypatch):
    import backend.main as main

    sample = [{
        "ticker": "2330.TW",
        "model_version": "v4.1",
        "last_price": 100.0,
        "change_percent": 1.2,
        "total_score": 80.0,
        "ai_probability": 0.8,
        "trend_score": 20.0,
        "momentum_score": 30.0,
        "volatility_score": 30.0,
    }]

    call_count = {"db": 0}

    def fake_top_scores(limit, sort_by='score', version=None):
        call_count["db"] += 1
        return sample

    monkeypatch.setattr(main, "get_top_scores_from_db", fake_top_scores)
    monkeypatch.setattr(main, "get_stock_name", lambda _t: "TSMC")
    main.clear_api_caches()

    r1 = client.get("/api/v4/sniper/candidates?limit=1")
    r2 = client.get("/api/v4/sniper/candidates?limit=1")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert call_count["db"] == 1


def test_api_v4_candidates_cache_can_be_invalidated(monkeypatch):
    import backend.main as main

    sample = [{
        "ticker": "2330.TW",
        "model_version": "v4.1",
        "last_price": 100.0,
        "change_percent": 1.2,
        "total_score": 80.0,
        "ai_probability": 0.8,
        "trend_score": 20.0,
        "momentum_score": 30.0,
        "volatility_score": 30.0,
    }]

    call_count = {"db": 0}

    def fake_top_scores(limit, sort_by='score', version=None):
        call_count["db"] += 1
        return sample

    monkeypatch.setattr(main, "get_top_scores_from_db", fake_top_scores)
    monkeypatch.setattr(main, "get_stock_name", lambda _t: "TSMC")
    main.clear_api_caches()

    r1 = client.get("/api/v4/sniper/candidates?limit=1")
    assert r1.status_code == 200
    assert call_count["db"] == 1

    main.clear_api_caches()

    r2 = client.get("/api/v4/sniper/candidates?limit=1")
    assert r2.status_code == 200
    assert call_count["db"] == 2


def test_api_stock_detail_uses_close_as_last_price(monkeypatch):
    import pandas as pd
    import backend.main as main

    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [98.0, 99.0, 100.0],
            "high": [101.0, 102.0, 103.0],
            "low": [97.0, 98.0, 99.0],
            "close": [99.0, 100.0, 101.0],
            "volume": [1000, 1000, 1000],
        }
    )

    monkeypatch.setattr(main, "fetch_stock_data", lambda _ticker: df.copy())
    monkeypatch.setattr(main, "predict_prob", lambda _df: {"prob": 0.5, "details": {}})
    monkeypatch.setattr(main, "generate_analysis_report", lambda *_args, **_kwargs: "ok")

    from core import indicators_v2, rise_score_v2

    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0, trend_score_v2=1.0, momentum_score_v2=1.0, volatility_score_v2=1.0))

    response = client.get("/api/stock/2330")
    assert response.status_code == 200
    body = response.json()
    assert body["ai_target_price"] == 116.15
    assert body["ai_stop_price"] == 95.95


def test_api_stock_detail_score_contains_price_fields(monkeypatch):
    import pandas as pd
    import backend.main as main

    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [98.0, 99.0, 100.0],
            "high": [101.0, 102.0, 103.0],
            "low": [97.0, 98.0, 99.0],
            "close": [99.0, 100.0, 101.0],
            "volume": [1000, 1000, 1000],
        }
    )

    monkeypatch.setattr(main, "fetch_stock_data", lambda _ticker: df.copy())
    monkeypatch.setattr(main, "predict_prob", lambda _df: {"prob": 0.5, "details": {}})
    monkeypatch.setattr(main, "generate_analysis_report", lambda *_args, **_kwargs: "ok")

    from core import indicators_v2, rise_score_v2

    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df)
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=1.0, trend_score_v2=1.0, momentum_score_v2=1.0, volatility_score_v2=1.0))

    response = client.get("/api/stock/2330")
    assert response.status_code == 200
    body = response.json()
    assert body["score"]["last_price"] == 101.0
    assert body["score"]["change_percent"] == 1.0


def test_api_v4_stock_detail_prefers_local_db_snapshot(monkeypatch):
    import pandas as pd
    import backend.main as main

    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=80, freq="D"),
            "open": [100.0] * 80,
            "high": [101.0] * 80,
            "low": [99.0] * 80,
            "close": [100.0 + i * 0.1 for i in range(80)],
            "volume": [1000] * 80,
        }
    )

    monkeypatch.setattr(main, "load_from_db", lambda _ticker: df.copy())

    def _should_not_fetch(_ticker):
        raise AssertionError("fetch_stock_data should not run when DB snapshot exists")

    monkeypatch.setattr(main, "fetch_stock_data", _should_not_fetch)
    monkeypatch.setattr(main, "predict_prob", lambda _df: {"prob": 0.55})
    monkeypatch.setattr(main, "get_stock_name", lambda _ticker: "TSMC")
    monkeypatch.setattr(main, "get_latest_score_for_ticker", lambda _ticker: {"updated_at": "2024-01-10"})

    from core import indicators_v2, rise_score_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df.assign(trend_alignment=1, sma20_slope=1, rsi=55, is_squeeze=False, rel_vol=1.2, kd_cross_flag=False))
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=80.0, trend_score_v2=30.0, momentum_score_v2=30.0, volatility_score_v2=20.0))

    response = client.get("/api/v4/stock/2330")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "2330"
    assert body["ai_probability"] == 55.0


def test_api_v4_stock_detail_falls_back_to_fetch_when_db_empty(monkeypatch):
    import pandas as pd
    import backend.main as main

    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=80, freq="D"),
            "open": [100.0] * 80,
            "high": [101.0] * 80,
            "low": [99.0] * 80,
            "close": [100.0 + i * 0.1 for i in range(80)],
            "volume": [1000] * 80,
        }
    )

    monkeypatch.setattr(main, "load_from_db", lambda _ticker: pd.DataFrame())

    fetch_calls = {"count": 0}

    def _fetch(_ticker):
        fetch_calls["count"] += 1
        return df.copy()

    monkeypatch.setattr(main, "fetch_stock_data", _fetch)
    monkeypatch.setattr(main, "predict_prob", lambda _df: {"prob": 0.6})
    monkeypatch.setattr(main, "get_stock_name", lambda _ticker: "TSMC")
    monkeypatch.setattr(main, "get_latest_score_for_ticker", lambda _ticker: None)

    from core import indicators_v2, rise_score_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df.assign(trend_alignment=0, sma20_slope=0, rsi=45, is_squeeze=False, rel_vol=1.0, kd_cross_flag=False))
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=70.0, trend_score_v2=20.0, momentum_score_v2=30.0, volatility_score_v2=20.0))

    response = client.get("/api/v4/stock/2330")
    assert response.status_code == 200
    assert fetch_calls["count"] == 1


def test_api_v4_candidates_cache_key_respects_sort_and_version(monkeypatch):
    import backend.main as main

    sample = [{
        "ticker": "2330.TW",
        "model_version": "v4.1",
        "last_price": 100.0,
        "change_percent": 1.2,
        "total_score": 80.0,
        "ai_probability": 0.8,
        "trend_score": 20.0,
        "momentum_score": 30.0,
        "volatility_score": 30.0,
    }]

    calls = {"count": 0}

    def fake_top_scores(limit, sort_by='score', version=None):
        calls["count"] += 1
        return sample

    monkeypatch.setattr(main, "get_top_scores_from_db", fake_top_scores)
    monkeypatch.setattr(main, "get_stock_name", lambda _t: "TSMC")
    main.clear_api_caches()

    r1 = client.get("/api/v4/sniper/candidates?limit=1&sort=score")
    r2 = client.get("/api/v4/sniper/candidates?limit=1&sort=ai")
    r3 = client.get("/api/v4/sniper/candidates?limit=1&sort=ai&version=v4.2")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
    assert calls["count"] == 3


def test_sync_status_endpoint_returns_snapshot(monkeypatch):
    import backend.main as main

    main._sync_status_update(is_syncing=True, total=1, current=0, current_ticker="2330 TSMC")
    response = client.get("/api/sync/status")
    assert response.status_code == 200
    payload = response.json()

    payload["current"] = 999
    latest = main._sync_status_snapshot()
    assert latest["current"] == 0
    assert latest["is_syncing"] is True

    main._sync_status_update(is_syncing=False, current_ticker="")


def test_api_v4_candidates_rejects_invalid_sort():
    response = client.get("/api/v4/sniper/candidates?sort=invalid")
    assert response.status_code == 422
    body = response.json()
    assert "sort must be one of" in body.get("message", "")


def test_try_start_sync_is_atomic_flag_guard(monkeypatch):
    import backend.main as main

    main._sync_status_update(is_syncing=False)
    assert main._try_start_sync() is True
    assert main._try_start_sync() is False
    main._sync_status_update(is_syncing=False)


def test_api_v4_candidates_uses_batched_indicator_lookup(monkeypatch):
    import backend.main as main

    sample = [{
        "ticker": "2330",
        "model_version": "v4.1",
        "last_price": 100.0,
        "change_percent": 1.2,
        "total_score": 80.0,
        "ai_probability": 0.8,
        "trend_score": 20.0,
        "momentum_score": 30.0,
        "volatility_score": 30.0,
    }]

    calls = {"single": 0, "batch": 0}

    monkeypatch.setattr(main, "get_top_scores_from_db", lambda *args, **kwargs: sample)
    monkeypatch.setattr(main, "get_stock_name", lambda _t: "TSMC")

    def fake_single(_ticker):
        calls["single"] += 1
        return {}

    def fake_batch(tickers):
        calls["batch"] += 1
        return {t: {"rsi": 50, "macd": 0, "macd_signal": 0} for t in tickers}

    monkeypatch.setattr(main, "load_indicators_from_db", fake_single)
    monkeypatch.setattr(main, "load_indicators_for_tickers", fake_batch)

    main.clear_api_caches()
    r = client.get("/api/v4/sniper/candidates?limit=1")

    assert r.status_code == 200
    assert calls["batch"] == 1
    assert calls["single"] == 0


def test_api_v4_candidates_cache_key_changes_after_sync(monkeypatch):
    import backend.main as main

    sample = [{
        "ticker": "2330",
        "model_version": "v4.1",
        "last_price": 100.0,
        "change_percent": 1.2,
        "total_score": 80.0,
        "ai_probability": 0.8,
        "trend_score": 20.0,
        "momentum_score": 30.0,
        "volatility_score": 30.0,
    }]

    call_count = {"db": 0}

    def fake_top_scores(limit, sort_by='score', version=None):
        call_count["db"] += 1
        return sample

    monkeypatch.setattr(main, "get_top_scores_from_db", fake_top_scores)
    monkeypatch.setattr(main, "get_stock_name", lambda _t: "TSMC")
    monkeypatch.setattr(main, "load_indicators_for_tickers", lambda _tickers: {})
    main.clear_api_caches()

    main._sync_status_update(sync_epoch=10)
    r1 = client.get("/api/v4/sniper/candidates?limit=1")

    main._sync_status_update(sync_epoch=11)
    r2 = client.get("/api/v4/sniper/candidates?limit=1")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert call_count["db"] == 2


def test_mark_sync_completed_sets_epoch_and_timestamp():
    import backend.main as main

    before = main._sync_status_snapshot().get("sync_epoch", 0)
    main._sync_status_update(is_syncing=True, last_updated=None)

    main._mark_sync_completed()

    after_snapshot = main._sync_status_snapshot()
    assert after_snapshot["is_syncing"] is False
    assert isinstance(after_snapshot["last_updated"], str)
    assert after_snapshot["sync_epoch"] == before + 1
