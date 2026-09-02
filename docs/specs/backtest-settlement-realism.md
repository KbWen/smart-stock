---
status: frozen
title: Backtest Settlement Realism
source: external
source_doc: _product-backlog.md #1 (quant-expert panel audit, finding F2 — 3/3 independent auditors)
created: 2026-09-02
updated: 2026-09-02
frozen: 2026-09-02
primary_domain: backtest
secondary_domains: [transparency]
---

# Backtest Settlement Realism

Honest Metrics epic **#1** (review-finding, P0). `run_time_machine` books a winning trade at the
**session high** and a losing trade at the **session low**. Both are wrong, and the error is
one-directional: every win is credited with the best print of the day it never actually got, while
every loss is charged the worst print of the day it never actually paid. The magnitude-based numbers
the Backtest page and Strategy Lab show — `avg_return`, `avg_net_return`, `profit_factor`,
`net_profit_factor`, `sharpe_ratio`, `best_return` — inherit that inflation.

**Win rates are not among them.** A settled HIT is always positive and a settled STOP always
negative, so trade *signs* are invariant under this change and `win_rate` / `net_win_rate` cannot
move (the only exception is a `target_gain` small enough for costs to flip a win negative, which the
`ge=0.01` validation at both API surfaces makes unreachable in practice). Saying otherwise would
claim a correction this fix does not make.

All three independent auditors flagged this, and it was re-verified directly against
`backend/backtest.py:216-220`.

## Goal

Settle simulated exits at prices an order could actually have received, so the performance numbers a
user reads are achievable rather than best-case. A limit sell fills at the limit, not at the day's
high; a stop fills at the stop, not at the day's low — with the gap case handled honestly on both
sides.

## Acceptance Criteria

1. On a target touch (`day_high_pct >= target_gain`), `locked_roi` is
   **`target_gain`**, not `day_high_pct` (`backend/backtest.py:218`). Gap exception: when the bar
   *opens* at or above the target, a resting limit sell fills at the open, so `locked_roi` is
   `day_open_pct` in that case. Formally: `locked_roi = max(target_gain, day_open_pct)` restricted to
   the branch where the target is touched.

2. On a stop touch (`day_low_pct <= -stop_loss`), `locked_roi` is **`-stop_loss`**,
   not `day_low_pct` (`backend/backtest.py:212`). Gap exception: when the bar *opens* at or below the
   stop, the stop becomes a market order filling at the open, so `locked_roi` is `day_open_pct` in
   that case. Formally: `locked_roi = min(-stop_loss, day_open_pct)` restricted to the branch where
   the stop is touched.

3. Same-bar precedence is **unchanged**: when a bar touches both the stop and the
   target, the stop still wins (`backend/backtest.py:209`). This is the existing deliberate
   conservative choice and this spec does not revisit it.

4. `max_gain_pct` and `max_drawdown_pct` continue to use `day_high_pct` / `day_low_pct`
   (`backend/backtest.py:206-207`). They are maximum favorable/adverse **excursion** measures, for
   which the intraday extreme is the correct input — they are not settlement prices and are out of
   scope.

5. The `PENDING` (neither barrier touched) path is unchanged: `locked_roi` remains
   the running `day_close_pct`, and the final value the last observed close.

6. Tests, each **empirically falsified** before acceptance (revert the fix, watch it
   fail):
   - a bar whose high exceeds the target settles at exactly `target_gain`, **not** at the high;
   - a bar that gaps open above the target settles at the **open**, above `target_gain`;
   - a bar whose low breaches the stop settles at exactly `-stop_loss`, **not** at the low;
   - a bar that gaps open below the stop settles at the **open**, below `-stop_loss`;
   - a bar touching both barriers still resolves to the stop (precedence regression guard);
   - net-of-cost arithmetic (`backend/backtest.py:224-226`) is applied to the new `locked_roi`
     unchanged, so the buy/sell cost asymmetry keeps working.

7. The direction of the change is **reported, not hidden**. The Work Log records a
   before/after run of `run_time_machine` on the same seed and window, showing how each affected
   summary metric moved. AC2 alone makes losses *smaller*; AC1 alone makes wins *smaller*. The net
   effect is whatever it is — this spec does not permit tuning `target_gain`, `stop_loss`,
   `BACKTEST_AI_THRESHOLD`, or any default to compensate for a less attractive result.

8. **[POST-REVIEW]** `sharpe_ratio` is `None`, not `0.0`, when the standard deviation of net
   returns is NaN or exactly zero. Settlement realism **created** this case: a no-gap HIT now
   settles at exactly `target_gain` and a no-gap STOP at exactly `-stop_loss`, so a sample where
   every trade landed on the same barrier has zero dispersion, which continuous high/low values
   made effectively impossible before. Zero dispersion means *undefined*, not "no edge", but
   `Backtest.tsx:298` styles `0.00` as a real muted result. `None` matches the `profit_factor`
   precedent in the same summary object, and **both frontend surfaces already implement the null
   contract** — `Backtest.tsx:298` renders `!= null ? … : '—'` and `StrategyCompare.tsx:59`
   returns `'—'` for null/undefined/NaN — so this completes a contract the UI was already written
   against. `docs/API_CONTRACT.md` is updated to document the null, and `Backtest.tsx`'s type is
   widened from `number` to `number | null` to stop the type lying (`useStrategies.ts:32` already
   had it right). Test: `test_sharpe_is_none_when_dispersion_is_undefined`, falsified.

