import time
import numpy as np
import pandas as pd
from typing import Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
import great_expectations as gx

from app.storage.models import DatasetVersion
from app.data_quality.models import ExpectationResult
from app.data_quality.contracts import DataContractEngine
from app.data_quality.suites import ExpectationSuiteEngine
from app.data_quality.validator import GXEphemeralValidator
from app.data_quality.gates import QualityGate
from app.data_quality.repositories import ValidationRunRepository, ExpectationResultRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_for_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return str(obj)
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    elif pd.isna(obj):
        return None
    return obj


class DataQualityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.contract_engine = DataContractEngine(session)
        self.suite_engine = ExpectationSuiteEngine(session)
        self.validator = GXEphemeralValidator()
        self.run_repo = ValidationRunRepository(session)
        self.result_repo = ExpectationResultRepository(session)

    async def validate_dataset(self, dataset_name: str, dataset_version: DatasetVersion, df: pd.DataFrame, pipeline_run_id: str = None) -> Tuple[bool, float]:
        """
        Main pipeline integration point.
        Returns (should_halt, health_score)
        """
        start_time = time.time()
        logger.info(f"Starting Data Quality validation for {dataset_name} (v{dataset_version.version})")

        # 1. Get or Create Contract
        contract = await self.contract_engine.get_or_create_contract(dataset_name, df)

        # 2. Get or Create Suite
        suite_model, gx_suite = await self.suite_engine.get_or_create_suite(contract)

        # 3. Execute GX Validation
        validation_results = self.validator.validate(df, gx_suite, dataset_name)

        # 4. Evaluate Gates & Health Score
        should_halt, health_score, counts = QualityGate.evaluate(validation_results)
        execution_time_ms = (time.time() - start_time) * 1000

        # 5. Persist Validation Run
        gx_version = gx.__version__
        checksum = None  # Handled by discovery logic primarily

        run = await self.run_repo.create(
            suite_id=suite_model.id,
            dataset_version_id=dataset_version.id,
            success=validation_results.success,
            quality_score=health_score,
            execution_time_ms=execution_time_ms,
            counts=counts,
            gx_version=gx_version,
            dataset_checksum=checksum
        )
        run.pipeline_run_id = pipeline_run_id
        await self.session.flush()

        # 6. Persist Granular Results
        db_results = []
        for res in validation_results.results:
            meta = res.expectation_config.meta if res.expectation_config else {}

            # Extract basic Python types to avoid JSON serialization errors of nested GX structures
            json_dict = res.to_json_dict()
            kwargs = json_dict.get("expectation_config", {}).get("kwargs", {})
            safe_kwargs = sanitize_for_json({k: v for k, v in kwargs.items() if not k.startswith('_')})

            result_data = sanitize_for_json(json_dict.get("result", {}))
            observed = result_data.get("observed_value")
            observed_str = str(observed) if observed is not None else None

            db_res = ExpectationResult(
                validation_run_id=run.id,
                expectation_type=res.expectation_config.expectation_type if res.expectation_config else "unknown",
                severity=meta.get("severity", "ERROR"),
                success=res.success,
                kwargs=safe_kwargs,
                observed_value=observed_str,
                result_data=result_data,
                exception_info=str(res.exception_info) if res.exception_info else None
            )
            db_results.append(db_res)

        await self.result_repo.create_bulk(db_results)

        logger.info(f"Data Quality validation completed. Health Score: {health_score:.1f}. Halting: {should_halt}")

        # 7. Update Cache
        try:
            from app.data_quality.manager import DataQualityCacheManager
            cache_mgr = DataQualityCacheManager()
            await cache_mgr.cache_health_score(dataset_name, health_score)

            summary = {
                "success": validation_results.success,
                "score": health_score,
                "critical": counts["critical"],
                "error": counts["error"],
                "warning": counts["warning"],
                "time_ms": execution_time_ms
            }
            await cache_mgr.cache_validation_summary(dataset_version.id, summary)
        except Exception as e:
            logger.warning(f"Failed to update data quality cache: {e}")

        return should_halt, health_score
