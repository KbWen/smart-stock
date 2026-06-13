---
status: frozen
title: Backend Failure-State Honesty (No Fake 0.0%)
source: external
source_doc: _product-backlog.md (#2)
created: 2026-06-13
---

# Backend Failure-State Honesty

## Goal
A failed/unavailable AI prediction must NOT be presented as a genuine `0.0%`. Represent "prediction unavailable" (model missing, SHA256/HMAC mismatch, load error, prediction exception, insufficient data) as `null` end-to-end (backend → API → frontend display), distinct from a genuine low probability. Serves the stage goal "data consistent with our claims" and removes the silent masking of integrity/availability failures.

## Acceptance Criteria
1. `core/ai/predictor.py:predict_prob` returns `None` on ALL failure paths — including the prediction-exception path, which currently returns `{"prob": 0.0, ...}`. `None` ⟺ "no genuine prediction"; a dict with `prob` ⟺ success.
2. A new helper `core/utils.py:to_ai_percent(value)` returns `None` when value is `None`, else `round(safe_float(value) * 100, 1)`. Used by all readers that emit `ai_prob`/`ai_probability`.
3. Writers (`backend/routes/sync.py`, `backend/recalculate.py`) pass `None` to `save_score_to_db` when `predict_prob` is unavailable (no `0.0` default). `save_score_to_db` stores SQL `NULL` (not `0.0`) when `ai_prob is None`.
4. Readers (`v4_candidates_service`, `v4_stock_detail_service`, `v4_meta_service`, `legacy_service`, `top_picks_service`) emit `ai_prob`/`ai_probability` as `null` when the underlying value is unavailable, instead of coercing to `0`. Backtest (`backend/backtest.py`) is OUT of scope (it filters failed predictions out via threshold; never displays a fake 0.0).
5. Frontend: `ai_prob` / `ai_probability` typed `number | null`. When `null`, the candidate row, technical scanner, and detail card show an honest "N/A" / "—" (NOT "0.0%" and NOT a "HIGH RISK" recommendation badge). Sorting and filtering by AI prob are null-safe (nulls sink to the bottom; excluded from "HIGH AI").
6. Tests: backend unit tests assert `predict_prob` exception → `None`, `to_ai_percent(None) → None`, and a save→load NULL round-trip; frontend test asserts a null ai_prob renders "N/A"/"—" not "0.0%". Backend pytest green, frontend vitest + production build green.

## Non-goals
- Global degraded-model disclosure / model-quality banner (that is backlog #3).
- Backtest metric labels / Sharpe / sentinel (backlog #4).
- Retraining or changing model quality.
- Changing the genuine prediction math.

## Constraints
- `stock_scores.ai_probability` column is already nullable (`REAL`); no schema migration needed.
- Preserve existing behavior for genuine predictions (a real low prob still renders as its number).
- Centralize the null/percent logic in `to_ai_percent` to avoid divergent coercion across readers.
- Small, reversible; no change to ranking semantics beyond null-safety.

## API / Data Contract
- `ai_prob` (candidates/meta) and `ai_probability` (detail) become `number | null` in API responses. `null` = prediction unavailable.
- No new endpoints; no schema change.

## File Relationship
INDEPENDENT
