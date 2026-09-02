import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import hashlib
import hmac as _hmac
import joblib
import os
import shutil
import json
import glob
from datetime import datetime
from core import config as _cfg
from core.ai.common import FEATURE_COLS, MODEL_PATH, PRED_DAYS, TARGET_GAIN, STOP_LOSS, BUY_TARGET, MIN_TRAIN_ROWS, MIN_PREDICT_ROWS, MAX_SAVED_MODELS, select_for_deletion, timestamps_to_delete, CURRENT_SETTLEMENT
from core.ai import common as _c  # read LABEL_MODE / ATR_* dynamically (togglable)
from core.logger import setup_logger

logger = setup_logger("core.ai.trainer")


def _compute_targets(closes, highs, lows, atr, mode):
    """Vectorized 3-class Sniper target via a triple-barrier rule.

    Class 2 (StrongBuy): the StrongBuy target is touched before the stop within
    PRED_DAYS. Class 1 (Buy): the Buy target is touched first (and not StrongBuy).
    Class 0 (Hold): stop touched first, or no target touched.

    Barriers (no look-ahead — entry price AND entry ATR are taken at the entry row;
    only FUTURE highs/lows decide a touch):
      - mode 'atr'  : strong = entry + ATR_TARGET_MULT*atr; buy = entry + ATR_BUY_MULT*atr;
                      stop = entry - ATR_STOP_MULT*atr  (per-row volatility-scaled)
      - mode 'fixed': strong = entry*(1+TARGET_GAIN); buy = entry*(1+BUY_TARGET);
                      stop = entry*(1-STOP_LOSS)        (legacy fixed-percentage)

    A NaN entry ATR (warm-up rows) yields NaN barriers -> no touch -> Hold; those rows
    are dropped later via the FEATURE_COLS NaN filter, so they never train on a fake label.
    """
    n = len(closes)
    targets = np.zeros(n, dtype=int)
    valid_n = n - PRED_DAYS
    if valid_n <= 0:
        return targets

    entry_prices = closes[:valid_n]
    offsets = np.arange(1, PRED_DAYS + 1)
    future_idx = np.arange(valid_n)[:, None] + offsets[None, :]
    future_highs = highs[future_idx]
    future_lows = lows[future_idx]

    if mode == "atr":
        entry_atr = atr[:valid_n]
        stop_price = (entry_prices - _c.ATR_STOP_MULT * entry_atr)[:, None]
        target_strong = (entry_prices + _c.ATR_TARGET_MULT * entry_atr)[:, None]
        target_buy = (entry_prices + _c.ATR_BUY_MULT * entry_atr)[:, None]
    else:
        stop_price = entry_prices[:, None] * (1 - STOP_LOSS)
        target_strong = entry_prices[:, None] * (1 + TARGET_GAIN)
        target_buy = entry_prices[:, None] * (1 + BUY_TARGET)

    stop_mask = future_lows <= stop_price
    strong_mask = future_highs >= target_strong
    buy_mask = future_highs >= target_buy

    sentinel = PRED_DAYS + 1
    first_stop = np.where(stop_mask.any(axis=1), stop_mask.argmax(axis=1), sentinel)
    first_strong = np.where(strong_mask.any(axis=1), strong_mask.argmax(axis=1), sentinel)
    first_buy = np.where(buy_mask.any(axis=1), buy_mask.argmax(axis=1), sentinel)

    strong_first = first_strong < first_stop
    buy_first = (first_buy < first_stop) & (~strong_first)

    targets[:valid_n][strong_first] = 2
    targets[:valid_n][buy_first] = 1
    return targets


