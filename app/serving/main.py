from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from app.serving.config import serving_config
from app.serving.api.v1.router import v1_router
from app.monitoring.middleware import monitoring_middleware
from app.serving.exceptions import (
    validation_error_handler,
    not_found_error_handler,
    service_unavailable_handler,
    internal_error_handler
)
from app.inference.exceptions import InputValidationError, ModelLoadError, InferenceError, PredictionError

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.storage.database import init_db
    import threading
    from app.data.discovery import DatasetDiscovery
    from app.serving.dependencies import _prediction_engine
    from app.cache import RedisClient

    # Initialize Database connection and create tables
    await init_db()
    
    # Initialize Redis Cloud connection pool
    redis_client = await RedisClient.get_instance()
    
    # Start Prediction Engine immediately to warm caches
    await _prediction_engine.start()
    
    def run_discovery():
        discovery = DatasetDiscovery()
        discovery.discover_datasets()
        
    import sys, os
    from app.config import settings
    if "pytest" not in sys.modules and not os.getenv("PYTEST_CURRENT_TEST") and settings.environment.lower() != "test":
        threading.Thread(target=run_discovery, daemon=True).start()
    yield
    # Cleanly disconnect from Redis on application shutdown
    await redis_client.disconnect()

def create_app() -> FastAPI:
    """
    Constructs the FastAPI application for deployment.
    """
    app = FastAPI(
        title=serving_config.title, 
        version=serving_config.api_version,
        description="FeatureFlow Online Inference API",
        lifespan=lifespan
    )
    
    # 1. Mount Middleware
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=monitoring_middleware)
    
    # 2. Register Centralized Exception Handlers
    app.add_exception_handler(InputValidationError, validation_error_handler)
    app.add_exception_handler(InferenceError, not_found_error_handler)
    app.add_exception_handler(ModelLoadError, service_unavailable_handler)
    app.add_exception_handler(PredictionError, internal_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
    
    # 3. Mount Routers
    app.include_router(v1_router, prefix=f"/api/{serving_config.api_version}")
    from app.serving.api.v1.endpoints import health, model_cache
    app.include_router(health.router, tags=["health"])
    app.include_router(model_cache.router, tags=["model_cache"])
    
    return app


# The standard ASGI entrypoint (e.g. `uvicorn app.serving.main:app`)
app = create_app()
