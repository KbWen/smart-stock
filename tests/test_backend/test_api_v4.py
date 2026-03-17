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
    with patch("backend.routes.stock.run_time_machine", return_value=mock_data):
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
    import backend.routes.stock as stock_route

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

    monkeypatch.setattr(stock_route.score_repo, "get_top_scores", fake_top_scores)
    monkeypatch.setattr(stock_route.stock_repo, "get_stock_name", lambda _t: "TSMC")
    stock_route.clear_api_caches()

    r1 = client.get("/api/v4/sniper/candidates?limit=1")
    r2 = client.get("/api/v4/sniper/candidates?limit=1")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert call_count["db"] == 1


def test_api_v4_candidates_cache_can_be_invalidated(monkeypatch):
    import backend.routes.stock as stock_route

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

    monkeypatch.setattr(stock_route.score_repo, "get_top_scores", fake_top_scores)
    monkeypatch.setattr(stock_route.stock_repo, "get_stock_name", lambda _t: "TSMC")
    stock_route.clear_api_caches()

    r1 = client.get("/api/v4/sniper/candidates?limit=1")
    assert r1.status_code == 200
    assert call_count["db"] == 1

    stock_route.clear_api_caches()

    r2 = client.get("/api/v4/sniper/candidates?limit=1")
    assert r2.status_code == 200
    assert call_count["db"] == 2


def test_api_stock_detail_uses_close_as_last_price(monkeypatch):
    import pandas as pd
    import backend.routes.stock as stock_route

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

    monkeypatch.setattr(stock_route.legacy_stock_detail_service.stock_repo, "fetch_price_history", lambda _ticker, **kwargs: df.copy())
    monkeypatch.setattr(stock_route.legacy_stock_detail_service.stock_repo, "load_price_history", lambda _ticker: df.copy())
    monkeypatch.setattr(stock_route.legacy_stock_detail_service, "predict_prob", lambda _df: {"prob": 0.5, "details": {}})
    monkeypatch.setattr(stock_route.legacy_stock_detail_service, "generate_analysis_report", lambda *_args, **_kwargs: "ok")

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
    import backend.routes.stock as stock_route

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

    monkeypatch.setattr(stock_route.legacy_stock_detail_service.stock_repo, "fetch_price_history", lambda _ticker, **kwargs: df.copy())
    monkeypatch.setattr(stock_route.legacy_stock_detail_service.stock_repo, "load_price_history", lambda _ticker: df.copy())
    monkeypatch.setattr(stock_route.legacy_stock_detail_service, "predict_prob", lambda _df: {"prob": 0.5, "details": {}})
    monkeypatch.setattr(stock_route.legacy_stock_detail_service, "generate_analysis_report", lambda *_args, **_kwargs: "ok")

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
    import backend.routes.stock as stock_route
    stock_route.clear_api_caches()

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

    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "load_price_history", lambda _ticker: df.copy())

    def _should_not_fetch(_ticker, **kwargs):
        raise AssertionError("fetch_price_history should not run when DB snapshot exists")

    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "fetch_price_history", _should_not_fetch)
    monkeypatch.setattr(stock_route.v4_stock_detail_service, "predict_prob", lambda _df: {"prob": 0.55})
    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "get_stock_name", lambda _ticker: "TSMC")
    monkeypatch.setattr(stock_route.v4_stock_detail_service.score_repo, "get_latest_score", lambda _ticker: {"updated_at": "2024-01-10"})

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
    import backend.routes.stock as stock_route
    stock_route.clear_api_caches()

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

    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "load_price_history", lambda _ticker: pd.DataFrame())

    fetch_calls = {"count": 0}

    def _fetch(_ticker, **kwargs):
        fetch_calls["count"] += 1
        return df.copy()

    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "fetch_price_history", _fetch)
    monkeypatch.setattr(stock_route.v4_stock_detail_service, "predict_prob", lambda _df: {"prob": 0.6})
    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "get_stock_name", lambda _ticker: "TSMC")
    monkeypatch.setattr(stock_route.v4_stock_detail_service.score_repo, "get_latest_score", lambda _ticker: None)

    from core import indicators_v2, rise_score_v2
    monkeypatch.setattr(indicators_v2, "compute_v4_indicators", lambda in_df: in_df.assign(trend_alignment=0, sma20_slope=0, rsi=45, is_squeeze=False, rel_vol=1.0, kd_cross_flag=False))
    monkeypatch.setattr(rise_score_v2, "calculate_rise_score_v2", lambda in_df: in_df.assign(total_score_v2=70.0, trend_score_v2=20.0, momentum_score_v2=30.0, volatility_score_v2=20.0))

    response = client.get("/api/v4/stock/2330")
    assert response.status_code == 200
    assert fetch_calls["count"] == 1


