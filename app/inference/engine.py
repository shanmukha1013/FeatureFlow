import pandas as pd
from typing import Dict, List, Any
from io import StringIO
import time
from datetime import datetime
import uuid

from app.utils.logger import get_logger
from app.inference.registry import InferenceModelRegistry
from app.inference.predictor import ModelPredictor
from app.inference.exceptions import InferenceError, PredictionError
from app.inference.request import PredictionRequest
from app.inference.response import PredictionResponse
from app.inference.validator import RequestValidator
from app.training.artifacts import LocalArtifactStore
from app.monitoring.audit import AuditLogger, AuditEvent
from app.storage.database import AsyncSessionLocal
from app.storage.repositories.core import ChampionModelRepository, ModelRepository

logger = get_logger(__name__)

class PredictionEngine:
    """
    Centralized Inference Service.
    Loads active models into memory, handles batching/CSV, routing, and fallbacks.
    """
    def __init__(self, artifact_store: LocalArtifactStore):
        self.artifact_store = artifact_store
        
        self.routing_registry = InferenceModelRegistry()
        self.validator = RequestValidator()
        
        self.predictors: Dict[str, ModelPredictor] = {}
        
        self.stats = {
            "prediction_count": 0,
            "total_latency_ms": 0.0,
            "last_prediction_time": None
        }

    async def start(self):
        """Warms up the engine by loading CHAMPION models from DB into memory."""
        logger.info("Initializing Prediction Engine.")
        
        champion_meta = None
        
        async with AsyncSessionLocal() as session:
            champion_repo = ChampionModelRepository(session)
            model_repo = ModelRepository(session)
            
            # For simplicity, we just load the first champion model
            # In a real system we'd load champions per dataset
            # Here we just load all champions
            from sqlalchemy.future import select
            from app.storage.models import ChampionModel
            result = await session.execute(select(ChampionModel))
            champions = result.scalars().all()
            
            active_models = []
            for c in champions:
                model = await model_repo.get(c.model_id)
                if model:
                    active_models.append(model)
                    if not champion_meta:
                        champion_meta = model
                        
            # Actually, `ModelPredictor` needs the loaded ML artifact.
            for meta in active_models:
                try:
                    # In a real system, ModelPredictor would use ArtifactStore to load from artifact_uri
                    import joblib
                    # Assume meta.artifact_uri is the local path (e.g. from artifact_store.save)
                    # For now we'll mock the predictor loading to just use the artifact_uri if possible
                    # or we pass artifact_store to predictor
                    predictor = ModelPredictor(
                        model_id=meta.id,
                        version=f"v{meta.version}",
                        loader=None, # We'll refactor predictor next
                        validator=self.validator,
                        training_registry=None,
                        model_alias=meta.id
                    )
                    # Override predictor's model with artifact store load
                    # Predictor constructor currently expects `loader.load(model_id)`
                    # We'll fix `ModelPredictor` next
                    predictor.model = self.artifact_store.load(meta.id, f"v{meta.version}")
                    
                    self.predictors[meta.id] = predictor
                    self.routing_registry.set_alias(meta.id, meta.id, f"v{meta.version}")
                    
                    # Also need feature names and metadata
                    from app.training.metadata import ModelMetadata
                    # Construct a dummy metadata just for Predictor usage
                    predictor.metadata = ModelMetadata(
                        model_id=meta.id,
                        model_version=f"v{meta.version}",
                        algorithm=meta.name,
                        target_column="target",
                        feature_version="1.0.0",
                        dataset_version=meta.dataset.name if meta.dataset else "unknown",
                        hyperparameters=meta.hyperparameters,
                        metrics=meta.metrics,
                        artifact_path=meta.artifact_uri,
                        artifact_checksum="",
                        dataset_size=0,
                        feature_count=0,
                        feature_names=[], # Predictor doesn't strictly use this unless it validates
                        feature_importance={},
                        shap_summary={},
                        baseline_profile={},
                        split_config={},
                        training_duration_ms=0,
                        lifecycle_state="CHAMPION"
                    )
                    
                    await AuditLogger.record(session, AuditEvent(event_name="MODEL_LOADED", component="PredictionEngine", severity="INFO", payload={"model_id": meta.id, "state": "CHAMPION"}))
                except Exception as e:
                    logger.error(f"Failed to load model {meta.id}: {e}")
                    
            from app.inference.routing import global_traffic_router
            global_traffic_router.configure(
                champion_id=champion_meta.id if champion_meta else None,
                challenger_id=None,
                champion_weight=1.0 
            )
            
            if champion_meta:
                self.routing_registry.set_default(champion_meta.id, f"v{champion_meta.version}")
            else:
                logger.warning("No CHAMPION model found during Prediction Engine startup.")

    async def _execute_predict(self, request: PredictionRequest, alias: str = "default") -> PredictionResponse:
        """Core prediction logic with fallback mechanism."""
        try:
            from app.inference.routing import global_traffic_router
            
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
                
            async with AsyncSessionLocal() as session:
                await AuditLogger.record(session, AuditEvent(event_name="PREDICTION_STARTED", component="PredictionEngine", severity="INFO", payload={"request_id": request.request_id}))
            
            response = predictor.predict(request)
            
            async with AsyncSessionLocal() as session:
                await AuditLogger.record(session, AuditEvent(event_name="PREDICTION_FINISHED", component="PredictionEngine", severity="INFO", payload={"request_id": request.request_id, "latency_ms": response.latency_ms}))
            
            self.stats["prediction_count"] += 1
            self.stats["total_latency_ms"] += response.latency_ms
            self.stats["last_prediction_time"] = datetime.utcnow().isoformat()
            
            return response
            
        except Exception as e:
            logger.error(f"Prediction failed on primary path: {e}")
            async with AsyncSessionLocal() as session:
                await AuditLogger.record(session, AuditEvent(event_name="PREDICTION_FAILED", component="PredictionEngine", severity="ERROR", payload={"error": str(e), "request_id": request.request_id}))
            
            fallback_predictor = None
            for pid, p in self.predictors.items():
                if pid != model_id:
                    fallback_predictor = p
                    break
                    
            if fallback_predictor:
                logger.warning(f"Initiating fallback to {fallback_predictor.model_id}")
                async with AsyncSessionLocal() as session:
                    await AuditLogger.record(session, AuditEvent(event_name="FALLBACK_ACTIVATED", component="PredictionEngine", severity="WARNING", payload={"fallback_model_id": fallback_predictor.model_id}))
                try:
                    response = fallback_predictor.predict(request)
                    self.stats["prediction_count"] += 1
                    return response
                except Exception as fallback_e:
                    raise PredictionError(f"Primary and Fallback predictions failed.") from fallback_e
                    
            raise PredictionError("Prediction failed and no fallback models are available.") from e

    async def predict_single(self, features: Dict[str, Any], entity_id: str = None, alias: str = "default") -> PredictionResponse:
        req = PredictionRequest(request_id=str(uuid.uuid4()), entity_id=entity_id or "anon", features=features)
        return await self._execute_predict(req, alias)

    async def predict_batch(self, batch_features: List[Dict[str, Any]], alias: str = "default") -> List[PredictionResponse]:
        responses = []
        for features in batch_features:
            responses.append(await self.predict_single(features, alias=alias))
        return responses

    async def predict_csv(self, csv_data: str, alias: str = "default") -> List[PredictionResponse]:
        df = pd.read_csv(StringIO(csv_data))
        batch = df.to_dict(orient="records")
        return await self.predict_batch(batch, alias=alias)
