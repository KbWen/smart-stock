"""Tests for the Transparency Panel backend (docs/specs/transparency-panel.md v1.0.0).

Covers AC1 (endpoint shape, honest nulls, counts-only) and AC2 (TTL cache +
rate-limit tier presence).
"""
import importlib
import sys

import pytest
from fastapi.testclient import TestClient

# test_backtest.py injects a fake core.data into sys.modules at import time.
# Make sure we bind to the REAL core.data module for this suite.
if "core.data" in sys.modules and not hasattr(sys.modules["core.data"], "get_db_connection"):
    del sys.modules["core.data"]

import core.config  # noqa: E402


@pytest.fixture
def app_client(monkeypatch, tmp_path):
    """Fresh temp DB per test + a TestClient bound to it (triggers app startup)."""
    db_path = tmp_path / "transparency_test.db"
    monkeypatch.setattr(core.config, "DB_PATH", str(db_path))

    from core import data as cdata
    cdata._DB_READY = False
    cdata._DB_READY_PATH = None

    import backend.main as main
    importlib.reload(main)

    from backend.limiter import limiter as shared_limiter
    shared_limiter.reset()

    import backend.routes.transparency as transparency_mod
    transparency_mod._reset_transparency_cache()

    with TestClient(main.app) as client:
        yield client
    shared_limiter.reset()
    transparency_mod._reset_transparency_cache()


FAKE_ENTRY = {
    "timestamp": "20260701_1200",
    "version": "v9.20260701_1200",
    "trained_at": "20260701_1200",
    "samples": 5000,
    "train_samples": 4000,
    "test_samples": 1000,
    "class_distribution": {"hold": 0.6, "buy": 0.3, "strong": 0.1},
    "oos_metrics": {
        "accuracy": 0.72,
        "precision_strong": 0.55,
        "recall_strong": 0.4,
        "f1_strong": 0.46,
        "precision_buy": 0.5,
        "recall_buy": 0.45,
    },
}


# ---------------------------------------------------------------------------
# (a) shape with a model present
# ---------------------------------------------------------------------------

def test_transparency_shape_with_model_present(app_client, monkeypatch):
    import backend.routes.transparency as transparency_mod

    monkeypatch.setattr(
        transparency_mod, "get_model_health",
        lambda: {"status": "ok", "version": "v9.20260701_1200", "message": ""},
    )
    monkeypatch.setattr(transparency_mod, "list_available_models", lambda: [FAKE_ENTRY])

    resp = app_client.get("/api/transparency")
    assert resp.status_code == 200
    body = resp.json()

    assert "data" in body and "model" in body
    data = body["data"]
    assert isinstance(data["universe_size"], int)
    assert "tickers_with_history" in data
    assert "date_range" in data
    coverage = data["coverage"]
    for key in ("with_predict_rows", "with_train_rows", "short_count", "min_predict_rows", "min_train_rows"):
        assert key in coverage
    assert coverage["min_predict_rows"] == core.config.MIN_PREDICT_ROWS
    assert coverage["min_train_rows"] == core.config.MIN_TRAIN_ROWS

    model = body["model"]
    assert model["status"] == "ok"
    assert model["version"] == "v9.20260701_1200"
    assert model["trained_at"] == "20260701_1200"
    assert model["samples"] == 5000
    assert model["test_samples"] == 1000
    assert model["class_distribution"] == FAKE_ENTRY["class_distribution"]
    assert model["oos_metrics"] == FAKE_ENTRY["oos_metrics"]


def test_transparency_trained_at_falls_back_to_timestamp_real_schema(app_client, monkeypatch):
    """Pin the REAL models_history.json schema (trainer.py:427): entries carry
    `timestamp` (YYYYMMDD_HHMM) and have NO `trained_at` key. The endpoint MUST
    fall back to `timestamp`, so a genuinely trained model never reads a null
    training time. (Tenth-man pre-mortem: FAKE_ENTRY carried both keys, which
    would let a future refactor drop the fallback with the suite still green.)"""
    import backend.routes.transparency as transparency_mod

    real_schema_entry = {
        "timestamp": "20260601_2031",
        "version": "v4.20260601_2031",
        # deliberately NO "trained_at" key
        "samples": 1065,
        "test_samples": 213,
        "class_distribution": {"hold": 0.907, "buy": 0.069, "strong": 0.024},
        "oos_metrics": {
            "accuracy": 0.94, "precision_strong": 0.0, "recall_strong": 0.0,
            "f1_strong": 0.0, "precision_buy": 0.0, "recall_buy": 0.0,
        },
    }
    monkeypatch.setattr(
        transparency_mod, "get_model_health",
        lambda: {"status": "degraded", "version": "v4.20260601_2031", "message": "x"},
    )
    monkeypatch.setattr(transparency_mod, "list_available_models", lambda: [real_schema_entry])

    model = app_client.get("/api/transparency").json()["model"]
    assert model["trained_at"] == "20260601_2031"  # fell back to timestamp, not null
    assert model["samples"] == 1065


