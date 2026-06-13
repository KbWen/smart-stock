---
status: living
title: Product Backlog — Optimization Round 2 (Adoptability · ML Labels · Data Completeness)
source: 2026-06-13 user-directed optimization (3 directions)
created: 2026-06-13
last_updated: 2026-06-13 (#3 Shipped via PR #22)
---

# Product Backlog

## Source Summary
Second optimization round after the honesty-first epic shipped (PR #20/#21). User gave three directions: (1) make the repo trivially easy for others to adopt and run; (2) improve the *actual* AI training, starting from the labels; (3) make the listed (上市) / OTC (上櫃) stock data comprehensive and complete. Previous epic backlog archived to `_product-backlog-honesty-first-2026-06-13.md` (all 6 Shipped — see Ship History in current_state.md). Execution order chosen by foundation-first dependency: #3 (data) → #2 (labels/model) → #1 (onboarding).

## Feature Inventory
| # | Feature | Kind | Labels | Priority | Spec File | Tier | Status | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 3 | Listed/OTC universe & price-data completeness — authoritative live TWSE/TPEX sourcing (replace stale twstock static list), include ETFs, market/kind tagging, history-coverage report + backfill | feature | data | P1 | docs/specs/listed-otc-data-completeness.md | feature | Shipped | — |
| 2 | ML label redesign — volatility/ATR-scaled triple-barrier targets to fix the degenerate (buy/strong precision=recall=0) model and rebalance class distribution | feature | ml | P0 | docs/specs/ml-label-volatility-scaling.md | feature | In Progress | #3 (soft) |
| 1 | Frictionless onboarding — one-command quickstart + seeded demo data + README run-through so a newcomer runs it in minutes | feature | onboarding | P1 | — | feature | Pending | — |

## Column Reference
- **Kind**: `feature` (planned) · `quick-win` (small planned) · `review-finding` (surfaced by review/audit) · `hotfix-spawn` (systemic issue from hotfix)
- **Priority**: `P0` (blocking, do now) · `P1` (high value, next batch) · `P2` (nice to have) · `—` (not yet prioritized)

## Status Key
- Pending: not yet started
- In Progress: spec generated, bootstrap running
- Shipped: feature shipped (see Ship History in current_state.md)
- Deferred: explicitly deferred
- Cancelled: explicitly cancelled

## Notes
- **#2 is P0** (the degenerate model is the core product-truth gap the honesty epic only *disclosed*; this fixes it) but has a **soft dependency on #3** — more complete/fresh data materially improves the relabel/retrain outcome. Hence #3 first.
- #1 is fully independent and can slot in at any point.
- Scope guard (spec-intake Hard Rule #5): #3 EXTENDS the `core/data.py` data layer; it does NOT modify shipped/frozen specs. ETF inclusion in the *universe* is data-completeness only — whether ETFs enter the *training set* is decided in #2, not here.
