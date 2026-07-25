import io
import pandas as pd
from app.utils.logger import get_logger
from app.events.schema import Event, EventType, EventSeverity
from app.events.bus import EventBus
from app.storage.database import AsyncSessionLocal
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)

class FeatureMaterializer:
    """
    Computes the canonical state of features offline and saves the materialized dataset.
    This fulfills the Enterprise Feature Store requirement to execute features
    once before training.
    """
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def materialize(self, dataset_id: str, dataset_name: str):
        logger.info(f"[Materializer] Starting offline materialization for dataset {dataset_name}")
        try:
            async with AsyncSessionLocal() as session:
                # 1. Fetch latest DatasetVersion
                from app.storage.models import DatasetVersion, Feature
                dv_res = await session.execute(
                    select(DatasetVersion)
                    .filter(DatasetVersion.dataset_id == dataset_id)
                    .order_by(DatasetVersion.created_at.desc())
                )
                dataset_version = dv_res.scalars().first()
                if not dataset_version or not dataset_version.raw_data:
                    logger.error(f"[Materializer] No raw data found for {dataset_name}")
                    return

                df = pd.read_csv(io.BytesIO(dataset_version.raw_data))

                # 2. Fetch Features
                f_res = await session.execute(
                    select(Feature)
                    .options(selectinload(Feature.dataset))
                    .filter(Feature.dataset_id == dataset_id, Feature.status == "ACTIVE")
                )
                features = f_res.scalars().all()
                if not features:
                    logger.warning(f"[Materializer] No active features found for {dataset_name}")
                    return

                # 3. Fit & Transform
                from app.features.transformer import FeatureTransformer
                transformer = FeatureTransformer()
                
                logger.info(f"[Materializer] Fitting {len(features)} features...")
                transformer.fit(df, features)
                
                logger.info(f"[Materializer] Transforming raw data...")
                materialized_df = transformer.transform(df, features)
                
                # 4. Save materialized data (Parquet)
                parquet_buffer = io.BytesIO()
                materialized_df.to_parquet(parquet_buffer, index=False)
                dataset_version.materialized_data = parquet_buffer.getvalue()
                
                # We also commit the feature states computed by `fit()`
                await session.commit()
                logger.info(f"[Materializer] Successfully materialized {len(materialized_df)} rows for {dataset_name}")

            # Publish event
            await self.bus.publish(Event(
                type=EventType.FEATURE_MATERIALIZED,
                source="feature.materializer",
                severity=EventSeverity.INFO,
                payload={"dataset_id": dataset_id, "dataset_name": dataset_name}
            ))
            
        except Exception as e:
            logger.error(f"[Materializer] Materialization failed for {dataset_name}: {e}")
            await self.bus.publish(Event(
                type=EventType.JOB_FAILED,
                source="feature.materializer",
                severity=EventSeverity.ERROR,
                payload={"dataset_id": dataset_id, "dataset_name": dataset_name, "error": str(e)}
            ))
