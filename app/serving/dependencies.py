"""
FastAPI Dependency Injection for the Serving Layer.
Manages the lifecycle of heavy ML registries and predictors.
"""
from typing import Dict
from threading import Lock

from app.training.artifacts import LocalArtifactStore
from app.training.registry import LocalModelRegistry
from app.inference.registry import InferenceModelRegistry
from app.inference.loader import RegistryModelLoader
from app.inference.validator import RequestValidator
from app.inference.predictor import ModelPredictor

# ---------------------------------------------------------
# SINGLETONS
# These objects are heavy and maintain disk caches/locks.
# They are initialized exactly once at application startup.
# ---------------------------------------------------------
_training_registry = LocalModelRegistry()
_artifact_store = LocalArtifactStore()
_loader = RegistryModelLoader(_training_registry, _artifact_store)
_validator = RequestValidator()
_inference_registry = InferenceModelRegistry()

# Note: In a real environment, a deployment script would populate 
# the InferenceModelRegistry here. For safety, we assume it starts empty 
# and gets hydrated elsewhere.

# ---------------------------------------------------------
# PREDICTOR CACHE
# Predictors load joblib binaries into memory. We strictly 
# cache them per alias/version to avoid MemoryLeaks or 
# CPU blocking during initialization.
# ---------------------------------------------------------
_predictor_cache: Dict[str, ModelPredictor] = {}
_cache_lock = Lock()

def get_inference_registry() -> InferenceModelRegistry:
    """Dependency injector for the alias registry."""
    return _inference_registry

def get_cached_predictor(alias: str = "default") -> ModelPredictor:
    """
    Dependency injector that safely resolves an alias and returns 
    a cached, memory-resident Predictor instance.
    """
    # 1. Resolve alias dynamically
    model_id, version = _inference_registry.resolve(alias)
    
    # 2. Check cache
    cache_key = f"{alias}_{model_id}_{version}"
    
    with _cache_lock:
        if cache_key not in _predictor_cache:
            # 3. Initialize lazily (heavy operation, happens once)
            _predictor_cache[cache_key] = ModelPredictor(
                model_id=model_id,
                version=version,
                loader=_loader,
                validator=_validator,
                training_registry=_training_registry,
                model_alias=alias
            )
            
    return _predictor_cache[cache_key]
