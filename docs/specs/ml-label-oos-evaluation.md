---
status: shipped
title: ML Label OOS Evaluation — ATR vs Fixed at Expanded Scale (Honest Findings)
source: external
source_doc: follow-up to ml-label-volatility-scaling.md (#2)
created: 2026-06-13
---

# ML Label OOS Evaluation — ATR vs Fixed at Expanded Scale

Follow-up verification for [#2 ML label redesign](ml-label-volatility-scaling.md), which shipped ATR-scaled labels (`LABEL_MODE=atr`) but explicitly disclaimed any full-universe out-of-sample (OOS) model-quality claim because the dev DB held only 6 tickers. This is the honest measurement at a larger (but still partial) scale.

## Method
- **Data**: storage.db expanded to **92 liquid TWSE tickers** (~99k price rows; ~42,275 labeled feature rows after indicator warm-up). Fetched via `core.data.fetch_stock_data`.
- **Split**: chronological 80/20 with a `PRED_DAYS` embargo (matches `trainer.train_and_save`). No shuffling — temporal order preserved.
- **Model**: the production ensemble (HistGradientBoosting + RandomForest + MLP) with the same class-weighting; identical setup for both label modes.
- **Reproduce**: `python scripts/eval_label_modes.py` (operates on whatever tickers are in storage.db).

## Results (out-of-sample test split, n=8,455)

| Label mode | Class dist (Hold/Buy/Strong) | StrongBuy precision / recall | Buy precision / recall | Accuracy |
|---|---|---|---|---|
| `fixed` (legacy) | 76.9 / 9.4 / 13.6 | 0.339 / 0.424 | 0.082 / 0.187 | 0.485 |
| `atr` (default)  | 54.8 / 15.7 / 29.6 | **0.363 / 0.518** | **0.120** / 0.150 | 0.351 |

## Honest conclusions (no overclaim)
1. **The degenerate model did NOT reproduce at 92-ticker scale under EITHER mode.** Both produce non-zero precision/recall for Buy and StrongBuy. The precision=recall=0 degeneracy found in the 2026-06-13 audit was largely a **small-data / low-volatility artifact of the 6-ticker dev DB** — more (and more varied) data is the bigger lever than the labeling change alone.
2. **ATR labels are a modest, directional improvement on the high-value StrongBuy class**: precision 0.339 → 0.363, recall 0.424 → 0.518; Buy precision also improves (0.082 → 0.120). Buy recall is slightly lower (0.187 → 0.150).
3. **Overall accuracy is lower for `atr` (0.485 → 0.351), but accuracy is the wrong metric here** — `fixed`'s 76.9% Hold base rate inflates it (predict-Hold scores high). For an imbalanced ranking task the per-class StrongBuy/Buy precision/recall above are the meaningful signals, and ATR wins on the StrongBuy precision+recall that the "sniper" strategy actually targets.
4. **Absolute precision is still low (0.12–0.36).** This is a hard prediction problem; neither labeling makes the model "good". ATR is a refinement, not a silver bullet.

## Caveat (scope of this evidence)
92 tickers, **biased toward large/liquid TWSE caps (~5% of the ~1,800 listed+OTC universe)**. This is materially more credible than the 6-ticker dev result but is NOT a full-universe validation. A complete picture needs the full universe backfilled (feature #3's `backfill_history`), including mid/small-caps and OTC, where volatility and base rates differ.

## Recommendation
Keep `LABEL_MODE=atr` as the default: it yields a balanced, learnable class distribution and a better StrongBuy precision+recall on this sample. The larger future lever for model quality is **universe coverage**, not further label tuning.

## File Relationship
INDEPENDENT (evaluation record). References #2 `ml-label-volatility-scaling.md`. No code-behavior change — this documents measured results and ships a reproducible eval script.
