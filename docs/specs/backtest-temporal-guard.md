---
status: frozen
title: Backtest Temporal Guard and Calendar-Aligned Entry
source: external
source_doc: _product-backlog.md #3 (quant-expert panel audit, findings F5/F6, plus two #1 review deferrals)
created: 2026-09-02
updated: 2026-09-02
frozen: 2026-09-02
primary_domain: backtest
secondary_domains: [transparency]
---

# Backtest Temporal Guard and Calendar-Aligned Entry

Honest Metrics epic **#3**, the epic's final item. Two defects in `run_time_machine` that make its
output mean less than the page around it implies, plus the two deferrals #1's review left here.

## The defects

**F5 — the backtest scores a model over the window that model was trained on.**
`backend/backtest.py:176` calls `predict_prob(df_past, version=version)` with the **deployed** model,
which `core/ai/trainer.py` refit on every row up to today. Labels look forward `PRED_DAYS = 20`
trading days, so for `days_ago=30` the model has already seen the outcomes it is now being scored on.
The page is titled AI 回測報告 and reads as evidence of skill; it is in-sample recall. #4 established
the same fact for the rotation benchmark and recorded `in_sample: true` on the entry — the
**user-facing** backtest has no such marker.

**F6 — the entry point is a row offset, so the "portfolio" is not one cross-section.**
`backend/backtest.py:149` computes `entry_idx = len(df_full) - days_ago`. Row counts differ per
ticker — halts drop rows (`core/bulk_history.py:54-56` returns `None` for `--` cells), stale tickers
stop updating, partial backfills leave gaps — so a ticker with missing rows enters on a **different
calendar date**. Yet `:309` reports a single `simulated_date` taken from `top_picks[0]` alone, and
`holding_days` / `exit_date_actual` come from that same one pick. "Top Picks from 30 days ago" is
presented as a portfolio observed on one day; it is not.

