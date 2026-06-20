---
status: frozen
title: Real-AI First-Run (opt-in)
source: external
source_doc: _product-backlog.md (Directly-Usable v1, #5)
created: 2026-06-20
frozen: 2026-06-20
---

# Real-AI First-Run (opt-in)

## Goal
Give a user a one-command, OPT-IN path from a fresh clone to **populated AI probabilities** (not N/A): fast bulk backfill (#4) → train the model → recalculate scores. N/A stays the default (no model bundled); this path is explicitly opt-in and slower than the offline demo.

## Acceptance Criteria
1. `scripts/setup_real_ai.py [--days N] [--listed-only] [--min-tickers M]` orchestrates, in order: bulk backfill (`core.bulk_history.backfill_bulk`) → coverage check (`core.data.report_history_coverage`) → (gated) train (`backend.train_ai.main`) → recalculate (`backend.recalculate.recalculate_all(incremental=False)`).
2. **Honest gating**: if fewer than `--min-tickers` (default 50) tickers have ≥ `MIN_TRAIN_ROWS` history, training is SKIPPED, AI stays N/A, and the script says so clearly (a tiny-data model would be degenerate — worse than honest N/A). Below the ~92 OOS floor, training proceeds but warns the model may be weak.
3. No model is bundled; the trained model is local + gitignored. The default offline demo / N/A behaviour is unchanged (this script is never run automatically).
4. The orchestration is unit-testable: the four steps are injectable; tests verify ordering + the gating branch with no network/DB/training.
5. quickstart output + README document the opt-in command and its honest caveats (takes minutes; raw prices via #4; a weak model is disclosed by `model_health`).
6. Honesty-first preserved: AI is populated only when real data + a real (if weak) model exist; `model_health` discloses a degraded model in the UI (shipped in #3 / ui-model-state-disclosure).

## Non-goals
- Improving model quality / new architecture (data scale is the lever, not this script); bundling a `.pkl`; wiring training into the default flow or `/api/sync`.

## Constraints
- Honesty-first: never fabricate AI; gate on real coverage; disclose weak models. Small & reversible (additive opt-in script). Reuses #4 backfill + shipped `train_ai` / `recalculate` (unchanged).

## API / Data Contract
- No API change. Reuses `backfill_bulk`, `report_history_coverage`, `train_ai.main`, `recalculate_all`.

## File Relationship
EXTENDS docs/specs/onboarding-quickstart.md, docs/specs/accelerated-universe-sync.md