def test_api_v4_candidates_cache_key_respects_sort_and_version(monkeypatch):
    import backend.routes.stock as stock_route

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

    monkeypatch.setattr(stock_route.score_repo, "get_top_scores", fake_top_scores)
    monkeypatch.setattr(stock_route.stock_repo, "get_stock_name", lambda _t: "TSMC")
    stock_route.clear_api_caches()

    r1 = client.get("/api/v4/sniper/candidates?limit=1&sort=score")
    r2 = client.get("/api/v4/sniper/candidates?limit=1&sort=ai")
    r3 = client.get("/api/v4/sniper/candidates?limit=1&sort=ai&version=v4.2")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
    assert calls["count"] == 3


def test_sync_status_endpoint_returns_snapshot(monkeypatch):
    import backend.routes.sync as sync_route

    sync_route._sync_status_update(is_syncing=True, total=1, current=0, current_ticker="2330 TSMC")
    response = client.get("/api/sync/status")
    assert response.status_code == 200
    payload = response.json()

    payload["current"] = 999
    latest = sync_route.get_sync_status_snapshot()
    assert latest["current"] == 0
    assert latest["is_syncing"] is True

    sync_route._sync_status_update(is_syncing=False, current_ticker="")


def test_api_v4_candidates_rejects_invalid_sort():
    response = client.get("/api/v4/sniper/candidates?sort=invalid")
    assert response.status_code == 422
    body = response.json()
    assert "sort must be one of" in body.get("message", "")


def test_try_start_sync_is_atomic_flag_guard(monkeypatch):
    import backend.routes.sync as sync_route

    sync_route._sync_status_update(is_syncing=False)
    assert sync_route._try_start_sync() is True
    assert sync_route._try_start_sync() is False
    sync_route._sync_status_update(is_syncing=False)


def test_api_v4_candidates_uses_batched_indicator_lookup(monkeypatch):
    import backend.routes.stock as stock_route

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

    monkeypatch.setattr(stock_route.score_repo, "get_top_scores", lambda *args, **kwargs: sample)
    monkeypatch.setattr(stock_route.stock_repo, "get_stock_name", lambda _t: "TSMC")

    def fake_single(_ticker):
        calls["single"] += 1
        return {}

    def fake_batch(tickers):
        calls["batch"] += 1
        return {t: {"rsi": 50, "macd": 0, "macd_signal": 0} for t in tickers}

    monkeypatch.setattr(stock_route.indicator_repo, "load_for_ticker", fake_single)
    monkeypatch.setattr(stock_route.indicator_repo, "load_for_tickers", fake_batch)

    stock_route.clear_api_caches()
    r = client.get("/api/v4/sniper/candidates?limit=1")

    assert r.status_code == 200
    assert calls["batch"] == 1
    assert calls["single"] == 0


def test_api_v4_candidates_cache_key_changes_after_sync(monkeypatch):
    import backend.routes.stock as stock_route
    import backend.routes.sync as sync_route

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

    monkeypatch.setattr(stock_route.score_repo, "get_top_scores", fake_top_scores)
    monkeypatch.setattr(stock_route.stock_repo, "get_stock_name", lambda _t: "TSMC")
    monkeypatch.setattr(stock_route.indicator_repo, "load_for_tickers", lambda _tickers: {})
    stock_route.clear_api_caches()

    sync_route._sync_status_update(sync_epoch=10)
    r1 = client.get("/api/v4/sniper/candidates?limit=1")

    sync_route._sync_status_update(sync_epoch=11)
    r2 = client.get("/api/v4/sniper/candidates?limit=1")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert call_count["db"] == 2


def test_mark_sync_completed_sets_epoch_and_timestamp():
    import backend.routes.sync as sync_route

    before = sync_route.get_sync_status_snapshot().get("sync_epoch", 0)
    sync_route._sync_status_update(is_syncing=True, last_updated=None)

    sync_route._mark_sync_completed()

    after_snapshot = sync_route.get_sync_status_snapshot()
    assert after_snapshot["is_syncing"] is False
    assert isinstance(after_snapshot["last_updated"], str)
    assert after_snapshot["sync_epoch"] == before + 1


# ── Schema Parity Tests (backend-refactor-modular AC#8) ───────────────────────


