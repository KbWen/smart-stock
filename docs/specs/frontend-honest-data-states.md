---
status: frozen
title: Frontend Honest Data States (Remove Mock-as-Live)
source: external
source_doc: _product-backlog.md (#1)
created: 2026-06-13
---

# Frontend Honest Data States

## Goal
Stop the frontend from ever presenting fabricated `mockData.ts` content as real/live data. On fetch failure or empty result, every affected view must show an honest state (loading / no-data / connection-error or a clearly-marked stale-offline indicator) instead of invented numbers for real tickers. This directly serves the stage goal "data consistent with our claims."

## Acceptance Criteria
1. No production (non-test) code path renders `frontend/v4/src/mockData.ts` content as if it were real/live data. The `MOCK_*` constants are removed from the `fallbackData` of every production `useCachedApi` call site (`useDashboardData.ts`, `useStockAnalysis.ts`, `StockList.tsx`, `pages/Indicators.tsx`, `pages/MarketRisk.tsx`, `pages/Backtest.tsx`).
2. On a failed or empty fetch with NO prior real data, each affected view renders an explicit honest state — a loading skeleton, an empty "無資料" message, or a "連線失敗 / 載入錯誤,請重試" error — never fabricated values.
3. `pages/MarketRisk.tsx` (currently renders mock market status with no `isPlaceholder`/`error` guard) gates on error/empty and shows an honest error/empty state on API failure.
4. When real data was previously loaded and a later refresh fails, a view MAY keep the last-known REAL value but MUST visibly indicate staleness/offline (reuse existing `isDbStale`-style banner pattern; add an offline/error indicator where missing). No silent substitution.
5. `mockData.ts` is either deleted (if no longer referenced) or retained ONLY for test usage; it must not be importable into a live render path. Decision recorded in plan.
6. Existing frontend test suite passes (any test asserting mock-fallback rendering is updated to assert the honest state). Production build (`tsc -b && vite build`) is green. New/updated tests cover the honest error/empty path for at least `MarketRisk` and the candidate list.

## Non-goals
- Honest model-state disclosure for the degenerate model (that is backlog #3).
- Backend failure-state / `ai_prob=0.0` changes (backlog #2).
- Any visual redesign, new components beyond what an honest empty/error state needs, or changes to the success-path rendering.

## Constraints
- Preserve existing success-path behavior and Taiwan color conventions (red=up, green=down).
- Prefer changes at `useCachedApi` call sites over altering the hook's public signature; if the hook changes, keep it backward-compatible.
- Small, reversible: per-view honest-state handling; no cross-cutting refactor of the data layer.
- Keep loading/skeleton UX already provided by `isPlaceholder` where it exists.

## API / Data Contract
- No backend contract change. Consumes existing endpoints (`/api/market_status`, `/api/v4/sniper/candidates`, `/api/v4/stock/{ticker}`, `/api/v4/meta`, `/api/backtest`).
- Relies on `useCachedApi` exposing `loading`, `error`, `isPlaceholder` (already present per audit).

## File Relationship
INDEPENDENT
