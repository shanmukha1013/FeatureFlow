import io

import pandas as pd
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.events.bus import EventBus
from app.events.schema import Event, EventSeverity, EventType
from app.storage.database import AsyncSessionLocal
from app.utils.logger import get_logger

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

                logger.info("[Materializer] Transforming raw data...")
                materialized_df = transformer.transform(df, features)

                # Retrieve the actual entity column name from Dataset
                from app.storage.models import Dataset
                ds_res = await session.execute(select(Dataset).filter(Dataset.id == dataset_id))
                dataset_record = ds_res.scalars().first()
                entity_col = dataset_record.entity_key_column if dataset_record and dataset_record.entity_key_column else "_entity_id"

                # Copy the entity key column from raw data into materialized_df so it can be extracted
                if entity_col in df.columns:
                    materialized_df[entity_col] = df[entity_col]

                # 4. Save materialized data (Parquet)
                parquet_buffer = io.BytesIO()
                materialized_df.to_parquet(parquet_buffer, index=False)
                dataset_version.materialized_data = parquet_buffer.getvalue()

                # 5. Extract and Persist Feature Values (Offline Store / Source of Truth)
                import uuid

                from app.storage.models import Dataset, FeatureValue

                logger.info("[Materializer] Extracting feature values to PostgreSQL...")
                ds_res = await session.execute(select(Dataset).filter(Dataset.id == dataset_id))
                dataset_record = ds_res.scalars().first()
                entity_col = dataset_record.entity_key_column if dataset_record and dataset_record.entity_key_column else "_entity_id"

                # Map feature name -> feature_id
                feature_name_to_id = {f.name: f.id for f in features}

                feature_values_to_insert = []
                for _, row in materialized_df.iterrows():
                    entity_id = str(row.get(entity_col, uuid.uuid4()))
                    for f_name, f_id in feature_name_to_id.items():
                        if f_name in row:
                            val = row[f_name]
                            if pd.isna(val):
                                val = None
                            elif hasattr(val, "item"):
                                val = val.item()  # convert numpy types

                            feature_values_to_insert.append({
                                "id": str(uuid.uuid4()),
                                "feature_id": f_id,
                                "entity_id": entity_id,
                                "value_json": {"value": val},
                                "status": "ACTIVE",
                                "version": 1
                            })

                if feature_values_to_insert:
                    from sqlalchemy import insert
                    await session.execute(insert(FeatureValue).values(feature_values_to_insert))

                # We also commit the feature states computed by `fit()` and inserted FeatureValues
                await session.commit()
                logger.info(f"[Materializer] Successfully materialized {len(materialized_df)} rows and persisted {len(feature_values_to_insert)} feature values for {dataset_name}")

            # Publish events
            await self.bus.publish(Event(
                type=EventType.FEATURE_MATERIALIZED,
                source="feature.materializer",
                severity=EventSeverity.INFO,
                payload={"dataset_id": dataset_id, "dataset_name": dataset_name}
            ))

            await self.bus.publish(Event(
                type=EventType.FEATURE_VALUES_CREATED,
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
