---
status: raw
title: Raw Spec Intake — Quant Expert Panel Audit (Batch A+B+C)
source: three independent read-only audit reports commissioned 2026-09-02
received: 2026-09-02
---

## Provenance

Three independent read-only auditors were commissioned with disjoint lenses and no knowledge of
each other's assignment:

1. **ML methodology** — labeling, features, training, validation, leakage.
2. **Backtest realism** — execution modeling, cost realism, TW market mechanics, survivorship.
3. **Data integrity & risk** — source consistency, corporate actions, point-in-time correctness,
   honesty of user-facing numbers.

Convergence across independent lenses is recorded per finding below; it is the strongest signal
available for prioritization. The primary agent independently re-read `backend/backtest.py:195-235`
and `core/ai/trainer.py:225-270` and confirmed findings F1 and F2 directly.

**Scope selected by the user**: batch A+B+C (backtest settlement honesty, ML validation
correctness, docs-vs-reality alignment). Batch D (price-source consistency — mixed raw/adjusted
series, `source` column, reconciliation-script false PASS) was explicitly **deferred** at intake:
it requires a `stock_history` schema migration plus handling of existing `storage.db` files, and
is likely ADR-worthy. It is preserved at the end of this file so the deferral is recoverable.

---

## Findings selected for this intake

### F1 — Training embargo is measured in pooled rows, not dates (CONFIRMED, 3/3 auditors)

`core/ai/trainer.py:225-241`. `X_all` is `pd.concat` of every ticker's frame then `sort_values('date')`,
so one calendar day contributes N rows (N = number of tickers). The split is
`split_idx = int(len(X_all) * 0.8)` with the train set embargoed as `X_all.iloc[:split_idx - PRED_DAYS]`
— removing `PRED_DAYS = 20` **rows**, which at the 92-ticker scale used in
`docs/specs/ml-label-oos-evaluation.md` is ≈ **0.2 trading days**.

Every triple-barrier label spans 20 *trading days*, so roughly `20 × N` train rows still have their
outcomes resolved inside the test window. The same defect exists at `core/ai/trainer.py:263` —
`TimeSeriesSplit(n_splits=3, gap=PRED_DAYS)`, where sklearn's `gap` is also counted in samples —
and at `scripts/eval_label_modes.py:70`.

**Consequence**: every `oos_metrics.precision_strong` / `recall_strong` in `models_history.json`, the
ATR-vs-fixed comparison table in `docs/specs/ml-label-oos-evaluation.md`, and the OOS numbers served
by `backend/routes/transparency.py:93` are optimistically biased. They are not clean out-of-sample.

**Proposed fix**: compute the embargo in dates, not rows — choose a split *date*, train on
`date <= cut_date - PRED_DAYS trading days`, test on `date > cut_date`; scale the CV `gap` by the
per-date row count (or split per-date).

### F2 — Winning exits are booked at the bar's high, not at the target price (CONFIRMED, 3/3 auditors)

`backend/backtest.py:216-220`. On a target touch the simulator sets `locked_roi = day_high_pct` — the
full session high — rather than `target_gain`. The stop branch at `:210-215` sets
`locked_roi = day_low_pct`, the full session low.

The bias is **one-directional**: losers are booked at the worst intraday print, winners at the best.
A resting limit sell fills at the target, not at the day's high.

**Consequence**: `avg_return`, `net_win_rate`, `profit_factor` and `sharpe_ratio` are all inflated.
A day that gaps to +25% against a 15% target books +25%.

**Proposed fix**: `locked_roi = target_gain` on HIT. On STOP, use `max(day_low_pct, -stop_loss)` unless
the bar *opened* below the stop, in which case use the open (gap fill).

### F3 — Docs assert mitigations the code does not provide (CONFIRMED, 3/3 auditors)

- `docs/DATA_INTEGRITY.md:42` presents the exact F1 code as the mitigation for "Chronological
  Leakage", describing a guarantee that does not hold.
- `docs/DATA_INTEGRITY.md:51` claims `random.seed(42)` + `random.sample()` mitigates "Selection Bias
  (backtesting only stocks that survived)". Random sampling *from a survivor-only universe* does not
  remove survivorship bias; it only makes the sample unbiased *within* survivors.
- `docs/DATA_INTEGRITY.md:53` claims outcome-peeking is mitigated, which F2 contradicts.
- `docs/DATA_INTEGRITY.md:66-70` attributes good backtest numbers to "True Out-of-Sample
  generalization" and asserts that consistent profit factors across `days_ago` "validate the lack of
  look-ahead bias" — a non-sequitur, and in tension with the project's own recorded finding that the
  model is degenerate/weak.
- `README.md:237` claims the 80/20 time-series split achieves 資料外洩 "完全杜絕" (completely eliminated).
- `docs/project_meta/whitepaper.md:89` states market data "is fetched with `auto_adjust=True`" as a
  system-wide property — false since the bulk-history path shipped.
