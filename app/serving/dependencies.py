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

def get_inference_registry() -> InferenceModelRegistry:
    return _inference_registry

def get_cached_predictor(alias: str = "default") -> ModelPredictor:
    # Legacy wrapper for backward compatibility
    from app.inference.exceptions import InferenceError
    engine = get_prediction_engine()
    model_id, version = engine.routing_registry.resolve(alias)
    predictor = engine.predictors.get(model_id)
    if not predictor:
        raise InferenceError(f"Predictor for alias {alias} not found.")
    return predictor

from app.inference.engine import PredictionEngine

# ---------------------------------------------------------
# GLOBAL PREDICTION ENGINE
# Centralizes model loading, routing, and batching logic.
# ---------------------------------------------------------
_prediction_engine = PredictionEngine(
    training_registry=_training_registry,
    artifact_store=_artifact_store
)

def get_prediction_engine() -> PredictionEngine:
    """Dependency injector for the unified prediction engine."""
    return _prediction_engine
