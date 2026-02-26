"""Compare DB close prices vs TWSE daily close prices for recent trading days."""

from __future__ import annotations

import argparse
import sqlite3
import sys
import os
from datetime import datetime, timedelta

import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config
from core.data import standardize_ticker


def _get_db_recent_closes(ticker: str, n_days: int) -> pd.DataFrame:
    code = standardize_ticker(ticker)
    conn = sqlite3.connect(config.DB_PATH)
    try:
        df = pd.read_sql(
            """
            SELECT date, close
            FROM stock_history
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            conn,
            params=(code, n_days),
        )
    finally:
        conn.close()
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
    return df.sort_values('date')


def _fetch_twse_close(date_yyyymmdd: str, stock_no: str) -> float | None:
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_yyyymmdd}&stockNo={stock_no}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get('stat') != 'OK':
        return None

    data = payload.get('data') or []
    # payload date row uses Minguo year e.g., 113/02/20
    target_dt = datetime.strptime(date_yyyymmdd, '%Y%m%d')
    target_label = f"{target_dt.year - 1911}/{target_dt.month:02d}/{target_dt.day:02d}"

    for row in data:
        if row and row[0] == target_label:
            close_text = row[6].replace(',', '')
            return float(close_text)
    return None


def validate_prices(ticker: str, trading_days: int = 3) -> int:
    db_df = _get_db_recent_closes(ticker, trading_days)
    if db_df.empty:
        print(f"No DB prices found for {ticker}.")
        return 2

    stock_no = standardize_ticker(ticker)
    mismatches = []

    for _, row in db_df.iterrows():
        d = row['date']
        db_close = float(row['close'])
        twse_close = _fetch_twse_close(d, stock_no)
        if twse_close is None:
            print(f"{d}: TWSE close unavailable (non-trading day or API gap).")
            continue
        if abs(db_close - twse_close) > 1e-6:
            mismatches.append((d, db_close, twse_close))

    if mismatches:
        print("Mismatches found:")
        for d, dbv, twsev in mismatches:
            print(f"- {d}: DB={dbv}, TWSE={twsev}")
        return 1

    print(f"All checked closes match for {ticker}.")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', default='2330.TW')
    parser.add_argument('--days', type=int, default=3)
    args = parser.parse_args()
    raise SystemExit(validate_prices(args.ticker, args.days))
