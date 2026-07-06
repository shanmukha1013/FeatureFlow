"""
Provides centralized state management for Feature definitions.

Decoupled from global singletons, it acts as an isolated namespace where 
features are registered, verified, and queried prior to transformation.
"""
from typing import Dict, List

from app.features.feature import BaseFeature
from app.features.exceptions import DuplicateFeatureError, FeatureNotFoundError, InvalidFeatureError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FeatureRegistry:
    """
    Namespace manager for storing and retrieving initialized ML features.
    
    Designed to be instantiated per execution context (e.g., per pipeline run or test)
    to strictly avoid global mutable state pollution.
    """
    def __init__(self) -> None:
        # Strict mapping of feature.name to its corresponding BaseFeature instance
        self._features: Dict[str, BaseFeature] = {}

    def register(self, feature: BaseFeature) -> None:
        """
        Validates and registers a new feature into this registry instance.
        
        Args:
            feature: The initialized BaseFeature subclass.
            
        Raises:
            InvalidFeatureError: If the argument is not a valid Feature instance.
            DuplicateFeatureError: If the feature name conflicts with an existing entry.
        """
        if not isinstance(feature, BaseFeature):
            raise InvalidFeatureError("Registry strictly accepts instances inheriting from BaseFeature.")
            
        name: str = feature.name
        if name in self._features:
            error_msg = f"Registration collision: Feature '{name}' is already registered."
            logger.error(error_msg)
            raise DuplicateFeatureError(error_msg)
            
        self._features[name] = feature
        logger.info(f"Registered feature: {name} [v{feature.metadata.version}]")

    def get(self, feature_name: str) -> BaseFeature:
        """
        Retrieves a strictly typed feature definition by name.
        
        Args:
            feature_name: The string identifier for the feature.
            
        Returns:
            The associated BaseFeature instance.
            
        Raises:
            FeatureNotFoundError: If the requested feature was never registered.
        """
        if feature_name not in self._features:
            error_msg = f"Lookup failed: Feature '{feature_name}' does not exist in this registry."
            logger.error(error_msg)
            raise FeatureNotFoundError(error_msg)
            
        return self._features[feature_name]

    def has_feature(self, feature_name: str) -> bool:
        return feature_name in self._features

    def remove(self, feature_name: str) -> None:
        """
        Evicts a feature from the registry.
        
        Args:
            feature_name: The string identifier for the feature.
            
        Raises:
            FeatureNotFoundError: If the feature is missing.
        """
        if feature_name not in self._features:
            raise FeatureNotFoundError(f"Eviction failed: Feature '{feature_name}' not found.")
            
        del self._features[feature_name]
        logger.info(f"Evicted feature: {feature_name}")

    def list_features(self) -> List[str]:
        """Returns an unordered list of all registered feature names."""
        return list(self._features.keys())

global_feature_registry = FeatureRegistry()