def prepare_features(df, is_training=True):
    """
    Creates tabular features + Sniper 3-class target for each row.

    The 3-class triple-barrier target is computed by ``_compute_targets`` and depends
    on ``common.LABEL_MODE`` (see ``core/config.py``):
      - 'atr' (default): barriers scale with per-row ATR-14 (ATR_TARGET_MULT / ATR_BUY_MULT
        / ATR_STOP_MULT) — volatility-adjusted so the class distribution stays learnable.
      - 'fixed' (legacy): Class 2 = +15% before -5%, Class 1 = +10% before -5%, within 20
        trading days; Class 0 = stop-first or no target hit.
    """
    # Minimum rows required: training needs SMA240 warm-up (~260 rows),
    # prediction is more lenient (~120 rows). Values come from core/config.py.
    min_rows = MIN_TRAIN_ROWS if is_training else MIN_PREDICT_ROWS
    if df.empty or len(df) < min_rows:
        return pd.DataFrame(), pd.Series()
    
    df = df.copy()
    
    # Ensure macd_hist and vol_ma20 are present for V2 factor calculation
    if 'macd' in df.columns and 'macd_signal' in df.columns:
        df['macd_hist'] = df['macd'] - df['macd_signal']
    if 'vol_ma20' not in df.columns and 'volume' in df.columns:
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
    
    # --- Ensure required base indicators are present ---
    required_base = ['rsi', 'macd', 'macd_signal', 'sma_20', 'sma_60', 'sma_120', 'sma_240', 'atr', 'k', 'd', 'bb_width', 'bb_percent']
    if any(col not in df.columns for col in required_base):
        from core.indicators_v2 import compute_v4_indicators
        df = compute_v4_indicators(df)
        
    # Double check after calculation
    for col in required_base:
        if col not in df.columns:
            return pd.DataFrame(), pd.Series()
            
    # --- Add Rise Scores (Vectorized V2) ---
    from core.indicators_v2 import calculate_trend_factors, calculate_momentum_factors, calculate_volatility_factors
    from core.rise_score_v2 import calculate_rise_score_v2
    df = calculate_trend_factors(df)
    df = calculate_momentum_factors(df)
    df = calculate_volatility_factors(df)
    df = calculate_rise_score_v2(df)
    
    # --- Derived Features (Normalized) ---
    close = df['close'].replace(0, np.nan)
    df['macd_rel'] = df['macd'] / close
    df['macd_hist_rel'] = (df['macd'] - df['macd_signal']) / close
    
    df['sma_diff'] = (df['sma_20'] - df['sma_60']) / df['sma_60'].replace(0, np.nan)
    df['price_vs_sma20'] = (df['close'] - df['sma_20']) / df['sma_20'].replace(0, np.nan)
    df['price_vs_sma60'] = (df['close'] - df['sma_60']) / df['sma_60'].replace(0, np.nan)
    
    # Slopes (5-day relative change)
    df['sma20_slope'] = df['sma_20'].pct_change(5)
    df['sma60_slope'] = df['sma_60'].pct_change(5)
    
    df['return_1d'] = df['close'].pct_change(1)
    df['return_5d'] = df['close'].pct_change(5)
    df['return_10d'] = df['close'].pct_change(10)
    
    vol_ma = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / vol_ma.replace(0, np.nan)
    
    # ATR (normalized)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(14).mean()
    df['atr_norm'] = atr / close
    
    df['kd_diff'] = df['k'] - df['d']
    
    # Compatibility Mappings for older models (if any)
    for col in FEATURE_COLS:
        if col not in df.columns:
            # Simple fallback if v2 columns are missing but v1 exist or vice-versa
            if '_v2' in col:
                old_col = col.replace('_v2', '')
                if old_col in df.columns:
                    df[col] = df[old_col]
            else:
                new_col = col + '_v2'
                if new_col in df.columns:
                    df[col] = df[new_col]
                    
    # --- SNIPER TARGET (MULTI-LABEL) ---
    # Triple-barrier labels; barrier mode (atr / fixed) read dynamically from config
    # so it is togglable and reversible. See _compute_targets for the rule.
    closes = df['close'].to_numpy(dtype=float)
    highs = df['high'].to_numpy(dtype=float)
    lows = df['low'].to_numpy(dtype=float)
    atr_arr = df['atr'].to_numpy(dtype=float) if 'atr' in df.columns else np.full(len(df), np.nan)
    df['target'] = _compute_targets(closes, highs, lows, atr_arr, _c.LABEL_MODE)
    
    # Keep feature vector aligned with FEATURE_COLS and sanitize missing values.
    # IMPORTANT: for training data we only forward-fill to avoid pulling values
    # from future rows into early indicator warm-up periods.
    df[FEATURE_COLS] = df[FEATURE_COLS].replace([np.inf, -np.inf], np.nan)
    if is_training:
        df[FEATURE_COLS] = df[FEATURE_COLS].ffill()
    # Prediction fills nothing. It used to `ffill().bfill()`: the bfill could never reach the
    # prediction row (it is the last one, so there is no later value to pull back) but the ffill
    # could, carrying YESTERDAY's indicator into today whenever today's is uncomputable. That is
    # a quieter version of the same defect -- a stale number is still a number the model reads as
    # an observation of today. Measured on the 92-ticker dev panel: 0 latest rows depend on it.
    # See docs/specs/unknown-is-not-zero-ml-features.md (AC1, amended).

    # Prediction only needs features, but we MUST NOT drop the last PRED_DAYS if is_training=False
    if is_training:
        df_clean = df.dropna(subset=['target'])
        if len(df_clean) > PRED_DAYS:
            df_clean = df_clean.iloc[:-PRED_DAYS]
    else:
        df_clean = df

    df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
    if is_training:
        # Drop warmup rows where long-period indicators (SMA240 etc.) are still NaN
        # after ffill. These rows pre-date the first valid indicator value and would
        # otherwise be filled with 0, biasing the model with fake "zero" features.
        # This line is load-bearing: it is what keeps the training panel clean, and
        # test_unknown_is_not_zero.py fails if it is removed.
        df_clean = df_clean.dropna(subset=FEATURE_COLS)
    # Prediction deliberately keeps NaN/inf. An uncomputable feature must reach
    # predict_prob() so it can refuse; a 0 here would be a specific, plausible, wrong
    # claim about the stock rather than a blank. There used to be an unconditional
    # `.fillna(0)` on this line -- it was a no-op for training (the dropna above already
    # removed those rows) and the entire defect for prediction.
    
    if df_clean.empty:
        return pd.DataFrame(), pd.Series()
    return df_clean[FEATURE_COLS], df_clean['target']

