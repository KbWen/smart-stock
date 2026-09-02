---
status: frozen
title: Date-Based Train/Test Embargo
source: external
source_doc: _product-backlog.md #2 (quant-expert panel audit, finding F1 — 3/3 independent auditors)
created: 2026-09-02
updated: 2026-09-02
frozen: 2026-09-02
primary_domain: ml
secondary_domains: [transparency]
---

# Date-Based Train/Test Embargo

Honest Metrics epic **#2** (review-finding, P0). The training embargo is measured in **pooled rows**
on a cross-sectionally stacked panel, so it removes almost no time at all.

`core/ai/trainer.py:225-232` concatenates every ticker's frame and sorts by date, which means one
calendar day contributes **N rows** (N = number of tickers). `:237-238` then splits at
`int(len(X_all) * 0.8)` and embargoes the train set by `X_all.iloc[:split_idx - PRED_DAYS]` —
dropping `PRED_DAYS = 20` **rows**. At the 92-ticker scale used in
`docs/specs/ml-label-oos-evaluation.md` that is **≈ 0.2 trading days**.

Every triple-barrier label looks forward **20 trading days**. So roughly `20 × N` training rows
still have their outcomes resolved inside the test window: the model is trained on the answer to the
question it is then scored on. `core/ai/trainer.py:263` repeats the mistake —
`TimeSeriesSplit(n_splits=3, gap=PRED_DAYS)`, where scikit-learn's `gap` is also counted in
**samples** — and `scripts/eval_label_modes.py:70` carries the same line.

All three independent auditors raised this. `docs/DATA_INTEGRITY.md:42` presents this exact code as
the mitigation for "Chronological Leakage", and `README.md:237` claims data leakage is 「完全杜絕」;
correcting those claims is backlog #6, sequenced after this so it can describe real behaviour.

## Goal

Make the embargo mean what its own documentation says: no training row's label window may overlap
any evaluation row's date. Measure the split and the gap in **trading days drawn from the panel's own
calendar**, not in pooled rows, so `oos_metrics` is genuinely out-of-sample.

## Acceptance Criteria

1. The holdout split is chosen by **date**, not row offset. Let `cut_date` be the
   date of the row at `int(len(X_all) * 0.8)` in the date-sorted panel. The test set is every row
   with `date >= cut_date`; the train set is every row with `date < embargo_date`, where
   `embargo_date` is the date `PRED_DAYS` **trading days** before `cut_date`, taken from the sorted
   unique dates present in the panel (its own calendar — no external holiday table).

2. No training row's label window may reach the test set. Stated as a testable
   invariant: the number of distinct panel dates in `[max(train.date), min(test.date))` is
   `>= PRED_DAYS`.

3. The cross-validation gap is scaled to the panel's width. `TimeSeriesSplit`'s `gap`
   counts samples, so it is set to `PRED_DAYS × max_rows_per_date` over the training split, where
   `max_rows_per_date` is the largest number of rows any single date contributes. Using the **max**
   rather than the mean is deliberate: it is the only choice that *guarantees* the gap spans at
   least `PRED_DAYS` distinct dates on an uneven panel. The cost is bounded and disclosed — at 92
   tickers it is ~1,840 rows of a ~42,000-row training split (≈4%).

4. Insufficient data fails **honestly and loudly**, never silently. If the panel has
   fewer than `PRED_DAYS + 1` distinct dates before `cut_date`, or the embargo empties the train
   split, or `TimeSeriesSplit` cannot produce the requested folds under the scaled gap, training
   aborts with an explicit message naming the shortfall — it does **not** fall back to a smaller
   embargo, a row-based split, or an unsplit fit. A contaminated `oos_metrics` is worse than no
   model, because the number is published on `/transparency`.

5. `scripts/eval_label_modes.py:70` receives the same date-based split and scaled
   gap, so the ATR-vs-fixed comparison in `docs/specs/ml-label-oos-evaluation.md` is reproducible
   against corrected numbers rather than the contaminated ones it currently reports.

