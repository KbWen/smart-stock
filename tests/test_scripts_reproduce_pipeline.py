"""Tests for scripts/reproduce_pipeline.py (Honest Research Workbench epic #5).

The orchestrator is pure: stages are injectable so we verify ordering, the
honest summary shape, and honest failure reporting without running any real
seed/train/backtest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.reproduce_pipeline import reproduce_pipeline, STAGES, CAVEAT  # noqa: E402

CANONICAL = ["data", "label", "train", "backtest", "eval"]


def test_stage_order_is_canonical():
    assert [s["key"] for s in STAGES] == CANONICAL


def test_map_only_default_has_no_side_effects():
    res = reproduce_pipeline(run=False)
    assert res["ran"] is False
    assert res["stages"] == CANONICAL
    # Honest caveat always present.
    assert "DEGENERATE" in res["caveat"] and res["caveat"] == CAVEAT


def test_runs_stages_in_canonical_order_via_injection():
    order = []

    def mk(name):
        def _fn():
            order.append(name)
            return {"ok": name}
        return _fn

    fns = {k: mk(k) for k in CANONICAL}
    res = reproduce_pipeline(run=True, stage_fns=fns)
    assert res["ran"] is True
    assert order == CANONICAL
    assert res["stages"]["backtest"] == {"ok": "backtest"}
    assert "DEGENERATE" in res["caveat"]


def test_stage_failure_is_reported_honestly_and_run_continues():
    def boom():
        raise RuntimeError("nope")

    fns = {"data": boom}
    fns.update({k: (lambda: {"ok": True}) for k in ("label", "train", "backtest", "eval")})
    res = reproduce_pipeline(run=True, stage_fns=fns)
    # Failure recorded, not raised; later stages still ran.
    assert res["stages"]["data"] == {"error": "nope"}
    assert res["stages"]["eval"] == {"ok": True}
