"""
Configures structured JSON logging globally.
Integrates context variables to automatically inject correlation IDs into every log statement.
"""
import contextvars
import logging
import json
from datetime import datetime, timezone

# Context variable to hold trace ID across async execution boundaries
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="system")


class StructuredJSONFormatter(logging.Formatter):
    """
    Overrides standard Python logging to emit 100% JSON logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
            "module": record.module
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_structured_logging() -> None:
    """
    Hijacks the root logger to strictly enforce JSON formatting platform-wide.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
