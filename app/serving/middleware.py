"""
Defines middleware for the FastAPI application.
"""
import uuid
import time
from fastapi import Request
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def request_tracking_middleware(request: Request, call_next):
    """
    Intercepts HTTP requests to inject correlation IDs and track latency.
    Emits structured logs for telemetry.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    
    # Store request_id in state so it can be passed to the Inference Layer
    request.state.request_id = request_id
    
    logger.info(f"Incoming Request [{request_id}] - {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    latency = (time.perf_counter() - start_time) * 1000
    logger.info(f"Completed Request [{request_id}] - Status {response.status_code} in {latency:.2f}ms")
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(latency)
    
    return response
