---
status: frozen
module: api-core
---
# Spec: Backend Stock Route Modularization (Services + Repositories)

## 1. Goal

Refactor `backend/routes/stock.py` from a single mixed-responsibility route module into a layered backend design where:

- Routes only handle request parsing and HTTP response mapping.
- Business logic lives in Services.
- Data access and persistence live in Repositories.

This refactor must preserve current API behavior for existing v4 frontend consumers.

## 2. Acceptance Criteria (AC)

- [x] **Layer split exists**: New modules are introduced under `backend/services/` and `backend/repositories/`, and route handlers in `backend/routes/stock.py` become thin wrappers (REQ/RES only). _(done: services/v4_*_service.py + repositories/*)_
- [x] **No direct DB in routes**: Route handlers do not call `get_db_connection`, raw SQL, or persistence helpers directly. _(done: routes delegate to service layer)_
- [x] **No scoring/business computation in routes**: Route handlers do not run indicator/score/AI orchestration logic directly. _(done: computation in services/core)_
- [x] **Stable v4 API contracts**: `GET /api/v4/sniper/candidates`, `GET /api/v4/stock/{ticker}`, and `GET /api/v4/meta` return backward-compatible JSON structures (field names/types preserved). _(done: confirmed by frontend working)_
- [x] **Ticker-key compatibility kept**: `/api/v4/meta` continues to return `data` keyed by the requested ticker token. _(done: v4_meta_service preserves key format)_
- [x] **Error semantics preserved**: Existing HTTP status behavior for validation/not-found/server errors remains equivalent. _(done: HTTPException pattern preserved)_
- [x] **Cache behavior preserved**: Existing API cache semantics (TTL/sync-epoch invalidation) remain functionally equivalent after extraction. _(done: cache logic in service constructors)_
- [x] **Regression coverage**: API-level tests verify response schema parity for v4 endpoints before/after modularization. _(done: test_v4_candidates_schema_parity, test_v4_stock_detail_schema_parity, test_v4_meta_schema_parity added 2026-03-17 — all 3 v4 endpoints verified field names + types)_

## 3. Non-goals

- Changing endpoint URLs, query parameter names, or response payload schema for current clients.
- Rewriting indicator algorithms, AI models, or score formulas.
- Changing database schema or performing a storage migration.
- Frontend code refactor (except optional fixture/test updates required by preserved contract verification).

## 4. Constraints

- Must keep FastAPI routing and existing route paths intact.
- Must avoid unauthorized cross-domain refactors outside stock-route scope.
- Refactor should be incremental and reversible (phase-by-phase extraction with parity checks).
- Existing frozen specs must not be edited.

## 5. API / Data Contract

### 5.1 External API Contract (Must Stay Stable)

- `GET /api/v4/sniper/candidates`
- `GET /api/v4/stock/{ticker}`
- `GET /api/v4/meta?tickers=A,B,C`

Contract stability rules:

- Preserve response top-level keys and nested structures.
- Preserve numeric formatting behavior currently consumed by v4 UI (e.g., rounded percentage fields).
- Preserve `updated_at`, `model_version`, `signals`, and score breakdown key names.

### 5.2 Target Internal Module Contract

Proposed repositories (data-access only):

- `ScoreRepository`
  - `get_top_scores(limit, sort_by, version)`
  - `get_latest_score(ticker, model_version=None)`
  - `get_latest_scores_for_tickers(tickers)`
  - `save_score(...)`
- `IndicatorRepository`
  - `get_indicators(ticker)`
  - `get_indicators_for_tickers(tickers)`
- `StockRepository`
  - `get_stock_name(ticker)`
  - `load_price_history(ticker)`
  - `fetch_price_history(ticker, days=None, force_download=False)`
- `SystemRepository`
  - `get_sync_epoch()`
  - `check_db_health()`

Proposed services (business/orchestration):

- `TopPicksService`
- `LegacyStockDetailService` (`/api/stock/{ticker}` and verify)
- `V4CandidatesService`
- `V4StockDetailService`
- `V4MetaService`
- `SmartScanService`
- `HealthService`

Route layer responsibilities only:

- Validate and normalize HTTP input.
- Call exactly one service entrypoint per endpoint.
- Convert service exceptions/results into HTTP responses.

## 6. State Metadata

- Spec status: `draft`
- Freeze rule: transition to `frozen` only after user approval.

## 7. File Relationship

- **EXTENDS**: `docs/specs/api-refactor-perf.md` (continues backend modularization intent from `main.py` scope into `stock.py` route domain).
- **CONSTRAINT-ALIGNED WITH**: `docs/specs/frontend-api-opt.md` and `docs/specs/smart-stock-cache.md` (no v4 frontend contract breakage).
- **INDEPENDENT** from auth/payment specs.

## Migration Notes (Implementation Planning Input)

Suggested extraction order (for `/plan`):

1. Extract repositories with no route behavior change.
2. Extract pure formatters/helpers and cache access utilities.
3. Extract `V4MetaService` first (highest frontend coupling).
4. Extract `V4CandidatesService` and `V4StockDetailService`.
5. Extract legacy endpoints and health/backtest/smart-scan services.
6. Final pass: enforce thin routes and run contract regression tests.
