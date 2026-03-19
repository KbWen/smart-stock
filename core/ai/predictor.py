import hashlib
import numpy as np
import pandas as pd
import joblib
import os
import json
import logging
import threading
from collections import OrderedDict
from typing import Optional
from core.ai.common import FEATURE_COLS, MODEL_PATH, MAX_PREDICTION_CACHE_SIZE, VERSION_RE, validate_version_string

# ---------------------------------------------------------------------------
# Thread-safe model version state
# ---------------------------------------------------------------------------
_version_lock = threading.Lock()
_current_model_version = "unknown"

# LRU model cache capped at _MAX_CACHED_MODELS entries
_cache_lock = threading.Lock()
_model_cache: OrderedDict = OrderedDict()
_MAX_CACHED_MODELS = MAX_PREDICTION_CACHE_SIZE

logger = logging.getLogger(__name__)


def _read_sidecar(path: str) -> Optional[str]:
    """Read a sidecar file, returning its stripped content or None if absent/unreadable."""
    try:
        return open(path, 'r', encoding='utf-8').read().strip()
    except FileNotFoundError:
        return None  # no sidecar — legacy model, allow load
    except Exception as exc:
        logger.warning("Cannot read sidecar %s: %s", path, exc)
        return None  # unreadable — allow load


def _verify_checksum(path: str, model_bytes: Optional[bytes] = None) -> bool:
    """Return True if SHA256 sidecar matches the file, or if no sidecar exists (legacy).

    Pass model_bytes to skip re-reading the file (avoids double I/O when HMAC is active).
    """
    expected = _read_sidecar(path + '.sha256')
    if expected is None:
        return True  # no sidecar — legacy model, allow load
    try:
        if model_bytes is None:
            model_bytes = open(path, 'rb').read()
        actual = hashlib.sha256(model_bytes).hexdigest()
    except Exception as exc:
        logger.warning("Cannot hash model file %s: %s", path, exc)
        return False
    if actual != expected:
        logger.warning("Checksum mismatch for %s (actual: %s)", path, actual)
        return False
    return True


def _set_model_version(version: str) -> None:
    """Thread-safe write to current model version."""
    global _current_model_version
    with _version_lock:
        _current_model_version = version


def _cache_get(path: str):
    """Return cached model data and bump to MRU position, or None if absent."""
    with _cache_lock:
        if path in _model_cache:
            _model_cache.move_to_end(path)
            return _model_cache[path]
    return None


def _cache_put(path: str, model_data) -> None:
    """Insert model data into LRU cache, evicting oldest entry when full."""
    with _cache_lock:
        _model_cache[path] = model_data
        _model_cache.move_to_end(path)
        while len(_model_cache) > _MAX_CACHED_MODELS:
            _model_cache.popitem(last=False)


def get_model_version() -> str:
    """Returns the current model version string, loading it if necessary."""
    with _version_lock:
        if _current_model_version != "unknown":
            return _current_model_version
    # Load outside the lock — joblib.load is expensive
    if os.path.exists(MODEL_PATH):
        try:
            if not _verify_checksum(MODEL_PATH):
                return _current_model_version  # checksum mismatch — skip load
            model_data_all = joblib.load(MODEL_PATH)
            if isinstance(model_data_all, dict) and 'version' in model_data_all:
                _set_model_version(model_data_all['version'])
            else:
                _set_model_version("legacy")
        except Exception:
            pass
    with _version_lock:
        return _current_model_version


def list_available_models():
    """Returns a list of all trained model versions found in the history log."""
    history_path = os.path.join(os.path.dirname(MODEL_PATH), "models_history.json")
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def predict_prob(df, version: Optional[str] = None):
    """
    Predicts buy probability. Supports specific version loading with caching.
    Thread-safe: model version is updated via _set_model_version (lock-protected).
    """
    # 1. Determine Path
    target_path = MODEL_PATH
    if version and version != "latest":
        if not validate_version_string(version):
            logger.warning("Rejected invalid version string: %r", version)
            return None
        # Extract timestamp: supports 'v4.20260213_2240' → '20260213_2240'
        ts = version.split('.')[-1]
        base_dir = os.path.dirname(MODEL_PATH)
        name_part = os.path.splitext(os.path.basename(MODEL_PATH))[0]

        versioned_filename = f"{name_part}_{ts}.pkl"
        target_path = os.path.join(base_dir, versioned_filename)

        if not os.path.exists(target_path):
            logger.warning("Version %s not found at %s. Falling back to default.", version, target_path)
            target_path = MODEL_PATH

    # 2. Load Model (with LRU Cache)
    model_data_all = _cache_get(target_path)
    if model_data_all is None:
        if not os.path.exists(target_path):
            return None
        try:
            if not _verify_checksum(target_path):
                return None  # SHA256 mismatch — refuse to load
            model_data_all = joblib.load(target_path)
            _cache_put(target_path, model_data_all)
        except Exception:
            return None

    # 3. Extract Model components + update version (thread-safe)
    if isinstance(model_data_all, dict) and 'ensemble' in model_data_all:
        _set_model_version(model_data_all.get('version', 'unknown'))
        model_data = model_data_all['ensemble']
    else:
        _set_model_version("legacy")
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
                # Robust Feature Mapping (sklearn 1.0+ feature_names_in_)
                if hasattr(clf, "feature_names_in_"):
                    X_clf = X_single.reindex(columns=clf.feature_names_in_, fill_value=0)
                else:
                    X_clf = X_single

                p_array = clf.predict_proba(X_clf)[0]

                # 3-Class System Breakdown
                sb_prob = float(p_array[2]) if len(p_array) > 2 else 0.0
                b_prob  = float(p_array[1]) if len(p_array) > 1 else 0.0
                h_prob  = float(p_array[0]) if len(p_array) > 0 else 0.0

                win_p = sb_prob + b_prob
                probs[name] = {
                    "win_prob": win_p,
                    "strong_buy_prob": sb_prob,
                    "buy_prob": b_prob,
                    "hold_prob": h_prob,
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
            p_vec  = clf.predict_proba(X_clf)[0]
            win_p  = float(np.sum(p_vec[1:])) if len(p_vec) > 1 else 0.0
            sb_prob = float(p_vec[2]) if len(p_vec) > 2 else 0.0
            b_prob  = float(p_vec[1]) if len(p_vec) > 1 else 0.0
            h_prob  = float(p_vec[0]) if len(p_vec) > 0 else 0.0
            return {"prob": win_p, "details": {"legacy": {
                "win_prob": win_p,
                "strong_buy_prob": sb_prob,
                "buy_prob": b_prob,
                "hold_prob": h_prob,
            }}}
    except Exception as e:
        import traceback
        error_msg = f"Prediction Error: {e}\n{traceback.format_exc()}"
        logger.exception("%s", error_msg)
        return {"prob": 0.0, "error": error_msg}