def class_prevalence(y) -> dict:
    """Share of each class in a label series — the base rate a precision must be read against."""
    if y is None or len(y) == 0:
        return {'hold': 0.0, 'buy': 0.0, 'strong': 0.0}
    return {
        'hold': float((y == 0).mean()),
        'buy': float((y == 1).mean()),
        'strong': float((y == 2).mean()),
    }


def lift_over_prevalence(precision, prevalence):
    """precision / base rate. 1.0 means no better than guessing at the class prevalence.

    Returns None — never a sentinel — when the class is absent from the split being scored:
    there is no base rate to divide by, so there is no honest number to report.
    """
    if prevalence is None or prevalence <= 0:
        return None
    return round(float(precision) / float(prevalence), 4)


class InsufficientPanelHistory(Exception):
    """The panel cannot support a clean date-based embargo.

    Raised instead of silently shrinking the embargo, because `oos_metrics` is published on
    /transparency — a contaminated number is worse than an absent model.
    """


def chronological_split(df_all, pred_days=PRED_DAYS, test_fraction=0.2):
    """Split a cross-sectional panel by DATE, embargoing `pred_days` TRADING DAYS.

    An embargo is a statement about time, not about rows. On a stacked panel one calendar day
    contributes N rows (N = tickers), so an `iloc[:split_idx - pred_days]` embargo removes
    `pred_days / N` days — at 92 tickers, about 0.2 of a day against a 20-day label horizon.
    The two are only equivalent when N == 1, which is why the defect survived: on a
    single-ticker frame the row arithmetic was accidentally correct.

    `df_all` must carry a `date` column and be sorted by it. Trading days come from the panel's
    own sorted unique dates — no external holiday calendar, and no assumption that every ticker
    trades every day.

    Returns `(train_mask, test_mask, meta)` where `meta` carries `cut_date`, `embargo_date`,
    `gap_dates` (distinct panel dates strictly between the last train date and the first test
    date, inclusive of the boundary handling in AC2) and `cv_gap` (the sample-count gap to hand
    to `TimeSeriesSplit`, scaled by the widest date in the training split).

    Raises `InsufficientPanelHistory` when a clean split is impossible.
    """
    if 'date' not in df_all.columns:
        raise InsufficientPanelHistory(
            "panel has no 'date' column, so a date-based embargo cannot be computed"
        )

    dates = pd.to_datetime(df_all['date'])
    if getattr(dates.dt, 'tz', None) is not None:
        # Comparing tz-aware against the tz-naive values derived below raises a TypeError that
        # would escape this function's own exception type. Normalise to UTC-naive instead.
        dates = dates.dt.tz_convert('UTC').dt.tz_localize(None)
    if dates.isna().any():
        # train_and_save only attaches `date` to frames that carry one, so a mixed batch yields
        # NaT. Those rows would silently vanish from BOTH splits while `gap_dates` still reported
        # a healthy embargo -- exactly the kind of quiet wrongness this spec exists to remove.
        raise InsufficientPanelHistory(
            f"{int(dates.isna().sum())} of {len(dates)} rows have no usable date; refusing to "
            "split a partially dated panel"
        )
    unique_dates = np.sort(dates.unique())
    if len(unique_dates) < pred_days + 2:
        raise InsufficientPanelHistory(
            f"panel spans {len(unique_dates)} distinct dates; a {pred_days}-day embargo plus a "
            f"non-empty train and test split needs at least {pred_days + 2}"
        )

    split_idx = int(len(df_all) * (1.0 - test_fraction))
    cut_date = dates.iloc[min(split_idx, len(df_all) - 1)]

    cut_pos = int(np.searchsorted(unique_dates, np.datetime64(cut_date)))
    if cut_pos - pred_days < 1:
        raise InsufficientPanelHistory(
            f"only {cut_pos} distinct dates precede the split date {pd.Timestamp(cut_date).date()}; "
            f"a {pred_days}-day embargo would leave no training data"
        )
    embargo_date = unique_dates[cut_pos - pred_days]

    train_mask = (dates < embargo_date).to_numpy()
    test_mask = (dates >= cut_date).to_numpy()
    if not train_mask.any() or not test_mask.any():
        raise InsufficientPanelHistory(
            f"date-based split produced {int(train_mask.sum())} train and {int(test_mask.sum())} "
            f"test rows; the panel is too short for a clean holdout"
        )

    # Distinct panel dates separating the two sides. AC2's invariant.
    gap_dates = int(
        np.searchsorted(unique_dates, np.datetime64(cut_date))
        - np.searchsorted(unique_dates, np.datetime64(dates[train_mask].max()))
    )

    # TimeSeriesSplit counts `gap` in SAMPLES, so scale by the widest date in the train split.
    # The max (not the mean) is the only choice that GUARANTEES the gap spans >= pred_days
    # distinct dates on an uneven panel, where tickers do not all trade every day.
    train_counts = dates[train_mask].value_counts()
    max_rows_per_date = int(train_counts.max()) if not train_counts.empty else 1
    cv_gap = pred_days * max_rows_per_date

    meta = {
        'cut_date': pd.Timestamp(cut_date),
        'embargo_date': pd.Timestamp(embargo_date),
        'gap_dates': gap_dates,
        'max_rows_per_date': max_rows_per_date,
        'cv_gap': cv_gap,
        'n_train': int(train_mask.sum()),
        'n_test': int(test_mask.sum()),
        # Rows are not time. The cut is taken at a row position, so on a panel whose ticker count
        # grows over time a "20% of rows" test window can span far fewer than 20% of the dates.
        'n_train_dates': int(dates[train_mask].nunique()),
        'n_test_dates': int(dates[test_mask].nunique()),
    }
    return train_mask, test_mask, meta


