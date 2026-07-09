"""
Centralizes configuration management for FeatureFlow.

Provides a strict, immutable contract for application settings.
Loaded once per execution context to avoid hardcoded paths and values.
"""
import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass(frozen=True)
class Settings:
    """
    Application settings loaded from the environment.
    
    Attributes are frozen to prevent runtime mutation, enforcing a single 
    source of truth for configurations.
    """
    project_name: str = os.getenv("PROJECT_NAME", "FeatureFlow")
    environment: str = os.getenv("ENVIRONMENT") or os.getenv("ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    data_dir: str = os.getenv("DATA_DIR", "./datasets")
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

    def __post_init__(self):
        if not self.database_url:
            logger.error("CRITICAL: DATABASE_URL environment variable is missing!")
            sys.exit(1)
        
        # Ensure we use asyncpg for PostgreSQL URLs
        if self.database_url.startswith("postgresql://"):
            object.__setattr__(self, 'database_url', self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1))
        elif self.database_url.startswith("postgres://"):
            object.__setattr__(self, 'database_url', self.database_url.replace("postgres://", "postgresql+asyncpg://", 1))

    @property
    def is_production(self) -> bool:
        """Determines if the current environment is strictly 'production'."""
        return self.environment.lower() == "production"

# Instantiate a default settings object for convenience. 
# It is frozen, so it acts as an immutable constant.
settings = Settings()
