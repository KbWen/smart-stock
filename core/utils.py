from datetime import datetime
from core.logger import setup_logger

logger = setup_logger(__name__)

def safe_float(value, default=0.0):
    """Safely convert a value to float, returns default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def parse_date(date_str):
    """Safely parse date string to datetime object."""
    if not date_str:
        return None
    try:
        if isinstance(date_str, datetime):
            return date_str
        return datetime.strptime(date_str, '%Y-%m-%d')
    except Exception as e:
        logger.debug(f"Failed to parse date {date_str}: {e}")
        return None

def format_percentage(value, decimals=1):
    """Format a float as a percentage string."""
    return f"{(safe_float(value) * 100):.{decimals}f}%"
