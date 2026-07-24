import asyncio
from typing import Dict, Any, Optional

from app.utils.logger import get_logger
from app.storage.database import AsyncSessionLocal
from app.storage.models import ExplanationMetadata
from app.explainability.explainer import ExplainerEngine
from app.explainability.cache import get_explanation_cache
from app.monitoring.audit import AuditLogger, AuditEvent

logger = get_logger(__name__)


class ExplanationManager:
    """
    Coordinates caching, SHAP execution, and PostgreSQL persistence asynchronously.
    """

    def __init__(self):
        self.cache = get_explanation_cache()
        self.explainer = ExplainerEngine()

    async def check_cache(self, model_id: str, m_ver: str, f_ver: str, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fast synchronous-like check of the cache before background generation."""
        try:
            cached_data, src = await self.cache.get_explanation(model_id, m_ver, f_ver, features)
            return cached_data
        except Exception as e:
            logger.warning(f"Failed to check explanation cache: {e}")
            return None

    async def generate_background(
        self,
        prediction_id: str,
        model_id: str,
        m_ver: str,
        f_ver: str,
        features: Dict[str, Any],
        predictor: Any,
        user_id: Optional[str] = None
    ):
        """
        Designed to run in FastAPI BackgroundTasks.
        """
        logger.info(f"Starting background explanation generation for prediction {prediction_id}")
        try:
            # 1. Check Redis Cache
            cached_data, src = await self.cache.get_explanation(model_id, m_ver, f_ver, features)

            if cached_data:
                logger.info(f"Explanation cache HIT for {prediction_id}")
                async with AsyncSessionLocal() as session:
                    await AuditLogger.record(session, AuditEvent(event_name="SHAP_CACHE_HIT", component="Explainability", severity="INFO", payload={"prediction_id": prediction_id}))
                    await session.commit()
                # Even on cache hit, we might want to store metadata in PG if it doesn't exist for this specific prediction_id
                await self._persist_metadata(
                    prediction_id=prediction_id,
                    model_id=model_id,
                    user_id=user_id,
                    cache_status="HIT",
                    generation_time_ms=0.0,
                    expl_data=cached_data,
                    hash_val=self.cache.compute_hash(features),
                    m_ver=m_ver,
                    f_ver=f_ver
                )
                return

            # 2. Cache MISS -> Generate using SHAP
            logger.info(f"Explanation cache MISS for {prediction_id}. Executing SHAP...")
            async with AsyncSessionLocal() as session:
                await AuditLogger.record(session, AuditEvent(event_name="SHAP_CACHE_MISS", component="Explainability", severity="INFO", payload={"prediction_id": prediction_id}))
                await session.commit()

            # Execute SHAP
            # Note: For thread safety, we might want to offload to threadpool if this is blocking,
            # but since we're in a BackgroundTask, it's already executing outside the main request.
            # We'll use asyncio.to_thread to be safe since SHAP is CPU bound.
            expl_data, exec_time = await asyncio.to_thread(
                self.explainer.generate_explanation,
                model=predictor.model,
                features=features
            )

            # 3. Store in Redis
            await self.cache.store_explanation(model_id, m_ver, f_ver, features, expl_data)

            # 4. Persist to PostgreSQL
            await self._persist_metadata(
                prediction_id=prediction_id,
                model_id=model_id,
                user_id=user_id,
                cache_status="MISS",
                generation_time_ms=exec_time,
                expl_data=expl_data,
                hash_val=self.cache.compute_hash(features),
                m_ver=m_ver,
                f_ver=f_ver
            )

            async with AsyncSessionLocal() as session:
                await AuditLogger.record(session, AuditEvent(event_name="SHAP_GENERATED", component="Explainability", severity="INFO", payload={"prediction_id": prediction_id, "latency_ms": exec_time}))
                await session.commit()

        except Exception as e:
            logger.error(f"Background explanation generation failed for {prediction_id}: {e}")
            async with AsyncSessionLocal() as session:
                await AuditLogger.record(session, AuditEvent(event_name="SHAP_FAILED", component="Explainability", severity="ERROR", payload={"prediction_id": prediction_id, "error": str(e)}))
                await session.commit()

    async def _persist_metadata(
        self,
        prediction_id: str,
        model_id: str,
        user_id: Optional[str],
        cache_status: str,
        generation_time_ms: float,
        expl_data: Dict[str, Any],
        hash_val: str,
        m_ver: str,
        f_ver: str
    ):
        import shap
        shap_version = shap.__version__

        # Determine Dataset Health Score
        dataset_health_score = None
        expectation_suite_version = None

        try:
            from app.storage.models import Model
            from app.data_quality.models import ValidationRun
            from sqlalchemy.future import select
            from sqlalchemy import desc

            async with AsyncSessionLocal() as session:
                # Get dataset ID
                model_stmt = select(Model).filter_by(id=model_id)
                model_res = await session.execute(model_stmt)
                model_obj = model_res.scalar_one_or_none()

                if model_obj:
                    # Get Validation Run
                    val_stmt = select(ValidationRun).join(ValidationRun.dataset_version)\
                        .filter(ValidationRun.dataset_version.has(dataset_id=model_obj.dataset_id))\
                        .order_by(desc(ValidationRun.created_at)).limit(1)
                    val_res = await session.execute(val_stmt)
                    latest_val = val_res.scalar_one_or_none()

                    if latest_val:
                        dataset_health_score = latest_val.quality_score
                        # Try to get suite version if joined, but simple default is ok

        except Exception as e:
            logger.warning(f"Could not fetch dataset health score for explanation: {e}")

        async with AsyncSessionLocal() as session:
            meta = ExplanationMetadata(
                prediction_id=prediction_id,
                model_id=model_id,
                user_id=user_id,
                generation_time_ms=generation_time_ms,
                cache_status=cache_status,
                top_features=expl_data.get("top_features"),
                visualization_data=expl_data.get("visualization_data"),
                hash=hash_val,
                model_version=m_ver,
                feature_version=f_ver,
                shap_library_version=shap_version,
                dataset_health_score=dataset_health_score,
                expectation_suite_version=expectation_suite_version
            )
            session.add(meta)
            await session.commit()
