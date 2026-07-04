"""
Lightweight Aspect-Oriented decorators for unobtrusive observability.
Strictly forbidden from modifying inputs, outputs, or catching exceptions.
"""
import time
from functools import wraps
from typing import Any, Callable

from app.monitoring.metrics import MetricsRegistry
from app.monitoring.logger import correlation_id_var
from app.monitoring.audit import AuditLogger, AuditEvent

def track_latency(component_name: str):
    """Measures the execution time of a function."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                latency = (time.perf_counter() - start_time) * 1000
                MetricsRegistry.histogram(f"{component_name}_latency_ms", latency)
        return wrapper
    return decorator

def count_invocations(component_name: str):
    """Tracks how often a function is called, and splits success vs failure."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            MetricsRegistry.increment(f"{component_name}_invocations_total")
            try:
                return func(*args, **kwargs)
            except Exception:
                MetricsRegistry.increment(f"{component_name}_errors_total")
                raise
        return wrapper
    return decorator

def audit_event(event_name: str, component: str):
    """Automatically emits an immutable audit event upon success or failure."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                AuditLogger.record(AuditEvent(
                    event_name=f"{event_name}Completed",
                    component=component,
                    severity="INFO",
                    payload={"status": "success"},
                    correlation_id=correlation_id_var.get()
                ))
                return result
            except Exception as e:
                AuditLogger.record(AuditEvent(
                    event_name=f"{event_name}Failed",
                    component=component,
                    severity="ERROR",
                    payload={"error": str(e)},
                    correlation_id=correlation_id_var.get()
                ))
                raise
        return wrapper
    return decorator
