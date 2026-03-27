---
Branch: master
Session: 2026-03-27
Feature: 視覺衝擊力升級 Phase 1
Classification: feature
Status: shipped
---

## Task
視覺衝擊力升級 Phase 1 — 買入信號視覺化 + V4 Sniper 分數強化

## Spec
`.agentcortex/specs/visual-upgrade-phase1.md` [Frozen]

## Evidence
```
Backend:  143 passed, 1 deselected, 3 warnings — 11.28s  (+3 new)
Frontend: 38 passed (7 test files) — 1.95s  (+4 new)
Production build: tsc -b ✅
```

## Files Created
- `backend/services/v4_stock_detail_service.py` (get_stock_history method added)
- `backend/routes/stock.py` (history endpoint added)
- `frontend/v4/src/components/charts/PriceSignalChart.tsx`
- `frontend/v4/src/components/__tests__/PriceSignalChart.test.tsx`

## Files Modified
- `frontend/v4/src/components/dashboard/ScoreBreakdown.tsx` (useCountUp animation)
- `frontend/v4/src/components/SniperCard.tsx` (PriceSignalChart integrated)
- `tests/test_backend/test_api_v4.py` (3 new tests)
- `.agentcortex/specs/visual-upgrade-phase1.md` (created + frozen)
- `.agentcortex/context/current_state.md` (spec index + ship history updated)

## AC Coverage
- AC1: ✅ history endpoint returns {date, close, is_squeeze, golden_cross, volume_spike}[]
- AC2: ✅ _write_cache with optional ttl param; history uses 60s TTL (not default 300s)
- AC3: ✅ PriceSignalChart: Line + ReferenceDot yellow/blue/purple
- AC4: ✅ useCountUp hook with requestAnimationFrame, ease-out cubic, ~1s duration
- AC5: ✅ useCachedApi with enabled=Boolean(ticker) prevents race conditions
- AC6: ✅ Backend 143/143, Frontend 38/38

## Key Decisions
- Route order: `/api/v4/stock/{ticker}/history` registered BEFORE `{ticker}` to prevent "history" matched as ticker
- history cache independent from main stock cache (separate key space `history:{ticker}`)
- df-path only for history (no DB cache dual-path complexity)
- Recharts ComposedChart chosen over separate chart types for mixed Line+ReferenceDot in single SVG

## Review Findings (fixed before ship)
1. [CRITICAL] Cache TTL mismatch: `_write_cache` used default 300s instead of spec-required 60s → added `ttl` param + `_HISTORY_CACHE_TTL_SECONDS = 60`
2. [CRITICAL] Production build failure: Recharts Tooltip formatter `(value: number | string)` doesn't match `Formatter<...>` type → widened to `number | string | undefined`, used `Number(value ?? 0)`
3. [CRITICAL] Skeleton-forever bug: `if (loading || isPlaceholder)` kept skeleton on error → changed to `if (loading && isPlaceholder)`, added `(error && isPlaceholder)` to empty state branch
4. [MINOR] ResizeObserver constructor mock — fixed by mocking entire recharts module instead
5. [MINOR] Missing ESLint disable comment explanation for stale closure in useCountUp — added inline comment

ship:[doc=.agentcortex/specs/visual-upgrade-phase1.md][code=frontend/v4/src/components/charts/PriceSignalChart.tsx][log=.agentcortex/context/work/master.md]