6. Tests, each **empirically falsified** before acceptance (restore the row-based
   embargo, watch them fail) — and written against a synthetic multi-ticker panel so the invariant
   is checked directly rather than inferred from a metric:
   - on an N-ticker panel, the distinct-date gap between train and test is `>= PRED_DAYS`, and the
     same assertion **fails** under the old row-based embargo;
   - the CV gap spans `>= PRED_DAYS` distinct dates in every fold;
   - a panel with too few dates aborts with the honest message instead of training;
   - a single-ticker panel (where rows and dates coincide) still behaves correctly — the fix must
     not regress the degenerate case it was already handling by accident.

7. The change in reported metrics is **measured and recorded**, not asserted. The
   Work Log records `oos_metrics` before and after on the same data and seed. These numbers are
   expected to get **worse**, because the previous ones were contaminated; per the epic honesty
   guard, no threshold, feature, label mode, or model hyper-parameter may be adjusted to soften that.

## Non-goals

- **No fix for F7** (model rotation ranking on an in-sample backtest) — backlog #4.
- **No fix for F8/F9/F10** (OOS metrics attributed to the split model rather than the shipped
  full-data refit; missing test-split prevalence and lift-over-baseline; `get_model_health` calling a
  below-prevalence model "ok") — backlog #5. In particular `class_distribution` continues to record
  the **train** split here; correcting that is #5's job.
- **No uniqueness/overlap sample weighting.** With a 20-day horizon sampled daily, ~20 consecutive
  rows per ticker share one outcome path, so effective sample size is far below `len(X_all)`. Real,
  but a separate modelling change.
- **No doc rewrite.** `docs/DATA_INTEGRITY.md:42` and `README.md:237` are corrected in #6.
- No change to features, label definition, model architecture, hyper-parameters, or the API surface.

## Constraints

- **Small and reversible**: the change is confined to the split/gap computation in
  `core/ai/trainer.py:train_and_save` and the mirrored block in `scripts/eval_label_modes.py`.
- **Honesty guard** (epic-wide): the corrected metrics are expected to look worse. Nothing may be
  tuned to compensate, and a number that cannot be computed cleanly is not reported at all.
- **Panel calendar only**: trading days come from the sorted unique dates present in the data. No
  external calendar dependency, and no assumption that every ticker trades every day.
- **No retrain is forced by this change.** The shipped `model_sniper.pkl` is untouched; its stored
  `oos_metrics` were computed under the old split and stay as they are until someone retrains. That
  staleness is disclosed, not silently corrected.

## Domain Decisions

- **[DECISION]** An embargo is a statement about **time**, not about rows. On a cross-sectional panel
  the two are only equivalent when N=1, which is exactly why the defect survived: on a single-ticker
  frame the row-based code was accidentally correct.
- **[DECISION]** The trading calendar is the panel's own sorted unique dates. Introducing an external
  holiday table would add a dependency and a second source of truth for something the data already
  answers.
- **[CONSTRAINT]** Any future splitter in this repo must be validated by the distinct-date gap
  invariant (AC2), not by row arithmetic. A row-count assertion cannot distinguish a correct embargo
  from this bug.
- **[TRADEOFF]** The CV gap uses `max_rows_per_date` rather than the mean, spending ~4% more training
  rows than strictly necessary on a balanced panel. Correctness on an uneven panel is worth more than
  those rows, and the alternative — a custom date-aware splitter — is a larger change than this spec's
  scope.
- **[CONSTRAINT]** Insufficient data aborts training rather than degrading the embargo. `oos_metrics`
  is published on `/transparency`, so a contaminated number is worse than an absent model.

## File Relationship

EXTENDS `docs/specs/ml-label-volatility-scaling.md` (owns the triple-barrier labels whose 20-day
horizon this embargo must clear) and `docs/specs/ml-label-oos-evaluation.md` (whose ATR-vs-fixed
comparison was produced with the contaminated split and is re-measured here). Feeds
`docs/specs/transparency-panel.md`, which surfaces `oos_metrics` to users.
