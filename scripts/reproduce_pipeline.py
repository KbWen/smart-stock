#!/usr/bin/env python3
"""Reproducible reference: the honest end-to-end pipeline in one command (epic #5).

Maps — and optionally RUNS — the full `data -> label -> train -> backtest -> eval`
flow so a developer / learner can read AND reproduce the mechanism end to end.

Honesty-first: on the offline demo (or ANY small dataset) the trained model is
DEGENERATE — precision/recall on Buy/StrongBuy collapse to ~0 and accuracy is
inflated by the dominant Hold class. This script discloses that at every stage
and points at the real code; it demonstrates the MECHANISM, not a production
model. A non-degenerate model needs ~1000+ rows/ticker and ~92+ tickers (the OOS
floor from docs/specs/ml-label-oos-evaluation.md). Full walkthrough: docs/REPRODUCE.md.

Usage:
  python scripts/reproduce_pipeline.py          # print the pipeline map (safe, fast, no side effects)
  python scripts/reproduce_pipeline.py --run     # run the offline demo pipeline end to end
"""
import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# One row per pipeline stage: what it does, the REAL code behind it, and the
# single command to run just that stage. Kept in sync with docs/REPRODUCE.md.
STAGES = [
    {"key": "data", "title": "Data",
     "what": "Load price history (offline demo fixture, or authoritative TWSE/TPEX bulk backfill).",
     "code": "scripts/seed_demo.py · core/bulk_history.py",
     "cmd": "python scripts/seed_demo.py   (offline)  |  python scripts/fast_backfill.py --days 1100  (real)"},
    {"key": "label", "title": "Label",
     "what": "ATR volatility-scaled triple-barrier labels; inspect the Hold/Buy/StrongBuy class distribution.",
     "code": "core/ai/common.py (LABEL_MODE=atr) · core/ai/label_analysis.py:label_distribution",
     "cmd": "library — computed inside training; distributions surfaced by scripts/eval_label_modes.py"},
    {"key": "train", "title": "Train",
     "what": "Train the GB+RF+MLP ensemble; OOS metrics are recorded to models_history.json.",
     "code": "backend/train_ai.py · core/ai/trainer.py",
     "cmd": "python backend/train_ai.py"},
    {"key": "backtest", "title": "Backtest",
     "what": "Net-of-cost sniper backtest (TW commission/tax/slippage; Sharpe, drawdown).",
     "code": "backend/backtest.py:run_time_machine",
     "cmd": "GET /api/backtest   (or import run_time_machine)"},
    {"key": "eval", "title": "OOS Eval",
     "what": "Out-of-sample precision/recall for Buy/StrongBuy (atr vs fixed labeling).",
     "code": "scripts/eval_label_modes.py",
     "cmd": "python scripts/eval_label_modes.py"},
]

CAVEAT = (
    "HONEST CAVEAT: on the offline demo / any small dataset the trained model is DEGENERATE "
    "(Buy/StrongBuy precision & recall ~0; accuracy inflated by the Hold class). It demonstrates "
    "the MECHANISM, not a production-quality model. A non-degenerate model needs ~1000+ rows/ticker "
    "and ~92+ tickers (the OOS floor). model_health discloses a weak model honestly in the UI. "
    "See docs/REPRODUCE.md and docs/specs/ml-label-oos-evaluation.md."
)


def print_map() -> None:
    print("Honest end-to-end pipeline — data -> label -> train -> backtest -> eval")
    print("(read docs/REPRODUCE.md for the full walkthrough)\n")
    for i, s in enumerate(STAGES, 1):
        print(f"  {i}. {s['title']:<9} {s['what']}")
        print(f"       code: {s['code']}")
        print(f"       run : {s['cmd']}\n")
    print(CAVEAT)


def _manual(cmd: str):
    """A stage that is heavier/opt-in and is NOT auto-run — reported honestly with
    its command rather than faked. (train/eval are slow and, on demo data,
    degenerate; the map + docs/REPRODUCE.md tell you exactly how to run them.)"""
    return lambda: {"auto_ran": False, "manual_cmd": cmd,
                    "note": "heavier / opt-in — run manually (see docs/REPRODUCE.md)"}


def _default_stage_fns() -> dict:
    """Lazy real wiring for --run (offline demo). Only the fast, robust stages
    auto-run in-process (data seed + a net-of-cost backtest, which genuinely work
    on demo data); label/train/eval are flagged manual (honest — not faked).
    Imports are lazy so `print_map` (the default) has zero heavy imports."""
    def data():
        from scripts.seed_demo import main as seed_main
        seed_main([])
        from core.data import get_history_context
        return {"auto_ran": True, "history": get_history_context()}

    def backtest():
        from backend.backtest import run_time_machine
        res = run_time_machine(days_ago=30, limit=20)
        return {"auto_ran": True, "summary": (res or {}).get("summary")}

    return {
        "data": data,
        "label": _manual("(library) core/ai/label_analysis.py:label_distribution — see scripts/eval_label_modes.py"),
        "train": _manual("python backend/train_ai.py"),
        "backtest": backtest,
        "eval": _manual("python scripts/eval_label_modes.py"),
    }


def reproduce_pipeline(run: bool = False, stage_fns: dict = None) -> dict:
    """Print the honest pipeline map; if ``run`` is True, execute each stage via
    ``stage_fns`` (injectable for testing) IN ORDER and return an honest per-stage
    summary. A failing stage is recorded honestly and the run continues — this is
    a reference/demonstration run, not a production job."""
    print_map()
    if not run:
        return {"ran": False, "stages": [s["key"] for s in STAGES], "caveat": CAVEAT}

    fns = stage_fns or _default_stage_fns()
    summary = {}
    for s in STAGES:
        key = s["key"]
        print(f"\n[reproduce] === {s['title']} ===")
        fn = fns.get(key)
        if fn is None:
            summary[key] = {"skipped": "no stage fn"}
            continue
        try:
            summary[key] = fn()
            print(f"[reproduce]   {s['title']} ok.")
        except Exception as e:  # honest: report, don't hide, keep going
            summary[key] = {"error": str(e)}
            print(f"[reproduce]   {s['title']} FAILED: {e} (continuing — reference run).")
    print("\n" + CAVEAT)
    return {"ran": True, "stages": summary, "caveat": CAVEAT}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Reproducible reference: the honest end-to-end pipeline (epic #5).")
    ap.add_argument("--run", action="store_true",
                    help="Actually run the offline demo pipeline end to end (default: print the map only).")
    args = ap.parse_args(argv)
    reproduce_pipeline(run=args.run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
