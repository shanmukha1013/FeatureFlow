import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from evidently.legacy.metric_preset import DataDriftPreset
from evidently.legacy.report import Report
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.cache.redis_client import RedisClient
from app.storage.models import DatasetVersion, MonitoringReport
from app.utils.logger import get_logger

logger = get_logger(__name__)

REPORTS_DIR = "reports"


class MonitoringService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis = RedisClient()
        if not os.path.exists(REPORTS_DIR):
            os.makedirs(REPORTS_DIR)

    async def _get_dataset_df(self, dataset_id: str) -> pd.DataFrame:
        result = await self.session.execute(
            select(DatasetVersion)
            .filter_by(dataset_id=dataset_id)
            .order_by(desc(DatasetVersion.created_at))
            .limit(1)
        )
        version = result.scalar_one_or_none()
        if not version or not version.file_path:
            raise ValueError(f"No valid dataset version or file_path found for dataset {dataset_id}")

        # Load data using pandas directly as a fast track.
        # In a full enterprise scenario, we'd use DataLoader abstractions here.
        if not os.path.exists(version.file_path):
            raise FileNotFoundError(f"Data file not found at {version.file_path}")

        return pd.read_csv(version.file_path)

    async def run_drift_analysis(self, reference_dataset_id: str, current_dataset_id: str) -> MonitoringReport:
        logger.info(f"Running drift analysis: ref={reference_dataset_id}, curr={current_dataset_id}")

        # 1. Load Data
        ref_df = await self._get_dataset_df(reference_dataset_id)
        curr_df = await self._get_dataset_df(current_dataset_id)

        # 2. Run Evidently
        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=ref_df, current_data=curr_df)

        report_dict = report.as_dict()
        html_content = report.get_html()

        # Extract metadata
        metrics_summary = report_dict.get("metrics", [])
        dataset_drift_metric = next((m for m in metrics_summary if m.get("metric") == "DatasetDriftMetric"), None)

        drift_detected = False
        stats = {}
        if dataset_drift_metric and "result" in dataset_drift_metric:
            res = dataset_drift_metric["result"]
            drift_detected = res.get("dataset_drift", False)
            stats = {
                "drift_share": res.get("share_of_drifted_columns"),
                "number_of_columns": res.get("number_of_columns"),
                "number_of_drifted_columns": res.get("number_of_drifted_columns"),
            }

        from app.observability.instrumentation import record_drift_check
        record_drift_check(drift_detected)

        # 3. Save HTML to Disk
        report_id = str(uuid.uuid4())
        timestamp_str = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H%M%S")
        html_filename = f"drift_{timestamp_str}_{report_id[:8]}.html"
        html_path = os.path.join(REPORTS_DIR, html_filename)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 4. Save Metadata to PostgreSQL
        monitoring_report = MonitoringReport(
            id=report_id,
            reference_dataset_id=reference_dataset_id,
            current_dataset_id=current_dataset_id,
            drift_detected=drift_detected,
            metrics=stats,
            html_path=html_path,
            status="COMPLETED"
        )
        self.session.add(monitoring_report)
        await self.session.commit()
        await self.session.refresh(monitoring_report)

        # 5. Cache HTML in Redis
        cache_key = f"monitoring:latest:{current_dataset_id}"

        async def _set_cache(client):
            await client.set(cache_key, html_content, ex=86400 * 30)
            return True

        try:
            await self.redis.execute_with_retry(_set_cache)
        except Exception:
            pass

        return monitoring_report

    async def get_latest_report_html(self, dataset_id: str) -> Optional[str]:
        # Try Redis first
        cache_key = f"monitoring:latest:{dataset_id}"

        async def _get_cache(client):
            return await client.get(cache_key)

        try:
            html = await self.redis.execute_with_retry(_get_cache)
        except Exception:
            html = None

        if html:
            return html.decode('utf-8') if isinstance(html, bytes) else html

        # Fallback to PostgreSQL & Disk
        result = await self.session.execute(
            select(MonitoringReport)
            .filter_by(current_dataset_id=dataset_id)
            .order_by(desc(MonitoringReport.created_at))
            .limit(1)
        )
        report = result.scalar_one_or_none()
        if report and report.html_path and os.path.exists(report.html_path):
            with open(report.html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    async def get_history(self, dataset_id: str, limit: int = 10) -> List[MonitoringReport]:
        result = await self.session.execute(
            select(MonitoringReport)
            .filter_by(current_dataset_id=dataset_id)
            .order_by(desc(MonitoringReport.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
