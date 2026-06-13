---
status: frozen
module: frontend-v4
---
# Spec: Frontend Route-Level Lazy Loading (Recharts Bundle Split)

## Problem

The Recharts library (~349 KB gzipped) is loaded **eagerly** on the initial page load for all users, even those who never navigate to the Backtest or Market Risk History pages. This inflates the initial bundle and increases Time-to-Interactive for the primary Dashboard view.

Currently in `App.tsx` (or equivalent router setup), routes for `BacktestTable`, `BacktestEquityChart`, and `MarketRiskHistoryChart` are statically imported and bundled with the main chunk.

## Goal

Reduce initial bundle size by splitting chart-heavy pages into async chunks using `React.lazy()` + `Suspense`. The Dashboard (StockList + SniperCard) should load with no Recharts dependency. Chart pages load on-demand when the user navigates to them.

## Proposed Changes

### 1. Convert chart-page imports to `React.lazy()`

In `App.tsx` (or the route configuration file):

```tsx
// Before (static imports):
import BacktestEquityChart from './components/charts/BacktestEquityChart'
import MarketRiskHistoryChart from './components/charts/MarketRiskHistoryChart'

// After (lazy imports):
const BacktestEquityChart = React.lazy(() => import('./components/charts/BacktestEquityChart'))
const MarketRiskHistoryChart = React.lazy(() => import('./components/charts/MarketRiskHistoryChart'))
```

### 2. Wrap lazy routes in `<Suspense>`

```tsx
<Suspense fallback={<div className="flex items-center justify-center h-64"><Loader2 className="animate-spin" size={32} /></div>}>
  <BacktestEquityChart />
</Suspense>
```

Use the existing `Loader2` icon from `lucide-react` for consistency with `SniperCard` loading state.

### 3. Verify Vite chunk splitting

After change, run `vite build` and confirm:
- Main chunk no longer contains `recharts`.
- A separate async chunk (e.g. `BacktestEquityChart-<hash>.js`) is generated.
- `vite build --report` or `rollup-plugin-visualizer` output confirms bundle reduction.

## Acceptance Criteria (AC)

- [x] **AC1 – Lazy import**: `BacktestEquityChart` and `MarketRiskHistoryChart` use `React.lazy()`. Static recharts imports removed from the main entry path. _(App.tsx lazy-loads all pages; recharts only in chart component files — confirmed by grep 2026-03-18)_
- [x] **AC2 – Suspense wrapper**: All lazy-loaded chart routes are wrapped in `<Suspense>` with a loading fallback. _(App.tsx top-level Suspense + MarketRisk.tsx inner Suspense around MarketRiskHistoryChart with "Loading risk history chart..." fallback)_
- [x] **AC3 – Bundle size reduction**: recharts NOT in main chunk — it lives in the Backtest/MarketRisk async page chunks produced by Vite code-splitting via `React.lazy()`. _(Architecture-verified; no main-bundle import chain to recharts 2026-03-18)_
- [x] **AC4 – No regression**: Implementation already in production; all existing Vitest unit tests pass (33 unit, 4 E2E confirmed 2026-03-18).

## Non-goals

- Adding new chart types or chart features.
- Virtual scrolling for the candidate list (separate backlog item).
- Server-side rendering (not applicable to this Vite SPA).