**D1 (deferred from #1) — a gap-up through the target on a stop bar books an unachievable loss.**
Entry 100, `target_gain=0.15`, `stop_loss=0.05`, bar `open=122, high=135, low=80`: the stop branch
runs first, the open is not below the stop, so it settles `STOP` at −5%. But a resting limit sell at
115 is marketable at the 122 open — it fills there, on the session's first print, before any tick can
reach 95. Deferred from #1 on **measured** grounds: it needs a ≥20% intraday range at default
barriers, and only **4 of 99,287 real bars (0.004%)** are that wide, with TW's ±10% daily limit
making it structurally near-impossible. It is recorded here so the deferral is closed rather than
forgotten.

**D2 (deferred from #1) — `best_stock` is an arbitrary tie-break.** `backend/backtest.py:322` uses
`idxmax` on `actual_return`; since #1 every no-gap HIT settles at exactly `target_gain`, so ties are
now the norm and the "best" pick is whichever row happens to sort first.

## Goal

Stop the backtest implying a property it does not have, and make its cross-section real: one entry
date for the whole run, and an explicit statement when the model scoring it was trained over the
window being scored.

## Acceptance Criteria

1. Entry is resolved by **calendar date**, not row offset. A single `as_of` date is
   chosen once for the run (from the panel's own trading calendar), and each ticker enters on its
   last row at or before that date. A ticker with no row within a small tolerance of `as_of` is
   **excluded from the run**, not silently entered on some other day.

2. `simulated_date` is the run's `as_of`, not `top_picks[0]`'s date. The response
   reports how many candidates were **excluded**, so a thin cross-section is visible rather than
   inferred. **[AMENDED POST-REVIEW]** One count was not enough: the pre-mortem measured that on
   the real DB ~285 of 300 candidates exit at the "no price rows at all" branch, which the first
   implementation never counted — so the banner would have read "0 excluded" for a run using 16
   tickers, *certifying* a thin cross-section as full. Two counts are reported
   (`excluded_no_data_at_as_of`, `excluded_no_price_rows`) alongside the denominator, and the UI
   renders them **outside** the temporal banner so the two facts do not share one conditional.

3. Each pick carries its own `entry_date`, `holding_days` and `exit_date`, which it
   already does — but the **summary** stops borrowing one pick's values for the whole run. Where a
   summary-level value is not well defined across picks, it is reported as such rather than taken
   from an arbitrary member.

4. The response states, in a machine field, whether the model scoring the run was
   trained over the scored window: `model_temporal_scope` is `"in_sample"` when the active model's
   training date is at or after `as_of`, `"as_of_model"` when it precedes it. It **fails toward
   `in_sample`** — the pessimistic reading — because an unmarked in-sample number is the failure
   this epic exists to remove.

   **[AMENDED POST-REVIEW]** The training date comes from `trained_at` **or `timestamp`**, and the
   compact `%Y%m%d_%H%M` form is parsed explicitly. Real `models_history.json` entries have **no
   `trained_at` key at all** — it lives inside the pickled model metadata — so the first
   implementation was hard-wired to `"in_sample"` forever, and `pd.to_datetime` raises on the
   compact form, meaning a naive key swap would have stayed just as inert. `"unknown"` is dropped:
   the Constraint says indeterminate resolves to `in_sample`, so a third token was never emitted.

5. The Backtest page and Strategy Lab surface that field in words, next to the
   headline metrics: an in-sample run is labelled as measuring recall over data the model has seen,
   not as evidence of predictive skill. No number is hidden; the framing around it changes.

6. **D1 is fixed now that its branch is being touched anyway**: when a bar's open
   is at or above `target_gain`, the target filled at the open before any intrabar path could reach
   the stop, so the bar settles `HIT` at the open. Same-bar stop-before-target precedence is
   otherwise unchanged — it exists for genuine intrabar *ambiguity*, and a gap open through a barrier
   is not ambiguous.

7. **D2 is fixed**: `best_stock` breaks ties on `net_return`, then on ticker, so it
   is deterministic rather than dependent on row order.

8. Tests, each empirically falsified before acceptance:
   - two tickers with different row counts enter on the **same calendar date**, and the one missing
     data at `as_of` is excluded rather than entered on a different day;
   - `simulated_date` equals the run's `as_of` even when `top_picks[0]` has a different entry row;
   - `model_temporal_scope` is `in_sample` for a model trained after `as_of`, `as_of_model` for one
     trained before it, and `in_sample` when `trained_at` is missing;
   - a bar that gaps open above the target and also breaches the stop settles `HIT` at the open;
   - a bar that touches both barriers **intrabar** still resolves to the stop (precedence regression
     guard);
   - `best_stock` is stable when several picks tie on `actual_return`.

9. The measured effect on the real panel is recorded in the Work Log — how many
   candidates the calendar alignment excludes, and whether the summary metrics move.

## Non-goals

- **No as-of model training.** Making the backtest genuinely out-of-sample requires training a model
  per window, which is a different and much larger feature. This spec makes the situation **visible**;
  it does not fix it. `model_temporal_scope` is the marker a future feature would flip.
- **No survivorship fix.** The universe is still today's listed set; that stays a documented,
  unmitigated limitation.
- **No change to settlement** beyond D1's single branch, to the cost model, or to any metric
  definition.
- **No change to the entry price rule.** The signal still uses the entry bar's close and the trade
  still fills at it — a distinct look-ahead defect, recorded in `_raw-intake.md`, deliberately left.

## Constraints

- **Excluding a ticker is honest; entering it on the wrong day is not.** Where the calendar cannot be
  honoured, the candidate leaves the run and the count is reported.
- **Fail toward the pessimistic reading.** An indeterminate training date yields `in_sample`.
- **[POST-REVIEW] The run's calendar is a property of the data, not of the sample.** `as_of` comes
  from one `SELECT DISTINCT date` over the whole table, falling back to the loaded frames only when
  no DB is reachable. Deriving it from whichever frames happened to load first made `as_of` — and
  therefore every number — shift with `BACKTEST_CANDIDATE_POOL`, the volume prefilter, or a DB
  edit, against this project's own reproducibility claim.
- **Honesty guard** (epic-wide): the sample size may shrink and the metrics may move. Nothing may be
  loosened to keep the numbers looking the same.

## Domain Decisions

- **[DECISION]** A cross-sectional backtest needs one date, not one row offset. Rows are not time —
  the same confusion that produced #2's zero-day embargo, in a different file.
- **[DECISION]** `model_temporal_scope` is a machine token with the display text in the frontend,
  following #6's rule: string-matching user-facing wording is a silent-failure mode.
- **[CONSTRAINT]** A summary-level field must never be taken from an arbitrary member of a
  collection. `simulated_date`, `holding_days` and `exit_date_actual` were all read off
  `top_picks[0]`; any new summary field must be defined across the whole run or omitted.
- **[TRADEOFF]** Excluding tickers with no row at `as_of` shrinks an already small sample. A thin,
  honest cross-section beats a full one assembled from different days, and the exclusion count is
  reported so the thinness is visible.

## File Relationship

EXTENDS `docs/specs/backtest-settlement-realism.md` (#1, whose review deferred D1 and D2 here) and
`docs/specs/backtest-and-performance-opt.md` (which owns `run_time_machine`). Consumed by
`docs/specs/strategy-lab.md`. Related to `docs/specs/model-rotation-ranking-honesty.md` (#4), which
established the `in_sample` marker for the rotation benchmark; this adds the user-facing equivalent.
