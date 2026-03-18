# Work Log: backend-refactor-modular

Classification: refactor
Classified by: Antigravity
Frozen: false
Created Date: 2026-03-05
Owner: Antigravity
Recommended Skills: systematic-debugging, executing-plans, test-driven-development

## Session Info

- Agent: Antigravity
- Session: 2026-03-05T14:35:00+08:00
- Platform: Antigravity

## Goal

Refactor `backend/routes/stock.py` into a layered architecture with Services and Repositories to improve maintainability while preserving API stability for v4 frontend.

## Proposed Steps

### Phase 1: Infrastructure & Repositories

- [ ] Create directory structure: `backend/services/`, `backend/repositories/`.
- [ ] Implement `ScoreRepository`: Move DB queries related to stock scores from `stock.py` to this module.
- [ ] Implement `IndicatorRepository`: Move indicator data access.
- [ ] Implement `StockRepository`: Move basic stock metadata and price history fetching.
- [ ] Implement `SystemRepository`: Move sync-epoch and health checks.

### Phase 2: Services & Logic Extraction

- [ ] Implement `V4MetaService`: Orchestrate meta data fetching (bulk) calls to repositories.
- [ ] Implement `V4CandidatesService`: Orchestrate candidate filtering and enrichment logic.
- [ ] Implement `V4StockDetailService`: Orchestrate individual stock detail components.
- [ ] Implement `TopPicksService`: Handle legacy top-picks logic.

### Phase 3: Route Refactoring

- [ ] Refactor `backend/routes/stock.py` handlers to inject services and call them.
- [ ] Ensure all handlers are "thin" (mapping REQ/RES only).
- [ ] Remove direct DB connections and raw logic from the route file.

### Phase 4: Verification

- [ ] Run backend unit tests: `pytest tests/test_backend`.
- [ ] Run v4 regression tests: Verify JSON schema parity for `/api/v4/meta`, `/api/v4/sniper/candidates`.
- [ ] Confirm no regressions in frontend `StockList` enrichment.

## Constraints & AC

- **AC 1**: `backend/routes/stock.py` size reduced (target < 10KB).
- **AC 2**: API Contract Parity: Zero change in existing JSON response structure.
- **AC 3**: Latency: No performance regression in bulk meta fetching.

## Context Read Receipt

- `docs/specs/backend-refactor-modular.md` -> Frozen (SSoT)
- `current_state.md` -> Updated with Ship History

## Next Step Recommendation

→ `/implement` (Phase 1: Repositories extraction)
