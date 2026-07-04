"""
Why this file exists:
Centralizes custom exceptions for the Feature Layer to provide clear, 
traceable error handling throughout the feature definition and transformation lifecycle.

Its responsibility:
Defines the base feature exception and specialized errors for registries, validation, 
and transformation failures.
"""

class FeatureError(Exception):
    """Base exception for all Feature Layer errors."""
    pass

class FeatureNotFoundError(FeatureError):
    """Raised when attempting to retrieve an unregistered feature."""
    pass

class DuplicateFeatureError(FeatureError):
    """Raised when attempting to register a feature that already exists."""
    pass

class InvalidFeatureError(FeatureError):
    """Raised when a feature definition or its metadata is invalid."""
    pass

class FeatureTransformationError(FeatureError):
    """Raised when a feature transformation fails during execution."""
    pass
