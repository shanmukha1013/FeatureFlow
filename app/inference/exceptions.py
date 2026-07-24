"""
Centralizes exceptions for the Inference Layer.
"""


class InferenceError(Exception):
    """Base exception for all Inference Layer errors."""


class PredictionError(InferenceError):
    """Raised when the model fails to generate a prediction."""


class ModelLoadError(InferenceError):
    """Raised when an artifact or its metadata fails to load."""


class InputValidationError(InferenceError):
    """Raised when a prediction request violates the expected feature schema."""
