import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import joblib
import os
import shutil
import json
import glob
from datetime import datetime
from core.ai.common import FEATURE_COLS, MODEL_PATH, PRED_DAYS, TARGET_GAIN, STOP_LOSS, BUY_TARGET, MIN_TRAIN_ROWS, MIN_PREDICT_ROWS, MAX_SAVED_MODELS, profit_factor_sort_key

def prepare_features(df, is_training=True):
    """
    Creates tabular features + Sniper 3-class target for each row.
    Class 2: hits +15% before -5% within 20 trading days.
    Class 1: hits +10% before -5% (and does not hit +15% first).
    Class 0: all other outcomes (stop first or no target hit).
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
    required_base = ['rsi', 'macd', 'macd_signal', 'sma_20', 'sma_60', 'k', 'd', 'bb_width', 'bb_percent']
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
    closes = df['close'].to_numpy(dtype=float)
    highs = df['high'].to_numpy(dtype=float)
    lows = df['low'].to_numpy(dtype=float)
    n = len(df)
    targets = np.zeros(n, dtype=int)

    valid_n = n - PRED_DAYS
    if valid_n > 0:
        entry_prices = closes[:valid_n]
        offsets = np.arange(1, PRED_DAYS + 1)
        future_idx = np.arange(valid_n)[:, None] + offsets[None, :]

        future_highs = highs[future_idx]
        future_lows = lows[future_idx]

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

    df['target'] = targets
    
    # Keep feature vector aligned with FEATURE_COLS and sanitize missing values.
    # IMPORTANT: for training data we only forward-fill to avoid pulling values
    # from future rows into early indicator warm-up periods.
    df[FEATURE_COLS] = df[FEATURE_COLS].replace([np.inf, -np.inf], np.nan)
    if is_training:
        df[FEATURE_COLS] = df[FEATURE_COLS].ffill()
    else:
        df[FEATURE_COLS] = df[FEATURE_COLS].ffill().bfill()

    # Prediction only needs features, but we MUST NOT drop the last PRED_DAYS if is_training=False
    if is_training:
        df_clean = df.dropna(subset=['target'])
        if len(df_clean) > PRED_DAYS:
            df_clean = df_clean.iloc[:-PRED_DAYS]
    else:
        df_clean = df

    df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
    df_clean[FEATURE_COLS] = df_clean[FEATURE_COLS].fillna(0)
    
    if df_clean.empty:
        return pd.DataFrame(), pd.Series()
    return df_clean[FEATURE_COLS], df_clean['target']

def train_and_save(all_dfs):
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
        print("No valid training data found.")
        return
    
    df_all = pd.concat(data_list)
    if 'date' in df_all.columns:
        df_all = df_all.sort_values('date')
        X_all = df_all[FEATURE_COLS]
        y_all = df_all['target']
    else:
        X_all = df_all[FEATURE_COLS]
        y_all = df_all['target']

    X_all = X_all.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # 2. Chronological Split (Final Evaluation set)
    split_idx = int(len(X_all) * 0.8)
    X_train_full, X_test = X_all.iloc[:split_idx], X_all.iloc[split_idx:]
    y_train_full, y_test = y_all.iloc[:split_idx], y_all.iloc[split_idx:]
    
    win_rate_2 = (y_train_full == 2).mean()
    win_rate_1 = (y_train_full == 1).mean()
    win_rate_0 = (y_train_full == 0).mean()
    
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
    
    # Cross Validation on Training part
    tscv = TimeSeriesSplit(n_splits=3)
    for fold, (t_idx, v_idx) in enumerate(tscv.split(X_train_full)):
        X_t, X_v = X_train_full.iloc[t_idx], X_train_full.iloc[v_idx]
        y_t, y_v = y_train_full.iloc[t_idx], y_train_full.iloc[v_idx]
        w_t = train_weights.iloc[t_idx]
        
        # HistGradientBoosting automatically uses all available OpenMP threads
        clf_gb_cv = HistGradientBoostingClassifier(max_iter=100, max_depth=4, learning_rate=0.05, random_state=42)
        clf_gb_cv.fit(X_t, y_t, sample_weight=w_t)
        y_pred = clf_gb_cv.predict(X_v)
        print(f"Fold {fold+1} Validation Accuracy: {clf_gb_cv.score(X_v, y_v):.2f}")

    print("\nTraining final ensemble on train split and evaluating on holdout test split...")

    clf_gb = HistGradientBoostingClassifier(max_iter=100, max_depth=4, learning_rate=0.05, random_state=42)
    clf_gb.fit(X_train_full, y_train_full, sample_weight=train_weights)

    clf_rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight=class_weights, n_jobs=-1)
    clf_rf.fit(X_train_full, y_train_full)

    mlp_base = MLPClassifier(hidden_layer_sizes=(128, 64), activation='relu', max_iter=1000, early_stopping=True, random_state=42)
    clf_mlp = make_pipeline(StandardScaler(), mlp_base)
    clf_mlp.fit(X_train_full, y_train_full, mlpclassifier__sample_weight=train_weights.to_numpy())

    print("\n" + "-"*30)
    print("FINAL EVALUATION (Out-of-Sample Results, Equal-Weight Ensemble)")
    gb_proba = clf_gb.predict_proba(X_test)
    rf_proba = clf_rf.predict_proba(X_test)
    mlp_proba = clf_mlp.predict_proba(X_test)
    ensemble_pred = np.argmax((gb_proba + rf_proba + mlp_proba) / 3.0, axis=1)
    report = classification_report(y_test, ensemble_pred, target_names=['Hold', 'Buy', 'StrongBuy'], zero_division=0)
    print(report)

    oos_accuracy = accuracy_score(y_test, ensemble_pred)
    oos_precision_2 = precision_score(y_test, ensemble_pred, labels=[2], average='macro', zero_division=0)
    oos_recall_2 = recall_score(y_test, ensemble_pred, labels=[2], average='macro', zero_division=0)
    oos_f1_2 = f1_score(y_test, ensemble_pred, labels=[2], average='macro', zero_division=0)
    oos_precision_1 = precision_score(y_test, ensemble_pred, labels=[1], average='macro', zero_division=0)
    oos_recall_1 = recall_score(y_test, ensemble_pred, labels=[1], average='macro', zero_division=0)
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

    mlp_final_base = MLPClassifier(hidden_layer_sizes=(128, 64), activation='relu', max_iter=1000, early_stopping=True, random_state=42)
    clf_mlp_final = make_pipeline(StandardScaler(), mlp_final_base)
    clf_mlp_final.fit(X_all, y_all, mlpclassifier__sample_weight=full_weights.to_numpy())

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
    name_part, ext_part = os.path.splitext(os.path.basename(MODEL_PATH))
    versioned_path = os.path.join(base_dir, f"{name_part}_{timestamp}{ext_part}")
    joblib.dump(model_metadata, versioned_path)
    shutil.copy(versioned_path, MODEL_PATH)

    print("\n📊 Running post-training benchmark backtest (30 days)...")
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from backend.backtest import run_time_machine
        bt_result = run_time_machine(days_ago=30, limit=20)
        bt_summary = bt_result.get('summary', {})
        backtest_score = {
            'profit_factor': bt_summary.get('profit_factor', 0),
            'win_rate': round(bt_summary.get('win_rate', 0), 3),
            'sniper_hit_rate': round(bt_summary.get('sniper_hit_rate', 0), 3),
            'avg_return': round(bt_summary.get('avg_return', 0), 4),
        }
    except Exception as e:
        print(f"⚠️ Backtest scoring failed: {e}")
        backtest_score = {'profit_factor': 0, 'win_rate': 0, 'sniper_hit_rate': 0, 'avg_return': 0}

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
        "oos_metrics": {
            "accuracy": round(oos_accuracy, 4),
            "precision_strong": round(oos_precision_2, 4),
            "recall_strong": round(oos_recall_2, 4),
            "f1_strong": round(oos_f1_2, 4),
            "precision_buy": round(oos_precision_1, 4),
            "recall_buy": round(oos_recall_1, 4),
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
    with open(history_path, 'w') as f: json.dump(history[-50:], f, indent=2)
    
    # Rotation: keep MAX_SAVED_MODELS best-performing models by profit_factor (AC1, AC2, AC4)
    keep_timestamps = {h['timestamp'] for h in sorted(history, key=profit_factor_sort_key, reverse=True)[:MAX_SAVED_MODELS]}
    keep_timestamps.add(timestamp)  # AC4: always protect freshly-trained model

    try:
        active_realpath = os.path.realpath(MODEL_PATH)
    except Exception:
        active_realpath = None

    for fpath in glob.glob(os.path.join(base_dir, f"{name_part}_*{ext_part}")):
        ts_part = os.path.basename(fpath)[len(name_part) + 1: -len(ext_part)]
        if ts_part in keep_timestamps:
            continue
        try:
            if active_realpath and os.path.realpath(fpath) == active_realpath:
                continue  # AC4: never delete the active model file
            os.remove(fpath)
        except Exception:
            pass

    print(f"Model trained and saved as {version_tag}")
