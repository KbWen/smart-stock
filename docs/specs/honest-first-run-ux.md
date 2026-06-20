---
status: shipped
title: Legible Honest First-Run UX
source: external
source_doc: _product-backlog.md (Directly-Usable v1, #3)
created: 2026-06-20
frozen: 2026-06-20
shipped: 2026-06-20
---

# Legible Honest First-Run UX

## Goal
Make the honest fresh-clone / demo state **legible** so a first-time user reads it as an intentional demo ("AI model not trained yet; technical scores are live"), NOT as a broken product — without hiding the honest N/A. Today the AI column shows bare "N/A" everywhere with no inline explanation, scattered English sits inside an otherwise Traditional-Chinese UI, and the prominent sync button silently triggers a 10–15 min full-market sync.

## Acceptance Criteria
1. A clear no-model / demo indicator tells the user the AI model isn't trained yet while technical scores are live, surfaced from the existing `model_health` signal (extend `ModelHealthBanner` and/or a small header badge). Must not fabricate a model.
2. AI "N/A" is reframed inline with a short reason (e.g. "N/A · 尚未訓練模型") + tooltip, in `ScoreBreakdown` and `CandidateRow`/`CandidateTable` — the value stays honestly absent, never a fake number.
3. Scattered English UI strings are localized to Traditional Chinese: sidebar nav labels (`Layout`), `SniperCard` empty/loading states, `StockList` empty / no-data / error states, and the AI Analyst neutral fallback (`backend/services/v4_stock_detail_service.py`).
4. The full-market sync trigger ("同步資料庫") warns the user it starts a slow (~10–15 min) network sync before running (confirm dialog or unmistakable label), so newcomers don't trip it unaware.
5. Honesty preserved: N/A is reframed, never hidden or replaced by a fake value; no data, scoring, or model behavior changes. Existing honest loading/no-data/error states remain.
6. Design gate (§4.4): a DSoT visual artifact for the new/changed UI exists and the implementation matches it; `/review` verifies fidelity.

## Non-goals
- Training a model (#5), data-sync acceleration (#4), Docker (#6).
- Redesigning the dashboard layout or visual system; full app i18n / English UI. Scope is the first-run legibility surfaces above.

## Constraints
- Honesty-first: never hide N/A; surface model state truthfully via existing `get_model_health` / `model_health`.
- Small & reversible; reuse existing components (`ModelHealthBanner`, `Tooltip`) and the `useDashboardData` / `useCachedApi` hooks; do not rewrite the data layer.
- Keep existing frontend vitest tests green (update intentionally-changed string assertions).
- UI language: Traditional Chinese (繁體中文).

## API / Data Contract
- No new endpoints. Consumes existing `model_health` from `/api/market_status` (or `/api/init`). The badge/banner derive purely from existing fields.

## File Relationship
EXTENDS docs/specs/frontend-honest-data-states.md, docs/specs/ui-model-state-disclosure.md
