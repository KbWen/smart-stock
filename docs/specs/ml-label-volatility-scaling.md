---
status: frozen
title: ML Label Redesign — Volatility (ATR)-Scaled Triple-Barrier Targets
source: external
source_doc: _product-backlog.md (#2)
created: 2026-06-13
---

# ML Label Redesign — Volatility (ATR)-Scaled Triple-Barrier Targets

## Goal
Fix the **root cause** of the degenerate model surfaced by the 2026-06-13 audit (Buy/StrongBuy precision = recall = 0): the training labels use **fixed-percentage** triple barriers (+15% strong / +10% buy / −5% stop within 20 days) that ignore each stock's volatility, producing a severely imbalanced, volatility-dependent class distribution that the model cannot learn. Replace them with **ATR-scaled** barriers so the class distribution is balanced and learnable — and prove the rebalancing with reproducible evidence rather than claiming it.

## Background (measured on the dev dataset, 6 tickers × ~729 trading days)
- Fixed labels (current `core/ai/trainer.py:prepare_features`): overall **Hold 91.1% / Buy 4.9% / Strong 4.0%**, and wildly volatility-dependent per stock — e.g. low-vol `1264` = Strong 0.2% (99.6% Hold, no learnable positive signal) vs `1336` = Strong 11.1%. This imbalance is the mechanism behind the degenerate classifier.
- Prototype ATR-scaled labels (target/stop as multiples of ATR-14, same 20-day window): **Hold 58.7% / Buy 14.5% / Strong 26.7%** at multipliers (strong 3.0, buy 1.8, stop 1.5) — a balanced, learnable distribution.

## Acceptance Criteria
1. ATR-scaled triple-barrier labeling is implemented in `core/ai/trainer.py:prepare_features`, driven by config constants (`ATR_TARGET_MULT`, `ATR_BUY_MULT`, `ATR_STOP_MULT`, `LABEL_MODE`) in `core/config.py` and mirrored in `core/ai/common.py` (no magic numbers; config is the single source of truth, consistent with the existing PRED_DAYS/TARGET_GAIN pattern).
2. The barrier unit is the **per-row ATR-14** (`df['atr']`, computed at entry only — no look-ahead). Warm-up rows where ATR is NaN are excluded from the label set (no fake-zero feature/label leakage, per `engineering_guardrails.md §3`).
3. `LABEL_MODE` defaults to `atr` (the fix). The legacy `fixed` mode is **preserved and selectable** (`LABEL_MODE=fixed` reproduces the prior labels exactly) so the change is feature-flagged and reversible (`engineering_guardrails.md §2.2`).
4. **Honesty gate**: a reproducible label-distribution analysis (script + test) reports the fixed-vs-ATR class distribution on the available data. Ship claims are scoped to the **demonstrated effect** ("ATR labeling rebalances the class distribution from ~4% to ~27% StrongBuy on the dev dataset"). It MUST explicitly state that **full-universe out-of-sample precision/recall improvement is NOT validated here** because the dev DB holds only 6 tickers — no production model-quality claim is made without that data. Existing model-state disclosure (ModelHealthBanner / `get_model_health`) keeps the UI honest about whether a retrain has happened.
5. Strategy-parameter SSoT is preserved: `trainer.py` references the config constants; `backtest.py` exit semantics are intentionally **unchanged** (user-configurable fixed-% exits) — the label/strategy relationship is documented, no silent divergence introduced.
6. Tests cover: ATR barrier hit/miss correctness on synthetic data (strong-before-stop, buy-before-stop, stop-first, none), config wiring, `LABEL_MODE=fixed` backward-compatibility (identical to prior labels), and a distribution-rebalancing assertion on seeded data. No regression in existing `tests/test_core/test_ai.py` / trainer tests.

## Non-goals
- Changing backtest **exit rules** (remain user-configurable fixed-% exits — feature #4 territory, already shipped).
- Claiming full-universe OOS model-quality improvement — **data-limited; explicitly out of scope** (only label rebalancing is validated here).
- Model architecture / feature-set changes; UI changes; auto-retraining.

## Constraints
- `engineering_guardrails.md §2.2`: existing fixed-label behavior MUST remain available via `LABEL_MODE=fixed`.
- `engineering_guardrails.md §3`: no look-ahead — ATR and entry price are taken at the entry row; only future highs/lows determine barrier touches.
- `§1.3` reproducibility: all multipliers are config constants; same input → same labels.
- Existing saved models are untouched; only the **next** training run uses the new labels (no silent change to live predictions).

## API / Data Contract
- `core/config.py` (additive): `LABEL_MODE` (`"atr"|"fixed"`, default `"atr"`), `ATR_TARGET_MULT` (3.0), `ATR_BUY_MULT` (1.8), `ATR_STOP_MULT` (1.5).
- `core/ai/trainer.py:prepare_features(df, is_training=True)` — unchanged signature; label computation branches on `LABEL_MODE`. 3-class output (0/1/2) semantics preserved.
- New: `core/ai/label_analysis.py:label_distribution(dfs, mode)` → `{hold, buy, strong, n}` for reproducible evidence.

## File Relationship
EXTENDS `core/ai/trainer.py` labeling. INDEPENDENT of feature #3 (different files). No prior spec overlaps the label definition.
