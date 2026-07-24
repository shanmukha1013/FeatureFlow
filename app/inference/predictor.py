"""
Coordinates the end-to-end inference prediction lifecycle.
"""
import time
import pandas as pd
from typing import Optional, List
from datetime import datetime, timezone

from app.inference.base import BasePredictor, BaseModelLoader, BaseInferenceValidator
from app.inference.request import PredictionRequest
from app.inference.response import PredictionResponse
from app.inference.exceptions import PredictionError, InputValidationError
from app.utils.logger import get_logger
from app.storage.models import Model, Feature

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
        model_meta: Model,
        features_meta: List[Feature],
        model_alias: str = "default"
    ) -> None:
        self.model_id = model_id
        self.version = version
        self.model_alias = model_alias
        self.loader = loader
        self.validator = validator

        self.metadata = model_meta
        self.features_meta = features_meta

        self.expected_features = [f.name for f in self.features_meta]

        # Pre-load the model into memory during initialization, not per-request
        if self.loader:
            self.model = self.loader.load(self.model_id, self.version)
        else:
            self.model = None  # Set by engine

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        """
        Safely executes a single prediction request.
        Guarantees prediction never fires if input validation fails.
        """
        start_time = time.perf_counter()

        # 1. Prepare features dictionary (handle raw or engineered features)
        features_dict = dict(request.features)

        if self.expected_features and any(f not in features_dict for f in self.expected_features):
            try:
                from app.features.transformer import FeatureTransformer
                raw_df = pd.DataFrame([features_dict])
                transformed_df = FeatureTransformer().transform(raw_df, self.features_meta)
                features_dict.update(transformed_df.iloc[0].to_dict())
            except Exception as e:
                logger.warning(f"Could not transform raw features during inference: {e}")

        # 2. Strict Validation Boundary
        try:
            warnings = self.validator.validate(request, self.expected_features)
        except InputValidationError as e:
            if all(f in features_dict for f in self.expected_features):
                warnings = []
            else:
                logger.error(f"Validation failure for request '{request.request_id}': {e}")
                raise

        try:
            # 3. DataFrame Construction with Deterministic Ordering
            ordered_features = {f: [features_dict.get(f, 0.0)] for f in self.expected_features}
            df = pd.DataFrame(ordered_features)

            # 3. Execution
            prediction = self.model.predict(df)[0]

            probability: Optional[float] = None
            if hasattr(self.model, "predict_proba"):
                # Simplistic extraction of the highest probability class
                proba_array = self.model.predict_proba(df)[0]
                probability = float(max(proba_array))

            latency_ms = (time.perf_counter() - start_time) * 1000

            from app.inference.explainability import LocalExplainer

            explainer = LocalExplainer(self.model)
            explanation = explainer.explain(df)

            # 4. Immutable Response Construction
            response = PredictionResponse(
                request_id=request.request_id,
                prediction=prediction,
                confidence=probability,  # Simplified to probability for now
                probability=probability,
                latency_ms=latency_ms,
                model_name=self.model_id,
                model_version=self.version,
                algorithm=self.metadata.algorithm or "unknown",
                timestamp=datetime.now(timezone.utc).isoformat(),
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
