import hashlib
import hmac as _hmac
import io
import numpy as np
import pandas as pd
import joblib
import os
import json
import logging
import threading
from collections import OrderedDict
from typing import Optional
from core.ai.common import FEATURE_COLS, MODEL_PATH, MAX_PREDICTION_CACHE_SIZE, VERSION_RE, validate_version_string, MIN_PREDICT_ROWS
from core import config as _cfg

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
        logger.warning("Checksum mismatch for %s — expected %s got %s", path, expected, actual)
        return False
    return True


def _verify_hmac(path: str, model_bytes: bytes) -> bool:
    """Verify HMAC-SHA256 signature if MODEL_SIGNING_KEY is set and a .sig sidecar exists.

    Returns True if signing is not configured, no sidecar exists, or signature matches.
    Returns False only on an explicit mismatch when a key is configured.
    """
    signing_key = _cfg.MODEL_SIGNING_KEY
    if not signing_key:
        return True  # signing not configured
    expected = _read_sidecar(path + '.sig')
    if expected is None:
        return True  # no sidecar — legacy model, allow load
    actual = _hmac.new(signing_key.encode(), model_bytes, hashlib.sha256).hexdigest()
    if not _hmac.compare_digest(actual, expected):
        logger.warning("HMAC signature mismatch for %s — possible tampering", path)
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
    """Returns the current model version string, loading it if necessary.

    Uses double-checked locking: first check inside lock (fast path), then load
    outside lock (expensive), then re-check inside lock before writing (prevents
    two threads from each doing a full joblib.load when both see 'unknown').
    """
    global _current_model_version
    with _version_lock:
        if _current_model_version != "unknown":
            return _current_model_version
    # Load outside the lock — joblib.load is expensive and must not block callers
    version_candidate = None
    try:
        model_bytes = open(MODEL_PATH, 'rb').read()
        if not _verify_checksum(MODEL_PATH, model_bytes):
            with _version_lock:
                return _current_model_version  # checksum mismatch — skip update
        model_data_all = joblib.load(io.BytesIO(model_bytes))
        version_candidate = model_data_all['version'] if isinstance(model_data_all, dict) and 'version' in model_data_all else "legacy"
    except FileNotFoundError:
        pass  # model not yet trained
    except Exception as exc:
        logger.warning("Failed to load model version from %s: %s", MODEL_PATH, exc)
    # Second check inside lock: only write if another thread hasn't already resolved it
    if version_candidate is not None:
        with _version_lock:
            if _current_model_version == "unknown":
                _current_model_version = version_candidate
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


