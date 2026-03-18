from core import config

# ===== SNIPER STRATEGY PARAMETERS =====
# IMPORTANT: All strategy parameters flow from core/config.py.
# Training (trainer.py) and Backtest (backtest.py) MUST use these constants.
# DO NOT hardcode equivalent magic numbers in other files.
PRED_DAYS = config.PRED_DAYS       # Look-ahead window (max 20 trading days)
TARGET_GAIN = config.TARGET_GAIN   # +15% profit target
STOP_LOSS = config.STOP_LOSS       # -5% stop loss
BUY_TARGET = config.BUY_TARGET     # +10% buy target (Class 1)

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
