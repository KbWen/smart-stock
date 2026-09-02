import math
import re
from core import config

# ===== SNIPER STRATEGY PARAMETERS =====
# All strategy constants flow from core/config.py. TARGET_GAIN / STOP_LOSS / BUY_TARGET
# are the FIXED-mode (LABEL_MODE='fixed') training-label barriers; in the default 'atr'
# mode the trainer uses ATR_*_MULT below instead. The backtest EXIT is user-tunable and
# does NOT read these (see backend/backtest.py). Do not hardcode equivalent numbers elsewhere.
PRED_DAYS = config.PRED_DAYS       # Look-ahead window (max 20 trading days)
TARGET_GAIN = config.TARGET_GAIN   # +15% StrongBuy target (fixed-mode label only)
STOP_LOSS = config.STOP_LOSS       # -5% stop loss (fixed-mode label only)
BUY_TARGET = config.BUY_TARGET     # +10% Buy target (fixed-mode label, Class 1)

# Label mode + ATR-scaled barrier multipliers (single source of truth = config.py).
# trainer.py reads these dynamically (module attributes) so the labeling mode is
# togglable and the label-distribution analysis can compare modes.
LABEL_MODE = config.LABEL_MODE
ATR_TARGET_MULT = config.ATR_TARGET_MULT
ATR_BUY_MULT = config.ATR_BUY_MULT
ATR_STOP_MULT = config.ATR_STOP_MULT

# Win = price hits +15% BEFORE it hits -5% within 20 days
# This is a 3:1 Risk/Reward ratio

MODEL_PATH = config.MODEL_PATH

# Data Length Requirements
MIN_TRAIN_ROWS = config.MIN_TRAIN_ROWS    # Minimum rows for training (needs SMA240)
MIN_PREDICT_ROWS = config.MIN_PREDICT_ROWS  # Minimum rows for prediction (more lenient)

# Backtest Filtering
BACKTEST_AI_THRESHOLD = config.BACKTEST_AI_THRESHOLD

# Model Lifecycle
MAX_SAVED_MODELS = 5  # Max versioned .pkl files retained; shared by trainer.py rotation and manage_models.py prune
MAX_PREDICTION_CACHE_SIZE = 3  # LRU cap for in-process model cache in predictor.py


# Version string format: v<N>.<YYYYMMDD>_<HHMM>  e.g. v4.20260319_0800
VERSION_RE = re.compile(r'^v\d+\.\d{8}_\d{4}$')


def validate_version_string(version: str) -> bool:
    """Return True if version matches the canonical format (prevents path traversal)."""
    return bool(VERSION_RE.match(version))


# The fill model the benchmark backtest currently uses. Entries recorded before 2026-09-02 booked
# a winning trade at the session HIGH and a loser at the session LOW, which on the same seed and
# window moved profit factor 0.74 -> 0.80. A profit factor measured under one settlement rule is
# not comparable to one measured under another, and rotation DELETES files based on that comparison.
CURRENT_SETTLEMENT = "achievable_fill"


def is_rankable(h: dict, settlement: str = CURRENT_SETTLEMENT) -> bool:
    """True when this entry's profit factor may be compared with others'.

    Requires a matching settlement marker AND a finite profit factor. An entry that fails either
    test is NOT ranked last -- it is protected from automatic deletion. Sorting an unknown to the
    bottom is a silent decision to delete it, and the two things `profit_factor: None` used to mean
    (a flawless backtest with no losing trades, and a backtest that raised) are both unknowns, not
    failures.
    """
    bt = h.get('backtest_30d') or {}
    if bt.get('settlement') != settlement:
        return False
    pf = bt.get('profit_factor')
    if pf is None or isinstance(pf, bool):
        return False
    try:
        return math.isfinite(float(pf))
    except (TypeError, ValueError):
        return False


def profit_factor_sort_key(h: dict) -> float:
    """Sort key for RANKABLE model history entries, descending-friendly.

    Only meaningful for entries where ``is_rankable(h)`` is True -- callers must filter first.
    Unrankable entries have no position in this ordering by design; giving them one is what let a
    flawless backtest and a crashed one both sort below a model that lost money on every trade.
    """
    return float((h.get('backtest_30d') or {}).get('profit_factor'))


def select_for_deletion(history: list, keep: int, protected_versions=None) -> tuple:
    """Return ``(to_delete, protected)`` for a rotation/prune pass.

    The single rule this module exists to enforce: **an irreversible action requires a comparable
    measurement.** Only rankable entries compete for the ``keep`` slots; everything else is
    protected, even when its profit factor is the lowest present. The store growing past ``keep``
    is the correct outcome of refusing a bad comparison.
    """
    protected_versions = set(protected_versions or ())
    rankable = [h for h in history if is_rankable(h)]
    unrankable = [h for h in history if not is_rankable(h)]
    keepers = {id(h) for h in sorted(rankable, key=profit_factor_sort_key, reverse=True)[:keep]}
    to_delete = [
        h for h in rankable
        if id(h) not in keepers and h.get('version') not in protected_versions
    ]
    return to_delete, unrankable

# ===== FEATURE ENGINEERING =====
FEATURE_COLS = [
    'rsi', 'macd_rel', 'macd_hist_rel',
    'sma_diff', 'price_vs_sma20', 'price_vs_sma60',
    'dist_sma120', 'dist_sma240',
    'sma20_slope', 'sma60_slope', 'sma120_slope', 'sma240_slope',
    'return_1d', 'return_5d', 'return_10d',
    'vol_ratio', 'vol_trend_60d',
    'atr_norm',
    'bb_width', 'bb_percent',
    'k', 'd', 'kd_diff',
    'total_score_v2', 'trend_score_v2', 'momentum_score_v2', 'volatility_score_v2'
]