- `core/market.py:68-72` labels breadth as `"LOW RISK (BULL)"` / `"HIGH RISK (BEAR)"` purely from the
  share of tickers with `trend_score > 20` — no volatility, no index, no drawdown, no correlation —
  and `frontend/v4/src/pages/MarketRisk.tsx:74` claims it assesses "動量均值與系統風險", which does not exist.

**Proposed fix**: correct each claim to describe what the code actually does after F1/F2 land; name
survivorship as a known *unmitigated* limitation; replace the circular verification paragraph with a
falsifiable control (e.g. a label-shuffle test where profit factor should collapse to ~1); rename
`risk_level` to a breadth label and fix its tooltip.

### F5 — The backtest scores a model that was trained on the backtest window (CONFIRMED, 2/3 auditors)

`backend/backtest.py:176` calls `predict_prob(df_past, version=version)` with the *production* model,
which `core/ai/trainer.py:238-241` trained on all rows up to today. For `days_ago=30` the model has
already seen the 30 days it is being scored on, so the run measures in-sample recall while the UI
frames it as an AI 回測報告. `docs/DATA_INTEGRITY.md:66-69` asserts the opposite.

**Proposed fix**: compare the selected model's `trained_at` (`core/ai/trainer.py:361`) against the
entry date and refuse to run — or badge the result explicitly in-sample — when the model post-dates
the entry. Training an as-of model per backtest window is the fuller fix and is out of scope here.

### F6 — Entry point is a row offset, so the "portfolio" is not one cross-section (CONFIRMED, 2/3 auditors)

`backend/backtest.py:149` computes `entry_idx = len(df_full) - days_ago`. Row counts differ per ticker
(halts drop rows — `core/bulk_history.py:54-56` returns `None` for `--` cells; stale tickers stop
updating), so a ticker with gaps enters on a *different calendar date*. Yet `backend/backtest.py:309`
reports a single `simulated_date` taken from `top_picks[0]` alone and presents it as the whole run's
window, alongside `holding_days` and `exit_date_actual` from the same single pick.

**Proposed fix**: resolve the entry by calendar date per ticker and drop tickers with no row on or
near that date.

### F7 — Model rotation ranks candidates by an in-sample backtest (CONFIRMED, 1/3 auditors)

`core/ai/trainer.py:326-343` refits the deployed ensemble on **all** data, then `:409-421` immediately
runs `run_time_machine(days_ago=30)` and stores its `profit_factor` as `backtest_30d`. Training labels
reach up to T−20 with barriers looking forward to T, so the T−30…T−10 window scored by that backtest is
the price path the model was fit on. `core/ai/trainer.py:472` and `backend/manage_models.py:141` then
keep the top `MAX_SAVED_MODELS` by `profit_factor_sort_key` (`core/ai/common.py:48-55`).

**Consequence**: the retained "best" model is the one that best memorized the last month, and the PF
shown by `manage_models list` is both inflated and selection-biased.

**Proposed fix**: run the rotation backtest on a window that post-dates the final fit's label horizon
(`days_ago > PRED_DAYS + holding_days`, i.e. ≥ 45), or rank by held-out `oos_metrics` instead.

Related, same file: `core/ai/common.py:55` maps a `None` profit factor (the no-losing-trade case,
`backend/backtest.py:288`) to `-1.0`, i.e. *below* a PF of 0.0 — so a model with zero losses sorts last
and is pruned first.

### F8 — Reported OOS metrics describe a model that is never deployed (CONFIRMED, 1/3 auditors)

`core/ai/trainer.py:298-310` evaluates the 80%-trained ensemble; `:326-345` builds and ships a
*different* ensemble refit on 100% of the data. `models_history.json` attaches the former's metrics to
the latter's `version`, and `backend/routes/transparency.py:93` plus `core/ai/predictor.py:177-181`
serve them as the active model's numbers. Refitting on the full set is standard practice; attributing
the holdout score to the shipped artifact is not.

**Proposed fix**: rename the stored field to make the attribution explicit (e.g.
`oos_metrics_of_split_model`) and carry that framing into the transparency payload and UI copy.

### F9 — No no-skill baseline is recorded, and the OOS spec's conclusion inverts once one is added (CONFIRMED, 1/3 auditors)

`docs/specs/ml-label-oos-evaluation.md:23-24` reports `fixed` StrongBuy prevalence 13.6% at precision
0.339 (**2.49× lift**) versus `atr` prevalence 29.6% at precision 0.363 (**1.23× lift**). For the Buy
class: fixed 9.4% → 0.082 (**0.87×**) and atr 15.7% → 0.120 (**0.76×**) — both *below* a random
classifier. Line 28 calls 0.082 → 0.120 an improvement and line 29 concludes "ATR wins", neither of
which survives base-rate normalization.

