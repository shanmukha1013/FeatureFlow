"""
Defines abstract contracts for the Training Layer.

Decouples the orchestration of training from the underlying implementations
of data splitting, model algorithms, and metric evaluation.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Tuple, Dict, Any


class BaseSplitter(ABC):
    """Abstract interface for dataset partitioning."""

    @abstractmethod
    def split(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Splits feature and target dataframes.
        Returns: X_train, X_test, y_train, y_test
        """
        ...


class BaseTrainer(ABC):
    """Abstract interface for machine learning algorithms."""

    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """Returns the semantic name of the algorithm."""
        ...

    @abstractmethod
    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> Any:
        """
        Executes the training sequence.
        Returns the trained model object.
        """
        ...


class BaseEvaluator(ABC):
    """Abstract interface for model evaluation."""

    @abstractmethod
    def evaluate(self, model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """
        Evaluates a trained model.
        Returns a dictionary of computed metrics.
        """
        ...
