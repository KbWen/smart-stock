"""Tests for scripts/setup_real_ai.py — opt-in real-AI orchestration (v1 #5).

The four steps (backfill / coverage / train / recalc) are injected, so the unit
tests verify the orchestration + honest gating with no network, DB, or training.
"""
import importlib

setup = importlib.import_module("scripts.setup_real_ai")


def test_skips_training_when_insufficient_data():
    calls = []
    res = setup.setup_real_ai(
        backfill_fn=lambda: {"tickers": 100, "rows": 500},
        coverage_fn=lambda: {"with_train_rows": 10, "universe": 100},
        train_fn=lambda: calls.append("train"),
        recalc_fn=lambda: calls.append("recalc"),
        min_tickers=50,
    )
    assert res["trained"] is False
    assert res["reason"] == "insufficient_data"
    assert calls == []  # honest: no training/recalc -> AI stays N/A


def test_trains_then_recalcs_when_sufficient_data():
    calls = []
    res = setup.setup_real_ai(
        backfill_fn=lambda: {"tickers": 2000, "rows": 500000},
        coverage_fn=lambda: {"with_train_rows": 150, "universe": 2000},
        train_fn=lambda: calls.append("train"),
        recalc_fn=lambda: calls.append("recalc"),
        min_tickers=50,
    )
    assert res["trained"] is True
    assert calls == ["train", "recalc"]  # train BEFORE recalc


def test_min_tickers_boundary_is_inclusive():
    calls = []
    res = setup.setup_real_ai(
        backfill_fn=lambda: {"tickers": 100, "rows": 1},
        coverage_fn=lambda: {"with_train_rows": 50},
        train_fn=lambda: calls.append("train"),
        recalc_fn=lambda: calls.append("recalc"),
        min_tickers=50,
    )
    assert res["trained"] is True  # exactly min_tickers -> trains
    assert calls == ["train", "recalc"]
