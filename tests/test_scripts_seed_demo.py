"""Tests for scripts/seed_demo.py — offline demo seeding.

spec_ref: docs/specs/onboarding-quickstart.md (AC2, AC5)
Verifies the demo seed populates price history AND scores from the bundled
fixture WITHOUT any network access, and is idempotent.
"""
import importlib
import sqlite3
import sys

import pandas as pd
import pytest

import core.config

# Guard: other test modules (e.g. test_backtest) inject a fake `core.data` into
# sys.modules. Restore the real one, then pre-import the modules that bind it so
# their bindings are the REAL core.data regardless of later pollution.
if "core.data" in sys.modules and not hasattr(sys.modules["core.data"], "standardize_ticker"):
    del sys.modules["core.data"]

seed_demo = importlib.import_module("scripts.seed_demo")
import backend.recalculate  # noqa: E402,F401 — bind recalculate to the real core.data at collection


def _fresh_db(monkeypatch, tmp_path):
    db = tmp_path / "demo.db"
    monkeypatch.setattr(core.config, "DB_PATH", str(db))
    from core import data as cdata
    cdata._DB_READY = False  # force schema init on the new path
    # Hard offline guarantee: any network fetch is a test failure.
    monkeypatch.setattr(
        cdata, "fetch_stock_data",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("seed must not hit the network")),
    )
    return str(db)


def test_seed_demo_populates_offline(monkeypatch, tmp_path):
    db = _fresh_db(monkeypatch, tmp_path)
    # Pin a deterministic model state (other suite tests pollute the predictor cache).
    monkeypatch.setattr(backend.recalculate, "get_model_version", lambda: "v4.demo")
    monkeypatch.setattr(backend.recalculate, "predict_prob", lambda df: {"prob": 0.5})
    res = seed_demo.seed(force=True)

    assert res["loaded"] > 0
    assert len(res["tickers"]) >= 3
    assert "2330" in res["tickers"]

    conn = sqlite3.connect(db)
    try:
        n_hist = conn.execute("SELECT COUNT(*) FROM stock_history").fetchone()[0]
        n_scores = conn.execute("SELECT COUNT(*) FROM stock_scores").fetchone()[0]
    finally:
        conn.close()
    assert n_hist > 0           # price history loaded from the fixture
    assert n_scores > 0         # scores computed offline by recalculate


def test_seed_demo_is_idempotent_without_force(monkeypatch, tmp_path, capsys):
    _fresh_db(monkeypatch, tmp_path)
    seed_demo.seed(force=True)              # first seed loads
    capsys.readouterr()
    res2 = seed_demo.seed(force=False)      # second seed must skip the load
    out = capsys.readouterr().out
    assert res2["loaded"] == 0
    assert "Skipping load" in out


def test_seed_demo_works_without_model(monkeypatch, tmp_path):
    """Honest fresh-clone path: no bundled model → technical scores still compute, AI = NULL."""
    db = _fresh_db(monkeypatch, tmp_path)
    monkeypatch.setattr(backend.recalculate, "get_model_version", lambda: "unknown")
    monkeypatch.setattr(backend.recalculate, "predict_prob", lambda df: {"prob": None})

    seed_demo.seed(force=True)

    conn = sqlite3.connect(db)
    try:
        n_scores = conn.execute("SELECT COUNT(*) FROM stock_scores").fetchone()[0]
        n_ai = conn.execute(
            "SELECT COUNT(*) FROM stock_scores WHERE ai_probability IS NOT NULL"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n_scores > 0   # technical scores computed even with no model
    assert n_ai == 0      # AI probability is honestly NULL without a model


def test_seed_demo_missing_fixture_raises(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path)
    with pytest.raises(FileNotFoundError):
        seed_demo.seed(force=True, fixture=str(tmp_path / "nope.csv"))


def test_demo_fixture_has_credible_largecap_set():
    """The bundled demo fixture features recognizable large-cap TWSE names (not an
    obscure handful) so the first-run 'Top Candidates' looks credible (v1 #2)."""
    df = pd.read_csv(seed_demo.FIXTURE, dtype={"ticker": str})
    tickers = set(df["ticker"].unique())
    assert len(tickers) >= 12, f"expected a credible demo set, got {len(tickers)} tickers"
    # household names that should anchor the demo
    for code in ("2330", "2317", "2454", "2412"):
        assert code in tickers, f"missing recognizable ticker {code}"
    # enough history per ticker for technical indicators + a meaningful chart
    assert df.groupby("ticker").size().min() >= 200
