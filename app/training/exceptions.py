"""
Centralizes exceptions for the Training Layer.
"""

class TrainingError(Exception):
    """Base exception for all Training Layer errors."""
    pass

class DatasetPreparationError(TrainingError):
    """Raised when preparing the dataset for training fails (e.g., missing columns)."""
    pass

class TrainingFailure(TrainingError):
    """Raised when a machine learning model fails to fit the training data."""
    pass

class EvaluationError(TrainingError):
    """Raised when calculating metrics against the test set fails."""
    pass

class ArtifactError(TrainingError):
    """Raised when persisting or loading a trained model binary fails."""
    pass

class RegistryError(TrainingError):
    """Raised when registering or retrieving model metadata fails."""
    pass
