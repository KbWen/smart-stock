#!/usr/bin/env python3
"""Opt-in: set up the REAL AI on first run (Directly-Usable v1 #5).

Chains the fast full-universe bulk backfill (option C, #4) -> model training ->
score recalculation, so AI probabilities are populated instead of N/A. This is
OPT-IN and slower than the offline demo; no model is bundled with the repo, and
the trained model is local + gitignored.

Honesty: if the backfill does not yield enough tickers with sufficient history,
training is SKIPPED and AI stays N/A — a model trained on too little data would
be degenerate (worse than an honest N/A). When a model IS trained on a small set,
the warning is surfaced and `model_health` discloses a weak model in the UI.

Usage: python scripts/setup_real_ai.py [--days 400] [--listed-only] [--min-tickers 50]
"""
import argparse
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core import config  # noqa: E402

OOS_FLOOR = 92  # tickers at which the degenerate model stopped reproducing (ml-label-oos-evaluation)


def setup_real_ai(days: int = 400, listed_only: bool = False, min_tickers: int = 50,
                  backfill_fn=None, coverage_fn=None, train_fn=None, recalc_fn=None) -> dict:
    """Backfill -> (gated) train -> recalc. Pure orchestration: all four steps are
    injectable for testing. Returns a summary dict. Honest: skips training when
    fewer than ``min_tickers`` have >= MIN_TRAIN_ROWS history (AI stays N/A)."""
    if backfill_fn is None:
        from core.bulk_history import backfill_bulk
        backfill_fn = lambda: backfill_bulk(  # noqa: E731
            days=days, listed_only=listed_only, sleep_fn=lambda: time.sleep(0.2))
    if coverage_fn is None:
        from core.data import report_history_coverage as coverage_fn
    if train_fn is None:
        from backend.train_ai import main as train_fn
    if recalc_fn is None:
        from backend.recalculate import recalculate_all
        recalc_fn = lambda: recalculate_all(incremental=False)  # noqa: E731

    print(f"[setup_real_ai] Step 1/3: bulk-backfilling ~{days} weekdays (raw prices)...")
    bf = backfill_fn() or {}
    print(f"[setup_real_ai]   backfill: {bf.get('tickers')} tickers, {bf.get('rows')} rows.")

    cov = coverage_fn() or {}
    trainable = int(cov.get("with_train_rows", 0) or 0)
    print(f"[setup_real_ai] Step 2/3: {trainable} tickers have >= {config.MIN_TRAIN_ROWS} rows "
          f"(need >= {min_tickers} to train).")

    if trainable < min_tickers:
        print(f"[setup_real_ai] SKIP training: only {trainable} trainable tickers (< {min_tickers}). "
              f"AI stays N/A (honest). Re-run with a larger --days to gather more history.")
        return {"backfill": bf, "trainable": trainable, "trained": False, "reason": "insufficient_data"}

    if trainable < OOS_FLOOR:
        print(f"[setup_real_ai]   WARNING: {trainable} tickers is below the ~{OOS_FLOOR} OOS floor; the "
              f"model may be weak/degenerate (model_health will disclose this honestly in the UI).")

    print("[setup_real_ai] Training the ensemble (GB+RF+MLP) — this can take several minutes...")
    train_fn()
    print("[setup_real_ai] Step 3/3: recalculating scores so AI probabilities populate...")
    recalc_fn()
    print("[setup_real_ai] Done. Start the app: python backend/main.py  ->  http://localhost:8000")
    return {"backfill": bf, "trainable": trainable, "trained": True, "reason": "trained"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Opt-in: backfill + train + recalc for real AI (v1 #5).")
    ap.add_argument("--days", type=int, default=400, help="Weekdays to backfill (default 400, ~1.5y).")
    ap.add_argument("--listed-only", action="store_true", help="TWSE listed only (skip TPEX/OTC).")
    ap.add_argument("--min-tickers", type=int, default=50,
                    help="Minimum trainable tickers before training runs (default 50).")
    args = ap.parse_args(argv)

    from core.data import init_db
    init_db()
    res = setup_real_ai(days=args.days, listed_only=args.listed_only, min_tickers=args.min_tickers)
    return 0 if res.get("trained") else 2


if __name__ == "__main__":
    raise SystemExit(main())
