"""
Centralizes exceptions for the Inference Layer.
"""

class InferenceError(Exception):
    """Base exception for all Inference Layer errors."""
    pass

class PredictionError(InferenceError):
    """Raised when the model fails to generate a prediction."""
    pass

class ModelLoadError(InferenceError):
    """Raised when an artifact or its metadata fails to load."""
    pass

class InputValidationError(InferenceError):
    """Raised when a prediction request violates the expected feature schema."""
    pass
