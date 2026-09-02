---
status: active
title: Product Backlog — Unknown Is Not Zero
source: 2026-09-02 issue triage (12 open GitHub issues verified against master 88e6086)
created: 2026-09-02
last_updated: 2026-09-02 (#1 shipped; #2 next)
---

# Product Backlog

## Source Summary

Opened the same day the **Honest Metrics** epic closed. With the tracker untouched since 2026-06-05,
the user asked for its 12 open issues to be triaged. Every verdict was checked against master
`88e6086` before it was written — by reading the code, and in two cases by running it. One issue was
closed (GH #9: the capability already existed end-to-end), eight were commented on, three were left
alone because nothing about them had changed.

Three of those verdicts found defects worth fixing, and the user selected all three.

**The theme, for two of the three, is one sentence**: a value that cannot be computed is filled with
`0`, and everything downstream then treats the unknown as known. That is the same failure this
project has been removing for a year — `profit_factor=None` rather than 9999, `ai_prob=NULL` rather
than a fake 0.0, `sharpe_ratio=None` when dispersion is undefined — reappearing in two places nobody
had looked at.

**What makes it worse than a plain bug is which value gets substituted.** `0` is not a neutral
placeholder in either location. `dist_sma240 = 0` asserts *the price is exactly on its 240-day mean*.
KD's `k = 0` renders as *extremely oversold* — a strong buy signal, shown for a stock nobody can
trade. In both cases the guard against a crash produced a confident falsehood instead, which is
strictly worse than the `NaN` it replaced, because a `NaN` is visibly missing and a plausible number
is not.

The third item is unrelated in cause and bundled for deployment correctness: behind the reverse proxy
this project documents, every user shares one rate-limit bucket.

**Both premises in the original issues were partly wrong, and were corrected at triage rather than
inherited.** GH #8 claims a `ZeroDivisionError` that pandas does not raise, and asks for exactly the
epsilon guard that manufactures the false signal. GH #14 describes `sma_240` as all-`NaN` at cold
start without noticing that the prediction gate lets those rows through at 120. Fixing what an issue
*says* rather than what the code *does* would have shipped two non-fixes.

## Feature Inventory
| # | Feature | Kind | Labels | Priority | Spec File | Tier | Status | Dependencies |
|---|---|---|---|---|---|---|---|---|
| 1 | Unknown is not zero — ML features. A ticker with 120 <= rows < 260 passes `MIN_PREDICT_ROWS` (`core/config.py:36`, checked at `core/ai/predictor.py:341`) but cannot support the 240-day features, so `dist_sma240` / `sma240_slope` (`core/ai/common.py:132-136`) are `NaN` and `fillna(0)` (`core/ai/trainer.py:200`, `core/ai/predictor.py:354`) turns them into `0` — an assertion that the price sits exactly on its annual mean, indistinguishable to the model from a ticker that genuinely does. Measured on ticker 2330's real last trading day: with full history `dist_sma240 = +0.3429` (34.3% above its annual mean); with 150 rows it is `0.0` (exactly on it), and `sma240_slope` goes +0.0312 -> 0.0. Affected band is **120 <= rows < 260**, and 260 is already in the codebase as `MIN_TRAIN_ROWS`. **Training is NOT affected** — `trainer.py:199` drops warm-up rows before the fill; the defect is prediction-only. (GH #14) | review-finding | ml | **P0** | docs/specs/unknown-is-not-zero-ml-features.md | feature | Shipped | — |
| 2 | Trusted-proxy client identity — `backend/limiter.py:9` keys rate limits on `get_remote_address`, i.e. `request.client.host`, which behind any reverse proxy is the proxy's address, so every user shares one bucket. (This project documents no proxy deployment -- `docker-compose.yml` publishes 8000 directly -- but its commented `CORS_ORIGINS` anticipates a separately-hosted frontend, and a proxy is the ordinary way to add TLS.) Must NOT be fixed by trusting `X-Forwarded-For`, which is client-settable and would trade "innocent users blocked" for "rate limiting does nothing": needs an explicit trusted-hop count, default `0` (today's behaviour), counting from the right. (GH #16) | review-finding | api, security | P1 | docs/specs/trusted-proxy-client-identity.md | feature | In Progress | — |
| 3 | Unknown is not zero — technical indicators. On a flat series (`close == high == low`: suspension, no-volume limit-down) `calculate_kd` returns `k = 0.0` because of its epsilon guard, which the product renders as extremely oversold. `calculate_rsi` (`core/analysis.py:15`) has no guard and returns `nan`. Neither raises. The fix is the opposite of the one GH #8 requests: an indicator that cannot be computed stays null and is disclosed. (GH #8) | review-finding | indicators | P1 | docs/specs/unknown-is-not-zero-indicators.md | feature | Pending | #1 |

## Sequencing Note

Order fixed by the user: **#1 → #2 → #3**.

#1 first because it is the only one that reaches the number users act on — the AI probability on a
candidate card. #2 second because it is small, self-contained, and the only item here that affects
anyone running the documented deployment. #3 last because it shares #1's root cause and should reuse
whatever disclosure shape #1 establishes rather than inventing a second one; the dependency is on the
*pattern*, not on the code.

Each ships as its own PR, merged to `master` before the next begins.

## Honesty Guard

Carried forward from the Honest Metrics epic, unchanged and equally binding here. Every fix in this
backlog is expected to make the product show **fewer signals and more blanks**. No item may
compensate by loosening a gate, widening a window, or substituting a different plausible number.
Where a value cannot be computed honestly it stays null and is labelled. Specifically rejected in
advance: raising `MIN_PREDICT_ROWS` to 260 as the whole fix (new listings vanish with no explanation
given to the user) and shortening the 240-day window (changes model inputs) — either may still turn out to be right, but only with the
impact measured first, not as a way to make the symptom go away.

## Column Reference
- **Kind**: `feature` (planned) · `quick-win` (small planned) · `review-finding` (surfaced by review/audit) · `hotfix-spawn` (systemic issue from hotfix)
- **Priority**: `P0` (blocking, do now) · `P1` (high value, next batch) · `P2` (nice to have) · `—` (not yet prioritized)

## Status Key
- Pending: not yet started
- In Progress: spec generated, bootstrap running
- Shipped: feature shipped (see Ship History in current_state.md)
- Deferred: explicitly deferred
- Cancelled: dropped

## Still Open, Not In This Backlog

Recorded so the deferrals stay recoverable rather than being rediscovered by the next audit.

**From the tracker, verified 2026-09-02 and left open with the reasoning in the issue thread:**

- **GH #10** SQLite `database is locked` — WAL (`core/data.py:117`) and a busy timeout (`:55`) are
  already in place; the missing piece is a write retry. Not attempted because there is **no recorded
  occurrence** to verify a fix against. Next step is evidence: the row of silently-swallowed
  `except sqlite3.OperationalError` at `core/data.py:195-230` should log before anything is built.
- **GH #11** model comparison dashboard — `GET /api/models` exists (`backend/routes/stock.py:86`).
  The dashboard must not be built as originally specified: profit factors written before and after
  PR #64 use different settlement regimes and `oos_metrics` before PR #65 had a zero-day embargo, so
  it has to read `settlement` / `oos_metrics_scope` / `embargo` and refuse to compare across them.
- **GH #15** ensemble weight sliders — deliberately not scheduled while StrongBuy precision (0.3454)
  sits below the test-split prevalence (0.3512). Sliders would imply that tuning improves accuracy.
- **GH #17** ex-dividend alerts — its premise is outdated and it is blocked by Batch D below.
- **GH #18** sync error reporting — retry and `failed_count` already exist; only the error *reason*
  is missing from `sync_status` (`backend/routes/sync.py:23-31`).
- **GH #12**, **GH #13**, **GH #19** — unimplemented feature requests, unchanged, no comment added.

**From the closed Honest Metrics epic** (`docs/DATA_INTEGRITY.md` §Verification is canonical):
survivorship bias, and the backtest scoring a model trained over its own window — disclosed via
`model_temporal_scope`, not removed.

## Deferred: Batch D — price-source consistency

> Carried forward from the Honest Metrics backlog, still deferred, still unaddressed by any feature.
> Needs a `stock_history` schema migration plus a story for existing `storage.db` files — likely
> ADR-worthy. **GH #17 (ex-dividend alerts) is blocked on this**: ex-dividend gaps are flattened in
> the adjusted rows and preserved in the raw ones, so the same corporate action looks different
> depending on which fetcher wrote that stretch of the series.

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

**Prior epics** (all shipped, archived):
`docs/specs/_product-backlog-honest-metrics-2026-09-02.md` ·
`docs/specs/_product-backlog-honest-research-workbench-2026-07-02.md` ·
`docs/specs/_product-backlog-directly-usable-v1-2026-06-20.md`
