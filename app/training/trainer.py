"""
Executes ML algorithms on prepared features.
"""
import pandas as pd
from typing import Any

from app.training.base import BaseTrainer
from app.training.exceptions import TrainingFailure
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LogisticRegressionTrainer(BaseTrainer):
    """
    Linear classification model targeting tabular numeric features.
    """

    def __init__(self, **hyperparameters: Any) -> None:
        self.hyperparameters = hyperparameters
        try:
            from sklearn.linear_model import LogisticRegression
            self._model = LogisticRegression(**hyperparameters)
        except ImportError:
            raise TrainingFailure("scikit-learn is required but not installed.")

    @property
    def algorithm_name(self) -> str:
        return "LogisticRegression"

    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> Any:
        logger.info(f"Commencing training sequence for {self.algorithm_name}.")
        try:
            self._model.fit(X_train, y_train)
            logger.info("Training sequence completed successfully.")
            return self._model
        except Exception as e:
            error_msg = f"Fatal failure during {self.algorithm_name} training: {e}"
            logger.error(error_msg)
            raise TrainingFailure(error_msg) from e


class RandomForestTrainer(BaseTrainer):
    """
    Ensemble classification model handling complex non-linear relationships.
    """

    def __init__(self, **hyperparameters: Any) -> None:
        self.hyperparameters = hyperparameters
        try:
            from sklearn.ensemble import RandomForestClassifier
            self._model = RandomForestClassifier(**hyperparameters)
        except ImportError:
            raise TrainingFailure("scikit-learn is required but not installed.")

    @property
    def algorithm_name(self) -> str:
        return "RandomForest"

    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> Any:
        logger.info(f"Commencing training sequence for {self.algorithm_name}.")
        try:
            self._model.fit(X_train, y_train)
            logger.info("Training sequence completed successfully.")
            return self._model
        except Exception as e:
            error_msg = f"Fatal failure during {self.algorithm_name} training: {e}"
            logger.error(error_msg)
            raise TrainingFailure(error_msg) from e


class DecisionTreeTrainer(BaseTrainer):
    """
    Non-linear classification model based on tree logic.
    """

    def __init__(self, **hyperparameters: Any) -> None:
        self.hyperparameters = hyperparameters
        try:
            from sklearn.tree import DecisionTreeClassifier
            self._model = DecisionTreeClassifier(**hyperparameters)
        except ImportError:
            raise TrainingFailure("scikit-learn is required but not installed.")

    @property
    def algorithm_name(self) -> str:
        return "DecisionTree"

    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> Any:
        logger.info(f"Commencing training sequence for {self.algorithm_name}.")
        try:
            self._model.fit(X_train, y_train)
            logger.info("Training sequence completed successfully.")
            return self._model
        except Exception as e:
            error_msg = f"Fatal failure during {self.algorithm_name} training: {e}"
            logger.error(error_msg)
            raise TrainingFailure(error_msg) from e
