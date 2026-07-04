"""
Defines abstract contracts for the Inference Layer.

Ensures the Predictor can coordinate loading, validating, and predicting
without coupling to concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Any, List

from app.inference.request import PredictionRequest
from app.inference.response import PredictionResponse

class BaseModelLoader(ABC):
    """Abstract interface for retrieving trained artifacts."""
    
    @abstractmethod
    def load(self, model_id: str, version: str) -> Any:
        ...

class BaseInferenceValidator(ABC):
    """Abstract interface for verifying feature vectors at inference time."""
    
    @abstractmethod
    def validate(self, request: PredictionRequest, expected_features: List[str]) -> List[str]:
        ...

class BasePredictor(ABC):
    """Abstract interface for the main prediction orchestrator."""
    
    @abstractmethod
    def predict(self, request: PredictionRequest) -> PredictionResponse:
        ...
