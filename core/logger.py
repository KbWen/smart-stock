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
    Placeholder for sending alerts (Slack, Discord, Email).
    Triggered by ERROR or CRITICAL logs.
    """
    alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"🔔 [{level}] {alert_time}: {message}"
    
    # Log the alert sending attempt
    default_logger.info(f"Triggering Alert: {formatted_msg}")
    
    # TODO: Implement actual Hook calls here
    # Example: requests.post(WEBHOOK_URL, json={"text": formatted_msg})
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
