---
status: frozen
title: Unknown Is Not Zero — ML Features
source: external
source_doc: _product-backlog.md #1 (2026-09-02 issue triage, GH #14)
created: 2026-09-02
frozen: 2026-09-02
primary_domain: ml
secondary_domains: [transparency]
---

# Unknown Is Not Zero — ML Features

Unknown Is Not Zero epic **#1** (review-finding, P0). The prediction path substitutes `0` for every
feature it cannot compute, and `0` is not a neutral value for these features — it is a specific,
plausible, wrong claim about the stock.

## The defect, as measured

Ticker **2330**, 1128 real rows, held at the **same final trading day**, varying only how much
history is supplied to `prepare_features(..., is_training=False)`:

| history supplied | features forced to exactly `0.0` (true value in parens) |
|---|---|
| 120 rows | `dist_sma240` (+0.3429), `sma120_slope` (+0.0277), `sma240_slope` (+0.0312) |
| 150–239 rows | `dist_sma240` (+0.3429), `sma240_slope` (+0.0312) |
| 240 rows | `sma240_slope` (+0.0312) |
| 260 rows | none |

On that day 2330 sat **34.3% above** its 240-day mean — a pronounced uptrend. Given short history the
model is told it sits **exactly on** that mean. The substitution does not merely lose information; it
replaces a strong signal with a confident, plausible, neutral falsehood that neither the MLP nor the
random forest can distinguish from a stock that genuinely sits on its annual mean.

The mechanism:

- The prediction gate is `MIN_PREDICT_ROWS = 120` (`core/config.py:36`), enforced twice —
  `core/ai/predictor.py:341` and `core/ai/trainer.py:94-96`.
- `dist_sma240` and `sma240_slope` (`core/ai/common.py:135-136`, both in `FEATURE_COLS`) need ~260
  rows before `sma_240` and its slope are defined.
- A ticker in **120 ≤ rows < 260** therefore passes the gate with those features `NaN`, and
  `core/ai/trainer.py:200` (`fillna(0)`) plus `core/ai/predictor.py:354`
  (`.replace([inf, -inf], nan).fillna(0)`) turn them into `0`.

**The correct threshold already exists in this codebase.** `MIN_TRAIN_ROWS = 260`
(`core/config.py:35`) carries the comment "needs SMA240". Training uses it; prediction does not.

**Training is not affected, and that is load-bearing.** `core/ai/trainer.py:195-199` calls
`df_clean.dropna(subset=FEATURE_COLS)` when `is_training=True`, with a comment naming this exact
hazard. The `fillna(0)` on the next line is reachable from the prediction path only. Whoever wrote
that dropna understood the problem; the guard was simply never extended to inference.

**A second substitution site** sits at `core/ai/predictor.py:364` and `:396`:
`X_single.reindex(columns=clf.feature_names_in_, fill_value=0)`. When the loaded model expects a
feature the frame does not contain, that feature is invented as `0` — the same defect, reached by a
different route (a model trained against a different `FEATURE_COLS`).

## Scope, measured before deciding anything

- **92-ticker dev panel: no ticker falls in the affected band** *by rows stored* (minimum 729).
  **This measurement was the wrong one, and review caught it.** What matters is the window each
  caller loads, not what the table holds. `backend/recalculate.py` loaded `RECALC_LOOKBACK_DAYS = 420`
  **calendar** days ≈ 225 trading rows on this data — below the requirement — so the refusal fired
  for **91 of 92 tickers**, and the first nightly recalculation would have wiped the AI probability
  from the whole product. Fixed by raising the window to 730, matching the detail and sync paths.
  Measured after: **0 of 92**. A row count in a table says nothing about the frame a model is given;
  every future gate of this kind must be measured **per caller window**.
- **Same panel: 0 of 92 tickers have any uncomputable feature on their latest row.** So refusing to
  predict when a feature is uncomputable refuses **nobody** on this data — it fires only in the
  situation it exists for.

## Goal

The prediction path must never present a computed number that rests on a value it invented. When a
feature required by the model cannot be computed, there is no prediction — `ai_prob` is `NULL`, which
this product already renders honestly — and the reason is available rather than silent.

## Acceptance Criteria

