"""
Standardized logging infrastructure for FeatureFlow.

Ensures that logs are formatted consistently across modules and respect
the globally configured logging level.
"""
import logging
import sys
from typing import Optional

import os

_LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s"
_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Initializes and returns a standardized logger instance.

    Args:
        name: The namespace for the logger (typically __name__).
        level: Optional log level to override the global setting.

    Returns:
        A fully configured logging.Logger instance.
    """
    logger: logging.Logger = logging.getLogger(name)

    # Avoid attaching multiple handlers to the same logger during tests or reloading
    if logger.hasHandlers():
        return logger

    # Resolve active log level
    active_level_str: str = level or os.getenv("LOG_LEVEL", "INFO")
    active_level: int = getattr(logging, active_level_str.upper(), logging.INFO)
    logger.setLevel(active_level)

    # Attach standard console handler or JSON handler based on environment
    console_handler = logging.StreamHandler(sys.stdout)

    # Use JSON formatter in production
    is_prod = os.getenv("ENVIRONMENT", "").lower() == "production"
    if is_prod:
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "time": self.formatTime(record, _DATE_FORMAT),
                    "name": record.name,
                    "level": record.levelname,
                    "function": record.funcName,
                    "message": record.getMessage()
                }
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_record)

        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Disable propagation to avoid duplicate logs if root logger is also configured
    logger.propagate = False

    return logger
