"""
Public API boundary for the Training Layer.
"""
from .exceptions import (
    TrainingError,
    DatasetPreparationError,
    TrainingFailure,
    EvaluationError,
    ArtifactError,
    RegistryError,
)
from .metadata import ModelMetadata
from .base import BaseSplitter, BaseTrainer, BaseEvaluator
from .dataset import TrainingDatasetBuilder
from .splitter import RandomSplitter, TimeBasedSplitter
from .trainer import LogisticRegressionTrainer, RandomForestTrainer
from .evaluator import ClassificationEvaluator
from .artifacts import LocalArtifactStore

__all__ = [
    "TrainingError",
    "DatasetPreparationError",
    "TrainingFailure",
    "EvaluationError",
    "ArtifactError",
    "RegistryError",
    "ModelMetadata",
    "BaseSplitter",
    "BaseTrainer",
    "BaseEvaluator",
    "TrainingDatasetBuilder",
    "RandomSplitter",
    "TimeBasedSplitter",
    "LogisticRegressionTrainer",
    "RandomForestTrainer",
    "ClassificationEvaluator",
    "LocalArtifactStore",
]
