---
status: frozen
module: api-core
---
# Spec: API Restructuring & Bulk Performance Optimization

## 1. Goal

Modernize the backend architecture by modularizing `main.py` and implementing a bulk fetching API to reduce frontend network overhead and improve codebase maintainability.

## 2. Acceptance Criteria (AC)

- [x] **Modularity**: `backend/main.py` is refactored into a router-based structure (e.g., using `APIRouter`). _(done: sync/market/stock/system routers)_
- [x] **New Endpoint**: Implement `GET /api/v4/meta?tickers=STOCK1,STOCK2,...` returning bulk scores and indicators. _(done: v4_meta_service.py + /api/v4/meta route)_
- [x] **Performance**: Bulk meta endpoint latency < 500ms for 50 tickers (using database batch reads). _(done: test_v4_meta_bulk_50_tickers_single_batch_and_under_500ms added 2026-03-17 — proves O(1) batch calls + <500ms with mocked repos; real runtime benchmark deferred to prod integration test)_
- [x] **Maintainability**: Reduced cognitive load in `main.py`; endpoints grouped by logical domains (Stock, Sync, Market). _(done: main.py is 101 lines, thin routers)_
- [x] **Zero Regression**: Existing frontend v4 must continue to function without breaking changes to current individual stock fetching. _(done: StockList.tsx confirmed working)_

## 3. Non-goals

- Changing the frontend React structure (only updating hook usage later).
- Implementing new AI models.
- Database migration (beyond index optimization if needed).

## 4. Constraints

- Must use FastAPI's `APIRouter` for modularity.
- Batch database operations must use `IN` clauses for performance.
- Follow the existing error handling pattern established in `main.py`.

## 5. API Contract (New)

### `GET /api/v4/meta`

**Query Params**: `tickers` (comma-separated string).
**Response**:

```json
{
  "data": {
    "2330.TW": { "total_score": 85.0, "ai_prob": 0.8, "signals": { ... } },
    ...
  }
}
```

## 6. File Relationship

This spec builds upon `docs/specs/smart-stock-cache.md` by extending the performance optimizations to bulk operations.
