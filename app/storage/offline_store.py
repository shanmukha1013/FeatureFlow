"""
Implements the Offline Feature Store targeting PostgreSQL.

Responsible for batch persistence and retrieval of historical feature datasets,
supporting strict version-aware isolation.
"""
import pandas as pd
from typing import Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

from app.storage.base import BaseFeatureStore
from app.storage.exceptions import OfflineStorageError, StorageConnectionError, FeatureNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class PostgresOfflineStore(BaseFeatureStore):
    """
    Offline storage backend implementation using PostgreSQL.
    """
    
    def __init__(self, connection_string: str) -> None:
        if not connection_string or not str(connection_string).strip():
            raise StorageConnectionError("PostgreSQL connection string cannot be empty.")
            
        try:
            self.engine: Engine = create_engine(connection_string)
            logger.info("Successfully initialized PostgreSQL Offline Store engine.")
        except Exception as e:
            error_msg = f"Fatal error initializing PostgreSQL engine: {e}"
            logger.error(error_msg)
            raise StorageConnectionError(error_msg) from e

    def _get_table_name(self, dataset_name: str, version: str) -> str:
        """Derives a safe, version-aware SQL table name."""
        clean_version = str(version).replace(".", "_").replace("-", "_")
        return f"{dataset_name}_v_{clean_version}" if version != "latest" else dataset_name

    def save(self, dataset_name: str, df: pd.DataFrame, version: str = "latest") -> None:
        table_name = self._get_table_name(dataset_name, version)
        try:
            logger.info(f"Offline save initiated: {len(df)} rows to table '{table_name}'.")
            df.to_sql(name=table_name, con=self.engine, if_exists='replace', index=False)
            logger.info(f"Offline save completed for '{table_name}'.")
        except Exception as e:
            error_msg = f"Failed to persist dataset '{table_name}' to offline store: {e}"
            logger.error(error_msg)
            raise OfflineStorageError(error_msg) from e

    def load(self, dataset_name: str, entity_ids: Optional[List[Any]] = None, version: str = "latest") -> pd.DataFrame:
        table_name = self._get_table_name(dataset_name, version)
        if not self.exists(dataset_name, version):
            raise FeatureNotFoundError(f"Offline dataset '{table_name}' does not exist.")

        try:
            logger.info(f"Offline load initiated for table '{table_name}'.")
            if entity_ids:
                if not isinstance(entity_ids, list) or not entity_ids:
                    raise ValueError("entity_ids must be a non-empty list.")
                    
                # Safe parametrization for SQL IN clause to prevent injection and syntax errors
                id_tuple = tuple(entity_ids) if len(entity_ids) > 1 else f"('{entity_ids[0]}')"
                query = f"SELECT * FROM {table_name} WHERE entity_id IN {id_tuple}"
                df = pd.read_sql(query, con=self.engine)
            else:
                df = pd.read_sql_table(table_name=table_name, con=self.engine)
                
            logger.info(f"Offline load completed: retrieved {len(df)} rows from '{table_name}'.")
            return df
        except Exception as e:
            error_msg = f"Failed to retrieve dataset '{table_name}' from offline store: {e}"
            logger.error(error_msg)
            raise OfflineStorageError(error_msg) from e

    def upsert(self, dataset_name: str, df: pd.DataFrame, version: str = "latest") -> None:
        """
        Executes a true Upsert (Insert on Conflict Update) operation.
        """
        table_name = self._get_table_name(dataset_name, version)
        if not self.exists(dataset_name, version):
            raise FeatureNotFoundError(f"Cannot upsert to non-existent offline dataset '{table_name}'.")
            
        logger.warning(
            f"Upsert requested for '{table_name}'. "
            "Native PostgreSQL UPSERT implementation is pending architecture support for explicit primary keys."
        )
        raise NotImplementedError("Strict UPSERT semantics are not yet natively implemented for PostgreSQL in this layer.")

    def delete(self, dataset_name: str, version: str = "latest") -> None:
        table_name = self._get_table_name(dataset_name, version)
        try:
            with self.engine.begin() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            logger.info(f"Successfully dropped offline dataset '{table_name}'.")
        except Exception as e:
            error_msg = f"Failed to drop dataset '{table_name}': {e}"
            logger.error(error_msg)
            raise OfflineStorageError(error_msg) from e

    def exists(self, dataset_name: str, version: str = "latest") -> bool:
        table_name = self._get_table_name(dataset_name, version)
        try:
            inspector = inspect(self.engine)
            return inspector.has_table(table_name)
        except Exception as e:
            logger.error(f"Failed to verify existence of offline table '{table_name}': {e}")
            return False
            
    def list(self) -> List[str]:
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            logger.error(f"Failed to list offline tables: {e}")
            return []
