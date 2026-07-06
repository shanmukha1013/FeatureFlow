from app.features.store.offline import global_offline_store
from app.features.store.online import global_online_store
from app.monitoring.audit import AuditLogger, AuditEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FeatureSyncManager:
    """Synchronizes features from PostgreSQL (Offline) to Redis (Online)."""
    
    def sync_entity(self, entity_id: str):
        """Fetches the latest features for an entity from Postgres and loads them into Redis."""
        try:
            features = global_offline_store.historical_lookup(entity_id)
            if features:
                global_online_store.write(entity_id, features)
                AuditLogger.record(AuditEvent(event_name="FEATURE_SYNCED", component="FeatureSyncManager", severity="INFO", payload={"entity_id": entity_id}))
            return features
        except Exception as e:
            logger.error(f"Failed to sync entity {entity_id}: {e}")
            return None

global_sync_manager = FeatureSyncManager()
