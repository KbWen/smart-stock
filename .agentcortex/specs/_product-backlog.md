---
status: living
title: Product Backlog — Honesty-First (Data-Consistent-With-Claims)
source: 2026-06-13 multi-agent code audit
created: 2026-06-13
last_updated: 2026-06-13 (#1 spec frozen, In Progress)
---

# Product Backlog

## Source Summary
Stage goal: a stable/simple/**data-consistent-with-its-claims** smart-stock — complete, not perfect. User chose **honesty-first**: fix truthfulness gaps and honestly reframe model state in the UI; model retraining is explicitly out of scope this stage. Items decomposed from the 2026-06-13 audit. Full detail in `_raw-intake.md`.

## Feature Inventory
| # | Feature | Spec File | Tier | Status | Dependencies |
|---|---|---|---|---|---|
| 1 | Frontend honest data states — remove mock-as-live (mockData.ts fallback → loading/no-data/error states) | .agentcortex/specs/frontend-honest-data-states.md | feature | In Progress | — |
| 2 | Backend failure-state honesty — predictor.py stops faking `ai_prob=0.0`; propagate null/no-data | — | feature | Pending | — |
| 3 | UI honest model-state disclosure — surface "model unready / low-confidence" instead of selling degenerate output | — | feature | Pending | #1, #2 |
| 4 | Backtest metric label honesty — Sharpe rename/annotate, 9999→N/A, dynamic ±gain/-loss tooltips (EXTENDS backtest-and-performance-opt) | — | quick-win | Pending | — |
| 5 | Docs ↔ reality sync — API_CONTRACT sync/trigger + backtest params, README auto-sync/10x/stock-count, ARCHITECTURE/TESTING fixes | — | quick-win | Pending | — |
| 6 | Frontend tests into CI — enforce 44 vitest + production build (EXTENDS frontend-testing) | — | quick-win | Pending | — |

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
