#!/usr/bin/env python3
"""Fast full-universe history backfill via TWSE/TPEX per-day bulk endpoints.

A far quicker alternative to the per-stock yfinance crawl for populating the
whole listed + OTC universe on first run: one HTTP call per trading day returns
ALL stocks' OHLCV. Real official data; each user fetches their own (no
redistribution). Prices are RAW (not split/dividend-adjusted) — internally
consistent, but different from the yfinance auto_adjust path.

Usage: python scripts/fast_backfill.py [--days 180] [--listed-only]
"""
import argparse
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.bulk_history import backfill_bulk  # noqa: E402
from core.data import init_db  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fast full-universe backfill via TWSE/TPEX per-day bulk endpoints."
    )
    ap.add_argument("--days", type=int, default=180,
                    help="Weekdays of history to backfill (default 180; holidays skipped).")
    ap.add_argument("--listed-only", action="store_true",
                    help="TWSE listed only (skip TPEX/OTC).")
    args = ap.parse_args(argv)

    init_db()
    print(f"[fast_backfill] backfilling ~{args.days} weekdays via TWSE/TPEX bulk endpoints (raw prices)...")
    res = backfill_bulk(days=args.days, listed_only=args.listed_only, sleep_fn=lambda: time.sleep(0.2))
    print(f"[fast_backfill] done: {res['tickers']} tickers, {res['rows']} rows, "
          f"{res['days_with_data']} trading days.")
    print("[fast_backfill] Next: python backend/recalculate.py (or restart the backend) to compute scores.")
    return 0 if res["tickers"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
