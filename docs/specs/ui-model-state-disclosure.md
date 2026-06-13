---
status: frozen
title: UI Honest Model-State Disclosure
source: external
source_doc: _product-backlog.md (#3)
created: 2026-06-13
---

# UI Honest Model-State Disclosure

## Goal
When the active AI model is degraded (cannot identify buy signals — e.g. the committed model with buy/strong precision=recall=0) or unavailable, the UI must say so honestly with a prominent banner, instead of silently presenting degenerate model output as actionable buy signals. Closes the headline "data vs claims" gap surfaced by the 2026-06-13 audit.

## Acceptance Criteria
1. `core/ai/predictor.py:get_model_health()` (exported from `core.ai`) reads the active model's recorded out-of-sample metrics from `models_history.json` and returns `{status, version, message}` where `status` is:
   - `"unavailable"` — model version is `"unknown"` (not loaded/trained) or no metrics recorded;
   - `"degraded"` — the active model's buy-signal discriminative power is zero, i.e. `precision_buy + recall_buy + precision_strong + recall_strong <= 0`;
   - `"ok"` — otherwise.
   `message` is a Traditional-Chinese, honest, user-facing string for non-`ok` states (empty for `ok`).
2. `GET /api/market_status` includes a `model_health` field (the dict from AC1).
3. Frontend renders a prominent banner (amber/red) when `model_health.status !== "ok"` on the Dashboard and the Technical Scanner (Indicators) pages, showing `message`. No banner when `ok`. The banner is purely informational (does not block the rest of the UI).
4. Tests: backend unit tests for `get_model_health` (ok / degraded / unavailable from synthetic history); frontend test that the banner shows on `degraded` and is absent on `ok`. Backend pytest + frontend vitest + production build green.

## Non-goals
- Retraining or improving the model (explicitly out of scope this stage).
- Per-stock null ai_prob handling (that is backlog #2, done).
- Changing prediction math or ranking.

## Constraints
- Read-only assessment from existing `models_history.json`; no schema/endpoint shape change beyond the additive `model_health` field.
- `get_model_health` must be cheap (no model load) — it reads the history JSON and the cached version string only.
- Degraded model still serves its (low) probabilities; the banner is disclosure, not suppression.

## API / Data Contract
- `GET /api/market_status` response gains `model_health: { status: "ok"|"degraded"|"unavailable", version: string, message: string }`. Additive; existing fields unchanged.

## File Relationship
INDEPENDENT
