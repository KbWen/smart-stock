---
status: frozen
title: Model Rotation Ranking Honesty
source: external
source_doc: _product-backlog.md #4 (quant-expert panel audit, finding F7; escalated to P0 by #1's review)
created: 2026-09-02
updated: 2026-09-02
frozen: 2026-09-02
primary_domain: ml
secondary_domains: [backtest]
---

# Model Rotation Ranking Honesty

Honest Metrics epic **#4**, the last P0, and the only one in this epic whose failure mode is
**irreversible**: `core/ai/trainer.py:697` calls `os.remove` on every `.pkl` outside the top
`MAX_SAVED_MODELS`, ranked by a number that is not comparable across the entries it ranks.

## The defects

**D1 — the ranking compares measurements taken with different rulers.**
`profit_factor_sort_key` (`core/ai/common.py:48-55`) reads `backtest_30d.profit_factor`, which
carries no marker for how it was measured. Before #1 (2026-09-02) a winning trade was booked at the
session **high** and a loser at the session **low**; after #1 both settle at achievable fill prices.
On the same seed and window that moved profit factor **0.74 → 0.80**. `core/ai/trainer.py:681` sorts
pre- and post-#1 entries together and `:697` then deletes the losers — **a genuinely better old model
can be deleted for having been measured with a different ruler, and the `.pkl` does not come back.**
`backend/manage_models.py:141-152` (`prune`) has the same defect with the same consequence.

**D2 — `profit_factor: None` collapses two opposite facts.**
`backend/backtest.py:324` returns `None` when there are **no losing trades** — a flawless run.
`core/ai/trainer.py:609` writes `None` when the benchmark backtest **raised**. The sort key maps both
to `-1.0`, i.e. **below a profit factor of 0.0**. So a model whose backtest was perfect and a model
whose backtest crashed are ranked identically, and both rank below a model that lost money on every
trade. Whichever it was, it is deleted first.

**D3 — the rotation backtest scores the model on data it was just fit on.**
`core/ai/trainer.py:599` runs `run_time_machine(days_ago=30)` immediately after refitting the
ensemble on **all** rows. Labels look forward `PRED_DAYS = 20` trading days, so the T−30…T−10 outcome
window the backtest scores is inside the price path the model was trained on. The retained "best"
model is the one that best memorised the last month, and the ranking is selection-biased on top of
being cross-regime.

## Goal

Never take an irreversible action on an incomparable measurement. Make the ranking compare like with
like, distinguish "undefined" from "failed", and score the rotation on a window the model has not
already seen.

## Acceptance Criteria

