import pandas as pd
from typing import Dict, List, Any
from io import StringIO
import time
from datetime import datetime
import uuid

from app.utils.logger import get_logger

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
        
        self.validator = RequestValidator()
        
        # We will use an in-memory dictionary for active predictors since
        # the ML models themselves must stay in memory for fast inference.
        # But routing information and defaults are derived from the DB.
        self.routing_registry = {}
        self.default_alias = None
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
                    # Fetch features for this dataset
                    from app.storage.models import Feature
                    feature_result = await session.execute(
                        select(Feature).filter(Feature.dataset_id == meta.dataset_id)
                    )
                    features_meta = feature_result.scalars().all()
                    
                    predictor = ModelPredictor(
                        model_id=meta.id,
                        version=f"v{meta.version}",
                        loader=None,
                        validator=self.validator,
                        model_meta=meta,
                        features_meta=features_meta,
                        model_alias=meta.id
                    )
                    # Load model from disk artifact
                    predictor.model = self.artifact_store.load(meta.id, f"v{meta.version}")
                    
                    self.predictors[meta.id] = predictor
                    self.routing_registry[meta.id] = (meta.id, f"v{meta.version}")
                    
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
                self.default_alias = champion_meta.id
            else:
                logger.warning("No CHAMPION model found during Prediction Engine startup.")

    async def _execute_predict(self, request: PredictionRequest, alias: str = "default") -> PredictionResponse:
        """Core prediction logic with fallback mechanism."""
        try:
            from app.inference.routing import global_traffic_router
            
            if alias == "default":
                # Fallback to the first active champion if traffic router is unconfigured
                model_id = global_traffic_router.select_model() or self.default_alias
                if not model_id:
                    raise InferenceError("No champion or challenger models configured for traffic routing.")
            else:
                model_id, version = self.routing_registry.get(alias, (None, None))
                if not model_id:
                    raise InferenceError(f"Alias {alias} not found in routing registry.")
                
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
