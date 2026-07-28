import asyncio
from typing import Dict, Any

from app.utils.logger import get_logger
from app.events.schema import Event, EventType, EventSeverity
from app.events.bus import EventBus
from app.storage.database import AsyncSessionLocal
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.storage.models import FeatureValue, Feature

logger = get_logger(__name__)

class OnlineStoreSyncWorker:
    """
    Dedicated worker that subscribes to FEATURE_VALUES_CREATED events
    and synchronizes extracted features from PostgreSQL into the Redis Online Feature Store.
    """
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe(EventType.FEATURE_VALUES_CREATED, self.handle_sync)

    async def handle_sync(self, event: Event):
        dataset_id = event.payload.get("dataset_id")
        dataset_name = event.payload.get("dataset_name")
        
        logger.info(f"[SyncWorker] Received FEATURE_VALUES_CREATED for dataset {dataset_name}. Starting sync to Online Store.")
        
        try:
            async with AsyncSessionLocal() as session:
                # Query all FeatureValues for this dataset
                result = await session.execute(
                    select(FeatureValue)
                    .options(selectinload(FeatureValue.feature))
                    .join(FeatureValue.feature)
                    .filter(Feature.dataset_id == dataset_id, FeatureValue.status != 'ARCHIVED')
                )
                feature_values = result.scalars().all()
                
                if not feature_values:
                    logger.warning(f"[SyncWorker] No FeatureValues found for dataset {dataset_name} in PostgreSQL.")
                    return
                
                # Repackage by entity_id
                entity_features_map: Dict[str, Dict[str, Any]] = {}
                for fv in feature_values:
                    if fv.feature and fv.feature.name:
                        entity_id = fv.entity_id
                        if entity_id not in entity_features_map:
                            entity_features_map[entity_id] = {}
                        
                        val = fv.value_json
                        if isinstance(val, dict) and "value" in val:
                            entity_features_map[entity_id][fv.feature.name] = val["value"]
                        else:
                            entity_features_map[entity_id][fv.feature.name] = val

                # Call OnlineFeatureStore to do batch store
                from app.cache.online_store import get_online_store
                online_store = get_online_store()
                
                await online_store.store_online_features_batch(
                    dataset=dataset_id,
                    entity_features_map=entity_features_map,
                    feature_version=1,
                    dataset_version=1
                )
                
                logger.info(f"[SyncWorker] Successfully synchronized {len(entity_features_map)} entities to Redis Online Store for dataset {dataset_name}.")
                
                # Publish event that sync is complete
                await self.bus.publish(Event(
                    type=EventType.ONLINE_STORE_SYNCED,
                    source="sync.worker",
                    severity=EventSeverity.INFO,
                    payload={"dataset_id": dataset_id, "dataset_name": dataset_name, "entity_count": len(entity_features_map)}
                ))

        except Exception as e:
            logger.error(f"[SyncWorker] Failed to sync features for dataset {dataset_name}: {e}")
            await self.bus.publish(Event(
                type=EventType.JOB_FAILED,
                source="sync.worker",
                severity=EventSeverity.ERROR,
                payload={"dataset_id": dataset_id, "dataset_name": dataset_name, "error": str(e)}
            ))