1. `backtest_30d` records how it was measured: a `settlement` marker naming the
   fill model (`"achievable_fill"`, the behaviour shipped in #1) and the `days_ago` window it used.
   Entries **without** the marker predate #1 — absence is the marker, extending the constraint #2
   and #5 established.

2. **Rotation never deletes what it cannot compare.** `profit_factor_sort_key` is
   replaced by a comparability-aware ranking: an entry is rankable only if its `settlement` marker
   matches the current one and its `profit_factor` is a finite number. Unrankable entries — a missing
   or different marker, a `None`/NaN profit factor — are **protected from automatic deletion**, not
   sorted to the bottom.

3. When protection means the store exceeds `MAX_SAVED_MODELS`, that is **stated, not
   silently absorbed**: the run logs how many entries were kept because they could not be compared
   and names the manual command to remove them. Growing the store is the correct outcome; deleting on
   a bad comparison is not.

4. `profit_factor: None` no longer means two things. The benchmark records a
   `status` distinguishing `ok`, `no_losing_trades` (the profit factor is genuinely undefined — a
   flawless run) and `failed` (the backtest raised). Both non-`ok` states are unrankable per AC2,
   but they are no longer indistinguishable to a reader or to a future feature.

5. **[AMENDED POST-REVIEW — the original AC was unachievable]** The original text required the
   benchmark to run on "a window the final fit has not seen", with `days_ago >= PRED_DAYS +
   holding_days`. **That property cannot be delivered.** Both reviewers derived the same thing: the
   final ensemble is refit on *every* row, training rows run to `T - PRED_DAYS`, and their labels
   resolve on prices through `T` — so any window ending before `T` sits inside the training data,
   and raising `days_ago` buries it *deeper*. At `days_ago=40` the scored `df_future` slice is
   exactly the training label window of the entry row.

   So the window stays at 30 (changing it would have altered what `win_rate` / `avg_return` mean
   against every older entry, for nothing), and the entry records the truth instead:
   `backtest_30d.in_sample: true`, plus `days_ago` and `holding_days` so the span is recorded rather
   than assumed from the field's name. A genuinely out-of-sample rotation score needs an **as-of
   model per window**, which is backlog #3's territory.

   This amendment is itself the epic's rule applied to my own spec: a claim that cannot be
   delivered is removed, not weakened into something that sounds delivered.

6. `backend/manage_models.py` `prune` uses the same comparability rule and the same
   protection, because it performs the same irreversible deletion from a different entry point.
   `list` shows the settlement marker so a human can see which scores are comparable.

7. Tests, each empirically falsified before acceptance:
   - an entry with a different or missing `settlement` marker is **never** selected for deletion,
     even when its profit factor is the lowest present;
   - a `None` profit factor is protected rather than ranked last — with a test that fails under the
     old `-1.0` sort key;
   - `no_losing_trades` and `failed` are distinguishable in the recorded entry;
   - among comparable entries the ranking is still by profit factor, descending;
   - the freshly-trained model is always protected (existing guarantee, regression guard);
   - **[POST-REVIEW]** the benchmark records `in_sample: true` and its actual window, rather than
     claiming a property it does not have;
   - **[POST-REVIEW]** a backtest that returns an **error dict** (`run_time_machine` does not always
     raise) records `status: failed`, not `no_losing_trades` — otherwise D2 is recreated inside the
     field added to fix it;
   - **[POST-REVIEW]** deletion is an **allow-list**: only timestamps explicitly selected are
     removed. The glob-and-keep shape silently expired the protection once `history` truncation
     dropped a protected entry;
   - **[POST-REVIEW]** two entries sharing a minute-resolution timestamp: the shared `.pkl` survives
     if either entry is protected;
   - **[POST-REVIEW]** a malformed `backtest_30d` (list, string, number) is unrankable and does not
     raise, and a negative `keep` raises rather than deleting everything.

8. No deletion path is added, widened, or made reachable from a new caller. The
   change can only ever result in **fewer** files being deleted than before.

## Non-goals

- **No fix for F5/F6** (the backtest scoring a model trained over its own window in the *user-facing*
  Backtest page; row-offset entry dates) — backlog #3. AC5 fixes the **rotation** benchmark only,
  which is a different call site with a different purpose.
- **No retrain, and no backfill of `settlement` onto existing entries.** Their absence is what makes
  them protected.
- **No change to the backtest engine, the model, or `MAX_SAVED_MODELS`.**
- No new ranking criterion (Sharpe, lift, recency). The defect is that the existing one is applied
  across incomparable measurements, not that profit factor is the wrong metric.

## Constraints

- **An irreversible action requires a comparable measurement.** Where that is unavailable, the action
  does not happen. This is the whole spec in one line.
- **Additive on the persisted structure**; absence of a key keeps its meaning.
- **Honesty guard** (epic-wide): the disk may hold more models after this change. That is the correct
  outcome of refusing a bad comparison, and must not be "fixed" by loosening the rule.

## Domain Decisions

- **[DECISION]** Unrankable means **protected**, not last. Sorting an unknown to the bottom is a
  silent decision to delete it; the `-1.0` sentinel made that decision for both a flawless backtest
  and a crashed one.
- **[DECISION]** `None` is split into named states rather than given a numeric sentinel. This is the
  same move as `profit_factor=None` over `9999` in `backtest-metric-label-honesty.md`, applied one
  level up: the problem there was a fake number, the problem here is a real number's absence meaning
  two different things.
- **[CONSTRAINT]** Any future ranking used to select files for deletion must be comparability-aware.
  A raw `sorted(history, key=...)` over a persisted metric is the shape of this bug.
- **[CONSTRAINT]** Deletion is an **allow-list**, never "everything not kept". `history` is
  truncated to the last 50 entries, so a keep-set derived from it silently stops covering older
  files — which is exactly how the protection expired around night 52 in the first implementation.
- **[CONSTRAINT]** The comparability key is `(settlement, days_ago, holding_days)`. `PRED_DAYS` is
  env-configurable, so two runs can share a settlement marker and still be measured over different
  spans; the window is part of the ruler, not decoration.
- **[TRADEOFF]** The model store can exceed `MAX_SAVED_MODELS` and stay there until a human prunes.
  Disk is cheap; an irreversibly deleted good model is not, and the cap was never a hard requirement.

## File Relationship

EXTENDS `docs/specs/backtest-settlement-realism.md` (#1, whose settlement change is what made the
stored profit factors incomparable) and `docs/specs/backtest-metric-label-honesty.md` (which
established `None` over a sentinel). Touches the rotation introduced in
`docs/specs/ai-pipeline-otc-optimization.md`.