# ---------------------------------------------------------------------------
# (b) model absent -> honest nulls
# ---------------------------------------------------------------------------

def test_transparency_model_absent_is_honest_null(app_client, monkeypatch):
    import backend.routes.transparency as transparency_mod

    monkeypatch.setattr(
        transparency_mod, "get_model_health",
        lambda: {
            "status": "unavailable",
            "version": "unknown",
            "message": "AI 模型尚未載入或尚未訓練，AI 機率暫時不可用。",
        },
    )
    monkeypatch.setattr(transparency_mod, "list_available_models", lambda: [])

    resp = app_client.get("/api/transparency")
    assert resp.status_code == 200
    model = resp.json()["model"]

    assert model["status"] == "unavailable"
    assert model["trained_at"] is None
    assert model["samples"] is None
    assert model["test_samples"] is None
    assert model["class_distribution"] is None
    assert model["oos_metrics"] is None
    # message must be the real honest string, never fabricated / never a raw exception
    assert "str(" not in resp.text
    assert model["message"] == "AI 模型尚未載入或尚未訓練，AI 機率暫時不可用。"


# ---------------------------------------------------------------------------
# (c) counts-only: raw `short` list must never leak
# ---------------------------------------------------------------------------

def test_transparency_never_leaks_raw_short_list(app_client, monkeypatch):
    import backend.routes.transparency as transparency_mod

    fake_coverage = {
        "universe": 10,
        "with_predict_rows": 4,
        "with_train_rows": 2,
        "short": ["2330", "2317", "1101", "9999", "8888", "7777"],
    }
    monkeypatch.setattr(transparency_mod, "report_history_coverage", lambda: fake_coverage)

    resp = app_client.get("/api/transparency")
    assert resp.status_code == 200
    body = resp.json()

    coverage = body["data"]["coverage"]
    assert isinstance(coverage["short_count"], int)
    assert coverage["short_count"] == 6
    assert "short" not in coverage
    # None of the raw tickers appear anywhere in the serialized response body
    for ticker in fake_coverage["short"]:
        assert ticker not in resp.text


# ---------------------------------------------------------------------------
# (d) cache: two hits within TTL -> underlying scan runs once
# ---------------------------------------------------------------------------

def test_transparency_cache_avoids_recompute_within_ttl(app_client, monkeypatch):
    import backend.routes.transparency as transparency_mod

    call_count = {"n": 0}
    real_coverage = {
        "universe": 3,
        "with_predict_rows": 1,
        "with_train_rows": 0,
        "short": ["1", "2"],
    }

    def _counting_coverage(*args, **kwargs):
        call_count["n"] += 1
        return real_coverage

    monkeypatch.setattr(transparency_mod, "report_history_coverage", _counting_coverage)

    resp1 = app_client.get("/api/transparency")
    resp2 = app_client.get("/api/transparency")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
    assert call_count["n"] == 1, "cache miss should recompute once; second hit within TTL must not rescan"


def test_transparency_cache_recomputes_after_manual_clear(app_client, monkeypatch):
    """Sanity check that the cache-clear helper actually invalidates (used by fixture)."""
    import backend.routes.transparency as transparency_mod

    call_count = {"n": 0}

    def _counting_coverage(*args, **kwargs):
        call_count["n"] += 1
        return {"universe": 1, "with_predict_rows": 0, "with_train_rows": 0, "short": []}

    monkeypatch.setattr(transparency_mod, "report_history_coverage", _counting_coverage)

    app_client.get("/api/transparency")
    transparency_mod._reset_transparency_cache()
    app_client.get("/api/transparency")

    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# (e) rate-limit constant present
# ---------------------------------------------------------------------------

def test_rate_limit_constant_present():
    import backend.routes.transparency as transparency_mod
    assert transparency_mod._RATE_TRANSPARENCY == "10/minute"
