"""
Serving Layer integration for observability.
"""
import uuid
import time
from fastapi import Request
from app.monitoring.logger import correlation_id_var
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def monitoring_middleware(request: Request, call_next):
    """
    Web interceptor to bind HTTP requests to the global telemetry context.
    """
    # 1. Generate/Extract Correlation ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # 2. Inject into ContextVar for internal tracking
    token = correlation_id_var.set(request_id)

    # Also attach to request state for legacy compatibility
    request.state.request_id = request_id

    start_time = time.perf_counter()

    try:
        response = await call_next(request)

        # 3. Compute Latency
        latency = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(latency)

        return response
    finally:
        # 4. Clean up ContextVar to prevent cross-request contamination
        correlation_id_var.reset(token)
