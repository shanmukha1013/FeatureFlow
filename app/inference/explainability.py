import pandas as pd
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

class LocalExplainer:
    """
    Computes local feature contributions for a specific prediction request.
    """
    def __init__(self, model: Any):
        self.model = model

    def explain(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Explains a single prediction instance.
        """
        contributions = {}
        try:
            if hasattr(self.model, "coef_"):
                # Logistic Regression
                coefs = self.model.coef_[0]
                values = df.iloc[0].values
                for name, coef, val in zip(df.columns, coefs, values):
                    contributions[name] = float(coef * val)
            elif type(self.model).__name__ in ["RandomForestClassifier", "DecisionTreeClassifier"]:
                # Fast Tree heuristic without heavy SHAP dependency for latency critical inference
                importances = self.model.feature_importances_
                values = df.iloc[0].values
                for name, imp, val in zip(df.columns, importances, values):
                    contributions[name] = float(imp * val)
        except Exception as e:
            logger.warning(f"Failed to generate local explanation: {e}")
            
        if not contributions:
            return {"top_contributors": [], "positive": [], "negative": []}
            
        sorted_contribs = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
        top = [{"feature": k, "contribution": v} for k, v in sorted_contribs[:5]]
        
        positive = [{"feature": k, "contribution": v} for k, v in sorted_contribs if v > 0]
        negative = [{"feature": k, "contribution": v} for k, v in sorted_contribs if v < 0]
        
        return {
            "top_contributors": top,
            "positive_contributors": positive,
            "negative_contributors": negative,
            "raw_scores": contributions
        }
