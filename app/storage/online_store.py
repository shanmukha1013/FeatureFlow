"""
Implements the Online Feature Store targeting Redis.

Responsible for ultra-fast, low-latency retrieval of feature vectors.
"""
import pandas as pd
import numpy as np
import json
from typing import Any, List, Optional

from app.storage.base import BaseFeatureStore
from app.storage.exceptions import OnlineStorageError, StorageConnectionError, FeatureNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RedisOnlineStore(BaseFeatureStore):
    """
    Online storage backend implementation using Redis.
    """
    
    def __init__(self, host: str, port: int = 6379, db: int = 0, default_ttl: int = 86400) -> None:
        if not host or not str(host).strip():
            raise StorageConnectionError("Redis host cannot be empty.")
            
        self.default_ttl = int(default_ttl)
        try:
            import redis
            self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            logger.info(f"Successfully initialized Redis Online Store client at {host}:{port}.")
        except ImportError:
            raise StorageConnectionError("Required dependency 'redis' is not installed.")
        except Exception as e:
            error_msg = f"Fatal error initializing Redis client: {e}"
            logger.error(error_msg)
            raise StorageConnectionError(error_msg) from e

    def _get_namespace(self, dataset_name: str, version: str) -> str:
        """Generates a safe Redis namespace key prefix."""
        clean_version = str(version).replace(".", "_")
        return f"{dataset_name}:v:{clean_version}" if version != "latest" else dataset_name

    def save(self, dataset_name: str, df: pd.DataFrame, version: str = "latest") -> None:
        namespace = self._get_namespace(dataset_name, version)
        try:
            logger.info(f"Online save initiated: {len(df)} vectors to namespace '{namespace}'.")
            pipeline = self.client.pipeline()
            
            # Enforce strong serialization boundaries: convert problematic Pandas NaNs to Python None
            # so the standard json library handles it safely as 'null'.
            safe_df = df.replace({np.nan: None})
            
            for _, row in safe_df.iterrows():
                entity_id = row['entity_id']
                key = f"{namespace}:{entity_id}"
                vector_dict = row.drop('entity_id').to_dict()
                pipeline.setex(name=key, time=self.default_ttl, value=json.dumps(vector_dict))
                
            pipeline.execute()
            logger.info(f"Online save completed: vectors persisted to namespace '{namespace}'.")
        except Exception as e:
            error_msg = f"Failed to persist vectors to Redis namespace '{namespace}': {e}"
            logger.error(error_msg)
            raise OnlineStorageError(error_msg) from e

    def load(self, dataset_name: str, entity_ids: Optional[List[Any]] = None, version: str = "latest") -> pd.DataFrame:
        if not entity_ids:
            raise OnlineStorageError("Online store requires an explicit list of entity_ids for lookup.")
            
        namespace = self._get_namespace(dataset_name, version)
        try:
            logger.info(f"Online load initiated: {len(entity_ids)} keys from namespace '{namespace}'.")
            keys = [f"{namespace}:{str(eid)}" for eid in entity_ids]
            results = self.client.mget(keys)
            
            records = []
            for eid, result in zip(entity_ids, results):
                if result:
                    vector = json.loads(result)
                    vector['entity_id'] = eid
                    records.append(vector)
                    
            if not records:
                raise FeatureNotFoundError(f"No vectors found in Redis for namespace '{namespace}'.")
                
            df = pd.DataFrame(records)
            logger.info(f"Online load completed: retrieved {len(df)} vectors.")
            return df
        except FeatureNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to retrieve vectors from Redis namespace '{namespace}': {e}"
            logger.error(error_msg)
            raise OnlineStorageError(error_msg) from e

    def upsert(self, dataset_name: str, df: pd.DataFrame, version: str = "latest") -> None:
        """
        Executes a true Upsert operation. 
        In Redis (Key-Value), saving effectively overwrites existing keys, serving as a native Upsert.
        """
        logger.info(f"Executing upsert in online store for '{dataset_name}'.")
        self.save(dataset_name, df, version)

    def delete(self, dataset_name: str, version: str = "latest") -> None:
        namespace = self._get_namespace(dataset_name, version)
        try:
            cursor = '0'
            deleted_count = 0
            while cursor != 0:
                cursor, keys = self.client.scan(cursor=cursor, match=f"{namespace}:*", count=1000)
                if keys:
                    self.client.delete(*keys)
                    deleted_count += len(keys)
            logger.info(f"Successfully evicted {deleted_count} vectors from Redis namespace '{namespace}'.")
        except Exception as e:
            error_msg = f"Failed to flush namespace '{namespace}' from Redis: {e}"
            logger.error(error_msg)
            raise OnlineStorageError(error_msg) from e

    def exists(self, dataset_name: str, version: str = "latest") -> bool:
        namespace = self._get_namespace(dataset_name, version)
        try:
            cursor, keys = self.client.scan(cursor=0, match=f"{namespace}:*", count=1)
            return len(keys) > 0
        except Exception as e:
            logger.error(f"Failed to check existence in Redis for '{namespace}': {e}")
            return False
            
    def list(self) -> List[str]:
        """Provides a best-effort list of available namespaces in Redis."""
        try:
            namespaces = set()
            cursor = '0'
            while cursor != 0:
                cursor, keys = self.client.scan(cursor=cursor, match="*", count=10000)
                for key in keys:
                    if ':' in key:
                        namespaces.add(key.split(':')[0])
            return list(namespaces)
        except Exception as e:
            logger.error(f"Failed to list Redis namespaces: {e}")
            return []
