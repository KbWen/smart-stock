import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from core import config

# Ensure logs directory exists
LOGS_DIR = os.path.join(config.BASE_DIR, "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOG_FILE = os.path.join(LOGS_DIR, "app.log")

# Optional alert sink. Alerts are sent ONLY when this is configured — when it is
# unset (the default), alerting is a silent no-op. We do not claim to alert when
# there is no sink (honesty-first).
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

def setup_logger(name=__name__):
    """Sets up a logger with rotating file handler and console output."""
    logger = logging.getLogger(name)
    
    # Set level from config
    level_str = config.LOG_LEVEL.upper()
    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if not logger.handlers:
        # File Handler (Rotating: 10MB per file, keep 5)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger

# Singleton-like default logger
default_logger = setup_logger("sniper")

def send_alert(message, level="ERROR"):
    """
    Send an alert to the configured webhook (Slack/Discord/etc.) for ERROR or
    CRITICAL logs. No-op (and NOT logged) when ALERT_WEBHOOK_URL is unset — we
    do not imply an alert fired when no sink is configured. Best-effort:
    delivery failures are swallowed so alerting never breaks the logging path.
    """
    if not ALERT_WEBHOOK_URL:
        return

    alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"🔔 [{level}] {alert_time}: {message}"
    try:
        import requests
        requests.post(ALERT_WEBHOOK_URL, json={"text": formatted_msg}, timeout=3)
    except Exception:
        # Never let alert delivery crash the caller's logging call.
        pass

class AlertHandler(logging.Handler):
    """Custom handler to trigger alerts on high-level logs."""
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            send_alert(self.format(record), level=record.levelname)

# Add AlertHandler to default_logger
alert_handler = AlertHandler()
alert_handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
default_logger.addHandler(alert_handler)
