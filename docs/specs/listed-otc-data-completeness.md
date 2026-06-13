---
status: frozen
title: Listed/OTC Universe & Price-Data Completeness
source: external
source_doc: _product-backlog.md (#3)
created: 2026-06-13
primary_domain: data
secondary_domains: []
---

# Listed/OTC Universe & Price-Data Completeness

## Goal
Make the tradable universe **comprehensive and fresh** and give the system **visibility + backfill** into price-history coverage, so every downstream consumer (V4 scoring, backtest, AI training in #2) sees complete data instead of a stale, ETF-excluded, silently-degrading list.

## Background (grounded in current code)
- `core/data.py:get_all_tw_stocks()` (line 287) derives the universe from the **`twstock` static bundled list**, filtering `info.type == '股票' AND info.market in ('上市','上櫃')`. Consequences:
  - The bundled list is only refreshed on `twstock` package releases → **misses new listings / delistings**.
  - `type == '股票'` **silently excludes ETFs** (0050, 0056, 006208, …).
  - When `twstock` is unavailable it returns **only whatever is already cached**, with no live refresh path.
- `fetch_stocks.py` already contains **working live fetchers** for authoritative sources — TWSE `STOCK_DAY_ALL` open-data (上市) and TPEX `daily_close_quotes` (上櫃) — returning code/name/volume, but it is a **standalone script** never wired into the universe.
- All universe consumers read only `s['code']` / `s['name']` (verified: `core/data.py:310` name_map, `backend/backtest.py:61`, `backend/routes/sync.py:94`, `backend/repositories/stock_repo.py`). Adding keys is **backward-compatible**.

## Acceptance Criteria
1. [FROM-SOURCE] The universe is sourced from **authoritative live endpoints** — TWSE `STOCK_DAY_ALL` (上市) + TPEX daily-close (上櫃) — via a reusable `core` function (logic promoted/refactored from `fetch_stocks.py`, not duplicated). `twstock` is demoted to an **offline fallback** used only when the live fetch fails. Results are cached to `stock_list_cache.json`.
2. Each universe entry carries `code`, `name`, `market` ∈ {`上市`,`上櫃`}, and `kind` ∈ {`股票`,`ETF`}. **ETFs are included** (no longer silently dropped). Existing consumers reading `code`/`name` keep working unchanged (additive fields only).
3. Universe size is **verifiable and ≥ the current 1819** equities (expected higher once ETFs + fresh listings are included). The existing 1h memory / 24h file cache TTL is retained, plus an **on-demand refresh path** (function/CLI) that forces a live re-fetch.
4. A **coverage report** function reports, across the universe, how many tickers have `≥ MIN_PREDICT_ROWS` and `≥ MIN_TRAIN_ROWS` of price history in the DB, and exposes a **backfill entry point** (reusing `fetch_stock_data`) to fetch missing/short histories. Counts are surfaced (logged/returned), never silent.
5. [FROM-SOURCE] Behavior degrades **gracefully**: live-fetch failure → twstock fallback → existing file cache; never blocks app startup, never throws to callers. A live fetch that returns 0 rows MUST NOT overwrite a good cache.
6. Tests cover: live-source parsing (mocked HTTP fixtures), fallback chain (live fail → twstock → file cache), ETF inclusion, `market`/`kind` tagging, and coverage-report counts. No regression in existing `get_all_tw_stocks` consumers.

## Non-goals
- Changing AI **label/training semantics** — that is feature #2. ETF presence in the *universe* does not imply ETFs enter the *training set*.
- Realtime/intraday tick data; non-Taiwan markets; paid data vendors.
- Re-architecting the DB schema (price history table stays as-is).

## Constraints
- Reuse the **same public endpoints already proven** in `fetch_stocks.py` — no new paid/external dependencies.
- Respect existing anti-throttling patterns (random sleep / chunked download in `fetch_stocks.py` and `fetch_stock_data`).
- `stock_list_cache.json` schema change must be **additive** (old readers must not break); a legacy cache lacking `market`/`kind` must still load (treated as `市場=unknown`/`kind=股票` until next refresh).
- Refresh must be **side-effect-safe** under the existing thread-locked cache (`_tw_stocks_cache_lock`).

## API / Data Contract
- `stock_list_cache.json`: `[{ "code": str, "name": str, "market": "上市"|"上櫃", "kind": "股票"|"ETF" }, …]` (adds `market`, `kind`).
- `get_all_tw_stocks() -> list[dict]`: same list, superset of prior keys. Existing `name_map = {s['code']: s['name']}` contract preserved.
- New: `refresh_stock_universe(force: bool=False) -> list[dict]` (live re-fetch + cache write).
- New: `report_history_coverage(tickers: list[str]|None=None) -> dict` → `{ universe: int, with_predict_rows: int, with_train_rows: int, short: list[str] }`.

## File Relationship
EXTENDS `core/data.py` (data layer). INDEPENDENT of other frozen specs. No spec overlap (Spec Index has no prior universe/data-sourcing spec).
