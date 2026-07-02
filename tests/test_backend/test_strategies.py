"""Tests for the Strategy Lab backend (docs/specs/strategy-lab.md v1.1.0).

Covers AC1 (persistence + seed/recalc guard), AC2 (CRUD + validation),
AC3 (compare bounds/throttle/honesty), AC4 (idempotent preset seeding),
and the backend half of AC7.
"""
import importlib
import json
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
    db_path = tmp_path / "strategies_test.db"
    monkeypatch.setattr(core.config, "DB_PATH", str(db_path))

    from core import data as cdata
    cdata._DB_READY = False
    cdata._DB_READY_PATH = None

    import backend.main as main
    importlib.reload(main)

    from backend.limiter import limiter as shared_limiter
    shared_limiter.reset()

    with TestClient(main.app) as client:
        yield client
    shared_limiter.reset()


def _params(**overrides):
    base = {
        "target_gain": 0.15,
        "stop_loss": 0.05,
        "holding_days": 20,
        "commission_rate": 0.001425,
        "tax_rate": 0.003,
        "slippage_rate": 0.001,
        "days_ago": 30,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# CRUD happy / invalid / duplicate
# ---------------------------------------------------------------------------

def test_list_strategies_includes_seeded_presets(app_client):
    resp = app_client.get("/api/strategies")
    assert resp.status_code == 200
    data = resp.json()
    names = {s["name"] for s in data}
    assert {"Tight", "Balanced", "Wide"}.issubset(names)


def test_create_strategy_happy_path(app_client):
    resp = app_client.post(
        "/api/strategies",
        json={"name": "My Strategy", "params": _params(), "notes": "test note"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My Strategy"
    assert data["params"]["target_gain"] == 0.15
    assert data["notes"] == "test note"
    assert "id" in data


def test_create_strategy_duplicate_name_returns_409(app_client):
    body = {"name": "Dup Strategy", "params": _params(), "notes": None}
    r1 = app_client.post("/api/strategies", json=body)
    assert r1.status_code == 200
    r2 = app_client.post("/api/strategies", json=body)
    assert r2.status_code == 409
    assert "str(" not in r2.text  # no raw exception leakage


def test_create_strategy_rejects_empty_name(app_client):
    resp = app_client.post("/api/strategies", json={"name": "   ", "params": _params()})
    assert resp.status_code == 422


def test_get_delete_strategy_roundtrip(app_client):
    created = app_client.post(
        "/api/strategies", json={"name": "ToDelete", "params": _params()}
    ).json()
    sid = created["id"]

    del_resp = app_client.delete(f"/api/strategies/{sid}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"ok": True}

    list_resp = app_client.get("/api/strategies")
    assert all(s["id"] != sid for s in list_resp.json())


def test_delete_nonexistent_strategy_returns_404(app_client):
    resp = app_client.delete("/api/strategies/999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# StrategyParams validation: bounds, NaN/Inf, missing key, extra key
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field,value", [
    ("target_gain", 0.0),
    ("target_gain", 0.51),
    ("stop_loss", 0.0),
    ("stop_loss", 0.51),
    ("holding_days", 0),
    ("holding_days", 91),
    ("commission_rate", -0.01),
    ("commission_rate", 0.06),
    ("tax_rate", 0.06),
    ("slippage_rate", 0.06),
    ("days_ago", 0),
])
def test_strategy_params_rejects_out_of_range(app_client, field, value):
    params = _params(**{field: value})
    resp = app_client.post("/api/strategies", json={"name": f"bad-{field}", "params": params})
    assert resp.status_code == 422


@pytest.mark.parametrize("field", ["target_gain", "stop_loss", "commission_rate", "tax_rate", "slippage_rate"])
def test_strategy_params_rejects_nan_and_inf(app_client, field):
    for bad in (float("nan"), float("inf"), float("-inf")):
        params = _params(**{field: bad})
        # NaN/Inf are not valid JSON; send as raw text with allow_nan-style values.
        payload = json.dumps({"name": "bad-nan", "params": params}).replace(
            "NaN", "NaN"
        )
        # httpx/starlette TestClient .json= uses stdlib json.dumps which raises on NaN
        # unless allow_nan (default True) -> emits literal NaN/Infinity tokens which
        # FastAPI's default json parser (orjson/ujson may reject, stdlib accepts).
        resp = app_client.post(
            "/api/strategies",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422, f"{field}={bad} should be rejected, got {resp.status_code}: {resp.text}"


def test_strategy_params_rejects_missing_key(app_client):
    params = _params()
    del params["holding_days"]
    resp = app_client.post("/api/strategies", json={"name": "missing-key", "params": params})
    assert resp.status_code == 422


def test_strategy_params_rejects_extra_key(app_client):
    params = _params()
    params["bogus_extra_field"] = 123
    resp = app_client.post("/api/strategies", json={"name": "extra-key", "params": params})
    assert resp.status_code == 422


def test_strategy_in_rejects_unknown_top_level_key(app_client):
    resp = app_client.post(
        "/api/strategies",
        json={"name": "top-extra", "params": _params(), "unexpected": True},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT partial update: notes-only edit must still validate merged params
# ---------------------------------------------------------------------------

def test_put_notes_only_still_returns_valid_merged_record(app_client):
    created = app_client.post(
        "/api/strategies", json={"name": "Notes Edit", "params": _params(), "notes": "old"}
    ).json()
    sid = created["id"]

    resp = app_client.put(f"/api/strategies/{sid}", json={"notes": "new note"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "new note"
    assert data["name"] == "Notes Edit"
    assert data["params"]["target_gain"] == 0.15  # untouched, still valid


def test_put_rename_duplicate_name_returns_409(app_client):
    app_client.post("/api/strategies", json={"name": "Existing1", "params": _params()})
    created2 = app_client.post(
        "/api/strategies", json={"name": "Existing2", "params": _params()}
    ).json()

    resp = app_client.put(f"/api/strategies/{created2['id']}", json={"name": "Existing1"})
    assert resp.status_code == 409


def test_put_nonexistent_strategy_returns_404(app_client):
    resp = app_client.put("/api/strategies/999999", json={"notes": "x"})
    assert resp.status_code == 404


def test_put_params_out_of_range_rejected(app_client):
    created = app_client.post(
        "/api/strategies", json={"name": "ToBreak", "params": _params()}
    ).json()
    resp = app_client.put(
        f"/api/strategies/{created['id']}",
        json={"params": _params(target_gain=0.99)},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Compare API
# ---------------------------------------------------------------------------

def test_compare_multi_id_happy_path(app_client, monkeypatch):
    s1 = app_client.post("/api/strategies", json={"name": "CmpA", "params": _params()}).json()
    s2 = app_client.post("/api/strategies", json={"name": "CmpB", "params": _params(holding_days=30)}).json()

    fake_summary = {"avg_net_return": 0.01, "net_win_rate": 0.5}

    import backend.routes.strategies as strategies_mod
    monkeypatch.setattr(
        strategies_mod, "run_time_machine",
        lambda **kwargs: {"summary": fake_summary, "top_picks": [{"ticker": "2330"}]},
    )

    resp = app_client.get(f"/api/strategies/compare?ids={s1['id']},{s2['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert "context" in data
    assert len(data["results"]) == 2
    for r in data["results"]:
        assert r["summary"] == fake_summary
        assert "top_picks" not in r


def test_compare_runs_serialized_not_concurrent(app_client, monkeypatch):
    """Compare must run the per-strategy backtests ONE AT A TIME. run_time_machine
    is itself internally parallel over a ~300-candidate pool, so running compares
    concurrently would multiply live thread/CPU load and can stall the single
    uvicorn worker on a full-universe DB (tenth-man pre-mortem finding)."""
    import threading
    import time

    s1 = app_client.post("/api/strategies", json={"name": "SerA", "params": _params()}).json()
    s2 = app_client.post("/api/strategies", json={"name": "SerB", "params": _params(holding_days=30)}).json()
    s3 = app_client.post("/api/strategies", json={"name": "SerC", "params": _params(holding_days=40)}).json()

    lock = threading.Lock()
    state = {"active": 0, "max_active": 0}

    def fake_run(**kwargs):
        with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        time.sleep(0.05)
        with lock:
            state["active"] -= 1
        return {"summary": {"avg_net_return": 0.01}}

    import backend.routes.strategies as strategies_mod
    monkeypatch.setattr(strategies_mod, "run_time_machine", fake_run)

    resp = app_client.get(f"/api/strategies/compare?ids={s1['id']},{s2['id']},{s3['id']}")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 3
    # Core assertion: at most ONE backtest ran at any instant.
    assert state["max_active"] == 1


def test_compare_dedupes_ids(app_client, monkeypatch):
    s1 = app_client.post("/api/strategies", json={"name": "DedupA", "params": _params()}).json()

    resp = app_client.get(f"/api/strategies/compare?ids={s1['id']},{s1['id']}")
    assert resp.status_code == 422


def test_compare_rejects_more_than_4_ids(app_client):
    ids = []
    for i in range(5):
        s = app_client.post(
            "/api/strategies", json={"name": f"Many{i}", "params": _params()}
        ).json()
        ids.append(str(s["id"]))
    resp = app_client.get(f"/api/strategies/compare?ids={','.join(ids)}")
    assert resp.status_code == 422


def test_compare_rejects_non_integer_token(app_client):
    resp = app_client.get("/api/strategies/compare?ids=1,abc")
    assert resp.status_code == 422


def test_compare_rejects_empty_ids(app_client):
    resp = app_client.get("/api/strategies/compare?ids=")
    assert resp.status_code == 422


def test_compare_per_id_error_slot_has_no_exception_text(app_client, monkeypatch):
    s1 = app_client.post("/api/strategies", json={"name": "Failing", "params": _params()}).json()

    import backend.routes.strategies as strategies_mod

    def _boom(**kwargs):
        raise RuntimeError("super secret internal stack trace details 12345")

    monkeypatch.setattr(strategies_mod, "run_time_machine", _boom)

    resp = app_client.get(f"/api/strategies/compare?ids={s1['id']}")
    assert resp.status_code == 200
    data = resp.json()
    result = data["results"][0]
    assert result["error"] == "backtest failed for this strategy"
    assert "12345" not in resp.text
    assert "secret" not in resp.text


def test_compare_timeout_returns_generic_error_slot(app_client, monkeypatch):
    s1 = app_client.post("/api/strategies", json={"name": "SlowOne", "params": _params()}).json()

    import backend.routes.strategies as strategies_mod

    def _slow(**kwargs):
        import time as _time
        _time.sleep(2)
        return {"summary": {}, "top_picks": []}

    monkeypatch.setattr(strategies_mod, "run_time_machine", _slow)
    monkeypatch.setattr(strategies_mod, "_COMPARE_TIMEOUT_SECONDS", 0.05)

    resp = app_client.get(f"/api/strategies/compare?ids={s1['id']}")
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] == "backtest failed for this strategy"


def test_compare_context_shape(app_client, monkeypatch):
    s1 = app_client.post("/api/strategies", json={"name": "CtxCheck", "params": _params()}).json()

    import backend.routes.strategies as strategies_mod
    monkeypatch.setattr(
        strategies_mod, "run_time_machine",
        lambda **kwargs: {"summary": {"avg_net_return": 0.0}, "top_picks": []},
    )

    resp = app_client.get(f"/api/strategies/compare?ids={s1['id']}")
    assert resp.status_code == 200
    context = resp.json()["context"]
    # No stock_history rows seeded in this fresh temp DB -> honestly None, never fabricated.
    assert context is None


# ---------------------------------------------------------------------------
# Rate limit tier presence
# ---------------------------------------------------------------------------

def test_rate_limit_constants_present():
    import backend.routes.strategies as strategies_mod
    assert strategies_mod._RATE_STRATEGY == "30/minute"
    assert strategies_mod._RATE_COMPARE == "5/minute"


# ---------------------------------------------------------------------------
# Idempotent seed_presets()
# ---------------------------------------------------------------------------

def test_seed_presets_is_idempotent(app_client):
    from backend.repositories.strategy_repo import StrategyRepository
    repo = StrategyRepository()

    before = len(app_client.get("/api/strategies").json())
    result1 = repo.seed_presets()
    result2 = repo.seed_presets()
    after = len(app_client.get("/api/strategies").json())

    assert after == before  # no dupes created
    assert result2["inserted"] == 0
    assert result1["suggested_default"] == "Balanced"
    assert result2["suggested_default"] == "Balanced"


# ---------------------------------------------------------------------------
# AC1 guard: seed_demo / recalculate_all must not touch strategies table
# ---------------------------------------------------------------------------

def test_seed_demo_and_recalculate_do_not_delete_strategies(app_client, monkeypatch, tmp_path):
    created = app_client.post(
        "/api/strategies", json={"name": "SurvivorStrategy", "params": _params()}
    ).json()
    sid = created["id"]

    import importlib as _importlib
    seed_demo = _importlib.import_module("scripts.seed_demo")

    monkeypatch.setattr(
        seed_demo, "fetch_stock_data" if hasattr(seed_demo, "fetch_stock_data") else "FIXTURE",
        getattr(seed_demo, "fetch_stock_data", seed_demo.FIXTURE),
        raising=False,
    )

    import backend.recalculate as recalculate_mod
    monkeypatch.setattr(recalculate_mod, "get_model_version", lambda: "v-test")
    monkeypatch.setattr(recalculate_mod, "predict_prob", lambda df: {"prob": 0.5})

    seed_demo.seed(force=True)
    recalculate_mod.recalculate_all(incremental=False)

    resp = app_client.get("/api/strategies")
    ids = [s["id"] for s in resp.json()]
    assert sid in ids, "strategies row must survive seed_demo + recalculate_all (spec AC1)"
