---
status: frozen
module: api-core
---
# Spec: API Restructuring & Bulk Performance Optimization

## 1. Goal

Modernize the backend architecture by modularizing `main.py` and implementing a bulk fetching API to reduce frontend network overhead and improve codebase maintainability.

## 2. Acceptance Criteria (AC)

- [ ] **Modularity**: `backend/main.py` is refactored into a router-based structure (e.g., using `APIRouter`).
- [ ] **New Endpoint**: Implement `GET /api/v4/meta?tickers=STOCK1,STOCK2,...` returning bulk scores and indicators.
- [ ] **Performance**: Bulk meta endpoint latency < 500ms for 50 tickers (using database batch reads).
- [ ] **Maintainability**: Reduced cognitive load in `main.py`; endpoints grouped by logical domains (Stock, Sync, Market).
- [ ] **Zero Regression**: Existing frontend v4 must continue to function without breaking changes to current individual stock fetching.

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