Nothing in `core/ai/trainer.py:428-449` stores a majority-class, prevalence, or buy-and-hold reference,
and `class_distribution` at `:434-438` records the **train** split, not the test split.

**Proposed fix**: store the *test-split* class prevalence alongside `oos_metrics` and report precision
as lift over prevalence wherever precision is surfaced.

### F10 — `get_model_health` calls a below-chance model "ok" (CONFIRMED, 1/3 auditors)

`core/ai/predictor.py:189-195` computes `buy_signal_power = p_buy + r_buy + p_strong + r_strong` and
returns `degraded` only when that sum is `<= 0`. A model at the measured 0.12 Buy precision (below
chance per F9) reports `status: "ok"` with an empty message, so `ModelHealthBanner` disappears and the
honest-disclosure path the project relies on silently stops firing.

**Proposed fix**: compare each precision against the test-split prevalence and mark `degraded` when
StrongBuy precision is at or below prevalence.

---

## Lower-priority items surfaced in the same audits (not selected)

- Look-ahead in the liquidity prefilter: `backend/backtest.py:36` averages `df['volume'].tail(20)` of
  the *full* frame, i.e. volume as of today, to admit candidates for a past entry. Latent — off by
  default (`BACKTEST_MIN_AVG_VOLUME=0`).
- No uniqueness/overlap weighting for concurrent labels (`core/ai/trainer.py:251-258`, `:317-324`):
  with a 20-day horizon sampled daily, effective sample size is ≈ 1/20 of `len(X_all)`.
- Train/serve feature skew on long-MA warm-up: training drops NaN rows (`core/ai/trainer.py:196`) but
  prediction zero-fills (`:197`), so a ticker with 120–249 rows is scored with `dist_sma240` and
  `sma240_slope` at 0 — read by the model as "price exactly on a perfectly flat 240-day MA".
- Label barriers do not match the yardstick `ai_prob` is judged by: labels are ATR-scaled while
  `backend/backtest.py:48-49` and `docs/GLOSSARY.md:7` use fixed +15%/−5%.
- No TW market mechanics: no ±10% daily price-limit check, no tick-size rounding, no 1,000-share lot,
  no suspension handling. ETF transaction tax (0.1%) is charged at the stock rate (0.3%) — conservative.
- `avg_max_drawdown` / `worst_drawdown` (`backend/backtest.py:281-283`) are per-position maximum
  adverse excursion, not peak-to-trough drawdown; the UI label is honest, the API field name is not.
- Sharpe is cross-sectional (dispersion across the N picks in one period), not a time-series Sharpe.
- Multiple-testing hazard in Strategy Lab compare is undisclosed.
- `candidate_pool_size` (`backend/backtest.py:310`) is `len(results)` — the count that passed the AI
  threshold — not the pool size.
- `BacktestEquityChart` is dead code: it renders only `if (data.history)` and `run_time_machine` never
  returns `history`.
- Bar-to-bar `change_percent` across arbitrary calendar gaps (`backend/recalculate.py:113`,
  `backend/routes/sync.py:139-141`); observed max gap in `storage.db` is 13 days.
- `scripts/validate_twse_prices.py:43-60,88-89` returns exit 0 with "All checked closes match" when a
  TPEX/OTC ticker yields zero comparable days.

---

## Batch D — deferred at intake (price-source consistency)

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

## Explicitly confirmed as correct (do not "fix")

Barrier causality is clean: entry price and entry ATR are taken at row t and only future highs/lows
decide touches (`core/ai/trainer.py:45-63`); same-bar stop-and-target ties resolve to the stop, which
is conservative (`:70-71`); the terminal `PRED_DAYS` unlabelable rows are dropped (`:186-187`). Every
indicator is trailing-only — no centered windows (`core/analysis.py:25-71`,
`core/indicators_v2.py:103-108`). `StandardScaler` sits inside the MLP pipeline and is fit on the train
split only (`core/ai/trainer.py:293-294`). `bfill` is confined to the inference path (`:178-181`). The
backtest slices `df_past = df_full.iloc[:entry_idx+1]` before recomputing indicators
(`backend/backtest.py:158-168`). Buy/sell cost asymmetry is modeled correctly and compounded, not
summed (`:224-226`), matching TW reality at 0.1425% / 0.3%. `profit_factor` returns `None` rather than
a 9999 sentinel (`:288`). Failed predictions return `None`, not a fake 0.0
(`core/ai/predictor.py:339-341`). `get_model_health` returns honest zh-TW `degraded` / `unavailable`
states (`:159-205`). NULL is preserved for unavailable AI probabilities (`core/data.py:674-675`).
`backfill_bulk` counts only confirmed writes (`core/bulk_history.py:191-200`). Bulk parsers drop `--`
(suspended) cells rather than zero-filling (`:54-56`).
