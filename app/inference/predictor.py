"""
Coordinates the end-to-end inference prediction lifecycle.
"""
import time
import pandas as pd
from typing import Optional

from app.inference.base import BasePredictor, BaseModelLoader, BaseInferenceValidator
from app.inference.request import PredictionRequest
from app.inference.response import PredictionResponse
from app.inference.exceptions import PredictionError, InputValidationError
from app.training.registry import LocalModelRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ModelPredictor(BasePredictor):
    """
    Coordinates validation, formatting, and model execution to generate safe predictions.
    Owns ONLY the prediction logic; delegates artifact loading and validation.
    """
    def __init__(
        self, 
        model_id: str, 
        version: str, 
        loader: BaseModelLoader, 
        validator: BaseInferenceValidator,
        training_registry: LocalModelRegistry,
        model_alias: str = "default"
    ) -> None:
        self.model_id = model_id
        self.version = version
        self.model_alias = model_alias
        self.loader = loader
        self.validator = validator
        
        # We fetch metadata directly from the training layer to guarantee we know
        # EXACTLY what features the model requires without guessing or hardcoding.
        self.metadata = training_registry.get(model_id)
        
        if not hasattr(self.metadata, "feature_names") or not self.metadata.feature_names:
            raise PredictionError(f"Model '{model_id}' metadata is missing strictly required 'feature_names'.")
            
        self.expected_features = self.metadata.feature_names
        
        # Pre-load the model into memory during initialization, not per-request
        self.model = self.loader.load(self.model_id, self.version)

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        start_time = time.time()
        
        # Merge requested features with Online/Offline Feature Store
        features = request.features.copy()
        
        if request.entity_id and request.entity_id != "anon":
            from app.features.store.online import global_online_store
            from app.features.store.sync import global_sync_manager
            
            # 1. Try Redis
            cached = global_online_store.read(request.entity_id)
            if cached:
                # requested features override stored features
                cached.update(features)
                features = cached
            else:
                # 2. Fallback to Postgres via SyncManager
                offline = global_sync_manager.sync_entity(request.entity_id)
                if offline:
                    offline.update(features)
                    features = offline
                    
        request.features = features
        
        """
        Safely executes a single prediction request.
        Guarantees prediction never fires if input validation fails.
        """
        start_time = time.perf_counter()
        
        # 1. Strict Validation Boundary
        try:
            warnings = self.validator.validate(request, self.expected_features)
        except InputValidationError as e:
            logger.error(f"Validation failure for request '{request.request_id}': {e}")
            raise # Fail fast, prediction engine will NOT touch invalid data
            
        try:
            # 2. DataFrame Construction with Deterministic Ordering
            # We strictly build the DataFrame using the EXACT column order expected by the model.
            ordered_features = {f: [request.features[f]] for f in self.expected_features}
            df = pd.DataFrame(ordered_features)
            
            # 3. Execution
            prediction = self.model.predict(df)[0]
            
            probability: Optional[float] = None
            if hasattr(self.model, "predict_proba"):
                # Simplistic extraction of the highest probability class
                proba_array = self.model.predict_proba(df)[0]
                probability = float(max(proba_array))
                
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            from datetime import datetime
            from app.inference.explainability import LocalExplainer
            
            explainer = LocalExplainer(self.model)
            explanation = explainer.explain(df)
            
            # 4. Immutable Response Construction
            response = PredictionResponse(
                request_id=request.request_id,
                prediction=prediction,
                confidence=probability, # Simplified to probability for now
                probability=probability,
                latency_ms=latency_ms,
                model_name=self.model_id,
                model_version=self.version,
                algorithm=self.metadata.algorithm,
                timestamp=datetime.utcnow().isoformat(),
                warnings=warnings,
                top_contributors=explanation.get("top_contributors", []),
                positive_contributors=explanation.get("positive_contributors", []),
                negative_contributors=explanation.get("negative_contributors", []),
                raw_scores=explanation.get("raw_scores", {})
            )
            
            # 5. Drift Monitoring (Background ingestion)
            try:
                from app.monitoring.drift.engine import global_drift_engine
                # Flatten the feature dictionary
                features_dict = df.iloc[0].to_dict()
                global_drift_engine.ingest(self.model_id, features_dict, float(prediction))
            except Exception as e:
                logger.warning(f"Failed to ingest data for drift monitoring: {e}")
            
            logger.debug(f"Prediction generated for entity '{request.entity_id}' via alias '{self.model_alias}' in {latency_ms:.2f}ms.")
            return response
            
        except Exception as e:
            error_msg = f"Fatal prediction execution failure for request '{request.request_id}': {e}"
            logger.error(error_msg)
            raise PredictionError(error_msg) from e
