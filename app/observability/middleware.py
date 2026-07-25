import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_active
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        # Simplify endpoint path to avoid high cardinality
        endpoint = request.url.path

        # Don't track metrics for /metrics itself to avoid noise
        if endpoint == "/metrics":
            return await call_next(request)

        http_requests_active.inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time
            http_requests_active.dec()

            # Normalize path variables if needed here, but for now we just record it
            # A more robust solution might use route names, but we keep it simple
            http_requests_total.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
