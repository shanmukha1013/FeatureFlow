import time
import pandas as pd
from typing import List
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger
from app.features.transformer import FeatureTransformer
from app.training.dataset import TrainingDatasetBuilder
from app.training.splitter import RandomSplitter
from app.training.trainer import LogisticRegressionTrainer, DecisionTreeTrainer, RandomForestTrainer
from app.training.evaluator import ClassificationEvaluator
from app.training.artifacts import LocalArtifactStore
from app.monitoring.audit import AuditLogger, AuditEvent
from app.storage.repositories.core import ModelRepository, ChampionModelRepository, ExperimentRepository, FeatureRepository
from app.storage.models import Dataset, Feature

logger = get_logger(__name__)

class TrainingOrchestrator:
    def __init__(self, data_dir: str = "datasets/raw"):
        self.data_dir = data_dir
        self.dataset_builder = TrainingDatasetBuilder()
        self.splitter = RandomSplitter(test_size=0.2)
        self.evaluator = ClassificationEvaluator()
        self.artifact_store = LocalArtifactStore()
        self.feature_transformer = FeatureTransformer()

    def _select_target_column(self, df: pd.DataFrame, dataset_name: str) -> str:
        """Heuristically select a low/medium-cardinality target column for automated classification training."""
        for col in df.columns:
            lower = col.lower()
            if lower in ['target', 'label', 'class', 'outcome', 'status', 'category', 'tier', 'type']:
                if df[col].nunique() <= min(50, len(df) // 2):
                    return col
            if lower.startswith('is_') or lower.startswith('has_'):
                if df[col].nunique() <= min(50, len(df) // 2):
                    return col
                
        valid_cols = []
        for c in df.columns:
            lower = c.lower()
            if lower.endswith('id') or 'uuid' in lower or 'ref' in lower or 'date' in lower or 'time' in lower or lower.endswith('_at') or 'timestamp' in lower:
                continue
            if df[c].nunique() > 50 and df[c].nunique() > min(50, len(df) * 0.1):
                continue
            valid_cols.append(c)
            
        if valid_cols:
            return valid_cols[-1]
            
        candidates = [(c, df[c].nunique()) for c in df.columns if df[c].nunique() > 1 and not c.lower().endswith('id') and not c.lower().endswith('_at')]
        if candidates:
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]
            
        return df.columns[-1]

    async def _get_features_for_dataset(self, session: AsyncSession, dataset_id: str) -> List[Feature]:
        feature_repo = FeatureRepository(session)
        features = await feature_repo.get_by_dataset(dataset_id)
        return features

    async def execute(self, session: AsyncSession, dataset_record: Dataset, relative_path: str = None) -> None:
        dataset_name = dataset_record.name
        logger.info(f"Starting Training Orchestration for dataset '{dataset_name}'")
        
        try:
            from app.data.loader import CSVDataLoader
            loader = CSVDataLoader(self.data_dir)
            if not relative_path:
                relative_path = f"raw/{dataset_name}.csv"
            df_raw = loader.load(relative_path)
            
            target_col = self._select_target_column(df_raw, dataset_name)
            
            features = await self._get_features_for_dataset(session, dataset_record.id)
            
            if not features:
                logger.warning(f"No engineered features found for dataset {dataset_name}. Skipping training.")
                return
                
            logger.info(f"Transforming {len(features)} features for training.")
            df_features = self.feature_transformer.transform(df_raw, features)
            
            df_features[target_col] = df_raw[target_col]
            df_features.dropna(subset=[target_col], inplace=True)
            
            if df_features[target_col].nunique() > 10:
                logger.info(f"Target column '{target_col}' has {df_features[target_col].nunique()} unique values. Discretizing to top 5 categories + 'Other' for classification stability.")
                top_classes = set(df_features[target_col].value_counts().nlargest(5).index)
                df_features[target_col] = df_features[target_col].apply(lambda x: x if x in top_classes else 'Other')
            
            from sklearn.preprocessing import LabelEncoder
            df_features[target_col] = LabelEncoder().fit_transform(df_features[target_col].astype(str))
            
            feature_names = [f.name for f in features]
            X, y = self.dataset_builder.prepare(df_features, feature_names, target_col)
            
            X_train, X_test, y_train, y_test = self.splitter.split(X, y)
            
            trainers = [
                LogisticRegressionTrainer(max_iter=1000),
                DecisionTreeTrainer(max_depth=5),
                RandomForestTrainer(n_estimators=100, max_depth=5)
            ]
            
            models_trained = []
            experiment_repo = ExperimentRepository(session)
            model_repo = ModelRepository(session)
            champion_repo = ChampionModelRepository(session)
            
            for trainer in trainers:
                algo_name = trainer.algorithm_name
                
                exp_name = f"Train {algo_name} on {dataset_name}"
                
                experiment = await experiment_repo.create({
                    "dataset_id": dataset_record.id,
                    "name": exp_name,
                    "algorithm": algo_name,
                    "hyperparameters": trainer.hyperparameters,
                    "status": "RUNNING"
                })
                
                await AuditLogger.record(session, AuditEvent(event_name="EXPERIMENT_STARTED", component="TrainingOrchestrator", severity="INFO", payload={"experiment_id": experiment.id}))
                await AuditLogger.record(session, AuditEvent(event_name="TRAINING_STARTED", component="TrainingOrchestrator", severity="INFO", payload={"algorithm": algo_name, "dataset": dataset_name}))
                
                start_time = time.time()
                try:
                    # 1. Train
                    ml_model = trainer.train(X_train, y_train)
                    train_duration = (time.time() - start_time) * 1000
                    
                    await AuditLogger.record(session, AuditEvent(event_name="TRAINING_FINISHED", component="TrainingOrchestrator", severity="INFO", payload={"algorithm": algo_name, "duration_ms": train_duration}))
                    
                    # 2. Evaluate
                    metrics = self.evaluator.evaluate(ml_model, X_test, y_test)
                    await AuditLogger.record(session, AuditEvent(event_name="EVALUATION_FINISHED", component="TrainingOrchestrator", severity="INFO", payload={"algorithm": algo_name, "accuracy": metrics.get("accuracy", 0)}))
                    
                    # 3. Model Versioning & ID
                    # Check existing models for versioning
                    existing_model = await model_repo.get_by_dataset_and_name(dataset_record.id, algo_name)
                    version = 1
                    if existing_model:
                        version = existing_model.version + 1
                    
                    model_id_str = f"mdl_{dataset_name}_{algo_name.lower()}_v{version}"
                    
                    # 4. Save Artifact
                    artifact_path, checksum = self.artifact_store.save(ml_model, model_id_str, f"v{version}")
                    if isinstance(metrics, dict):
                        metrics["_checksum"] = checksum
                    await AuditLogger.record(session, AuditEvent(event_name="ARTIFACT_SAVED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id_str, "checksum": checksum}))
                    
                    # 5. Explainability & Baseline Profiling
                    from app.training.explainability import GlobalExplainer
                    from app.monitoring.drift.baseline import BaselineProfiler
                    
                    explainer = GlobalExplainer()
                    feat_imp = explainer.compute_feature_importance(ml_model, feature_names)
                    shap_summ = explainer.compute_shap_summary(ml_model, X_train)
                    
                    baseline_profile = BaselineProfiler.compute_baseline(X_train, y_train)
                    await AuditLogger.record(session, AuditEvent(event_name="BASELINE_UPDATED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id_str, "baseline_features": len(baseline_profile) if isinstance(baseline_profile, dict) else 0}))
                    
                    if feat_imp:
                        await AuditLogger.record(session, AuditEvent(event_name="EXPLANATION_GENERATED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id_str}))
                    if shap_summ:
                        await AuditLogger.record(session, AuditEvent(event_name="SHAP_GENERATED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id_str}))
                        
                    # 6. Register Model
                    if existing_model:
                        # Update existing
                        meta = await model_repo.update(existing_model, {
                            "version": version,
                            "metrics": metrics,
                            "hyperparameters": trainer.hyperparameters,
                            "artifact_uri": artifact_path,
                            "status": "CANDIDATE"
                        })
                    else:
                        meta = await model_repo.create({
                            "dataset_id": dataset_record.id,
                            "name": algo_name,
                            "version": version,
                            "metrics": metrics,
                            "hyperparameters": trainer.hyperparameters,
                            "artifact_uri": artifact_path,
                            "status": "CANDIDATE"
                        })
                        
                    models_trained.append(meta)
                    
                    # Complete Experiment
                    await experiment_repo.update(experiment, {
                        "status": "COMPLETED",
                        "metrics": metrics,
                        "model_id": meta.id,
                        "end_time": datetime.now(timezone.utc)
                    })
                    await AuditLogger.record(session, AuditEvent(event_name="EXPERIMENT_FINISHED", component="TrainingOrchestrator", severity="INFO", payload={"experiment_id": experiment.id}))
                    await AuditLogger.record(session, AuditEvent(event_name="MODEL_REGISTERED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": meta.id}))
                    
                except Exception as e:
                    await experiment_repo.update(experiment, {
                        "status": "FAILED",
                        "end_time": datetime.now(timezone.utc)
                    })
                    await AuditLogger.record(session, AuditEvent(event_name="EXPERIMENT_FAILED", component="TrainingOrchestrator", severity="ERROR", payload={"experiment_id": experiment.id}))
                    await AuditLogger.record(session, AuditEvent(event_name="TRAINING_FAILED", component="TrainingOrchestrator", severity="ERROR", payload={"algorithm": algo_name, "error": str(e)}))
                    logger.error(f"Failed to train {algo_name}: {e}")
                    
            # 6. Champion Selection & Promotion Rules
            if models_trained:
                best_candidate = max(models_trained, key=lambda m: m.metrics.get('accuracy', 0))
                best_acc = best_candidate.metrics.get('accuracy', 0)
                
                # Find current active champion for this dataset
                current_champion_record = await champion_repo.get_by_dataset(dataset_record.id)
                
                if current_champion_record:
                    # load model
                    current_champion_model = await model_repo.get(current_champion_record.model_id)
                    current_acc = current_champion_model.metrics.get('accuracy', 0) if current_champion_model else 0
                    
                    if best_acc > current_acc:
                        # Promote new
                        await champion_repo.update(current_champion_record, {
                            "model_id": best_candidate.id
                        })
                        await AuditLogger.record(session, AuditEvent(event_name="CHAMPION_PROMOTED", component="TrainingOrchestrator", severity="INFO", payload={"new_champion": best_candidate.id, "accuracy": best_acc, "previous_champion": current_champion_model.id if current_champion_model else None}))
                        logger.info(f"Champion promoted: {best_candidate.id} outperformed old champion")
                    else:
                        logger.info(f"Candidate {best_candidate.id} ({best_acc:.4f}) failed to beat champion ({current_acc:.4f}). Archived.")
                else:
                    # First time training on this dataset version
                    await champion_repo.create({
                        "dataset_id": dataset_record.id,
                        "model_id": best_candidate.id
                    })
                    await AuditLogger.record(session, AuditEvent(event_name="CHAMPION_PROMOTED", component="TrainingOrchestrator", severity="INFO", payload={"new_champion": best_candidate.id, "accuracy": best_acc}))
                    logger.info(f"Initial champion promoted: {best_candidate.id}")
                    
                # Commit is deferred to the pipeline transaction

        except Exception as e:
            await session.rollback()
            logger.error(f"Training orchestration failed for dataset {dataset_name}: {e}")
