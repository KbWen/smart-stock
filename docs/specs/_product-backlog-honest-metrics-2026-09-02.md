---
status: archived
title: Product Backlog — Honest Metrics [COMPLETE — all 6 shipped 2026-09-02]
source: 2026-09-02 quant-expert panel audit (3 independent read-only auditors, batch A+B+C selected by user)
created: 2026-09-02
last_updated: 2026-09-02 (ALL 6 SHIPPED — epic complete)
---

# Product Backlog

## Source Summary

Three independent read-only auditors were commissioned with disjoint lenses — **ML methodology**,
**backtest realism**, and **data integrity & risk** — none of them knowing what the others were
assigned. They converged on the same small set of defects, which is the strongest prioritization
signal available here. The primary agent independently re-read `backend/backtest.py:195-235` and
`core/ai/trainer.py:225-270` and confirmed the two P0 findings directly rather than relying on the
reports alone.

The theme is the same 「說到做不到」 identity gap the 2026-07-19 audit found — but this time in the
**mathematics layer**, not the copy layer. `docs/DATA_INTEGRITY.md:42` presents the broken embargo
code *as the mitigation* for chronological leakage; `README.md:237` claims data leakage is 「完全杜絕」;
`docs/DATA_INTEGRITY.md:51` credits random sampling with mitigating survivorship bias, which it
cannot do. Meanwhile the backtest books winners at the session high and losers at the session low,
so every magnitude-based performance number a user sees is inflated in one direction.

**This directly threatens the project's stated differentiator** — transparency over prediction. A
research workbench whose own integrity doc overstates its guarantees is worse positioned than one
that never made the claim.

