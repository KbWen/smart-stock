---
status: frozen
title: OOS Metric Attribution and Baseline Lift
source: external
source_doc: _product-backlog.md #5 (quant-expert panel audit, findings F8/F9/F10; escalated to P0 by #2's measurement)
created: 2026-09-02
updated: 2026-09-02
frozen: 2026-09-02
primary_domain: ml
secondary_domains: [transparency]
---

# OOS Metric Attribution and Baseline Lift

Honest Metrics epic **#5**, escalated to **P0** by what #2 measured. Three defects that together let
the product present a model as usable when the numbers say it is not.

## The three defects

**F8 — the reported metrics describe a model that is never deployed.** `core/ai/trainer.py:445-450`
evaluates the ensemble trained on the 80% split; `:460+` then builds and ships a **different**
ensemble refit on 100% of the data. `models_history.json` attaches the former's numbers to the
latter's `version`, and `backend/routes/transparency.py:93` serves them as the active model's. Refitting
on the full set is standard practice; attributing the holdout score to the shipped artifact is not.

**F9 — no baseline, so precision cannot be read.** A precision of 0.35 means something very different
against a 14% base rate than against a 35% one. Nothing records the test-split prevalence: the stored
`class_distribution` is the **train** split (`core/ai/trainer.py:362-364`), and the UI renders it under
the OOS heading (`frontend/v4/src/pages/Transparency.tsx:165-184`), so a reader naturally reads it as
the denominator for the precision shown beside it. It is not.

The consequence, measured on this project's own data in #2: StrongBuy precision **0.3454 against a
0.3512 test prevalence** — a lift of **0.98×**, *below* the base rate. Guessing at the base rate would
do better.

**F10 — `get_model_health` will call that model `ok`.** `core/ai/predictor.py:190-203` computes
`buy_signal_power = precision_buy + recall_buy + precision_strong + recall_strong` and returns
`degraded` only when that sum is `<= 0`. Today the shipped model reports `degraded` — but **only by
accident**, because its metrics are literally all zero. Any model with a trace of signal that is still
below the base rate passes as `ok`, and the banner that exists to disclose weakness disappears.
Shipping #2 before this made the check most wrong exactly when the metrics became most honest.

Separately, every history entry written before 2026-09-02 lacks the `embargo` key that #2 added, which
means its `oos_metrics` were produced under a split that separated train from test by **0 trading
days**. Those numbers are contaminated by construction and are currently served without a marker.

## Goal

Make a reader — human or code — able to tell what the numbers describe, what they are measured
against, and whether they can be trusted at all. Where they cannot, say so in the surface that
already exists for saying so.

## Acceptance Criteria

1. `history_entry` records the **test-split** class prevalence as
   `test_class_distribution`, alongside the existing (train-split) `class_distribution`. The existing
   key is not renamed and not removed: old entries keep it, and it is genuinely the train
   distribution — the defect was that nothing said so.

2. `oos_metrics` gains `lift_strong` and `lift_buy` — precision divided by that
   class's test-split prevalence. A lift of `1.0` is "no better than the base rate". When the
   prevalence is zero the lift is `None`, never a sentinel, per the shipped `profit_factor=None`
   precedent.

3. The attribution is explicit and machine-readable. `history_entry` gains
   `oos_metrics_scope: "split_model"`, recording that the metrics were measured on the 80%-split
   ensemble while the shipped artifact is a full-data refit. Entries **without** the key predate this
   change.

4. `get_model_health` returns `degraded`, not `ok`, when either:
   - the entry has **no `embargo` key** — its metrics predate #2 and are contaminated by construction; or
   - `lift_strong` is present and `<= 1.0` — the model is at or below the base rate on the class the
     product actually acts on.

   The existing zero-power rule is kept as a third trigger, since a model with literal zeros is
   degraded regardless of what prevalence it is compared against. Each state gets its own honest
   zh-TW `message`; they are not collapsed into one string, because "we cannot trust these numbers"
   and "these numbers say the model has no edge" are different things for a reader to act on.

5. The `/api/transparency` payload carries the new fields, and the Transparency page
   **labels which split each distribution belongs to** — the current UI shows the train distribution
   under an OOS heading with no qualifier. Precision is shown with its lift beside it, and a lift at
   or below 1.0 is visually marked as no-edge rather than rendered as a neutral number.

6. Tests, each empirically falsified before acceptance:
   - `test_class_distribution` and the two lifts are computed from the **test** split, not the train
     split — a fixture where the two distributions differ proves which one was used;
   - a lift of exactly `1.0` is `degraded` (the boundary is inclusive: matching the base rate is not
     an edge);
   - an entry with no `embargo` key is `degraded` regardless of how good its metrics look;
   - a zero-prevalence class yields `lift = None` and does not raise;
   - the existing all-zero-metrics entry stays `degraded` (regression guard — the current shipped
     model must not silently become `ok`);
   - the transparency payload exposes the new fields and tolerates an old entry that lacks them.

7. The change is **measured, not asserted**. The Work Log records
   `get_model_health`'s verdict for the shipped entry before and after, and confirms that the shipped
   model's status does not silently improve.

## Non-goals

- **No fix for F7** (rotation ranking profit factors across settlement regimes) — backlog #4.
- **No fix for F5/F6** (the backtest scoring a model trained over its own window; row-offset entry
  dates) — backlog #3.
- **No retrain, and no backfill of the new keys onto old entries.** Their absence is the marker (#2's
  `[CONSTRAINT]`); writing values into them would destroy the only signal that those metrics are
  contaminated.
- **No change to the model, features, labels, thresholds, or the split itself.**
- No attempt to *improve* the model. The epic's position is unchanged: it is honestly weak.

## Constraints

- **Additive on the persisted structure.** New keys only; nothing renamed or removed, so an old
  `models_history.json` still loads and its missing keys carry meaning.
- **Honesty guard** (epic-wide): this change is expected to move the shipped model's status toward
  `degraded` and to surface a lift below 1.0. Nothing may be tuned to avoid that, and no threshold
  may be chosen to make a model pass.
- **A number that cannot be computed honestly is `None`**, not a sentinel.

## Domain Decisions

- **[DECISION]** Lift, not raw precision, is the honest headline for an imbalanced ranking task.
  Precision alone is unreadable without its denominator, and the denominator was never recorded.
- **[DECISION]** Absence of a key is the contamination marker, so the fix is additive-only. This
  extends #2's `[CONSTRAINT]` from `embargo` to the three keys added here.
- **[CONSTRAINT]** `get_model_health` must fail **toward** `degraded`. Any future metric it cannot
  evaluate — a missing key, an unparseable value — resolves to disclosure, never to `ok`.
- **[TRADEOFF]** `class_distribution` keeps its ambiguous name rather than being renamed to
  `train_class_distribution`. A rename would strip the field from every existing entry and show the
  panel a blank where a real number used to be. The ambiguity is resolved at the display layer, where
  it actually misled someone.

## File Relationship

EXTENDS `docs/specs/ui-model-state-disclosure.md` (which introduced `get_model_health` and the
`ModelHealthBanner`) and `docs/specs/transparency-panel.md` (which surfaces `oos_metrics`). Depends on
`docs/specs/date-based-train-test-embargo.md` (#2) for the `embargo` marker it reads, and on
`docs/specs/backtest-metric-label-honesty.md` for the `None`-not-sentinel precedent.
