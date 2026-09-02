---
status: raw
title: Raw Spec Intake
source: natural-language (issue triage session, 2026-09-02)
received: 2026-09-02
---

# Source

On 2026-09-02, immediately after the Honest Metrics epic closed, the user asked for the 12 open
GitHub issues to be triaged. Every issue was verified against master `88e6086` before any verdict
was written — by reading the code, and in two cases by running it. The triage closed one issue,
commented on eight, and left three untouched.

Three of those verdicts identified defects worth fixing. The user selected all three, in this order:
GH #14, GH #16, GH #8.

---

## Item 1 — GH #14: features that cannot be computed are filled with 0

**Verified by measurement.** A 150-row panel (above the prediction gate, below what `sma_240` needs)
run through `prepare_features`:

```
rows in: 150 | feature rows out: 150
  dist_sma120 = 0.0297548923951959
  dist_sma240 = 0.0            <-- fabricated
```

Mechanism, more precise than the original issue text:

- The gate is `MIN_PREDICT_ROWS = 120` (`core/config.py:36`), checked at `core/ai/predictor.py:341`.
- `dist_sma240` (`core/ai/common.py:135`, a member of `FEATURE_COLS`) needs **240** rows.
- So a ticker with 120 <= rows < 240 **passes the gate**, `sma_240` is `NaN`, `dist_sma240` is `NaN`,
  and `fillna(0)` at `core/ai/trainer.py:200` / `core/ai/predictor.py:354` turns it into `0`.

`dist_sma240 = 0` states to the model: *the price is sitting exactly on its 240-day moving average.*
That is not a missing value. It is a specific, central, entirely plausible assertion, and it was
manufactured. Neither the MLP nor the random forest can distinguish it from a ticker genuinely
sitting on its annual mean.

**Correction to the first reading of this**: the *training* path is already protected.
`core/ai/trainer.py:195-199` calls `df_clean.dropna(subset=FEATURE_COLS)` when `is_training=True`,
with a comment naming this exact hazard ("would otherwise be filled with 0, biasing the model with
fake 'zero' features"). The `fillna(0)` on the next line therefore only reaches the **prediction**
path. The defect is prediction-only, and narrower than the issue text suggests.

Directions considered at triage (not decided):

1. Make the gate per-feature — when history cannot support `sma_240`, decline to predict
   (`ai_prob = NULL`, which the frontend already renders honestly) rather than substitute.
2. Whatever the refusal, it must be attributable: which features could not be computed, so the
   product can say *why* there is no number instead of only that there isn't one.

**Measured afterwards, on real data (ticker 2330, 1128 rows, same final trading day):**

| history supplied | features forced to exactly 0.0 (true value) |
|---|---|
| 120 rows | `dist_sma240` (+0.3429), `sma120_slope` (+0.0277), `sma240_slope` (+0.0312) |
| 150-239 rows | `dist_sma240` (+0.3429), `sma240_slope` (+0.0312) |
| 240 rows | `sma240_slope` (+0.0312) |
| 260 rows | none |

The substitution is not neutral. On its real last trading day 2330 sat **34.3% above** its 240-day
mean — a pronounced uptrend — and the short-history path reports it as sitting exactly **on** that
mean. The fabricated value erases a strong signal and replaces it with a plausible neutral one.

The affected band is **120 <= rows < 260**, not `< 240`. And 260 is not a new number: it is
`MIN_TRAIN_ROWS` (`core/config.py:35`), already in the codebase with the comment "needs SMA240". The
correct threshold was known; it was simply never applied on the prediction path.

On the 92-ticker dev panel **no ticker falls in the affected band** (min 729 rows), so this defect is
latent on the shipped data and fires on a fresh install, a new listing, or a partial backfill. Also
measured: on that panel, **0 of 92** tickers have any uncomputable feature on their latest row, so
refusing to predict on an uncomputable feature would refuse nobody there.

Explicitly rejected as a shortcut: "just raise the gate to 240" (new listings disappear from the
product entirely) and "just shorten the 240-day window" (changes model inputs). Either may turn out
to be right, but only after the impact is measured.

---

## Item 2 — GH #16: the rate limiter identifies every user as the proxy

`backend/limiter.py:9`:

```python
limiter = Limiter(key_func=get_remote_address)
```

`get_remote_address` reads `request.client.host`. Behind Nginx/Caddy in the documented Docker
deployment that is the proxy's internal address, so every user shares one rate-limit bucket and
innocent users get 429s.

**The fix suggested in the issue would open a worse hole.** `X-Forwarded-For` is client-settable;
trusting it unconditionally lets anyone send a random address and bypass rate limiting entirely —
trading "innocent users are blocked" for "rate limiting does nothing".

Direction from triage: make it configurable and *untrusting by default*.

- A setting (e.g. `TRUSTED_PROXY_COUNT`, default `0`).
- `0` keeps today's behaviour exactly (direct deployment reads `request.client.host`).
- `N > 0` takes the Nth address **from the right** of `X-Forwarded-For` — the right-hand entries were
  written by our own proxies and are trustworthy; the left-hand ones came from the client and are
  not.
- The deployment docs must explain the setting, or an operator who sets it wrong will not know they
  are unprotected.

---

## Item 3 — GH #8: an indicator that cannot be computed reports an extreme instead

**Verified by measurement.** A perfectly flat 60-row series (`close == high == low`, i.e. a
suspended or no-volume limit-down ticker):

| | result |
|---|---|
| `calculate_rsi` | `nan` |
| `calculate_kd` | `k = 0.0`, `d = 0.0` |

Two corrections to the issue's premise:

- **No `ZeroDivisionError` is raised.** pandas division yields `nan`/`inf`. The claimed impact
  ("daily sync interrupted by an individual ticker") does not occur.
- **The epsilon guard the issue asks for is mostly already present**: `core/analysis.py:42` (KD's
  rsv), `:60` (Bollinger `bb_percent`), and nearly every ratio feature in
  `core/indicators_v2.py:46-99`. The one place it is missing is RSI: `core/analysis.py:15`,
  `rs = avg_gain / avg_loss`, which yields `nan` on a flat series.

**But the real defect is the suggested fix itself.** Because KD *does* carry the epsilon guard, a
flat ticker gets `k = 0.0` — which the product renders as *extremely oversold*, a strong buy signal,
for a stock nobody can trade. The guard converted an honest `NaN` into a confident falsehood.

This is the same disease as Item 1: filling a value that cannot be computed with `0` so that
downstream consumers treat the unknown as known. The project already has the opposite precedent —
`profit_factor=None`, `ai_prob=NULL`, and `sharpe_ratio=None` when dispersion is undefined.

Direction from triage: an indicator that cannot be computed stays `None`/`NaN` and is disclosed,
rather than being given a plausible number.

---

## Constraint carried from the closed epic

Every fix here is expected to make the product show **fewer** signals and **more** blanks. No item
may compensate by loosening a gate, widening a window, or substituting a different plausible number.
Where a value cannot be computed honestly it stays null and is labelled.
