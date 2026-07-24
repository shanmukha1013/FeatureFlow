"""
Centralizes configuration management for FeatureFlow.

Provides a strict, immutable contract for application settings.
Loaded once per execution context to avoid hardcoded paths and values.
"""
from app.utils.logger import get_logger
import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


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

    # Redis Cache Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://default:SIrbAOnl0X1prNZQ5qycQik1mDhk16KC@cup-calculator-relation-56972.db.redis.io:14389")
    redis_pool_size: int = int(os.getenv("REDIS_POOL_SIZE", "20"))
    redis_timeout: float = float(os.getenv("REDIS_TIMEOUT", "5.0"))
    redis_feature_ttl: int = int(os.getenv("REDIS_FEATURE_TTL", "86400"))
    redis_model_ttl: int = int(os.getenv("REDIS_MODEL_TTL", "3600"))
    redis_prediction_ttl: int = int(os.getenv("REDIS_PREDICTION_TTL", "1800"))

    # Phase 5: Redis Enterprise Observability & Hardening
    redis_monitor_interval: int = int(os.getenv("REDIS_MONITOR_INTERVAL", "30"))
    redis_recovery_probe_interval: int = int(os.getenv("REDIS_RECOVERY_PROBE_INTERVAL", "15"))
    redis_memory_alert_threshold: float = float(os.getenv("REDIS_MEMORY_ALERT_THRESHOLD", "0.80"))
    redis_benchmark_iterations: int = int(os.getenv("REDIS_BENCHMARK_ITERATIONS", "100"))
    redis_slow_command_threshold_ms: float = float(os.getenv("REDIS_SLOW_COMMAND_THRESHOLD_MS", "100.0"))

    # Phase 6: Enterprise Authentication & Security
    jwt_secret_keys: str = os.getenv("JWT_SECRET_KEYS", "featureflow-default-dev-secret-key-32b")  # OVERRIDE IN PRODUCTION
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    default_admin_email: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@featureflow.local")
    default_admin_password: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")  # OVERRIDE IN PRODUCTION
    bcrypt_rounds: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    max_login_attempts: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    lockout_duration_minutes: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

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
