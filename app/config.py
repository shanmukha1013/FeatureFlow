"""
Centralizes configuration management for FeatureFlow.

Provides a strict, immutable contract for application settings.
Loaded once per execution context to avoid hardcoded paths and values.
"""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    """
    Application settings loaded from the environment.
    
    Attributes are frozen to prevent runtime mutation, enforcing a single 
    source of truth for configurations.
    """
    project_name: str = os.getenv("PROJECT_NAME", "FeatureFlow")
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    data_dir: str = os.getenv("DATA_DIR", "./datasets")

    @property
    def is_production(self) -> bool:
        """Determines if the current environment is strictly 'production'."""
        return self.environment.lower() == "production"

# Instantiate a default settings object for convenience. 
# It is frozen, so it acts as an immutable constant.
settings = Settings()
