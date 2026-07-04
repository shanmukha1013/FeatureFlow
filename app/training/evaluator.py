"""
Evaluates trained artifacts against held-out test datasets.
"""
import pandas as pd
from typing import Any, Dict

from app.training.base import BaseEvaluator
from app.training.exceptions import EvaluationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ClassificationEvaluator(BaseEvaluator):
    """
    Computes standard classification metrics alongside detailed class-level reports.
    """
    def evaluate(self, model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        logger.info("Executing evaluation sequence on test partition.")
        try:
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report
            
            predictions = model.predict(X_test)
            metrics: Dict[str, Any] = {
                "accuracy": float(accuracy_score(y_test, predictions)),
                "precision": float(precision_score(y_test, predictions, average='weighted', zero_division=0)),
                "recall": float(recall_score(y_test, predictions, average='weighted', zero_division=0)),
                "f1": float(f1_score(y_test, predictions, average='weighted', zero_division=0))
            }
            
            # Detailed class-level statistics
            metrics["classification_report"] = classification_report(y_test, predictions, output_dict=True, zero_division=0)
            
            # Conditionally attach ROC-AUC for binary classification models with probability APIs
            if hasattr(model, "predict_proba") and len(y_test.unique()) == 2:
                proba = model.predict_proba(X_test)[:, 1]
                metrics["roc_auc"] = float(roc_auc_score(y_test, proba))
                
            logger.info(f"Evaluation completed. Accuracy: {metrics['accuracy']:.4f}")
            return metrics
            
        except Exception as e:
            error_msg = f"Failed to compute evaluation metrics: {e}"
            logger.error(error_msg)
            raise EvaluationError(error_msg) from e
