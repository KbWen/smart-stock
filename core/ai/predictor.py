import numpy as np
import pandas as pd
import joblib
import os
import json
import logging
from typing import Optional
from core.ai.common import FEATURE_COLS, MODEL_PATH

# Global variable to track the currently loaded model version
CURRENT_MODEL_VERSION = "unknown"
_model_cache = {}
logger = logging.getLogger(__name__)

def get_model_version():
    """Returns the current model version string, loading it if necessary."""
    global CURRENT_MODEL_VERSION
    if CURRENT_MODEL_VERSION == "unknown":
        if os.path.exists(MODEL_PATH):
            try:
                import joblib
                model_data_all = joblib.load(MODEL_PATH)
                if isinstance(model_data_all, dict) and 'version' in model_data_all:
                    CURRENT_MODEL_VERSION = model_data_all['version']
                else:
                    CURRENT_MODEL_VERSION = "legacy"
            except Exception:
                pass
    return CURRENT_MODEL_VERSION


def list_available_models():
    """Returns a list of all trained model versions found in the history log."""
    history_path = os.path.join(os.path.dirname(MODEL_PATH), "models_history.json")
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def predict_prob(df, version: Optional[str] = None):
    """
    Predicts buy probability. Supports specific version loading with caching.
    """
    global CURRENT_MODEL_VERSION
    
    # 1. Determine Path
    target_path = MODEL_PATH
    if version and version != "latest":
        # Extract timestamp: supports both 'v4.20260213_2240' and '20260213_2240'
        ts = version.split('.')[-1] if '.' in version else version
        base_dir = os.path.dirname(MODEL_PATH)
        name_part = os.path.splitext(os.path.basename(MODEL_PATH))[0]
        
        # Consistent filename: model_sniper_20260213_2240.pkl
        versioned_filename = f"{name_part}_{ts}.pkl"
        target_path = os.path.join(base_dir, versioned_filename)
        
        if not os.path.exists(target_path):
            logger.warning("Version %s not found at %s. Falling back to default.", version, target_path)
            target_path = MODEL_PATH

    # 2. Load Model (with Cache)
    if target_path in _model_cache:
        model_data_all = _model_cache[target_path]
    else:
        if not os.path.exists(target_path):
            return None
        try:
            model_data_all = joblib.load(target_path)
            _model_cache[target_path] = model_data_all
        except Exception:
            return None

    # 3. Extract Model components
    if isinstance(model_data_all, dict) and 'ensemble' in model_data_all:
        CURRENT_MODEL_VERSION = model_data_all.get('version', 'unknown')
        model_data = model_data_all['ensemble']
    else:
        CURRENT_MODEL_VERSION = "legacy"
        model_data = model_data_all
    
    if df.empty or len(df) < 60:
        return None
    
    # --- Feature Extraction ---
    try:
        from core.ai.trainer import prepare_features
        X_df, _ = prepare_features(df, is_training=False)
        
        if X_df.empty:
            return None
            
        # Take only the latest row for prediction
        X_single = X_df.iloc[[-1]] 
        X_single = X_single.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        if isinstance(model_data, dict):
            # Ensemble Voting
            probs = {}
            total_prob = 0
            count = 0
            for name, clf in model_data.items():
                # --- Robust Feature Mapping ---
                # Use model's own feature requirements if available (sklearn 1.0+)
                if hasattr(clf, "feature_names_in_"):
                    X_clf = X_single.reindex(columns=clf.feature_names_in_, fill_value=0)
                else:
                    X_clf = X_single
                
                p_array = clf.predict_proba(X_clf)[0]
                
                # 3-Class System Breakdown
                sb_prob = float(p_array[2]) if len(p_array) > 2 else 0.0
                b_prob = float(p_array[1]) if len(p_array) > 1 else 0.0
                h_prob = float(p_array[0]) if len(p_array) > 0 else 0.0
                
                win_p = sb_prob + b_prob
                probs[name] = {
                    "win_prob": win_p,
                    "strong_buy_prob": sb_prob,
                    "buy_prob": b_prob,
                    "hold_prob": h_prob
                }
                total_prob += win_p
                count += 1
            return {"prob": total_prob / count if count > 0 else 0, "details": probs}
        else:
            # Single model (Legacy support)
            clf = model_data
            if hasattr(clf, "feature_names_in_"):
                 X_clf = X_single.reindex(columns=clf.feature_names_in_, fill_value=0)
            else:
                 X_clf = X_single
            p_vec = clf.predict_proba(X_clf)[0]
            win_p = float(np.sum(p_vec[1:])) if len(p_vec) > 1 else 0.0
            sb_prob = float(p_vec[2]) if len(p_vec) > 2 else 0.0
            b_prob = float(p_vec[1]) if len(p_vec) > 1 else 0.0
            h_prob = float(p_vec[0]) if len(p_vec) > 0 else 0.0
            return {"prob": win_p, "details": {"legacy": {
                "win_prob": win_p,
                "strong_buy_prob": sb_prob,
                "buy_prob": b_prob,
                "hold_prob": h_prob
            }}}
    except Exception as e:
        import traceback
        error_msg = f"Prediction Error: {e}\n{traceback.format_exc()}"
        logger.exception("%s", error_msg)
        return {"prob": 0.0, "error": error_msg}
