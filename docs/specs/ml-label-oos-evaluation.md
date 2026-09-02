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

> [!WARNING]
> **Superseded 2026-09-02 — the table below was NOT out-of-sample.** The split it used embargoed
> `PRED_DAYS` **rows** of a cross-sectionally stacked panel, which at 92 tickers is a fraction of
> one day. Measured directly on the real panel, the resulting separation between train and test was
> **0 trading days** — the two sides shared a boundary date, so training rows had their 20-day label
> outcomes resolved inside the test window. Fixed in `docs/specs/date-based-train-test-embargo.md`
> (Honest Metrics #2). Corrected numbers are in **§Re-measurement** at the end of this file; the
> original table and conclusions are kept verbatim as the record of what was believed at the time.

## Results (2026-06-13 — CONTAMINATED, see the warning above; test split n=8,455)

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

## Re-measurement (2026-09-02, after the date-based embargo landed)

Two separate runs, described precisely because they answer different questions.

**A. The embargo's isolated effect** — one process, one panel, one seed, both splits. This is the
only controlled comparison here: nothing differs between the two rows except how the split was
computed. Panel: 74,539 labeled rows over 859 distinct dates, 92 tickers, `LABEL_MODE=atr`.

| split | embargo (trading days) | StrongBuy P / R | Buy P / R | accuracy |
|---|---|---|---|---|
| row-based (old) | **0** | 0.3516 / 0.7443 | 0.1503 / 0.1272 | 0.3526 |
| date-based (new) | **21** | 0.3454 / **0.6290** | 0.1410 / 0.1345 | 0.3552 |

StrongBuy recall falls by ~15% relative once the leak is closed — the largest single movement, and
the expected direction: the contaminated split was letting the model recall outcomes it had been
trained on. Precision drops slightly on both classes.

**B. Re-running `scripts/eval_label_modes.py`** — the same tool as the original table, now with the
date-based embargo (`embargo_days: 21`, cut 2026-01-07). **Not** directly comparable to the
2026-06-13 table: `storage.db` has moved on since June, so this run sees 37,336 labeled rows rather
than ~42,275. Both the embargo *and* the data changed.

| Label mode | Class dist (Hold/Buy/Strong) | StrongBuy P / R | Buy P / R | Accuracy |
|---|---|---|---|---|
| `fixed` (legacy) | 76.1 / 9.4 / 14.5 | 0.321 / 0.377 | 0.095 / 0.194 | 0.511 |
| `atr` (default) | 53.4 / 15.6 / 31.0 | 0.365 / 0.607 | 0.131 / 0.104 | 0.373 |

### What this does and does not settle

- **Settled**: the original numbers were not out-of-sample, and the corrected StrongBuy figures are
  worse. Conclusion 2's *direction* survives on raw precision — `atr` still scores higher than
  `fixed` on StrongBuy (0.365 vs 0.321).
- **NOT settled, deliberately**: whether `atr` is actually better once precision is normalised by
  the base rate. On this run `fixed` StrongBuy precision is 0.321 against a 14.5% prevalence
  (**≈2.2× lift**) while `atr` is 0.365 against 31.0% (**≈1.2× lift**), which inverts the ranking;
  `atr` Buy precision 0.131 against 15.6% prevalence is **below chance**. Recording test-split
  prevalence and reporting precision as lift is backlog **#5**, and re-deciding `LABEL_MODE` on that
  basis belongs there — not in an embargo fix. The `atr` default is unchanged here.
- The §Caveat below still applies in full: ~5% of the universe, large/liquid-cap biased.

## File Relationship
INDEPENDENT (evaluation record). References #2 `ml-label-volatility-scaling.md`. No code-behavior change — this documents measured results and ships a reproducible eval script.
