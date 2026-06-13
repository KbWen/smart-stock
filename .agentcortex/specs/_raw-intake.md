---
status: raw
title: Raw Spec Intake — Honesty-First (Data-Consistent-With-Claims)
source: natural-language
received: 2026-06-13
---

# Context

Stage goal: smart-stock must become a "stable, simple, and **data-consistent-with-its-claims**" version — complete at this stage, not perfect. Direction decided by user (2026-06-13): **honesty-first** — fix truthfulness gaps; reframe model state honestly in the UI; do NOT chase model training quality this stage.

Source = 2026-06-13 multi-agent code audit. The product can currently present non-real / failed / misleading data as real. Each work item below is a distinct fix.

# Work Items (raw)

## (1) Frontend mock fallback — stop showing fake data as real
`frontend/v4/src/mockData.ts` is wired as `fallbackData` into ~6 production files. On API failure the UI renders fabricated numbers for real tickers (e.g. 台積電 ai_prob 72.1, bull_ratio 62.5) plus stale 2026-02 dates and a hardcoded model version, with NO "sample/offline" badge. Worst offender: `frontend/v4/src/pages/MarketRisk.tsx` (~L28) does not gate on `isPlaceholder` at all. Others (`StockList.tsx`, `Indicators.tsx`, `useDashboardData.ts`/`MarketStatusHeader`, `useStockAnalysis.ts`, `Backtest.tsx`) are partially guarded but can still flash/keep mock.
Desired: remove mock-as-live, or replace with honest loading / no-data / connection-failed states. No invented data rendered as real.

## (2) Backend failure-state honesty
`core/ai/predictor.py` collapses model-missing / SHA256 mismatch / HMAC mismatch / exception / insufficient-rows into `ai_prob = 0.0` (L181-190, L278-282). Callers (`sync.py`, `recalculate.py`, `v4_stock_detail_service.py`, `v4_candidates_service.py`, `backtest.py`) coerce `None → 0.0`. The user then sees a literal "0.0%" (even badged "HIGH RISK") indistinguishable from a genuine low prediction, silently masking integrity/availability failures.
Desired: failure ≠ fake 0.0%. Propagate null / "no-data" / "unavailable" semantics so the UI can show it honestly.

## (3) UI honest model-state disclosure
The active model (`models_history.json` `v4.20260601_2031`) is degenerate: buy & strong precision=recall=0 (1065 samples, 90.7% Hold); it identifies zero buy signals. The product markets "AI buy signal prediction".
Desired: when the model is degraded/unavailable, the UI must NOT sell degenerate output as a buy signal — surface "模型訓練中 / 信心不足 / 未就緒" honestly. (Does NOT include retraining the model.)

## (4) Backtest metric label honesty
`backend/backtest.py`: the "Sharpe Ratio" (L289-292) is unannualized with no risk-free baseline — needs rename/annotation, and the ≥1.0 "good" threshold (annualized convention) is misleading. `profit_factor`/`net_profit_factor` use 9999 sentinel on zero-loss (L282,287) — show "N/A"/"∞" instead. `Backtest.tsx`(~L258)/`BacktestTable.tsx`(~L100) hardcode ±15%/-5% tooltips that contradict user-configurable sliders and the intraday-low realized loss (can exceed -5%). NOTE: overlaps shipped spec `backtest-and-performance-opt.md` → must be an EXTENDS amendment.

## (5) Docs ↔ reality sync
- `docs/API_CONTRACT.md` documents `POST /api/sync/trigger` (404; real route is `POST /api/sync`).
- README claims "auto-trigger sync >6h" (actually manual-only), "10x" parallel (actually 5 workers `CONCURRENCY_WORKERS`), "~1000 stocks" (actually 1819 in `stock_list_cache.json`).
- `docs/API_CONTRACT.md` `/api/backtest` not updated for V4.2 params (`commission_rate,tax_rate,slippage_rate,target_gain,stop_loss,holding_days`) or new response fields.
- `daily_run.bat` retrains daily vs README "use existing AI" (clarify docs/behavior).
- `docs/ARCHITECTURE.md:47` attributes sync lock to wrong file; `docs/project_meta/TESTING.md` references nonexistent test + stale CI command.

## (6) Frontend tests into CI
`.github/workflows/` runs backend pytest only (`-m "not integration"`). The 44 frontend vitest tests + production build are NOT enforced by CI, so the "Frontend 44/44" gate does not actually exist. RELATED: shipped spec `frontend-testing.md` (tests exist; CI integration is new) → EXTENDS.

# Explicitly OUT of scope (this stage)
- Annualized/academically-rigorous Sharpe.
- Alert webhook implementation (`core/logger.py:53` TODO/pass).
- Backtest sampling diversification (fixed `random.seed(42)`).
- Model retraining / model quality improvement.