## Clarifications Resolved

- **AC8 was added after review**, amending the "No change to metric definitions / No API contract
  change" Constraint below for this one field. Rationale: the reviewer and the tenth-man showed the
  change itself creates the zero-dispersion case, so shipping without AC8 would mean this very PR
  widens a flattering-sentinel path the `backtest-metric-label-honesty` spec exists to close. The
  amendment is narrow — one field, an existing precedent, and a UI that already handles it. The
  user was asked and delegated the scope call back with the standard "well-researched and good for
  the project"; the research is the two frontend call sites cited in AC8.
- **Stop-side settlement (AC2)**: confirmed at intake that **both** sides are corrected, not just the
  winning side. Fixing only AC1 would leave the simulation one-directionally *pessimistic* — an
  equally wrong execution model that understates profit factor on no principled basis. Keeping a
  known-wrong pessimistic loss figure as an implicit safety margin was rejected as its own form of
  dishonesty.

## Non-goals

- **No fix for F5** (the backtest scoring a model trained on the backtest window) — that is backlog
  #3 and needs a `trained_at` guard.
- **No fix for F6** (row-offset entry date rather than calendar-aligned) — also backlog #3.
- **No entry-price change.** The audit separately found that the signal uses the entry bar's close
  while the trade also fills at that close (`backend/backtest.py:154,158`), which is a distinct
  look-ahead defect. It is deliberately excluded here to keep this change small and reversible; it
  belongs with #3's temporal work.
- **No doc rewrite.** `docs/DATA_INTEGRITY.md:53` claims outcome-peeking is mitigated; correcting the
  integrity doc is backlog #6, sequenced deliberately after this lands so it describes real behavior.
- **No TW market mechanics** (±10% daily price limit, tick-size rounding, 1,000-share lots,
  suspension handling). A limit-up bar is genuinely unfillable and this change does not model that.
- No change to cost modeling, position sizing, metric definitions, API shape, or the frontend.

## Constraints

- **Small and reversible**: the change is confined to the two `locked_roi` assignments inside the
  forward-walk loop in `backend/backtest.py`. Rollback is reverting those two lines.
- **Honesty guard** (epic-wide): this fix is expected to change published numbers. No threshold,
  default, or metric definition may be adjusted to soften the result.
- **No API contract change** *(amended by AC8)*: response field **names** stay identical. The one
  type change is `sharpe_ratio` gaining `null`, which AC8 justifies and which both frontend
  surfaces already handle; `docs/API_CONTRACT.md` is updated to match. Nothing else moves.

## Domain Decisions

- **[DECISION]** A simulated exit settles at the price an **order** could have received, never at a
  bar's intraday extreme. The bar's high and low answer *whether* a barrier was touched; they do not
  answer *at what price the position left*. Conflating the two is what produced the inflation.
- **[DECISION]** The gap case is resolved by the bar's **open** on both sides: a bar that opens
  straight through a barrier gives a resting order no chance to fill at the barrier itself, so it
  fills at the open — better than the limit for a target, worse than the stop for a gap-down. This
  is the only place the open participates in settlement.
- **[CONSTRAINT]** Excursion measures (`max_gain_pct`, `max_drawdown_pct`) keep using the intraday
  extremes. They answer a different question — how far the position went against or in favour of the
  holder while open — and must not be "corrected" to settlement prices by future work.
- **[CONSTRAINT]** Settlement is clamped into `[day_low_pct, day_high_pct]`. The high and low are a
  bar's extremes by construction, but the open is a separate field a dirty feed can place outside
  them — an unadjusted open against split-adjusted extremes, or a column-order shift in a bulk
  parser (`core/bulk_history.py` reads TWSE and TPEX columns in different orders). Before this
  change settlement was bounded by construction because it *was* the high or the low; introducing
  the open created an unbounded path that the clamp closes. Added after independent review.
- **[CONSTRAINT]** Any future change to this loop must keep settlement defensive about missing data:
  an absent or NaN `open` settles exactly at the barrier rather than raising, because the OHLC frame
  is assembled from multiple ingest paths that do not all guarantee an open.
- **[TRADEOFF]** Same-bar stop-before-target precedence is preserved unchanged, so a bar that gaps
  open **above** the target while also trading below the stop still books a STOP even though the
  target demonstrably filled at the open first. Deferred to backlog #3 rather than amended, on
  **measured** grounds: the case needs a single bar whose open is ≥ `target_gain` above entry while
  its low is ≤ `-stop_loss` below it — an intraday range of ≥ 20% at the default barriers. Across
  the 99,287 real bars in `storage.db` only **4 (0.004%)** have a range that wide at all, and that
  is merely the *necessary* condition; Taiwan's ±10% daily price limit makes it structurally
  near-impossible for a limit-abiding security. It also biases conservative and is not a regression
  (the old code booked the session low, which was worse). Not worth amending a frozen AC for.

## File Relationship

EXTENDS `docs/specs/backtest-and-performance-opt.md` (owns `run_time_machine` and its net-of-cost
metrics) and `docs/specs/backtest-metric-label-honesty.md` (established the precedent that a metric
which cannot be computed honestly is reported as `None` rather than a flattering sentinel).
Consumed by `docs/specs/strategy-lab.md`, whose compare view reads these same summary metrics.
