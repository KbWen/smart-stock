---
status: frozen
title: Docs ↔ Reality Sync
source: external
source_doc: _product-backlog.md (#5)
created: 2026-06-13
---

# Docs ↔ Reality Sync

## Goal
Make the documentation match the actual implementation so the project's stated claims are honest.

## Acceptance Criteria
1. `docs/API_CONTRACT.md`: `POST /api/sync/trigger` → `POST /api/sync` (the real route); `GET /api/backtest` documents the V4.2 params (`commission_rate`, `tax_rate`, `slippage_rate`, `target_gain`, `stop_loss`, `holding_days`) and the real response fields (net metrics, `sharpe_ratio`, `profit_factor`/`net_profit_factor` null on no-loss, drawdowns).
2. `README.md`: stock count reflects reality (~1,800+, not "約 1000"); the "Smart Sync 2.0" claim no longer says auto-trigger or "10x" — it states manual/background trigger with `ThreadPoolExecutor` (5 workers).
3. `docs/ARCHITECTURE.md`: the sync-state lock is attributed to `backend/routes/sync.py` (not `backend/main.py`).
4. `docs/project_meta/TESTING.md`: references a real test file (not the nonexistent `tests/test_data_layer.py`); the CI command includes `-m "not integration"`.
5. `docs/guides/db-operations.md`: the curl example uses `POST /api/sync` (not `/api/sync/trigger`).
6. The `model_health` field added to `GET /api/market_status` (backlog #3) is documented.

## Non-goals
- Changing any runtime behavior (docs only).
- Rewriting docs beyond the inaccuracies above.

## File Relationship
INDEPENDENT
