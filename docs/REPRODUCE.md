# Reproduce the Pipeline — an Honest, End-to-End Walkthrough

This is the developer / learner reference for smart-stock's machine-learning +
quant pipeline. It maps the full **`data → label → train → backtest → eval`**
flow to the real code, and gives you the one command to reproduce each stage.

> **Read this first — the honesty contract.** On the offline demo (or any small
> dataset) the trained model is **degenerate**: Buy/StrongBuy precision & recall
> collapse to ~0 and "accuracy" is inflated by the dominant *Hold* class. That is
> not a bug — it is what a model trained on too little data honestly looks like,
> and the app's `model_health` surfaces it in the UI. A non-degenerate model needs
> roughly **1000+ rows/ticker** and **~92+ tickers** (the out-of-sample floor from
> [`ml-label-oos-evaluation.md`](specs/ml-label-oos-evaluation.md)). This pipeline
> demonstrates the **mechanism**, not a production-quality model.

## One command

```bash
python scripts/reproduce_pipeline.py         # print the pipeline map (safe, no side effects)
python scripts/reproduce_pipeline.py --run    # run the offline demo (auto-runs data + backtest)
```

`--run` auto-runs the fast, robust stages in-process (**data** seed and a
net-of-cost **backtest**, which genuinely work on demo data). The heavier,
opt-in stages (**label**, **train**, **eval**) are reported honestly with their
commands rather than half-run — run them yourself with the commands below.

## The five stages

### 1. Data — `scripts/seed_demo.py` · `core/bulk_history.py`
Load price history. Two honest sources:
- **Offline demo (default):** `python scripts/seed_demo.py` loads the bundled
  fixture (`data/demo/demo_prices.csv`, real auto-adjusted prices) and computes
  technical scores — no network. Great for reading the mechanism fast.
- **Real / full universe:** `python scripts/fast_backfill.py --days 1100` pulls
  the full ~1,800-stock universe from authoritative TWSE/TPEX **bulk** endpoints
  (~2 calls/day, no redistribution). Raw prices (not split/dividend-adjusted) —
  internally consistent for backtesting.

Coverage is honest and inspectable: `core/data.py:report_history_coverage` and
`get_history_context` report how many tickers meet the predict/train row
thresholds — the same numbers the **Transparency Panel** (`/transparency`) shows.

### 2. Label — `core/ai/common.py` (`LABEL_MODE=atr`) · `core/ai/label_analysis.py`
Training targets are **ATR volatility-scaled triple-barrier** labels: for each
entry, a target/stop/time barrier scaled by the stock's own ATR (no look-ahead).
This replaced fixed-percentage labels that ignored per-stock volatility and
produced a degenerate class distribution. Inspect the Hold/Buy/StrongBuy split
with `core/ai/label_analysis.py:label_distribution`; the OOS eval below also
surfaces it. Toggle `LABEL_MODE=fixed` to reproduce the legacy labels byte-for-byte.

### 3. Train — `backend/train_ai.py` · `core/ai/trainer.py`
```bash
python backend/train_ai.py
```
Trains the **GB + RF + MLP** ensemble with a chronological split (no look-ahead;
see [`DATA_INTEGRITY.md`](DATA_INTEGRITY.md)). Out-of-sample metrics (accuracy,
per-class precision/recall) are written to `models_history.json` and later
surfaced by `get_model_health()` and the Transparency Panel. On demo data this
produces a **degenerate** model — expected and disclosed.

### 4. Backtest — `backend/backtest.py:run_time_machine`
Net-of-cost sniper backtest with Taiwan transaction friction (commission, tax,
slippage) plus Sharpe and worst drawdown. Exposed at `GET /api/backtest`, and the
**Strategy Lab** (`/backtest`) lets you save/compare parameter bundles. Uses
`random.seed(42)` — reproducible within a stable universe cache.

### 5. OOS Eval — `scripts/eval_label_modes.py`
```bash
python scripts/eval_label_modes.py
```
Out-of-sample precision/recall for Buy/StrongBuy, comparing `atr` vs `fixed`
labeling on a chronological split with an embargo. This is the evidence tool
behind [`ml-label-oos-evaluation.md`](specs/ml-label-oos-evaluation.md): at
92-ticker scale the degeneracy did **not** reproduce (it was a small-data
artifact) — but absolute precision stays low. Results at demo scale are
**indicative only**, not a credible read.

> **Note (2026-09-02)**: the `atr`-vs-`fixed` conclusion this section used to
> state was produced under an embargo that separated train from test by **0
> trading days**. See the supersession warning and re-measurement in
> [`ml-label-oos-evaluation.md`](specs/ml-label-oos-evaluation.md). The
> corrected numbers do not settle `atr` vs `fixed` — on lift over the base rate
> the ranking inverts — and that decision is deliberately left open.

## What to trust

The honest value of this project is **transparency, not prediction accuracy**.
Reproduce the pipeline to understand and verify the mechanism; read
`/transparency` to see exactly what the running system knows; and treat every
score as a technical evaluation, never a guarantee.