def _metric(value) -> float:
    """Coerce a recorded metric to a float, treating None/invalid as 0.0."""
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def get_model_health() -> dict:
    """Assess the active model's usability from its recorded out-of-sample metrics.

    Cheap: reads the cached version string + models_history.json only (no model load).
    Returns {status, version, message}:
      - 'unavailable': model not loaded/trained, or no metrics recorded
      - 'degraded'   : one of three things is true, each with its own message because they are
                       different facts for a reader to act on --
                         (a) the entry has no `embargo` key, so its metrics predate the
                             date-based embargo and are contaminated by construction;
                         (b) StrongBuy lift is <= 1.0, i.e. the model is at or below the base
                             rate on the class the product acts on;
                         (c) zero buy-signal power (all buy/strong precision+recall are 0).
      - 'ok'         : otherwise
    `message` is an honest, user-facing zh-TW string for non-ok states ('' for ok).

    This function fails TOWARD disclosure: anything it cannot evaluate resolves to 'degraded' or
    'unavailable', never to 'ok'.
    """
    version = get_model_version()
    if not version or version == "unknown":
        return {
            "status": "unavailable",
            "version": version or "unknown",
            "message": "AI 模型尚未載入或尚未訓練，AI 機率暫時不可用。",
        }

    history = list_available_models()
    entry = next((h for h in history if h.get("version") == version), None)
    if entry is None and history:
        entry = history[-1]  # fall back to the latest recorded metrics
    metrics = (entry or {}).get("oos_metrics") or {}
    if not metrics:
        return {
            "status": "unavailable",
            "version": version,
            "message": "AI 模型缺少評估指標，AI 機率僅供參考。",
        }

    buy_signal_power = (
        _metric(metrics.get("precision_buy"))
        + _metric(metrics.get("recall_buy"))
        + _metric(metrics.get("precision_strong"))
        + _metric(metrics.get("recall_strong"))
    )
    if buy_signal_power <= 0:
        return {
            "status": "degraded",
            "version": version,
            "message": (
                "AI 模型對買訊的辨識力不足（買進/強買的準確率與召回率為 0）。"
                "AI 機率僅供參考，請勿單獨作為買賣依據。"
            ),
        }

    # An entry without an `embargo` block predates 2026-09-02, when the train/test embargo was
    # measured in pooled ROWS rather than trading days -- on the real panel that separated the two
    # sides by 0 days, so the metrics above were never out-of-sample. Do not present them as a
    # healthy model just because they look non-zero.
    if not (entry or {}).get("embargo"):
        return {
            "status": "degraded",
            "version": version,
            "message": (
                "此模型的評估指標是在舊的切分方式下產生的（訓練集與測試集實際上沒有隔離），"
                "數字並非真正的樣本外結果。重新訓練後才會有可信的指標；在那之前 AI 機率僅供參考。"
            ),
        }

    # Precision without its base rate is unreadable. A lift of 1.0 means the model is no better
    # than guessing at the class prevalence, so <= 1.0 is disclosed as degraded rather than shown
    # as a working model. Absent lift (older entry) does not trigger this branch -- the embargo
    # check above already caught those.
    # A post-embargo entry always carries lift_strong (trainer writes both together), so its
    # absence means a hand-edited or partially-written entry -- something we cannot evaluate.
    # The constraint is to fail TOWARD disclosure, so that resolves to degraded, not ok.
    lift_strong = metrics.get("lift_strong")
    if lift_strong is None:
        return {
            "status": "degraded",
            "version": version,
            "message": (
                "此模型缺少與基準比例的對照（提升倍數），無法判斷它是否真的優於隨機猜測。"
                "AI 機率僅供參考，請勿單獨作為買賣依據。"
            ),
        }
    if _metric(lift_strong) <= 1.0:
        return {
            "status": "degraded",
            "version": version,
            "message": (
                f"AI 模型在「強買」上的準確率並未優於基準比例（提升倍數 {_metric(lift_strong):.2f}×，"
                "1.0 代表與隨機猜測基準相同）。AI 機率僅供參考，請勿單獨作為買賣依據。"
            ),
        }

    return {"status": "ok", "version": version, "message": ""}


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
        try:
            # Read bytes once; reuse for checksum + optional HMAC + load (no double I/O)
            model_bytes = open(target_path, 'rb').read()
            if not _verify_checksum(target_path, model_bytes):
                return None  # SHA256 mismatch — refuse to load
            if not _verify_hmac(target_path, model_bytes):
                return None  # HMAC mismatch — refuse to load
            model_data_all = joblib.load(io.BytesIO(model_bytes))
            _cache_put(target_path, model_data_all)
        except FileNotFoundError:
            return None  # model not found or not yet trained
        except Exception as exc:
            logger.warning("Failed to load model from %s: %s", target_path, exc)
            return None

    # 3. Extract Model components + update version (thread-safe)
    if isinstance(model_data_all, dict) and 'ensemble' in model_data_all:
        _set_model_version(model_data_all.get('version', 'unknown'))
        model_data = model_data_all['ensemble']
    else:
        _set_model_version("legacy")
        model_data = model_data_all

    if df.empty or len(df) < MIN_PREDICT_ROWS:
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

                # Dynamic Class Mapping based on clf.classes_ to prevent index mismatch
                # Fallback to index-based breakdown if classes_ is not a real array (e.g. mocked classifiers)
                if hasattr(clf, "classes_") and isinstance(getattr(clf, "classes_", None), (list, np.ndarray, pd.Series)):
                    class_map = {val: idx for idx, val in enumerate(clf.classes_)}
                    h_prob = float(p_array[class_map[0]]) if 0 in class_map else 0.0
                    b_prob = float(p_array[class_map[1]]) if 1 in class_map else 0.0
                    sb_prob = float(p_array[class_map[2]]) if 2 in class_map else 0.0
                else:
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

            if hasattr(clf, "classes_") and isinstance(getattr(clf, "classes_", None), (list, np.ndarray, pd.Series)):
                class_map = {val: idx for idx, val in enumerate(clf.classes_)}
                h_prob = float(p_vec[class_map[0]]) if 0 in class_map else 0.0
                b_prob = float(p_vec[class_map[1]]) if 1 in class_map else 0.0
                sb_prob = float(p_vec[class_map[2]]) if 2 in class_map else 0.0
                win_p = b_prob + sb_prob
            else:
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
        # Prediction unavailable — return None (uniform with all other failure paths)
        # so a failure is never presented downstream as a genuine 0.0 probability.
        return None
