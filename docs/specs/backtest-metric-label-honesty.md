---
status: frozen
title: Backtest Metric Label Honesty
source: external
source_doc: _product-backlog.md (#4)
created: 2026-06-13
---

# Backtest Metric Label Honesty

## Goal
Backtest metrics must not claim more rigor/precision than they have. Fix the unannualized "Sharpe" label, the 9999 profit-factor sentinel, and the hardcoded ±15%/-5% tooltips that contradict the user's sliders.

## Acceptance Criteria
1. `backend/backtest.py`: `profit_factor` / `net_profit_factor` return `None` (not the `9999.0` sentinel) when there are no losing trades; rounding guards None. The UI renders "—" (N/A) for None (existing `?? '—'` fallback).
2. The Backtest "Sharpe" card is honestly labelled/annotated as an **unannualized, single-period** ratio (mean net return ÷ stddev across the Top-N picks, no risk-free baseline) — its tooltip states it is not comparable to a conventional annualized Sharpe.
3. STOP/HIT copy no longer hardcodes "+15% / -5%": the sniper-hit-rate tooltip in `Backtest.tsx` reflects the user's `target_gain`/`stop_loss` slider values, and the `BacktestTable` footnote is generic (no fixed percentages).
4. Backend pytest + frontend vitest + production build green; no change to the underlying computations beyond the sentinel→None.

## Non-goals
- Making Sharpe actually annualized / risk-free-adjusted (out of scope this stage).
- Changing drawdown / friction math.

## File Relationship
EXTENDS docs/specs/backtest-and-performance-opt.md