def test_v4_candidates_schema_parity(monkeypatch):
    """All field names and types of /api/v4/sniper/candidates must match the contract."""
    import backend.routes.stock as stock_route

    sample_score = [{
        "ticker": "2330.TW",
        "model_version": "v4.1",
        "last_price": 580.0,
        "change_percent": 1.5,
        "total_score": 82.0,
        "ai_probability": 0.75,
        "trend_score": 30.0,
        "momentum_score": 32.0,
        "volatility_score": 20.0,
        "updated_at": "2026-03-17",
    }]
    sample_inds = {
        "2330.TW": {"rsi": 58.0, "macd": 1.2, "macd_signal": 0.8, "rel_vol": 1.3}
    }

    monkeypatch.setattr(stock_route.score_repo, "get_top_scores", lambda *a, **kw: sample_score)
    monkeypatch.setattr(stock_route.stock_repo, "get_stock_name", lambda _t: "TSMC")
    monkeypatch.setattr(stock_route.indicator_repo, "load_for_tickers", lambda _t: sample_inds)
    monkeypatch.setattr(stock_route.v4_candidates_service.system_repo, "get_sync_epoch", lambda: 0)
    stock_route.clear_api_caches()

    resp = client.get("/api/v4/sniper/candidates?limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 1

    c = data[0]
    str_fields = ["ticker", "name"]
    num_fields = [
        "price", "change_percent", "rise_score", "ai_prob",
        "trend", "momentum", "volatility", "rsi_14", "macd_diff", "volume_ratio",
    ]
    for f in str_fields:
        assert f in c and isinstance(c[f], str), f"Field '{f}' missing or wrong type; got {type(c.get(f))}"
    for f in num_fields:
        assert f in c and isinstance(c[f], (int, float)), f"Field '{f}' missing or wrong type; got {type(c.get(f))}"
    assert "updated_at" in c


def test_v4_stock_detail_schema_parity(monkeypatch):
    """All field names and types of /api/v4/stock/{ticker} must match the documented contract."""
    import pandas as pd
    import backend.routes.stock as stock_route
    stock_route.clear_api_caches()

    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=80, freq="D"),
        "open": [100.0] * 80,
        "high": [101.0] * 80,
        "low": [99.0] * 80,
        "close": [100.0 + i * 0.1 for i in range(80)],
        "volume": [1000] * 80,
    })

    monkeypatch.setattr(stock_route.v4_stock_detail_service.score_repo, "get_latest_score", lambda _t: None)
    monkeypatch.setattr(stock_route.v4_stock_detail_service.indicator_repo, "load_for_ticker", lambda _t: {})
    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "load_price_history", lambda _t: df.copy())
    monkeypatch.setattr(stock_route.v4_stock_detail_service.stock_repo, "get_stock_name", lambda _t: "TSMC")
    monkeypatch.setattr(stock_route.v4_stock_detail_service.system_repo, "get_sync_epoch", lambda: 0)
    monkeypatch.setattr(stock_route.v4_stock_detail_service, "predict_prob", lambda _df: {"prob": 0.65})

    from core import indicators_v2, rise_score_v2
    monkeypatch.setattr(
        indicators_v2, "compute_v4_indicators",
        lambda in_df: in_df.assign(
            trend_alignment=1, sma20_slope=0.5, rsi=55.0,
            is_squeeze=False, rel_vol=1.2, kd_cross_flag=False,
        ),
    )
    monkeypatch.setattr(
        rise_score_v2, "calculate_rise_score_v2",
        lambda in_df: in_df.assign(
            total_score_v2=80.0, trend_score_v2=30.0,
            momentum_score_v2=30.0, volatility_score_v2=20.0,
        ),
    )

    resp = client.get("/api/v4/stock/2330")
    assert resp.status_code == 200
    body = resp.json()

    # Top-level primitive fields
    assert isinstance(body["ticker"], str), "ticker must be str"
    assert isinstance(body["name"], str), "name must be str"
    assert isinstance(body["price"], (int, float)), "price must be numeric"
    assert isinstance(body["ai_probability"], (int, float)), "ai_probability must be numeric"
    assert isinstance(body["analyst_summary"], str), "analyst_summary must be str"
    assert body.get("updated_at") is None or isinstance(body["updated_at"], str)

    # rise_score_breakdown sub-object
    rb = body["rise_score_breakdown"]
    assert isinstance(rb, dict), "rise_score_breakdown must be a dict"
    for key in ["total", "trend", "momentum", "volatility"]:
        assert key in rb and isinstance(rb[key], (int, float)), \
            f"rise_score_breakdown.{key} missing or wrong type"

    # signals sub-object
    sig = body["signals"]
    assert isinstance(sig, dict), "signals must be a dict"
    for key in ["squeeze", "golden_cross", "volume_spike"]:
        assert key in sig and isinstance(sig[key], bool), \
            f"signals.{key} missing or wrong type; got {type(sig.get(key))}"


