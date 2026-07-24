"""
Centralizes exceptions for the Training Layer.
"""


class TrainingError(Exception):
    """Base exception for all Training Layer errors."""


class DatasetPreparationError(TrainingError):
    """Raised when preparing the dataset for training fails (e.g., missing columns)."""


class TrainingFailure(TrainingError):
    """Raised when a machine learning model fails to fit the training data."""


class EvaluationError(TrainingError):
    """Raised when calculating metrics against the test set fails."""


class ArtifactError(TrainingError):
    """Raised when persisting or loading a trained model binary fails."""


class RegistryError(TrainingError):
    """Raised when registering or retrieving model metadata fails."""
