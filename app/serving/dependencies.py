"""
FastAPI Dependency Injection for the Serving Layer.
Manages the lifecycle of heavy ML registries and predictors.
"""
from typing import Dict
from threading import Lock

from app.training.artifacts import LocalArtifactStore
from app.inference.validator import RequestValidator
from app.inference.predictor import ModelPredictor

# ---------------------------------------------------------
# SINGLETONS
# These objects are heavy and maintain disk caches/locks.
# They are initialized exactly once at application startup.
# ---------------------------------------------------------
_artifact_store = LocalArtifactStore()
_validator = RequestValidator()

def get_cached_predictor(alias: str = "default") -> ModelPredictor:
    from app.inference.exceptions import InferenceError
    engine = get_prediction_engine()
    model_id, version = engine.routing_registry.get(alias, (None, None))
    if not model_id:
        # fallback to default
        model_id = engine.default_alias
    
    if not model_id:
        raise InferenceError(f"No active model alias found for {alias}.")
        
    predictor = engine.predictors.get(model_id)
    if not predictor:
        raise InferenceError(f"Predictor for {model_id} not loaded.")
    return predictor

from app.inference.engine import PredictionEngine

# ---------------------------------------------------------
# GLOBAL PREDICTION ENGINE
# Centralizes model loading, routing, and batching logic.
# ---------------------------------------------------------
_prediction_engine = PredictionEngine(artifact_store=_artifact_store)

def get_prediction_engine() -> PredictionEngine:
    """Dependency injector for the unified prediction engine."""
    return _prediction_engine