1. **[FROM-SOURCE]** The prediction path no longer substitutes **anything** for an uncomputable
   feature. `prepare_features(..., is_training=False)` returns the `NaN`, and `core/ai/predictor.py`
   no longer fills. `±inf` is treated identically to `NaN` (it is equally uncomputable, and
   `json.loads` will happily carry it — see the `math.isfinite` lesson from
   `docs/specs/oos-metric-attribution-and-lift.md`).

   **Amended during implement** (was: "no longer substitutes `0`"). Two other substitutions on the
   same path were found while inventorying for AC9, and a fix that removed only the `0` would have
   been a claim this spec could not support:
   - The prediction branch also ran `ffill().bfill()`. The `bfill()` can never reach the prediction
     row — it is the last one — but the `ffill()` could, carrying **yesterday's** indicator into
     today whenever today's was uncomputable. A stale number is still a number the model reads as
     an observation of today. Measured: **0** of the 92 dev-panel latest rows depend on it.
   - `backend/services/legacy_service.py` and `backend/recalculate.py` ran `df = df.fillna(0)`
     **before** calling `predict_prob`, to keep NaN out of the JSON payload. With `sma_240 = 0`,
     `dist_sma240` becomes a finite astronomical number rather than NaN, so the finite check sees
     nothing wrong. **Without this, the whole feature would have been inert on two of the three
     request paths while every unit test passed** — the unit tests build raw OHLCV, where
     `prepare_features` computes the indicators itself and the NaN is real. The model is now given
     the unfilled frame; the payload fill is unchanged.

2. **[FROM-SOURCE]** `predict_prob` returns `None` when any `FEATURE_COLS` value on the prediction
   row is not finite. This is its existing failure contract, so every caller
   (`backend/recalculate.py:131`, `backend/routes/sync.py:152`,
   `backend/services/legacy_service.py:59`) already handles it and `ai_prob` is stored `NULL`.

3. **[INFERRED]** The `reindex(..., fill_value=0)` at `core/ai/predictor.py:364` and `:396` no longer
   invents absent features. A model whose `feature_names_in_` is not satisfied by the frame yields
   `None` from `predict_prob`, not a probability computed over invented columns.

4. **[FROM-SOURCE]** The refusal is attributable, not silent: one log record naming the ticker and
   the offending feature names. A `None` that nobody can explain is how this defect survived.

5. **[INFERRED]** The API can state *why* there is no AI number. The **stock detail** payload gains a
   nullable `ai_unavailable_reason`, set to the machine token `insufficient_history` when
   `len(df) < MIN_FEATURE_ROWS`.

   **Amended during implement** (was: "stock/candidate payload", with a second token
   `uncomputable_features`). The candidate list is read from the `scores` table, where `ai_prob` is
   a stored scalar with nowhere to carry a reason; supplying one there needs either a schema
   migration (excluded by §Constraints) or a per-request row-count query. The second token is
   dropped for the same reason it would have been wrong: outside the short-history case the caller
   has no cheap way to know which features failed, so the field would have had to guess. Those
   refusals are logged with the feature names instead (AC4). The cached-DB branch of
   `/api/v4/stock/{ticker}` reports `null` — it deliberately does not load price history, so it
   cannot attribute the cause and does not pretend to.
   - `MIN_FEATURE_ROWS` is declared **once**, in `core/ai/common.py`, as the history the current
     `FEATURE_COLS` actually require: **250** = the 240-period SMA plus its 10-row slope
     (`sma_240.pct_change(10)`). Measured by sweeping 120→275 rows: 250 is the first fully
     computable count, and at 249 the sole offender is `sma240_slope`. *(This AC first said "260,
     matching `MIN_TRAIN_ROWS`" — wrong on both halves; `MIN_TRAIN_ROWS` is 260 and keeps 10 rows
     of margin over the real requirement.)*
   - This constant is for the **message only**. AC2's finite check is the sole gate. Two mechanisms
     that can disagree about whether to predict is how drift starts; only one decides, the other
     explains.

6. **[INFERRED]** `MIN_PREDICT_ROWS` stays `120`. Raising it to 260 would make the symptom vanish
   while telling the user nothing, and it is the wrong shape of fix: the guard must follow the
   features, so that adding a 500-day feature tomorrow is covered without anyone remembering to
   change a constant.

7. **[INFERRED]** The frontend states the reason where it already prints N/A —
   `ScoreBreakdown.tsx`, the detail panel, following AC5's narrowing. Its existing tooltip asserted
   a single cause (「尚未訓練 AI 模型…執行 train_ai.py 即可啟用」) for every missing number, which
   for a short-history stock sends the user to retrain a model that is working. Same defect the
   model-health chip had before it was keyed on a machine reason. Label text lives in the frontend;
   the API sends the machine token only — the `breadth_level` precedent from
   `docs/specs/docs-reality-alignment.md`.

8. **[FROM-SOURCE]** Tests that can fail:
   - Restoring the `fillna(0)` on the prediction path makes a test fail (2330-shaped frame truncated
     to 150 rows must yield no prediction; the same frame at full length must yield one).
   - Removing the `dropna` at `core/ai/trainer.py:199` makes a test fail. That line is what keeps
     training clean, it is not covered today, and this feature depends on it staying.
   - A model whose `feature_names_in_` demands a column the frame lacks yields `None`.

