import os

# Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "storage.db"))
DB_TIMEOUT = float(os.getenv("DB_TIMEOUT", 30.0))

# AI Model
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(BASE_DIR, "model_sniper.pkl"))
PRED_DAYS = int(os.getenv("PRED_DAYS", 20))
TARGET_GAIN = float(os.getenv("TARGET_GAIN", 0.15))
STOP_LOSS = float(os.getenv("STOP_LOSS", 0.05))
BUY_TARGET = float(os.getenv("BUY_TARGET", 0.10))  # +10% for Class 1 (Buy)

# AI Backtest / Strategy
# IMPORTANT: These are the single source of truth for all strategy parameters.
# Training (trainer.py) and Backtest (backtest.py) MUST reference these values.
# DO NOT hardcode magic numbers elsewhere.
BACKTEST_AI_THRESHOLD = float(os.getenv("BACKTEST_AI_THRESHOLD", 0.35))
MIN_TRAIN_ROWS = int(os.getenv("MIN_TRAIN_ROWS", 260))
MIN_PREDICT_ROWS = int(os.getenv("MIN_PREDICT_ROWS", 120))

# System / Backend
# Auto-detect CPU count for concurrency but cap at a safe level for SQLite
CPU_COUNT = os.cpu_count() or 4
CONCURRENCY_WORKERS = int(os.getenv("CONCURRENCY_WORKERS", 5)) 
TRAINING_WORKERS = int(os.getenv("TRAINING_WORKERS", max(2, CPU_COUNT - 1)))
USE_GPU = os.getenv("USE_GPU", "auto").lower() in ("true", "1", "auto")
CACHE_DURATION = int(os.getenv("CACHE_DURATION", 3600))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Model Integrity
# Optional HMAC signing key for model files. If set, trainer signs .pkl on save
# and predictor verifies the signature before loading. Leave unset for local dev.
MODEL_SIGNING_KEY: str = os.getenv("MODEL_SIGNING_KEY", "")

# Rise Score Weights (Sum should be 1.0)
WEIGHT_TREND = float(os.getenv("WEIGHT_TREND", 0.40))
WEIGHT_MOMENTUM = float(os.getenv("WEIGHT_MOMENTUM", 0.30))
WEIGHT_VOLATILITY = float(os.getenv("WEIGHT_VOLATILITY", 0.30))

# Cache Paths
STOCK_LIST_CACHE = os.path.join(BASE_DIR, "stock_list_cache.json")
MARKET_HISTORY_PATH = os.path.join(BASE_DIR, "market_history.json")
MODELS_HISTORY_PATH = os.path.join(BASE_DIR, "models_history.json")
