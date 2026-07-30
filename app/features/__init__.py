"""
Why this file exists:
Exposes the public API of the Feature Layer.

Its responsibility:
Aggregates and exports abstractions so external modules (like future pipelines)
can interact cleanly with the Feature Layer without deep imports.
"""
from .exceptions import (
    DuplicateFeatureError,
    FeatureError,
    FeatureNotFoundError,
    FeatureTransformationError,
    InvalidFeatureError,
)
from .feature import BaseFeature
from .metadata import FeatureMetadata
from .transformer import FeatureTransformer

__all__ = [
    "FeatureError",
    "FeatureNotFoundError",
    "DuplicateFeatureError",
    "InvalidFeatureError",
    "FeatureTransformationError",
    "FeatureMetadata",
    "BaseFeature",
    "FeatureTransformer",
]