9. **[INFERRED]** `docs/DATA_INTEGRITY.md` gains a row for imputed model inputs, stating what is now
   refused and what is still substituted anywhere else in the pipeline. If any substitution remains
   after this feature, it is named there rather than left for the next audit to find.

## Non-goals

- **Making short-history stocks predictable.** They become *honestly unpredictable*. Coverage on a
  fresh install goes down; that is the intended direction, per the backlog's Honesty Guard.
- **Retraining, or any change to `FEATURE_COLS`.** The feature set is untouched.
- **Backfilling `ai_prob` values already stored.** Existing rows were computed under the old path.
  They are not marked, because unlike a model-history entry there is nowhere honest to put a marker
  on a scalar column, and the next recalculation overwrites them.
- **The technical scores.** `total_score_v2` and its components continue to be computed and shown for
  a short-history stock; only the AI probability is withheld. GH #8 (epic #3) covers indicator-level
  substitution.
- **Shortening the 240-day windows.** Explicitly rejected in the backlog: it changes model inputs to
  make a disclosure problem disappear.

## Constraints

- `predict_prob`'s return contract does not change. Three call sites depend on `None`.
- No new dependency, no schema migration.
- The finite check runs on one row of ~27 features per ticker; it must not add a measurable pass over
  the panel.
- **`ai_prob = NULL` must remain distinguishable from `ai_prob = 0`.** The database column is
  nullable and `to_ai_percent` already honours this; a refusal must not become a zero anywhere in the
  chain.

## API / Data Contract

The **stock detail** payload (`/api/v4/stock/{ticker}` and `/api/stock/{ticker}`) gains one nullable
field:

```
ai_unavailable_reason: "insufficient_history" | null
```

`null` whenever `ai_probability` is non-null, and also when the AI number is missing for a reason
this feature does not diagnose (no model trained, model load failure) — those already surface
through `model_health` and must not be relabelled as a data problem.

`null` as well on the **cached-DB branch** of `/api/v4/stock/{ticker}`, which deliberately does not
load price history and therefore cannot attribute a cause. That branch serves most requests for six
hours after a recalculation, so the frontend must not assert a cause when the token is absent: when
`model_health` is `ok` it says the model is fine and the gap is on this stock's side, rather than
sending the user to retrain a working model.

The **candidate list** does not carry the field. It reads `ai_prob` as a stored scalar from the
`scores` table, which has nowhere to put a reason, and supplying one needs either a schema migration
(excluded by §Constraints) or a per-request row-count query.

The **backtest** response gains `excluded_unscorable` alongside the existing exclusion counts. A
refusal used to be coerced by `ai_prob = ... or 0.0` into a 0% forecast and dropped through the
strategy filter — indistinguishable from a stock the model scored and rejected, which is this epic's
own defect one layer down.

## Domain Decisions

- **[DECISION]** `0` is a value, not a blank. For a distance-from-mean feature it asserts *exactly at
  the mean*; for a slope it asserts *flat*. Both are among the most common true states a stock can be in,
  which is precisely what makes the substitution undetectable downstream. A model cannot learn to
  distrust an input that looks like every other input.
- **[DECISION]** The guard follows the **features**, not a row count. A finite check over
  `FEATURE_COLS` covers any future feature with any window without anyone remembering to update a
  constant; a threshold covers only the windows that existed when it was written.
- **[CONSTRAINT]** Exactly one mechanism decides whether to predict. `MIN_FEATURE_ROWS` explains the
  common case in the UI and must never gate. Two gates that can disagree is how a disclosure field
  ends up contradicting the behaviour it describes.
- **[TRADEOFF]** Refusing costs coverage on young databases — a fresh install predicts for fewer
  stocks than it does today. Accepted: this project's stated differentiator is transparency, and a
  probability computed from an invented input is worth less than a stated blank.
- **[CONSTRAINT]** `ai_prob = NULL` and `ai_prob = 0` must stay distinguishable end to end. The
  nullable column, `to_ai_percent`, and the frontend null branch already honour this; a refusal that
  degrades into a zero anywhere in the chain reintroduces the defect one layer down.
- **[DECISION]** `±inf` is treated as uncomputable, not clipped. It arises from the same division
  that produces `NaN`, and `json.loads` accepts bare `Infinity` — the lesson recorded in
  `docs/specs/oos-metric-attribution-and-lift.md` after `NaN` passed two guards.
- **[CONSTRAINT]** The `dropna` at `core/ai/trainer.py:199` is load-bearing for training cleanliness
  and is currently untested. This feature depends on it; a test must pin it so a future edit cannot
  silently move training onto the fabricating path.

## File Relationship

EXTENDS `docs/specs/backend-failure-state-honesty.md` (the `ai_prob = NULL` rather than fake `0.0`
precedent this feature applies to a case that spec did not reach) and
`docs/specs/ui-model-state-disclosure.md` (the reason is disclosed, not merely absent).
