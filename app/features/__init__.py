"""
Why this file exists:
Exposes the public API of the Feature Layer.

Its responsibility:
Aggregates and exports abstractions so external modules (like future pipelines)
can interact cleanly with the Feature Layer without deep imports.
"""
from .exceptions import (
    FeatureError,
    FeatureNotFoundError,
    DuplicateFeatureError,
    InvalidFeatureError,
    FeatureTransformationError,
)
from .metadata import FeatureMetadata
from .feature import BaseFeature
from .registry import FeatureRegistry
from .transformer import FeatureTransformer

__all__ = [
    "FeatureError",
    "FeatureNotFoundError",
    "DuplicateFeatureError",
    "InvalidFeatureError",
    "FeatureTransformationError",
    "FeatureMetadata",
    "BaseFeature",
    "FeatureRegistry",
    "FeatureTransformer",
]
