---
status: frozen
module: core-ai
version: 1.1.0
---

# AI Pipeline Correctness & OTC Stock Synchronization Optimization

Details the optimizations to prevent data leakage in ML training, fix MLPClassifier sample weight training, optimize OTC stock syncing speed, and align feature-indicator checks.

## Acceptance Criteria

### AC1: TPEX/OTC Stock Universe Integration
- In `core/data.py`, modify `get_all_tw_stocks()` to loop through `twstock.codes` and include both `'上市'` (listed) and `'上櫃'` (OTC) stocks.
- Standardize all tickers to their numeric 4-digit codes via `standardize_ticker` to ensure unique keys in database tables.

### AC2: Dynamic yfinance Suffix Resolution
- Build a cached mapping mapping clean ticker codes to their correct yfinance suffix (`.TW` or `.TWO`) using `twstock` metadata.
- Modify `fetch_stock_data()` to download using the correct suffix directly on the first attempt, preventing invalid `.TW` query timeouts for OTC stocks.
- Handle fallback defensively so that if the lookup is missing or fails, retry logic falls back to `.TWO` reliably.
- For non-Taiwan stocks (e.g. US stocks like `AAPL` or crypto like `BTC-USD`), bypass Taiwan suffix appending and return an empty suffix `""` to allow direct yfinance queries.

### AC3: Training Leakage Prevention (Temporal Embargo)

> [!WARNING]
> **AC3 is SUPERSEDED by `docs/specs/date-based-train-test-embargo.md` (2026-09-02).** Both bullets
> below specify the embargo in **rows**, which on a cross-sectionally stacked panel is not time at
> all: one date contributes N rows, so `PRED_DAYS` rows is `PRED_DAYS/N` days. Measured on the real
> 92-ticker panel, this AC as written produced a separation of **0 trading days**. The embargo is
> now counted in trading days from the panel's own calendar, and the `TimeSeriesSplit` gap is scaled
> by the widest date. The bullets are kept verbatim as the record of what was specified.

- In `core/ai/trainer.py:train_and_save()`, separate the training and testing sets with a gap of `PRED_DAYS` rows (temporal embargo) to prevent target overlapping look-ahead leakage.
- Initialize `TimeSeriesSplit` with `gap=PRED_DAYS` during cross-validation to prevent validation fold look-ahead leakage.

### AC4: MLPClassifier Oversampling & Dynamic Slicing
- Fix the MLPClassifier fit crash/misalignment by removing `mlpclassifier__sample_weight` from pipeline training.
- Handle MLP class imbalance by performing manual oversampling (replicating minority class samples in the training set according to target weights) prior to fitting the MLP.
- Disable random `early_stopping` inside `MLPClassifier` to avoid time-series look-ahead validation leaks.
- In `predictor.py:predict_prob()`, map probabilities dynamically based on `clf.classes_` indices rather than hardcoded indexes (`[0]`, `[1]`, `[2]`), protecting against missing target class scenarios.

### AC5: Feature Checker & Row Count Consistency
- Expand `required_base` indicators checked in `prepare_features()` to include all required features (`sma_120`, `sma_240`, `atr`) to prevent KeyErrors.
- Align `predictor.py`'s row count check from `len(df) < 60` to use `MIN_PREDICT_ROWS` (120) or higher.
- Ensure that if a stock has less than `MIN_TRAIN_ROWS` / `MIN_PREDICT_ROWS`, it handles empty features gracefully.
