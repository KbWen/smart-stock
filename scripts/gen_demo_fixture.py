#!/usr/bin/env python3
"""Regenerate the bundled offline demo fixture (data/demo/demo_prices.csv) with
REAL recent history for a set of recognizable large-cap TWSE tickers.

This is a MAINTAINER tool: it hits the network (yfinance) to fetch real,
auto-adjusted prices, then writes them to the committed fixture. The demo
RUNTIME (scripts/seed_demo.py) stays fully offline — it only reads this
committed CSV. Honesty: prices are real (auto-adjusted), never synthesized.

Usage: python scripts/gen_demo_fixture.py [--years 2]
"""
import argparse
import os
import sys
import time

import pandas as pd
import yfinance as yf

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_ROOT, "data", "demo", "demo_prices.csv")

# Recognizable large-cap TWSE (上市) names — a credible "Top Candidates" demo.
TICKERS = [
    "2330",  # 台積電 TSMC
    "2317",  # 鴻海 Hon Hai
    "2454",  # 聯發科 MediaTek
    "2412",  # 中華電 Chunghwa Telecom
    "2882",  # 國泰金 Cathay FHC
    "2308",  # 台達電 Delta
    "2303",  # 聯電 UMC
    "2881",  # 富邦金 Fubon FHC
    "1301",  # 台塑 Formosa Plastics
    "2002",  # 中鋼 China Steel
    "2603",  # 長榮 Evergreen Marine
    "3008",  # 大立光 Largan
    "2891",  # 中信金 CTBC FHC
    "2886",  # 兆豐金 Mega FHC
    "1216",  # 統一 Uni-President
]


def fetch_one(code: str, years: int):
    df = yf.Ticker(f"{code}.TW").history(period=f"{years}y", auto_adjust=True)
    if df.empty:
        return None
    df = df.reset_index()
    df["ticker"] = code
    df["date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    out = df[["ticker", "date", "Open", "High", "Low", "Close", "Volume"]].copy()
    out.columns = ["ticker", "date", "open", "high", "low", "close", "volume"]
    out = out.dropna(subset=["open", "high", "low", "close"])
    for col in ("open", "high", "low", "close"):
        out[col] = out[col].round(2)
    out["volume"] = out["volume"].fillna(0).astype("int64")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Regenerate the offline demo fixture from real TWSE prices.")
    ap.add_argument("--years", type=int, default=2, help="Years of daily history per ticker (default 2).")
    args = ap.parse_args(argv)

    frames = []
    for code in TICKERS:
        d = fetch_one(code, args.years)
        if d is None or d.empty:
            print(f"[gen_demo] WARN: no data for {code}, skipping", file=sys.stderr)
            continue
        frames.append(d)
        print(f"[gen_demo] {code}: {len(d)} rows")
        time.sleep(0.5)  # be polite to the data source

    if not frames:
        print("[gen_demo] FAILED: no data fetched", file=sys.stderr)
        return 1

    allrows = pd.concat(frames, ignore_index=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    allrows.to_csv(OUT, index=False)
    print(f"[gen_demo] wrote {len(allrows)} rows / {allrows['ticker'].nunique()} tickers -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
