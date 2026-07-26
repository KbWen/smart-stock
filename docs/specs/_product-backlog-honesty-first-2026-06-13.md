---
status: archived
title: Product Backlog — Honesty-First (Data-Consistent-With-Claims) [ARCHIVED — epic complete 2026-06-13]
source: 2026-06-13 multi-agent code audit
created: 2026-06-13
last_updated: 2026-06-13 (ALL 6 shipped via PR #20)
archived: 2026-07-26 (epic complete on 2026-06-13; superseded by the Optimization Round 2 backlog, then by _product-backlog.md)
---

# Product Backlog

## Source Summary
Stage goal: a stable/simple/**data-consistent-with-its-claims** smart-stock — complete, not perfect. User chose **honesty-first**: fix truthfulness gaps and honestly reframe model state in the UI; model retraining is explicitly out of scope this stage. Items decomposed from the 2026-06-13 audit. Full detail in `_raw-intake.md`.

## Feature Inventory
| # | Feature | Spec File | Tier | Status | Dependencies |
|---|---|---|---|---|---|
| 1 | Frontend honest data states — remove mock-as-live (mockData.ts fallback → loading/no-data/error states) | docs/specs/frontend-honest-data-states.md | feature | Shipped | — |
| 2 | Backend failure-state honesty — predictor.py stops faking `ai_prob=0.0`; propagate null/no-data | docs/specs/backend-failure-state-honesty.md | feature | Shipped | — |
| 3 | UI honest model-state disclosure — surface "model unready / low-confidence" instead of selling degenerate output | docs/specs/ui-model-state-disclosure.md | feature | Shipped | #1, #2 |
| 4 | Backtest metric label honesty — Sharpe rename/annotate, 9999→N/A, dynamic ±gain/-loss tooltips (EXTENDS backtest-and-performance-opt) | docs/specs/backtest-metric-label-honesty.md | quick-win | Shipped | — |
| 5 | Docs ↔ reality sync — API_CONTRACT sync/trigger + backtest params, README auto-sync/10x/stock-count, ARCHITECTURE/TESTING fixes | docs/specs/docs-reality-sync.md | quick-win | Shipped | — |
| 6 | Frontend tests into CI — enforce 44 vitest + production build (EXTENDS frontend-testing) | docs/specs/frontend-ci.md | quick-win | Shipped | — |

## Status Key
- Pending: not yet started
- In Progress: spec generated, bootstrap running
- Shipped: feature shipped (see Ship History in current_state.md)
- Deferred: explicitly deferred
- Cancelled: explicitly cancelled

## Notes
- **Recommended start: #1** — it establishes the honest loading/no-data/error UI pattern that #3 depends on, and removes the most direct "fake-data-as-real" deception.
- {#1, #2, #3} form a coupled cluster ("honest signal end-to-end"); #4/#5/#6 are independent quick-wins that can slot in at any point.
- Overlap (per spec-intake Hard Rule #5): #4 EXTENDS shipped `backtest-and-performance-opt.md`; #6 EXTENDS frozen `frontend-testing.md`. Do NOT modify those shipped/frozen specs — new EXTENDS specs only.
