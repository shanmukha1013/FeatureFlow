import pandas as pd
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

class GlobalExplainer:
    """
    Computes global feature importance and SHAP summaries for trained models.
    """
    def __init__(self):
        pass

    def compute_feature_importance(self, model: Any, feature_names: list) -> Dict[str, float]:
        """Extracts native feature importances from Tree or Linear models."""
        importances = {}
        try:
            if hasattr(model, "feature_importances_"):
                # Trees (Random Forest, Decision Tree, XGBoost)
                scores = model.feature_importances_
                importances = {name: float(score) for name, score in zip(feature_names, scores)}
            elif hasattr(model, "coef_"):
                # Linear Models (Logistic Regression)
                scores = model.coef_[0]
                # Use absolute value for magnitude of importance
                importances = {name: float(abs(score)) for name, score in zip(feature_names, scores)}
        except Exception as e:
            logger.warning(f"Could not compute native feature importance: {e}")
            
        # Sort by highest importance
        return dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    def compute_shap_summary(self, model: Any, X_train: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Computes a lightweight SHAP summary payload for dashboard visualization."""
        try:
            import shap
            import numpy as np
            
            # Sample background data to prevent memory exhaustion
            background = shap.sample(X_train, 100) if len(X_train) > 100 else X_train
            
            explainer = None
            if type(model).__name__ in ["RandomForestClassifier", "DecisionTreeClassifier"]:
                explainer = shap.TreeExplainer(model)
            elif type(model).__name__ in ["LogisticRegression"]:
                explainer = shap.LinearExplainer(model, background)
                
            if explainer:
                shap_values = explainer.shap_values(background)
                # If multiclass/binary it might return a list of arrays
                if isinstance(shap_values, list):
                    shap_values = shap_values[1] # Take positive class for binary
                    
                mean_abs_shap = np.abs(shap_values).mean(axis=0)
                feature_names = X_train.columns.tolist()
                
                summary = {name: float(val) for name, val in zip(feature_names, mean_abs_shap)}
                return dict(sorted(summary.items(), key=lambda item: item[1], reverse=True))
        except ImportError:
            logger.info("SHAP is not installed, skipping SHAP summary generation.")
        except Exception as e:
            logger.warning(f"Failed to generate SHAP summary: {e}")
            
        return None
