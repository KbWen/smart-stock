---
status: frozen
title: Accelerated Full-Universe History Sync (TWSE/TPEX bulk)
source: external
source_doc: _product-backlog.md (Directly-Usable v1, #4)
created: 2026-06-20
frozen: 2026-06-20
shipped: 2026-06-20
---

# Accelerated Full-Universe History Sync (TWSE/TPEX bulk)

## Goal
Cut the full-universe first-run sync from the current ~10–15 min per-stock yfinance crawl by backfilling history from the **authoritative TWSE/TPEX per-day bulk endpoints** — one HTTP call returns ALL stocks' OHLCV for a trading day, instead of one call per stock. Cleaner licensing (official source; each user fetches their own data — no redistribution), far fewer calls. This is the user-chosen "option C".

## Background (verified 2026-06-20)
- Current history fetch is per-stock: `core/data.py:fetch_stock_data` → `yf.Ticker(f"{code}.TW").history()` with a 0.5–1.5 s sleep/stock — the ~10–15 min wall for ~1,800 stocks.
- TWSE `MI_INDEX?response=json&date=YYYYMMDD&type=ALLBUT0999` returns a per-stock table (~1,366 rows) with code + 開/高/低/收 + volume for one date (col idx: 0=code, 5=open, 6=high, 7=low, 8=close, 2=volume).
- TPEX `daily_close_quotes/stk_quote_result.php?d=ROC_DATE&o=csv` returns all OTC stocks (col idx: 0=code, 2=close, 4=open, 5=high, 6=low, 8=volume) for one date — the same endpoint family `universe_source` already uses.

## Acceptance Criteria
1. A new `core/bulk_history.py` provides pure, network-injectable parsers `parse_twse_mi_index(payload)` and `parse_tpex_daily(csv_text, date)` that extract `{code, date, open, high, low, close, volume}` rows, filtering to the tradable universe (4-digit equities + `00`-prefixed ETFs, reusing `universe_source._is_universe_code`).
2. `fetch_twse_day(date)` / `fetch_tpex_day(date)` fetch + parse one trading day for all stocks; holidays / non-trading days (endpoint `stat != "OK"` or empty) yield an empty list, not an error.
3. `backfill_bulk(days=N, save_fn=...)` iterates the last N trading days, accumulates per-ticker OHLCV, and persists each ticker via the existing `core.data.save_to_db` — producing the same `stock_history` rows the per-stock path would, for the whole universe.
4. A `scripts/fast_backfill.py [--days N] [--listed-only]` CLI runs the backfill and reports tickers/rows fetched; default window is a sensible few-month history.
5. The existing per-stock yfinance path remains the fallback and is unchanged; bulk is additive (no behavior change to current `/api/sync`).
6. Tests cover the parsers (fixture payloads → correct OHLCV + universe filtering + holiday/empty handling) and the per-ticker assembly, without hitting the network.

## Non-goals
- Replacing/removing the yfinance path; intraday data; split/dividend adjustment (TWSE/TPEX daily close is raw — documented).
- Wiring bulk into the default `/api/sync` flow (kept as an opt-in tool/flag); model training (#5).

## Constraints
- Honesty: real official data only; no redistribution (each user fetches). TWSE/TPEX daily close is **raw** (not split/dividend-adjusted) unlike yfinance `auto_adjust=True` — note the difference; a bulk-backfilled DB is internally consistent (all raw).
- Small & reversible; EXTENDS the data layer (`universe_source` patterns); does not modify shipped specs. HTTP is injectable for tests (no live calls in CI).

## API / Data Contract
- No API endpoint change. Persistence contract: `core.data.save_to_db(ticker, df[date,open,high,low,close,volume])` (same as the per-stock path + `seed_demo`), keyed by bare code (e.g. `2330`).

## File Relationship
EXTENDS docs/specs/listed-otc-data-completeness.md
