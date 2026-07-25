import asyncio
import io
import pandas as pd
from datetime import datetime, timezone
from app.utils.logger import get_logger
from app.events.schema import Event, EventType, EventSeverity
from app.events.bus import EventBus
from app.storage.database import AsyncSessionLocal
from app.storage.repositories.core import DatasetRepository, FeatureRepository

logger = get_logger(__name__)

class LifecycleOrchestrator:
    """
    Listens to the EventBus and automatically orchestrates the ML feature lifecycle.
    """
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._register_handlers()

    def _register_handlers(self):
        self.bus.subscribe(EventType.DATASET_UPLOADED, self.handle_dataset_uploaded)
        self.bus.subscribe(EventType.DATASET_VALIDATED, self.handle_dataset_validated)
        self.bus.subscribe(EventType.FEATURES_REGISTERED, self.handle_features_registered)
        self.bus.subscribe(EventType.FEATURE_MATERIALIZED, self.handle_feature_materialized)
        self.bus.subscribe(EventType.JOB_COMPLETED, self.handle_job_completed)

    async def handle_dataset_uploaded(self, event: Event):
        logger.info(f"[Lifecycle] Received DATASET_UPLOADED for {event.payload.get('dataset_name')}")
        dataset_id = event.payload.get("dataset_id")
        
        async with AsyncSessionLocal() as session:
            # 1. Fetch data
            from sqlalchemy.future import select
            from app.storage.models import DatasetVersion
            dv_res = await session.execute(
                select(DatasetVersion)
                .filter(DatasetVersion.dataset_id == dataset_id)
                .order_by(DatasetVersion.created_at.desc())
            )
            dataset_version = dv_res.scalars().first()
            if not dataset_version or not dataset_version.raw_data:
                logger.error("[Lifecycle] Raw data not found.")
                return
            
            df = pd.read_csv(io.BytesIO(dataset_version.raw_data))
            
            # 2. Trigger Validation
            from app.data_quality.service import DataQualityService
            dq_service = DataQualityService(session)
            should_halt, health_score = await dq_service.validate_dataset(event.payload.get("dataset_name"), dataset_version, df)
            
            if should_halt:
                await self.bus.publish(Event(
                    type=EventType.DATASET_FAILED,
                    source="lifecycle.orchestrator",
                    severity=EventSeverity.ERROR,
                    payload={"dataset_id": dataset_id, "reason": "Data Quality Validation Failed"}
                ))
                return
                
            # 3. Publish Validated Event
            await self.bus.publish(Event(
                type=EventType.DATASET_VALIDATED,
                source="lifecycle.orchestrator",
                severity=EventSeverity.INFO,
                payload={
                    "dataset_id": dataset_id,
                    "dataset_name": event.payload.get("dataset_name"),
                    "health_score": health_score
                }
            ))

    async def handle_dataset_validated(self, event: Event):
        logger.info(f"[Lifecycle] Received DATASET_VALIDATED for {event.payload.get('dataset_name')}")
        dataset_id = event.payload.get("dataset_id")
        dataset_name = event.payload.get("dataset_name")
        
        async with AsyncSessionLocal() as session:
            # Fetch df
            from sqlalchemy.future import select
            from app.storage.models import DatasetVersion, Feature
            import uuid
            
            dv_res = await session.execute(
                select(DatasetVersion)
                .filter(DatasetVersion.dataset_id == dataset_id)
                .order_by(DatasetVersion.created_at.desc())
            )
            dataset_version = dv_res.scalars().first()
            if not dataset_version or not dataset_version.raw_data:
                return
            
            df = pd.read_csv(io.BytesIO(dataset_version.raw_data))
            
            # Baseline Profiling & Feature Extraction
            from app.monitoring.drift.baseline import BaselineProfiler
            try:
                profile = BaselineProfiler.compute_baseline(df, pd.Series([1]*len(df))) # Dummy target
            except Exception as e:
                logger.warning(f"Baseline profiling skipped: {e}")
                profile = {}
            
            # Auto-register features
            existing_features_res = await session.execute(
                select(Feature).filter(Feature.dataset_id == dataset_id)
            )
            existing_feature_names = {f.name for f in existing_features_res.scalars().all()}
            
            new_features = []
            for col in df.columns:
                if col in existing_feature_names:
                    continue
                dtype_str = str(df[col].dtype)
                feature = Feature(
                    id=str(uuid.uuid4()),
                    dataset_id=dataset_id,
                    name=col,
                    dtype=dtype_str,
                    transformation="passthrough",
                    status="ACTIVE",
                    version=1
                )
                session.add(feature)
                new_features.append(col)
            
            await session.commit()
            
            # Publish Profiling and Feature events
            await self.bus.publish(Event(
                type=EventType.DATASET_PROFILED,
                source="lifecycle.orchestrator",
                severity=EventSeverity.INFO,
                payload={"dataset_id": dataset_id, "profile_keys": list(profile.keys()) if isinstance(profile, dict) else []}
            ))
            
            await self.bus.publish(Event(
                type=EventType.FEATURES_REGISTERED,
                source="lifecycle.orchestrator",
                severity=EventSeverity.INFO,
                payload={"dataset_id": dataset_id, "dataset_name": dataset_name, "new_features": new_features}
            ))

    async def handle_features_registered(self, event: Event):
        logger.info(f"[Lifecycle] Received FEATURES_REGISTERED for {event.payload.get('dataset_name')}")
        dataset_id = event.payload.get("dataset_id")
        dataset_name = event.payload.get("dataset_name")
        
        # Trigger Materialization (Offline Feature Store)
        from app.features.materializer import FeatureMaterializer
        asyncio.create_task(FeatureMaterializer(self.bus).materialize(dataset_id, dataset_name))

    async def handle_feature_materialized(self, event: Event):
        logger.info(f"[Lifecycle] Received FEATURE_MATERIALIZED for {event.payload.get('dataset_name')}")
        dataset_id = event.payload.get("dataset_id")
        dataset_name = event.payload.get("dataset_name")
        
        # Human-in-the-Loop Intelligence
        # Instead of automatically orchestrating the training, we inform the Canvas
        # that the Feature Group is materialized and recommend the next action (Training).
        await self.bus.publish(Event(
            type=EventType.READY_FOR_TRAINING,
            source="lifecycle.orchestrator",
            severity=EventSeverity.INFO,
            payload={
                "dataset_id": dataset_id,
                "dataset_name": dataset_name,
                "recommendation": "Features are fully materialized. Proceed to model training."
            }
        ))

    async def handle_job_completed(self, event: Event):
        logger.info(f"[Lifecycle] Received JOB_COMPLETED for model {event.payload.get('model_name')}")
        
        await self.bus.publish(Event(
            type=EventType.READY_FOR_DEPLOYMENT,
            source="lifecycle.orchestrator",
            severity=EventSeverity.INFO,
            payload={
                "model_id": event.payload.get("model_id"),
                "model_name": event.payload.get("model_name"),
                "recommendation": "Training completed successfully. Review metrics and deploy to inference."
            }
        ))