def test_v4_meta_schema_parity(monkeypatch):
    """All field names and types of /api/v4/meta response must match the documented contract."""
    import backend.routes.stock as stock_route

    score_row = {
        "total_score": 80.0, "trend_score": 30.0, "momentum_score": 30.0,
        "volatility_score": 20.0, "last_price": 580.0, "change_percent": 1.2,
        "ai_probability": 0.7, "updated_at": "2026-03-17", "model_version": "v4.1",
    }
    ind_row = {
        "rsi": 55.0, "macd": 1.5, "macd_signal": 1.0, "rel_vol": 1.8,
        "is_squeeze": True, "kd_cross_flag": False,
    }

    monkeypatch.setattr(
        stock_route.v4_meta_service.score_repo,
        "load_latest_scores_for_tickers",
        lambda tickers: {t: score_row for t in tickers},
    )
    monkeypatch.setattr(
        stock_route.v4_meta_service.indicator_repo,
        "load_for_tickers",
        lambda tickers: {t: ind_row for t in tickers},
    )
    monkeypatch.setattr(stock_route.v4_meta_service.stock_repo, "get_stock_name", lambda _t: "TSMC")

    resp = client.get("/api/v4/meta?tickers=2330")
    assert resp.status_code == 200
    body = resp.json()

    assert "data" in body and isinstance(body["data"], dict), "Response must have 'data' dict"
    assert len(body["data"]) == 1

    entry = next(iter(body["data"].values()))
    num_fields = [
        "total_score", "trend_score", "momentum_score", "volatility_score",
        "last_price", "change_percent", "ai_prob",
    ]
    for f in num_fields:
        assert f in entry and isinstance(entry[f], (int, float)), \
            f"data[ticker].{f} missing or wrong type; got {type(entry.get(f))}"
    assert isinstance(entry["name"], str), "name must be str"
    assert isinstance(entry["model_version"], str), "model_version must be str"

    sig = entry["signals"]
    assert isinstance(sig, dict), "signals must be a dict"
    for key in ["squeeze", "golden_cross", "volume_spike"]:
        assert key in sig and isinstance(sig[key], bool), \
            f"signals.{key} missing or wrong type; got {type(sig.get(key))}"
    for key in ["rsi", "macd_diff", "rel_vol"]:
        assert key in sig and isinstance(sig[key], (int, float)), \
            f"signals.{key} missing or wrong type; got {type(sig.get(key))}"


# ── Performance Benchmark (api-refactor-perf AC#3) ───────────────────────────


def test_v4_meta_bulk_50_tickers_single_batch_and_under_500ms(monkeypatch):
    """GET /api/v4/meta with 50 tickers must use exactly 1 batch DB call and finish < 500ms."""
    import time
    import backend.routes.stock as stock_route

    tickers = [f"STOCK{i:02d}" for i in range(50)]
    tickers_param = ",".join(tickers)

    batch_calls = {"score": 0, "indicator": 0}

    def fake_scores(t_list):
        batch_calls["score"] += 1
        return {
            t: {
                "total_score": 70.0, "trend_score": 25.0, "momentum_score": 25.0,
                "volatility_score": 20.0, "last_price": 100.0, "change_percent": 0.5,
                "ai_probability": 0.6, "updated_at": "2026-03-17", "model_version": "v4.1",
            }
            for t in t_list
        }

    def fake_indicators(t_list):
        batch_calls["indicator"] += 1
        return {
            t: {"rsi": 50.0, "macd": 0.5, "macd_signal": 0.3, "rel_vol": 1.0,
                "is_squeeze": False, "kd_cross_flag": False}
            for t in t_list
        }

    monkeypatch.setattr(
        stock_route.v4_meta_service.score_repo, "load_latest_scores_for_tickers", fake_scores
    )
    monkeypatch.setattr(
        stock_route.v4_meta_service.indicator_repo, "load_for_tickers", fake_indicators
    )
    monkeypatch.setattr(stock_route.v4_meta_service.stock_repo, "get_stock_name", lambda _t: "TestCo")

    t0 = time.perf_counter()
    resp = client.get(f"/api/v4/meta?tickers={tickers_param}")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 50, f"Expected 50 entries, got {len(data)}"

    # Proves O(1) batch DB access — not 50 individual round-trips
    assert batch_calls["score"] == 1, \
        f"Expected 1 batch score call, got {batch_calls['score']} (sequential per-ticker calls detected)"
    assert batch_calls["indicator"] == 1, \
        f"Expected 1 batch indicator call, got {batch_calls['indicator']} (sequential per-ticker calls detected)"

    # With mocked repos the overhead is pure Python/FastAPI — must be well under 500ms
    assert elapsed_ms < 500, f"50-ticker meta took {elapsed_ms:.1f}ms; must be < 500ms"
