import pandas as pd
from typing import Dict, List, Any
from io import StringIO
import time
from datetime import datetime
import uuid

from app.utils.logger import get_logger
from app.inference.registry import InferenceModelRegistry
from app.inference.loader import RegistryModelLoader
from app.inference.predictor import ModelPredictor
from app.inference.exceptions import InferenceError, PredictionError
from app.inference.request import PredictionRequest
from app.inference.response import PredictionResponse
from app.inference.validator import RequestValidator
from app.training.artifacts import LocalArtifactStore
from app.training.registry import LocalModelRegistry
from app.training.metadata import ModelLifecycleState
from app.monitoring.audit import AuditLogger, AuditEvent

logger = get_logger(__name__)

class PredictionEngine:
    """
    Centralized Inference Service.
    Loads active models into memory, handles batching/CSV, routing, and fallbacks.
    """
    def __init__(self, training_registry: LocalModelRegistry, artifact_store: LocalArtifactStore):
        self.training_registry = training_registry
        self.artifact_store = artifact_store
        
        self.loader = RegistryModelLoader(self.training_registry, self.artifact_store)
        self.routing_registry = InferenceModelRegistry()
        self.validator = RequestValidator()
        
        # In-memory warmed predictors
        self.predictors: Dict[str, ModelPredictor] = {}
        
        # Engine stats for Management API
        self.stats = {
            "prediction_count": 0,
            "total_latency_ms": 0.0,
            "last_prediction_time": None
        }

    def start(self):
        """Warms up the engine by loading CHAMPION/CHALLENGER models into memory."""
        logger.info("Initializing Prediction Engine.")
        models = self.training_registry.list_models()
        
        champion_meta = None
        challenger_meta = None
        
        for mid in models:
            meta = self.training_registry.get(mid)
            if meta.lifecycle_state == ModelLifecycleState.CHAMPION:
                if not champion_meta or meta.training_timestamp > champion_meta.training_timestamp:
                    champion_meta = meta
            elif meta.lifecycle_state == ModelLifecycleState.CHALLENGER:
                if not challenger_meta or meta.training_timestamp > challenger_meta.training_timestamp:
                    challenger_meta = meta
                    
        active_models = [m for m in [champion_meta, challenger_meta] if m is not None]
                
        for meta in active_models:
            try:
                predictor = ModelPredictor(
                    model_id=meta.model_id,
                    version=meta.model_version,
                    loader=self.loader,
                    validator=self.validator,
                    training_registry=self.training_registry,
                    model_alias=meta.model_id
                )
                self.predictors[meta.model_id] = predictor
                self.routing_registry.set_alias(meta.model_id, meta.model_id, meta.model_version)
                AuditLogger.record(AuditEvent(event_name="MODEL_LOADED", component="PredictionEngine", severity="INFO", payload={"model_id": meta.model_id, "state": meta.lifecycle_state.value}))
            except Exception as e:
                logger.error(f"Failed to load model {meta.model_id}: {e}")
                
        from app.inference.routing import global_traffic_router
        global_traffic_router.configure(
            champion_id=champion_meta.model_id if champion_meta else None,
            challenger_id=challenger_meta.model_id if challenger_meta else None,
            champion_weight=1.0 # Default 100% to Champion initially
        )
        
        # Bind Default Alias to Champion
        if champion_meta:
            self.routing_registry.set_default(champion_meta.model_id, champion_meta.model_version)
        else:
            logger.warning("No CHAMPION model found during Prediction Engine startup.")

    def _execute_predict(self, request: PredictionRequest, alias: str = "default") -> PredictionResponse:
        """Core prediction logic with fallback mechanism."""
        try:
            from app.inference.routing import global_traffic_router
            
            # Dynamic A/B routing if "default" is used
            if alias == "default":
                selected_model_id = global_traffic_router.select_model()
                if not selected_model_id:
                    raise InferenceError("No champion or challenger models configured for traffic routing.")
                model_id = selected_model_id
            else:
                model_id, version = self.routing_registry.resolve(alias)
                
            predictor = self.predictors.get(model_id)
            
            if not predictor:
                raise InferenceError(f"Predictor for {model_id} is not loaded in memory.")
                
            AuditLogger.record(AuditEvent(event_name="PREDICTION_STARTED", component="PredictionEngine", severity="INFO", payload={"request_id": request.request_id}))
            
            response = predictor.predict(request)
            
            AuditLogger.record(AuditEvent(event_name="PREDICTION_FINISHED", component="PredictionEngine", severity="INFO", payload={"request_id": request.request_id, "latency_ms": response.latency_ms}))
            
            # Update stats
            self.stats["prediction_count"] += 1
            self.stats["total_latency_ms"] += response.latency_ms
            self.stats["last_prediction_time"] = datetime.utcnow().isoformat()
            
            return response
            
        except Exception as e:
            logger.error(f"Prediction failed on primary path: {e}")
            AuditLogger.record(AuditEvent(event_name="PREDICTION_FAILED", component="PredictionEngine", severity="ERROR", payload={"error": str(e), "request_id": request.request_id}))
            
            # Fallback logic: Use any other available loaded predictor
            fallback_predictor = None
            for pid, p in self.predictors.items():
                if pid != model_id:
                    fallback_predictor = p
                    break
                    
            if fallback_predictor:
                logger.warning(f"Initiating fallback to {fallback_predictor.model_id}")
                AuditLogger.record(AuditEvent(event_name="FALLBACK_ACTIVATED", component="PredictionEngine", severity="WARNING", payload={"fallback_model_id": fallback_predictor.model_id}))
                try:
                    response = fallback_predictor.predict(request)
                    self.stats["prediction_count"] += 1
                    return response
                except Exception as fallback_e:
                    raise PredictionError(f"Primary and Fallback predictions failed.") from fallback_e
                    
            raise PredictionError("Prediction failed and no fallback models are available.") from e

    def predict_single(self, features: Dict[str, Any], entity_id: str = None, alias: str = "default") -> PredictionResponse:
        req = PredictionRequest(request_id=str(uuid.uuid4()), entity_id=entity_id or "anon", features=features)
        return self._execute_predict(req, alias)

    def predict_batch(self, batch_features: List[Dict[str, Any]], alias: str = "default") -> List[PredictionResponse]:
        responses = []
        for features in batch_features:
            responses.append(self.predict_single(features, alias=alias))
        return responses

    def predict_csv(self, csv_data: str, alias: str = "default") -> List[PredictionResponse]:
        df = pd.read_csv(StringIO(csv_data))
        batch = df.to_dict(orient="records")
        return self.predict_batch(batch, alias=alias)
