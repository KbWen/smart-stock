---
status: living
title: Product Backlog — Honest Research Workbench
source: 2026-07-02 user-directed post-v1 product direction
created: 2026-07-02
last_updated: 2026-07-02 (#1 Strategy Lab Shipped; #6 CSRF-parity added as review-finding)
---

# Product Backlog

## Source Summary
After the "Directly-Usable v1" self-install epic completed (all 6 shipped 2026-06-20; archived to `_product-backlog-directly-usable-v1-2026-06-20.md`), the user set the next-stage direction: an **honest, self-hostable TW-stock research workbench** — primary audience TW retail investors (an antidote to black-box "AI 飆股" tools), secondary audience developers/quant learners wanting a transparent reproducible reference. **Differentiator = transparency/honesty, NOT prediction accuracy** (honesty-first preserved: the ML model is honestly weak; do not chase model quality as the headline).

**Cross-cutting design constraint (applies to every feature in this epic)**: the audience spans experts and complete novices, so the product must offer a solid base architecture + flexibility via **progressive disclosure — simple, good defaults up front; depth revealed on demand** — so even someone who "just wants to invest" has a good place to go. Each feature spec MUST state how it satisfies this (simple default path + expert depth path).

**Out of scope (honesty guards)**: no 飆股/guaranteed-profit framing; no fake numbers hiding a weak model (honest N/A stays honest); no live trading/order execution/money movement; no hosted service or external data send (self-install/local-only stays). Full source detail: `_raw-intake.md` (deleted after all first-round specs are generated).

## Feature Inventory
| # | Feature | Kind | Labels | Priority | Spec File | Tier | Status | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | Strategy Lab — named/saveable/side-by-side backtest workbench built on existing `/api/backtest` + TW cost sliders; compare net-of-cost equity/Sharpe/drawdown across saved strategies (flagship; needs no model improvement) | feature | backtest | P1 | docs/specs/strategy-lab.md | feature | Shipped | — |
| 2 | Transparency Panel — first-class "what does the system actually know" view: data coverage (history depth/universe completeness), model_health, last-trained, sample size, OOS metrics | feature | transparency | P1 | docs/specs/transparency-panel.md | feature | Shipped | — |
| 3 | Explainable Screening — deepen ScoreBreakdown on 選股雷達: which signals fired + that combo's backtested hit-rate + model_health/sample-size-qualified AI number | feature | screening | P1 | docs/specs/explainable-screening.md | feature | In Progress | #1 (soft) |
| 4 | Novice Entry — progressive-disclosure simple default / guided mode so casual "just want to invest" users have a good starting destination; expert depth on demand | feature | onboarding, ux | P2 | — | feature | Pending | #2, #3 (soft) |
| 5 | Reproducible Reference Layer — one-command data→label→train→backtest→eval flow + walkthrough doc for the developer/learner audience (Docker self-seed already exists) | feature | docs, ml | P2 | — | feature | Pending | — |
| 6 | CSRF-header parity — add the `smart_scan`-style `X-Requested-With` check to `/api/strategies` mutations (POST/PUT/DELETE) for security-baseline consistency (no active vuln — app has no cookie auth; frontend already sends the header). Surfaced by #1 independent review. | review-finding | api, security | P2 | — | quick-win | Pending | #1 |

## Column Reference
- **Kind**: `feature` (planned) · `quick-win` (small planned) · `review-finding` (surfaced by review/audit) · `hotfix-spawn` (systemic issue from hotfix)
- **Priority**: `P0` (blocking, do now) · `P1` (high value, next batch) · `P2` (nice to have) · `—` (not yet prioritized)

## Status Key
- Pending: not yet started
- In Progress: spec generated, bootstrap running
- Shipped: feature shipped (see Ship History in current_state.md)
- Deferred: explicitly deferred
- Cancelled: dropped
