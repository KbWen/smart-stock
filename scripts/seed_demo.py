#!/usr/bin/env python3
"""Seed storage.db with the bundled OFFLINE demo dataset, then compute scores.

Lets a fresh clone show a populated dashboard in seconds — fully offline, no
yfinance sync required. The price history and the trained model are gitignored,
so without this a new user sees an empty app until a slow network sync.

Idempotent & safe: if storage.db already holds price history for the demo tickers
it skips the load (so it never clobbers a user's real synced data) unless --force.
Scores are then computed from DB history via the existing recalculate pipeline.

Honesty note: no model is bundled (.pkl is gitignored). If no model is present the
dashboard shows AI probability as N/A (honest) — train via train_ai.py to enable it.
"""
import argparse
import os
import sys

# Allow running as a plain script (python scripts/seed_demo.py).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd  # noqa: E402

from core.data import get_db_connection, save_to_db, ensure_db_initialized  # noqa: E402

FIXTURE = os.path.join(_ROOT, "data", "demo", "demo_prices.csv")


def _existing_demo_tickers(fixture_tickers):
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT DISTINCT ticker FROM stock_history").fetchall()
        existing = {r[0] for r in rows}
        return existing.intersection(set(fixture_tickers))
    finally:
        conn.close()


def _score_count():
    conn = get_db_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM stock_history").fetchone()[0], \
            conn.execute("SELECT COUNT(*) FROM stock_scores").fetchone()[0]
    finally:
        conn.close()


def seed(force: bool = False, fixture: str = FIXTURE):
    """Load the demo fixture (idempotently) and compute scores offline.

    Returns a summary dict: {loaded, tickers, history_rows, scores}.
    """
    if not os.path.exists(fixture):
        raise FileNotFoundError(f"demo fixture not found: {fixture}")

    ensure_db_initialized()
    df = pd.read_csv(fixture, dtype={"ticker": str})
    fixture_tickers = sorted(df["ticker"].unique())

    overlap = _existing_demo_tickers(fixture_tickers)
    loaded = 0
    if overlap and not force:
        print(f"[seed_demo] storage.db already has {len(overlap)} demo ticker(s): {sorted(overlap)}.")
        print("[seed_demo] Skipping load to avoid clobbering existing data. Use --force to reload the demo.")
    else:
        for ticker in fixture_tickers:
            tdf = df[df["ticker"] == ticker][["date", "open", "high", "low", "close", "volume"]].copy()
            save_to_db(ticker, tdf)
            loaded += len(tdf)
        print(f"[seed_demo] Loaded {loaded} price rows for {len(fixture_tickers)} tickers: {fixture_tickers}")

    # Compute V4 scores from DB history only — no network (recalculate scopes to DB tickers).
    print("[seed_demo] Computing scores from local history (offline)...")
    from backend.recalculate import recalculate_all
    recalculate_all(incremental=False)

    history_rows, scores = _score_count()
    print(f"[seed_demo] Done. history rows: {history_rows}, score rows: {scores}.")
    print("[seed_demo] Next: start the backend (python backend/main.py) and frontend (cd frontend/v4 && npm run dev).")
    return {"loaded": loaded, "tickers": fixture_tickers, "history_rows": history_rows, "scores": scores}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Seed the offline demo dataset and compute scores.")
    parser.add_argument("--force", action="store_true",
                        help="Reload the demo fixture even if storage.db already has data.")
    args = parser.parse_args(argv)
    try:
        seed(force=args.force)
        return 0
    except Exception as exc:  # surface a clear failure to the user / quickstart script
        print(f"[seed_demo] FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
