import time
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from app.utils.logger import get_logger
from app.explainability.utils import get_explainer_for_model
from app.inference.exceptions import InferenceError

logger = get_logger(__name__)


class ExplainerEngine:
    """
    Core engine that delegates to SHAP to compute explainability values.
    """

    def __init__(self):
        pass

    def generate_explanation(self, model: Any, features: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """
        Executes SHAP and returns the result and execution time in ms.
        """
        start_time = time.perf_counter()

        try:
            ExplainerClass, explainer_type = get_explainer_for_model(model)

            # Prepare data
            # SHAP expects a 2D array-like for a single instance
            df = pd.DataFrame([features])

            # Initialize explainer.
            # Note: For KernelExplainer, we might need a background dataset.
            # For this enterprise version, Tree and Linear work natively with just the model.
            try:
                explainer = ExplainerClass(model)
            except Exception as e:
                logger.warning(f"Failed to initialize {explainer_type}: {e}. Falling back to default SHAP Explainer.")
                import shap
                explainer = shap.Explainer(model)

            shap_values = explainer(df)

            # Extract values for the single instance
            if hasattr(shap_values, "values"):
                vals = shap_values.values[0]
            else:
                vals = shap_values[0]

            # Depending on multi-class, vals might be 2D. We take the expected probability path (usually vals[:, 1] for binary)
            if len(vals.shape) > 1:
                vals = vals[:, 1]  # Assuming binary classification for simplicity in this general framework

            feature_names = df.columns.tolist()

            top_features = []
            for i, fname in enumerate(feature_names):
                val = float(vals[i])
                top_features.append({
                    "feature": fname,
                    "importance": abs(val),
                    "direction": "positive" if val > 0 else "negative"
                })

            # Sort by importance descending
            top_features.sort(key=lambda x: x["importance"], reverse=True)

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            base_val = shap_values.base_values[0] if hasattr(shap_values, "base_values") else 0.0
            if isinstance(base_val, (list, np.ndarray)):
                base_val = base_val[1] if len(base_val) > 1 else base_val[0]

            result = {
                "top_features": top_features,
                "visualization_data": {
                    "base_value": float(base_val),
                    "shap_values": [float(v) for v in vals]
                },
                "explainer_type": explainer_type
            }

            return result, execution_time_ms

        except Exception as e:
            logger.error(f"SHAP Explainer generation failed: {e}")
            raise InferenceError(f"Explainability generation failed: {e}")