def train_and_save(all_dfs):
    """Train and persist the ensemble. Returns True on success, False if training was refused.

    A caller MUST check the return value: an honest abort (no data, or a panel that cannot
    support a clean embargo) is indistinguishable from success if it is ignored.
    """
    print("=" * 60)
    print("SNIPER AI - Training (Hardened with Out-of-Sample Split)")
    print("=" * 60)
    
    # 1. Collect and Sort Data Chronologically to prevent leakage
    data_list = []
    for df in all_dfs:
        X, y = prepare_features(df)
        if not X.empty:
            df_feat = X.copy()
            df_feat['target'] = y
            # We assume 'date' is needed for sorting, but prepare_features stripped it.
            # Let's ensure 'date' survives if possible or use index
            if 'date' in df.columns:
                df_feat['date'] = df.loc[df_feat.index, 'date']
            data_list.append(df_feat)
    
    if not data_list:
        logger.error("Aborting training: no valid training data found.")
        return False
    
    df_all = pd.concat(data_list)
    if 'date' in df_all.columns:
        df_all = df_all.sort_values('date')
        X_all = df_all[FEATURE_COLS]
        y_all = df_all['target']
    else:
        X_all = df_all[FEATURE_COLS]
        y_all = df_all['target']

    X_all = X_all.replace([np.inf, -np.inf], np.nan).fillna(0)

    # 2. Chronological Split (Final Evaluation set with temporal embargo).
    # Measured in TRADING DAYS from the panel's own calendar — see chronological_split().
    try:
        train_mask, test_mask, split_meta = chronological_split(df_all, PRED_DAYS)
    except InsufficientPanelHistory as exc:
        logger.error("Aborting training: %s.", exc)
        logger.error(
            "Refusing to shrink the embargo - a contaminated oos_metrics is worse than no model."
        )
        return False

    X_train_full = X_all[train_mask]
    y_train_full = y_all[train_mask]
    X_test = X_all[test_mask]
    y_test = y_all[test_mask]

    print(
        f"Embargo: train ends before {split_meta['embargo_date'].date()}, test starts "
        f"{split_meta['cut_date'].date()} ({split_meta['gap_dates']} trading days apart)."
    )

    win_rate_2 = (y_train_full == 2).mean() if not y_train_full.empty else 0.0
    win_rate_1 = (y_train_full == 1).mean() if not y_train_full.empty else 0.0
    win_rate_0 = (y_train_full == 0).mean() if not y_train_full.empty else 1.0
    
    print(f"Total samples: {len(X_all)} (Train: {len(X_train_full)}, Test: {len(X_test)})")
    print(f"Class Dist (train split): StrongBuy(2): {win_rate_2:.1%}, Buy(1): {win_rate_1:.1%}, Hold(0): {win_rate_0:.1%}")
    
    # Calculate weights on training set only
    class_weights = {
        0: 1.0 / (win_rate_0 if win_rate_0 > 0 else 1),
        1: 1.0 / (win_rate_1 if win_rate_1 > 0 else 1),
        2: 2.0 / (win_rate_2 if win_rate_2 > 0 else 1)
    }
    total_w = sum(class_weights.values())
    class_weights = {k: v/total_w * 3 for k, v in class_weights.items()}
    train_weights = y_train_full.map(class_weights)
    
    print("\nTraining Ensemble (GB + RF + MLP) with TimeSeries Cross-Validation on Train Set...")
    
    # Cross Validation on Training part. TimeSeriesSplit's `gap` counts SAMPLES, not days, so it
    # is scaled by the widest date in the train split (see chronological_split()).
    # This CV is DIAGNOSTIC ONLY: each fold's classifier is fit, its accuracy printed, and then
    # discarded. It does not touch the shipped model or oos_metrics. So when the scaled gap makes
    # folds infeasible we degrade the diagnostic (fewer folds, or none) instead of aborting the
    # run -- the guarantee that matters, the holdout embargo, is already enforced above and is
    # unaffected. Aborting here would conflate a nice-to-have with the guarantee, and would strand
    # small panels (the shipped demo fixture among them) with no model at all.
    cv_gap = split_meta['cv_gap']
    cv_folds = []
    cv_splits_used = 0
    for n_splits in (3, 2):
        try:
            cv_folds = list(TimeSeriesSplit(n_splits=n_splits, gap=cv_gap).split(X_train_full))
            cv_splits_used = n_splits
            break
        except ValueError:
            continue
    if not cv_folds:
        logger.warning(
            "Skipping CV diagnostics: %s training rows cannot host 2 folds with a %s-sample gap. "
            "The holdout embargo (%s trading days) is unaffected.",
            len(X_train_full), cv_gap, split_meta['gap_dates'],
        )
    elif cv_splits_used < 3:
        logger.warning("CV diagnostics reduced to %s folds to keep the %s-sample gap intact.",
                       cv_splits_used, cv_gap)
    for fold, (t_idx, v_idx) in enumerate(cv_folds):
        X_t, X_v = X_train_full.iloc[t_idx], X_train_full.iloc[v_idx]
        y_t, y_v = y_train_full.iloc[t_idx], y_train_full.iloc[v_idx]
        w_t = train_weights.iloc[t_idx]
        
        # HistGradientBoosting automatically uses all available OpenMP threads
        clf_gb_cv = HistGradientBoostingClassifier(max_iter=100, max_depth=4, learning_rate=0.05, random_state=42)
        clf_gb_cv.fit(X_t, y_t, sample_weight=w_t)
        print(f"Fold {fold+1} Validation Accuracy: {clf_gb_cv.score(X_v, y_v):.2f}")

    print("\nTraining final ensemble on train split and evaluating on holdout test split...")

    clf_gb = HistGradientBoostingClassifier(max_iter=100, max_depth=4, learning_rate=0.05, random_state=42)
    clf_gb.fit(X_train_full, y_train_full, sample_weight=train_weights)

    clf_rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight=class_weights, n_jobs=-1)
    clf_rf.fit(X_train_full, y_train_full)

    # Oversampling for MLP training to handle class imbalance (as MLPClassifier doesn't support sample_weight)
    rng = np.random.default_rng(42)
    if not y_train_full.empty:
        weights_norm = train_weights.to_numpy() / train_weights.sum()
        resampled_indices = rng.choice(len(X_train_full), size=len(X_train_full), replace=True, p=weights_norm)
        X_train_mlp = X_train_full.iloc[resampled_indices]
        y_train_mlp = y_train_full.iloc[resampled_indices]
    else:
        X_train_mlp, y_train_mlp = X_train_full, y_train_full

    mlp_base = MLPClassifier(hidden_layer_sizes=(128, 64), activation='relu', max_iter=1000, early_stopping=False, random_state=42)
    clf_mlp = make_pipeline(StandardScaler(), mlp_base)
    clf_mlp.fit(X_train_mlp, y_train_mlp)

    print("\n" + "-"*30)
    print("FINAL EVALUATION (Out-of-Sample Results, Equal-Weight Ensemble)")
    gb_proba = clf_gb.predict_proba(X_test)
    rf_proba = clf_rf.predict_proba(X_test)
    mlp_proba = clf_mlp.predict_proba(X_test)
    ensemble_pred = np.argmax((gb_proba + rf_proba + mlp_proba) / 3.0, axis=1)
    report = classification_report(y_test, ensemble_pred, labels=[0, 1, 2], target_names=['Hold', 'Buy', 'StrongBuy'], zero_division=0)
    print(report)

    oos_accuracy = accuracy_score(y_test, ensemble_pred)
    oos_precision_2 = precision_score(y_test, ensemble_pred, labels=[2], average='macro', zero_division=0)
    oos_recall_2 = recall_score(y_test, ensemble_pred, labels=[2], average='macro', zero_division=0)
    oos_f1_2 = f1_score(y_test, ensemble_pred, labels=[2], average='macro', zero_division=0)
    oos_precision_1 = precision_score(y_test, ensemble_pred, labels=[1], average='macro', zero_division=0)
    oos_recall_1 = recall_score(y_test, ensemble_pred, labels=[1], average='macro', zero_division=0)

    # Precision is unreadable without its denominator. 0.35 against a 14% base rate is a real edge;
    # against a 35% base rate it is worse than guessing. The stored class_distribution is the TRAIN
    # split, so it was never the right denominator -- record the TEST prevalence and report lift.
    test_prevalence = class_prevalence(y_test)
    oos_lift_2 = lift_over_prevalence(oos_precision_2, test_prevalence['strong'])
    oos_lift_1 = lift_over_prevalence(oos_precision_1, test_prevalence['buy'])
    print(
        f"Test-split prevalence: Hold {test_prevalence['hold']:.1%}, "
        f"Buy {test_prevalence['buy']:.1%}, StrongBuy {test_prevalence['strong']:.1%}"
    )
    print(
        f"Lift over base rate: StrongBuy {oos_lift_2}, Buy {oos_lift_1} "
        "(1.0 = no better than guessing at the base rate)"
    )
    print("-"*30)

    # Retrain final deployable model on all data with same weighting logic
    full_win_rate_2 = (y_all == 2).mean()
    full_win_rate_1 = (y_all == 1).mean()
    full_win_rate_0 = (y_all == 0).mean()
    full_class_weights = {
        0: 1.0 / (full_win_rate_0 if full_win_rate_0 > 0 else 1),
        1: 1.0 / (full_win_rate_1 if full_win_rate_1 > 0 else 1),
        2: 2.0 / (full_win_rate_2 if full_win_rate_2 > 0 else 1)
    }
    total_w_all = sum(full_class_weights.values())
    full_class_weights = {k: v/total_w_all * 3 for k, v in full_class_weights.items()}
    full_weights = y_all.map(full_class_weights)

    clf_gb_final = HistGradientBoostingClassifier(max_iter=100, max_depth=4, learning_rate=0.05, random_state=42)
    clf_gb_final.fit(X_all, y_all, sample_weight=full_weights)

    clf_rf_final = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight=full_class_weights, n_jobs=-1)
    clf_rf_final.fit(X_all, y_all)

    # Oversampling for final MLP model training (no sample_weight support in MLPClassifier)
    if not y_all.empty:
        full_weights_norm = full_weights.to_numpy() / full_weights.sum()
        resampled_indices_all = rng.choice(len(X_all), size=len(X_all), replace=True, p=full_weights_norm)
        X_all_mlp = X_all.iloc[resampled_indices_all]
        y_all_mlp = y_all.iloc[resampled_indices_all]
    else:
        X_all_mlp, y_all_mlp = X_all, y_all

    mlp_final_base = MLPClassifier(hidden_layer_sizes=(128, 64), activation='relu', max_iter=1000, early_stopping=False, random_state=42)
    clf_mlp_final = make_pipeline(StandardScaler(), mlp_final_base)
    clf_mlp_final.fit(X_all_mlp, y_all_mlp)

    ensemble_model = {'gb': clf_gb_final, 'rf': clf_rf_final, 'mlp': clf_mlp_final}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    version_tag = f"v4.{timestamp}"
    
    print("\nTop 10 Important Features:")
    # HistGradientBoosting doesn't implement feature_importances_, we use RF's instead
    importances = clf_rf_final.feature_importances_
    feature_importance = dict(zip(FEATURE_COLS, importances.tolist()))
    sorted_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    
    for feat, imp in list(sorted_importance.items())[:10]:
        print(f"  {feat}: {imp:.4f}")
        
    model_metadata = {
        'version': version_tag, 
        'trained_at': datetime.now().isoformat(), 
        'ensemble': ensemble_model, 
        'features': FEATURE_COLS,
        'feature_importance': sorted_importance
    }
    
    base_dir = os.path.dirname(MODEL_PATH)
    if base_dir and not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
    name_part, ext_part = os.path.splitext(os.path.basename(MODEL_PATH))
    versioned_path = os.path.join(base_dir, f"{name_part}_{timestamp}{ext_part}")
    joblib.dump(model_metadata, versioned_path)
    # Write SHA256 checksum sidecar for integrity verification (H1)
    # Use atomic write (mkstemp + os.replace) so a mid-write crash never leaves
    # a truncated .sha256 that would permanently block loading this model.
    model_bytes = open(versioned_path, 'rb').read()
    sha256 = hashlib.sha256(model_bytes).hexdigest()
    import tempfile as _tempfile2
    _sha_fd, _sha_tmp = _tempfile2.mkstemp(dir=base_dir, suffix='.tmp')
    with os.fdopen(_sha_fd, 'w') as _f:
        _f.write(sha256)
    os.replace(_sha_tmp, versioned_path + '.sha256')
    # Write HMAC-SHA256 signature sidecar if MODEL_SIGNING_KEY is configured (L1)
    if _cfg.MODEL_SIGNING_KEY:
        sig = _hmac.new(_cfg.MODEL_SIGNING_KEY.encode(), model_bytes, hashlib.sha256).hexdigest()
        _sig_fd, _sig_tmp = _tempfile2.mkstemp(dir=base_dir, suffix='.tmp')
        with os.fdopen(_sig_fd, 'w') as _f:
            _f.write(sig)
        os.replace(_sig_tmp, versioned_path + '.sig')
    # Activate MODEL_PATH: update sidecars first, then the model binary.
    # Order rationale: if the .pkl copy is interrupted, the sha256 will mismatch
    # the partial file — predictor refuses to load and degrades to 0.0 (safe).
    # Copying .pkl to a temp file then os.replace avoids writing directly to
    # MODEL_PATH (which would corrupt it if interrupted mid-copy).
    if _cfg.MODEL_SIGNING_KEY:
        _asig_fd, _asig_tmp = _tempfile2.mkstemp(dir=base_dir, suffix='.tmp')
        os.close(_asig_fd)
        shutil.copy2(versioned_path + '.sig', _asig_tmp)
        os.replace(_asig_tmp, MODEL_PATH + '.sig')
    _asha_fd, _asha_tmp = _tempfile2.mkstemp(dir=base_dir, suffix='.tmp')
    os.close(_asha_fd)
    shutil.copy2(versioned_path + '.sha256', _asha_tmp)
    os.replace(_asha_tmp, MODEL_PATH + '.sha256')
    _apkl_fd, _apkl_tmp = _tempfile2.mkstemp(dir=base_dir, suffix='.tmp')
    os.close(_apkl_fd)
    shutil.copy2(versioned_path, _apkl_tmp)
    os.replace(_apkl_tmp, MODEL_PATH)

    # This benchmark is IN-SAMPLE and no choice of window fixes that. The final ensemble is
    # refit on every row, and training rows run to T-PRED_DAYS with labels resolving on prices
    # through T -- so the model has seen price information through T, and any window ending
    # before T sits inside it. Moving days_ago 30 -> 40 would have buried the window MORE
    # deeply while changing what win_rate / avg_return mean against every older entry, so the
    # window stays where it was and the entry records the truth instead. A genuinely
    # out-of-sample rotation score needs an as-of model per window: backlog #3.
    BENCHMARK_HOLDING_DAYS = 20
    benchmark_days_ago = 30
    print(f"\n[Benchmark] Running post-training benchmark backtest ({benchmark_days_ago} days back, IN-SAMPLE)...")
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from backend.backtest import run_time_machine
        bt_result = run_time_machine(days_ago=benchmark_days_ago, limit=20,
                                     holding_days=BENCHMARK_HOLDING_DAYS)
        bt_summary = bt_result.get('summary', {})
        pf = bt_summary.get('profit_factor', None)
        # run_time_machine RETURNS error dicts rather than raising for several conditions
        # (bad args, no stock list, "No stocks met requirements"), and those responses carry
        # no summary at all. Reading a missing profit_factor as "no losing trades" would
        # recreate D2 inside the very field added to fix it.
        if bt_result.get('error') or 'profit_factor' not in bt_summary:
            status = 'failed'
            pf = None
        elif pf is None:
            status = 'no_losing_trades'   # a genuinely flawless run: gains, zero losses
        else:
            status = 'ok'
        backtest_score = {
            'profit_factor': pf,
            'status': status,
            'error': bt_result.get('error') if status == 'failed' else None,
            'settlement': CURRENT_SETTLEMENT,
            'days_ago': benchmark_days_ago,
            'holding_days': BENCHMARK_HOLDING_DAYS,
            # The scored window lies inside the training data -- see the comment above. This
            # is a relative yardstick between models, not a measure of live skill.
            'in_sample': True,
            'win_rate': round(bt_summary.get('win_rate', 0), 3),
            'sniper_hit_rate': round(bt_summary.get('sniper_hit_rate', 0), 3),
            'avg_return': round(bt_summary.get('avg_return', 0), 4),
        }
    except Exception as e:
        print(f"[WARNING] Backtest scoring failed: {e}")
        backtest_score = {
            'profit_factor': None,
            'status': 'failed',
            'error': str(e)[:200],
            'settlement': CURRENT_SETTLEMENT,
            'days_ago': benchmark_days_ago,
            'holding_days': BENCHMARK_HOLDING_DAYS,
            'in_sample': True,
            'win_rate': 0, 'sniper_hit_rate': 0, 'avg_return': 0,
        }

    # History Log
    history_path = os.path.join(base_dir, "models_history.json")
    history_entry = {
        "timestamp": timestamp,
        "version": version_tag,
        "samples": len(X_all),
        "train_samples": len(X_train_full),
        "test_samples": len(X_test),
        "class_distribution": {
            "hold": round(win_rate_0, 3),
            "buy": round(win_rate_1, 3),
            "strong": round(win_rate_2, 3)
        },
        # An entry WITHOUT `embargo` predates the date-based split and its oos_metrics are
        # contaminated (the old row-based embargo separated train from test by ~0 trading days).
        # Absence of this key is therefore a reliable "pre-fix" marker for anything downstream
        # that needs to badge or exclude those numbers.
        # The metrics below were measured on the 80%-SPLIT ensemble; the artifact this entry names
        # is a full-data refit. Refitting on everything is standard practice, but attributing the
        # holdout score to the shipped model is not -- so the scope is stated rather than implied.
        # Entries WITHOUT this key predate 2026-09-02.
        "oos_metrics_scope": "split_model",
        "test_class_distribution": {
            "hold": round(test_prevalence['hold'], 3),
            "buy": round(test_prevalence['buy'], 3),
            "strong": round(test_prevalence['strong'], 3),
        },
        "embargo": {
            "days": split_meta['gap_dates'],
            "basis": "trading_days",
            "cut_date": str(split_meta['cut_date'].date()),
            "test_dates": split_meta['n_test_dates'],
            "train_dates": split_meta['n_train_dates'],
        },
        "oos_metrics": {
            "accuracy": round(oos_accuracy, 4),
            "precision_strong": round(oos_precision_2, 4),
            "recall_strong": round(oos_recall_2, 4),
            "f1_strong": round(oos_f1_2, 4),
            "precision_buy": round(oos_precision_1, 4),
            "recall_buy": round(oos_recall_1, 4),
            # precision / test-split prevalence. 1.0 means no better than the base rate.
            "lift_strong": oos_lift_2,
            "lift_buy": oos_lift_1,
        },
        "backtest_30d": backtest_score,
        "feature_importance_top5": dict(list(sorted_importance.items())[:5]),
    }
    history = []
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f: history = json.load(f)
        except Exception:
            pass
    history.append(history_entry)
    import tempfile as _tempfile
    _dir = os.path.dirname(history_path)
    _fd, _tmp = _tempfile.mkstemp(dir=_dir, suffix='.tmp')
    try:
        with os.fdopen(_fd, 'w') as _f:
            json.dump(history[-50:], _f, indent=2)
        os.replace(_tmp, history_path)
    except Exception:
        try:
            os.unlink(_tmp)
        except OSError:
            pass
        raise
    
    # Rotation. This selects files for IRREVERSIBLE deletion, so it only ever compares entries
    # measured the same way: a profit factor recorded under the pre-2026-09-02 settlement rule
    # is not comparable to one recorded after it, and ranking them together could delete a
    # genuinely better old model for having been measured with a different ruler.
    to_delete, protected = select_for_deletion(
        history, keep=MAX_SAVED_MODELS, protected_versions={version_tag}
    )
    # Delete ONLY what was selected. The previous shape -- glob every .pkl and remove anything
    # not in a keep-set -- silently expired the protection: `history` is truncated to the last
    # 50 entries, so a protected file eventually fell out of the keep-set and was removed by
    # the glob with no comparability check and no log line. An allow-list cannot do that.
    delete_timestamps = timestamps_to_delete(
        history, keep=MAX_SAVED_MODELS, protected_versions={version_tag}, fresh_timestamp=timestamp
    )
    if protected:
        print(
            f"[Rotation] Kept {len(protected)} model(s) that could not be compared "
            "(different or missing settlement marker, or no usable profit factor). The store "
            f"may exceed MAX_SAVED_MODELS={MAX_SAVED_MODELS} as a result -- that is deliberate. "
            "Remove one explicitly with: python backend/manage_models.py delete <version>"
        )

    try:
        active_realpath = os.path.realpath(MODEL_PATH)
    except Exception:
        active_realpath = None

    _SIDECAR_EXTS = ('.sha256', '.sig')
    for ts_part in sorted(delete_timestamps):
        fpath = os.path.join(base_dir, f"{name_part}_{ts_part}{ext_part}")
        if not os.path.exists(fpath):
            continue
        try:
            if active_realpath and os.path.realpath(fpath) == active_realpath:
                continue  # never delete the active model file
            os.remove(fpath)
            for sidecar_ext in _SIDECAR_EXTS:
                sidecar = fpath + sidecar_ext
                if os.path.exists(sidecar):
                    os.remove(sidecar)
        except Exception:
            pass

    print(f"Model trained and saved as {version_tag}")
    return True
