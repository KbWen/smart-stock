---
status: frozen
module: frontend-v4
---
# Spec: Frontend Dashboard API Integration Optimization

## Goal

Optimize the Sniper Dashboard (V4) to consume the `/api/v4/meta` bulk endpoint, ensuring that the stock list displays real-time indicators (Signals, RSI, Squeeze) without triggering individual detail requests or partial rendering waterfalls.

## Proposed Changes

### 1. Frontend Interface Alignment

Update `StockCandidate` in `useDashboardData.ts`:

- Include `signals` object matching the backend `/api/v4/meta` response.
- Add `rsi`, `macd_diff`, `rel_vol` directly or under signals.

### 2. Service Layer / Hook Optimization

Modify `useDashboardData` OR create a new `useBulkMeta` hook:

- Input: Array of tickers.
- Output: Map of meta data.
- Behavior: Fetches `/api/v4/meta?tickers=A,B,C` in a single request.

### 3. Component Integration

Update `StockList.tsx`:

- After fetching candidates, trigger a bulk meta fetch for those candidates.
- Merge the meta data into the `stocks` array before passing to `CandidateTable`.
- This ensures `CandidateRow` has all necessary flags (`signals.squeeze`, `signals.golden_cross`) during initial render.

## Acceptance Criteria (AC)

- [ ] **Single Batch Fetch**: Dashboard list triggers exactly one `/api/v4/meta` call for the visible stock list.
- [ ] **Signal Enrichment**: `CandidateRow` correctly renders "Squeeze" or "Golden Cross" tags based on real DB data.
- [ ] **Performance**: Total time to render enriched list (List API + Meta API) should be < 300ms.
- [ ] **No Waterfall**: No individual `/api/v4/stock/{ticker}` calls should occur until a stock is explicitly selected for the `SniperCard`.

## Non-goals

- Modifying the `SniperCard` detail view logic (beyond ensuring it still works).
- Adding new filtering logic in the frontend.
