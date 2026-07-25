import os
import time
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime, timezone

import mlflow
from mlflow.client import MlflowClient

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.config import settings
from app.storage.models import Experiment, DatasetVersion
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Configure MLflow Tracking URI
# Ensure we use psycopg2 for MLflow's synchronous SQLAlchemy backend
_db_url = settings.database_url or ""
if "+asyncpg" in _db_url:
    _db_url = _db_url.replace("+asyncpg", "+psycopg2")
elif _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg2://")

if "?" in _db_url:
    _db_url += "&options=-csearch_path%3Dmlflow"
else:
    _db_url += "?options=-csearch_path%3Dmlflow"

mlflow.set_tracking_uri(_db_url)
ARTIFACT_DIR = os.path.abspath("artifacts")
if not os.path.exists(ARTIFACT_DIR):
    os.makedirs(ARTIFACT_DIR)


class MLflowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = MlflowClient()

    async def run_training(
        self,
        dataset_id: str,
        algorithm: str,
        hyperparameters: Dict[str, Any],
        target_column: str = "target"
    ) -> Experiment:

        # 1. Setup MLflow Experiment
        experiment_name = f"FeatureFlow_{dataset_id}"
        exp = mlflow.get_experiment_by_name(experiment_name)
        if not exp:
            import pathlib
            artifact_uri = pathlib.Path(ARTIFACT_DIR).joinpath(experiment_name).as_uri()
            exp_id = mlflow.create_experiment(
                name=experiment_name,
                artifact_location=artifact_uri
            )
            from app.observability.instrumentation import record_mlflow_experiment_created
            record_mlflow_experiment_created()
        else:
            exp_id = exp.experiment_id

        mlflow.set_experiment(experiment_id=exp_id)

        # 2. Fetch Dataset
        result = await self.session.execute(
            select(DatasetVersion)
            .filter_by(dataset_id=dataset_id)
            .order_by(desc(DatasetVersion.created_at))
            .limit(1)
        )
        version = result.scalar_one_or_none()
        if not version or not version.file_path:
            raise ValueError(f"No valid dataset version or file_path found for dataset {dataset_id}")

        if not os.path.exists(version.file_path):
            raise FileNotFoundError(f"Data file not found at {version.file_path}")

        df = pd.read_csv(version.file_path)
        if target_column not in df.columns:
            # Fallback or error, for fast track we assume first/last column if not found
            target_column = df.columns[-1]

        y = df[target_column]
        X = df.drop(columns=[target_column])

        # Select trainer
        trainer = None
        if algorithm == "LogisticRegression":
            from app.training.trainer import LogisticRegressionTrainer
            trainer = LogisticRegressionTrainer(**hyperparameters)
        elif algorithm == "RandomForest":
            from app.training.trainer import RandomForestTrainer
            trainer = RandomForestTrainer(**hyperparameters)
        elif algorithm == "DecisionTree":
            from app.training.trainer import DecisionTreeTrainer
            trainer = DecisionTreeTrainer(**hyperparameters)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # 3. MLflow Run
        started_at = datetime.now(timezone.utc)
        start_time = time.time()

        with mlflow.start_run(experiment_id=exp_id) as run:
            run_id = run.info.run_id

            # Log params
            mlflow.log_param("algorithm", algorithm)
            mlflow.log_params(hyperparameters)
            mlflow.log_param("dataset_id", dataset_id)

            # Train
            model = trainer.train(X, y)

            # Basic eval metrics for demonstration (accuracy on train set)
            accuracy = model.score(X, y)
            metrics = {"accuracy": float(accuracy)}
            mlflow.log_metrics(metrics)

            # Log Model
            model_name = f"model_{dataset_id[:8]}"
            model_info = mlflow.sklearn.log_model(
                sk_model=model,
                name="model",
                registered_model_name=model_name
            )
            from app.observability.instrumentation import record_mlflow_model_registered
            record_mlflow_model_registered()

            artifact_uri = model_info.model_uri
            model_version = "1"

            # Fetch the latest version from MLflow
            try:
                latest_versions = self.client.search_model_versions(f"name='{model_name}'")
                if latest_versions:
                    model_version = latest_versions[-1].version
            except Exception as e:
                logger.warning(f"Could not fetch latest model versions: {e}")

        duration = time.time() - start_time
        finished_at = datetime.now(timezone.utc)

        # 4. Save Metadata to PostgreSQL
        experiment = Experiment(
            name=f"Run_{algorithm}_{run_id[:8]}",
            dataset_id=dataset_id,
            mlflow_run_id=run_id,
            mlflow_experiment_id=exp_id,
            model_name=model_name,
            model_version=str(model_version),
            status="COMPLETED",
            algorithm=algorithm,
            hyperparameters=hyperparameters,
            metrics=metrics,
            parameters=hyperparameters,
            artifact_uri=artifact_uri,
            duration=duration,
            started_at=started_at,
            finished_at=finished_at
        )
        self.session.add(experiment)
        await self.session.commit()
        await self.session.refresh(experiment)
        return experiment

    def promote_model(self, model_name: str, version: str, alias: str) -> bool:
        self.client.set_registered_model_alias(
            name=model_name,
            alias=alias,
            version=version
        )
        from app.observability.instrumentation import record_mlflow_model_promoted
        record_mlflow_model_promoted(alias)
        return True

    def get_experiments(self):
        return self.client.search_experiments()

    def get_run(self, run_id: str):
        return self.client.get_run(run_id)

    def get_models(self):
        return self.client.search_registered_models()

    def get_latest_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        try:
            model = self.client.get_registered_model(model_name)
            raw_aliases = getattr(model, "aliases", {})
            str_aliases = {k: str(v) for k, v in raw_aliases.items()}
            return {
                "name": model.name,
                "aliases": str_aliases,
                "latest_versions": [
                    {"version": str(v.version), "status": v.current_stage}
                    for v in getattr(model, "latest_versions", [])
                ]
            }
        except Exception as e:
            logger.error(f"Error getting model: {e}")
            return None