> [!NOTE]
> **Epic complete 2026-09-02.** All six features shipped (PRs #64–#68 plus #66). What the epic
> deliberately did **not** fix is recorded in `docs/DATA_INTEGRITY.md` §Verification, which is now
> the canonical statement of where this project stands: survivorship bias (no point-in-time
> universe), the backtest scoring a model trained over its own window (disclosed via
> `model_temporal_scope`, not removed — that needs an as-of model per window), and **deferred batch
> D**, price-source consistency. Batch D's detail moved into this file's §Deferred section below
> when `_raw-intake.md` was deleted, its job done.

**Scope selected by the user at intake**: batch A+B+C. Batch **D (price-source consistency)** was
explicitly deferred — mixed raw/adjusted series within one ticker, the missing `source` column, the
reconciliation script's OTC false PASS, and the absent point-in-time universe. It needs a
`stock_history` schema migration plus a story for existing `storage.db` files and is likely
ADR-worthy. Full detail is preserved in `_raw-intake.md` so the deferral is recoverable.

**Honesty guard for this epic**: every fix here is expected to make the numbers *look worse*. That is
the point, and no feature in this epic may compensate by loosening a threshold, changing a default,
or re-framing a metric to preserve an attractive figure. Where a number cannot be computed honestly,
it stays `None` / N/A — consistent with the shipped `profit_factor=None` and `ai_prob=NULL` precedent.

**Out of scope for the whole epic**: improving model quality (the model is honestly weak and stays
that way), training an as-of model per backtest window, live trading, and any change to the ML
feature set or label definition.

## Feature Inventory
| # | Feature | Kind | Labels | Priority | Spec File | Tier | Status | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | Backtest settlement realism — book a HIT at `target_gain` instead of the session high, and handle a gap-through stop at the open; removes the one-directional inflation in the magnitude-based metrics (`avg_return`, `profit_factor`, `sharpe_ratio`, `best_return`); win rates are structurally unaffected because trade signs do not change (F2, 3/3 auditors) | review-finding | backtest | P0 | docs/specs/backtest-settlement-realism.md | hotfix | Shipped | — |
| 2 | Date-based train/test embargo — measure the embargo in trading days rather than pooled rows, scale the `TimeSeriesSplit` gap by per-date row count, and apply the same correction in `scripts/eval_label_modes.py` (F1, 3/3 auditors) | review-finding | ml | P0 | docs/specs/date-based-train-test-embargo.md | feature | Shipped | — |
| 3 | Backtest temporal guard — refuse or explicitly badge a run whose model `trained_at` post-dates the entry date, and resolve the entry point by calendar date per ticker instead of a row offset (F5, F6). **Carries two #1 review deferrals**: a bar that gaps open above the target while also breaching the stop still books a STOP (measured at ≤0.004% of real bars, and structurally near-impossible under TW's ±10% limit), and `best_stock` is now an arbitrary tie-break because every no-gap HIT settles at exactly `target_gain` | review-finding | backtest | P1 | docs/specs/backtest-temporal-guard.md | feature | Shipped | #1 |
| 4 | Model rotation ranking honesty — move the rotation backtest window past the final fit's label horizon, and stop sorting a `None` profit factor below 0.0 (F7). **Raised in priority by #1**: `backtest_30d.profit_factor` entries written before and after the settlement fix are not comparable, `core/ai/trainer.py:472` ranks them together, and `:487` then irreversibly `os.remove`s the `.pkl` files outside the top 5 — so a genuinely better pre-fix model can be deleted for being measured with a different ruler. Needs a settlement marker on the persisted structure | review-finding | ml | **P0** | docs/specs/model-rotation-ranking-honesty.md | feature | Shipped | #2 |
| 5 | OOS metric attribution and baseline lift — attribute holdout metrics to the split model that earned them, record test-split class prevalence, report precision as lift over prevalence, and let `get_model_health` call a below-prevalence model degraded. **Raised to P0 by #2's measurement**: with a clean embargo StrongBuy precision 0.3454 sits BELOW the test-split prevalence 0.3512 — no skill to negative skill — and `core/ai/predictor.py:195` still reports `ok`, so the health check is now most wrong exactly when the metrics are most honest. #2 also added the `embargo` marker on history entries that the transparency badge will need (F8, F9, F10) | review-finding | ml, transparency | **P0** | docs/specs/oos-metric-attribution-and-lift.md | feature | Shipped | #2 |
| 6 | Docs-vs-reality alignment — correct the four `DATA_INTEGRITY.md` claims, `README.md:237` 「完全杜絕」, the whitepaper's `auto_adjust` assertion, and the `risk_level` naming plus its tooltip (F3, 3/3 auditors) | review-finding | docs | P0 | docs/specs/docs-reality-alignment.md | feature | Shipped | #1, #2 |

## Classification Note

#1 is `quick-win` by size — two assignments in one module plus tests — but was **escalated to
`hotfix`** at bootstrap. Escalation is never a bypass; the reason is that a `quick-win` makes the
review and test gates optional, and this change rewrites financial performance numbers that users
read as achievable. AC6 (six empirically falsified tests) and AC7 (a same-seed before/after evidence
run, with tuning explicitly forbidden) are review-grade requirements, and every honesty-affecting
change in this repo has gone through independent review. The gates are worth their cost here.

## Sequencing Note

#6 is P0 but deliberately **last** among the P0s: the docs must describe the behavior that exists
after #1 and #2 land, otherwise the same paragraphs get rewritten twice and risk being wrong in a new
way in between. #1 is the cheapest and its effect is immediately visible to users; #2 is the finding
all three auditors independently raised. #3–#5 are follow-ons that each depend on one of the two P0s.

## Column Reference
- **Kind**: `feature` (planned) · `quick-win` (small planned) · `review-finding` (surfaced by review/audit) · `hotfix-spawn` (systemic issue from hotfix)
- **Priority**: `P0` (blocking, do now) · `P1` (high value, next batch) · `P2` (nice to have) · `—` (not yet prioritized)

## Status Key
- Pending: not yet started
- In Progress: spec generated, bootstrap running
- Shipped: feature shipped (see Ship History in current_state.md)
- Deferred: explicitly deferred
- Cancelled: dropped

## Deferred: Batch D — price-source consistency

> Carried over verbatim from `_raw-intake.md` when that file was deleted at the end of the
> epic. It is the one audit finding no feature here addressed, and it needs a `stock_history`
> schema migration plus a story for existing `storage.db` files — likely ADR-worthy.

Preserved so the deferral is recoverable, not lost.

- Mixed adjusted/raw price basis within a single ticker's series. `core/data.py:622,628` fetches
  yfinance with `auto_adjust=True`; `core/bulk_history.py:9-11,190` writes raw TWSE/TPEX closes; both
  persist through the same `save_to_db` → `INSERT OR REPLACE INTO stock_history` (`core/data.py:568`).
  The schema (`core/data.py:120-131`) has **no `source` column**, so the two definitions are
  indistinguishable after write. Empirically confirmed in the shipped `storage.db`: ticker `2330` is
  100% fractional (adjusted) through 2026-04, 90% in 2026-05, 33% in 2026-06, and 0% from 2026-07 on,
  with round exchange-tick prices from 2026-06-11. Its older rows match `data/demo/demo_prices.csv` to
  0.0006% across 485 overlapping dates. At each source boundary a dividend or split becomes a fake
  overnight return feeding `return_1d`, ATR, and the triple-barrier labels.
- No TW corporate-action handling (減資, 除權息, rights issues): zero hits across `core/` and `backend/`.
  Documented as a non-goal in `docs/specs/accelerated-universe-sync.md:30`.
- Suspected: `core/data.py:604` treats any DB whose last row is not today as stale, so each
  weekend/holiday sync re-downloads 730 days of adjusted yfinance data and `INSERT OR REPLACE`s over
  bulk rows inside that window, creating a moving adjusted/raw seam at the 730-day boundary.
- Suspected: `core/data.py:625-630` falls back to the opposite `.TW`/`.TWO` suffix on an empty result,
  so a code delisted from TWSE but present on TPEX would be silently sourced from the other market.
- No point-in-time universe: the universe cache schema is `{code,name,market,kind}` with no
  listing/delisting dates, so `get_all_tw_stocks()` applies today's listed set retroactively.

---
