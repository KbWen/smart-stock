# ADR-004: Model-Rotation Sort Key — Net vs Gross Profit Factor

- **Status**: Proposed (2026-07-19)
- **Origin**: 2026-07-19 find-more audit (LOW).
- **applies_to**: `core/ai/common.py` (`profit_factor_sort_key`), `core/ai/trainer.py`
  (rotation), `backend/manage_models.py` (prune/list), `models_history.json` schema

## Context

Model retention/rotation ranks saved models by `profit_factor_sort_key`
(`core/ai/common.py:47`), which reads `h['backtest_30d']['profit_factor']` — the **gross**
profit factor. Used at `trainer.py:472` (keep top `MAX_SAVED_MODELS`) and
`manage_models.py:141` (prune). But the backtest and its UI are branded **net-of-cost**
(the summary exposes both `profit_factor` and `net_profit_factor`, and Net ROI / Net Win
Rate are the headline metrics). So the model the system *keeps* is chosen by a metric that
ignores the transaction friction the rest of the product foregrounds — a mild internal
inconsistency.

Severity is LOW (it only reorders near-ties, and on demo data backtests are often
degenerate). Critically, this is **model-rotation logic**, which the SSoT Global Lessons
`[Rotation Conflict]` + `[Sidecar Parity]` flag as historically bug-prone (a bad new model
once displaced a good old one). So even a "small" change here earns full review/test.

## Options

- **A — Switch the sort key to `net_profit_factor`.** Most consistent, but the history
  entries (`trainer.py:417`) currently persist only gross `profit_factor`; net must first
  be **persisted** and **backfilled/None-guarded** for pre-existing entries, or the sort
  silently treats old models as unranked. A schema + migration change.
- **B — Store both, prefer net with gross fallback (recommended).** Persist
  `net_profit_factor` alongside `profit_factor` in the history; `profit_factor_sort_key`
  prefers net when present, falls back to gross for legacy entries. Additive, backward-
  compatible, no destructive migration.
- **C — Leave + document.** Add a comment that rotation ranks by gross by design; cheapest,
  but leaves the net/gross inconsistency.

## Decision (recommended)

**B** — additive dual-store with a net-preferring, gross-fallback key. It removes the
inconsistency without a destructive `models_history.json` migration and stays safe for
legacy entries.

## Consequences / risks

- Classification: `feature` (touches model-selection data-flow + a persisted schema) —
  NOT a quick-win, per the rotation-safety lessons.
- MUST add a test proving: (a) a model with better net but worse gross now ranks higher;
  (b) a legacy entry lacking `net_profit_factor` still sorts via gross (no crash / no
  silent demotion to unranked).
- Keep `trainer.py` rotation and `manage_models.py` prune using the SAME key (they already
  share it) — do not fork the logic.

## Rollback

Additive fields + a single sort-key function change → branch-revertable; legacy history
entries remain valid throughout (fallback path).
