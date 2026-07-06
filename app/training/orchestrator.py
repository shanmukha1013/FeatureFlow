import time
import uuid
import pandas as pd
from typing import List, Dict, Any

from app.utils.logger import get_logger
from app.data.dataset_registry import DatasetMetadata, global_dataset_registry
from app.features.registry import global_feature_registry
from app.features.transformer import FeatureTransformer
from app.training.dataset import TrainingDatasetBuilder
from app.training.splitter import RandomSplitter
from app.training.trainer import LogisticRegressionTrainer, DecisionTreeTrainer, RandomForestTrainer
from app.training.evaluator import ClassificationEvaluator
from app.training.artifacts import LocalArtifactStore
from app.training.registry import LocalModelRegistry
from app.training.metadata import ModelMetadata, ModelLifecycleState
from app.monitoring.audit import AuditLogger, AuditEvent
from app.serving.dependencies import _training_registry

logger = get_logger(__name__)

# Reusing the registry attached to the dependency injection context if possible, 
# or just referencing it. The user said: "Update GET /management/models Return live registry."
# The `registries.py` endpoint uses `_training_registry` from `app.serving.dependencies`.

class TrainingOrchestrator:
    def __init__(self, data_dir: str = "datasets/raw"):
        self.data_dir = data_dir
        self.dataset_builder = TrainingDatasetBuilder()
        self.splitter = RandomSplitter(test_size=0.2)
        self.evaluator = ClassificationEvaluator()
        self.artifact_store = LocalArtifactStore()
        self.registry = _training_registry
        self.feature_transformer = FeatureTransformer(global_feature_registry)

    def _select_target_column(self, df: pd.DataFrame, dataset_name: str) -> str:
        """Heuristically select a target column for automated training."""
        # Prefer 'target', 'label', 'is_', 'has_'
        for col in df.columns:
            lower = col.lower()
            if lower in ['target', 'label', 'class', 'outcome']:
                return col
            if lower.startswith('is_') or lower.startswith('has_'):
                return col
                
        # Fallback to the last column that isn't an ID
        valid_cols = [c for c in df.columns if not c.lower().endswith('id')]
        if valid_cols:
            return valid_cols[-1]
        return df.columns[-1]

    def _get_features_for_dataset(self, dataset_name: str) -> List[str]:
        features = []
        for feat_name in global_feature_registry.list_features():
            f = global_feature_registry.get(feat_name)
            if f.metadata.source_dataset == dataset_name:
                features.append(feat_name)
        return features

    def execute(self, dataset_meta: DatasetMetadata) -> None:
        dataset_name = dataset_meta.dataset_name
        logger.info(f"Starting Training Orchestration for dataset '{dataset_name}'")
        
        try:
            from app.data.loader import CSVDataLoader
            loader = CSVDataLoader(self.data_dir)
            df_raw = loader.load(dataset_meta.relative_path)
            
            target_col = self._select_target_column(df_raw, dataset_name)
            feature_names = self._get_features_for_dataset(dataset_name)
            
            if not feature_names:
                logger.warning(f"No engineered features found for dataset {dataset_name}. Skipping training.")
                return
                
            logger.info(f"Transforming {len(feature_names)} features for training.")
            df_features = self.feature_transformer.transform(df_raw, feature_names)
            
            # Merge target column into features dataframe so we can split it
            df_features[target_col] = df_raw[target_col]
            
            # Drop rows where the target is missing
            df_features.dropna(subset=[target_col], inplace=True)
            
            # Label Encode the target to prevent classifier errors with string classes
            from sklearn.preprocessing import LabelEncoder
            df_features[target_col] = LabelEncoder().fit_transform(df_features[target_col])
            
            # Prepare Training Dataset
            X, y = self.dataset_builder.prepare(df_features, feature_names, target_col)
            
            # Train/Test Split
            X_train, X_test, y_train, y_test = self.splitter.split(X, y)
            
            trainers = [
                LogisticRegressionTrainer(max_iter=1000),
                DecisionTreeTrainer(max_depth=5),
                RandomForestTrainer(n_estimators=100, max_depth=5)
            ]
            
            models_trained = []
            
            for trainer in trainers:
                algo_name = trainer.algorithm_name
                
                # 1. Start Experiment
                from app.training.experiments.registry import global_experiment_registry
                from app.training.experiments.metadata import Experiment, ExperimentState
                import uuid
                from datetime import datetime
                
                run_id = str(uuid.uuid4())
                exp_id = f"exp_{dataset_name}_{algo_name.lower()}_{int(time.time())}"
                
                experiment = Experiment(
                    experiment_id=exp_id,
                    experiment_name=f"Train {algo_name} on {dataset_name}",
                    run_id=run_id,
                    dataset=dataset_name,
                    dataset_version=dataset_meta.version,
                    feature_version="1.0.0",
                    algorithm=algo_name,
                    hyperparameters=trainer.hyperparameters,
                    tags=["automated", algo_name.lower()],
                    lifecycle_state=ExperimentState.RUNNING,
                    start_time=datetime.utcnow()
                )
                global_experiment_registry.create(experiment)
                
                AuditLogger.record(AuditEvent(event_name="EXPERIMENT_STARTED", component="TrainingOrchestrator", severity="INFO", payload={"experiment_id": exp_id}))
                AuditLogger.record(AuditEvent(event_name="TRAINING_STARTED", component="TrainingOrchestrator", severity="INFO", payload={"algorithm": algo_name, "dataset": dataset_name}))
                
                start_time = time.time()
                try:
                    # 1. Train
                    model = trainer.train(X_train, y_train)
                    train_duration = (time.time() - start_time) * 1000
                    
                    AuditLogger.record(AuditEvent(event_name="TRAINING_FINISHED", component="TrainingOrchestrator", severity="INFO", payload={"algorithm": algo_name, "duration_ms": train_duration}))
                    
                    # 2. Evaluate
                    metrics = self.evaluator.evaluate(model, X_test, y_test)
                    AuditLogger.record(AuditEvent(event_name="EVALUATION_FINISHED", component="TrainingOrchestrator", severity="INFO", payload={"algorithm": algo_name, "accuracy": metrics.get("accuracy", 0)}))
                    
                    # 3. Model Versioning & ID
                    base_model_id = f"mdl_{dataset_name}_{algo_name.lower()}"
                    
                    existing_versions = [1]
                    for m_id in self.registry.list_models():
                        if m_id.startswith(base_model_id):
                            m_meta = self.registry.get(m_id)
                            try:
                                v_num = int(m_meta.model_version.replace("v", ""))
                                existing_versions.append(v_num + 1)
                            except: pass
                            
                    next_v = max(existing_versions)
                    version_str = f"v{next_v}"
                    model_id = f"{base_model_id}_{version_str}"
                    
                    # 4. Save Artifact
                    artifact_path, checksum = self.artifact_store.save(model, model_id, version_str)
                    AuditLogger.record(AuditEvent(event_name="ARTIFACT_SAVED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id, "checksum": checksum}))
                    
                    # 5. Explainability & Baseline Profiling
                    from app.training.explainability import GlobalExplainer
                    from app.monitoring.drift.baseline import BaselineProfiler
                    
                    explainer = GlobalExplainer()
                    feat_imp = explainer.compute_feature_importance(model, feature_names)
                    shap_summ = explainer.compute_shap_summary(model, X_train)
                    
                    baseline_profile = BaselineProfiler.compute_baseline(X_train, y_train)
                    AuditLogger.record(AuditEvent(event_name="BASELINE_UPDATED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id}))
                    
                    if feat_imp:
                        AuditLogger.record(AuditEvent(event_name="EXPLANATION_GENERATED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id}))
                    if shap_summ:
                        AuditLogger.record(AuditEvent(event_name="SHAP_GENERATED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id}))
                        
                    # 6. Register Model
                    meta = ModelMetadata(
                        model_id=model_id,
                        model_version=version_str,
                        algorithm=algo_name,
                        target_column=target_col,
                        feature_version="1.0.0",
                        dataset_version=dataset_meta.version,
                        hyperparameters=trainer.hyperparameters,
                        metrics=metrics,
                        artifact_path=artifact_path,
                        artifact_checksum=checksum,
                        dataset_size=len(X),
                        feature_count=len(feature_names),
                        feature_names=feature_names,
                        feature_importance=feat_imp,
                        shap_summary=shap_summ,
                        baseline_profile=baseline_profile,
                        split_config={"test_size": 0.2, "random_state": 42},
                        training_duration_ms=train_duration,
                        lifecycle_state=ModelLifecycleState.CANDIDATE
                    )
                    
                    self.registry.register(meta)
                    models_trained.append(meta)
                    
                    # Complete Experiment
                    global_experiment_registry.update(
                        experiment_id=exp_id,
                        lifecycle_state=ExperimentState.COMPLETED,
                        end_time=datetime.utcnow(),
                        metrics=metrics,
                        artifact_path=artifact_path,
                        model_version=version_str,
                        training_time_ms=train_duration
                    )
                    AuditLogger.record(AuditEvent(event_name="EXPERIMENT_FINISHED", component="TrainingOrchestrator", severity="INFO", payload={"experiment_id": exp_id}))
                    AuditLogger.record(AuditEvent(event_name="MODEL_REGISTERED", component="TrainingOrchestrator", severity="INFO", payload={"model_id": model_id}))
                    
                except Exception as e:
                    global_experiment_registry.update(
                        experiment_id=exp_id,
                        lifecycle_state=ExperimentState.FAILED,
                        end_time=datetime.utcnow(),
                        status_message=str(e)
                    )
                    AuditLogger.record(AuditEvent(event_name="EXPERIMENT_FAILED", component="TrainingOrchestrator", severity="ERROR", payload={"experiment_id": exp_id}))
                    AuditLogger.record(AuditEvent(event_name="TRAINING_FAILED", component="TrainingOrchestrator", severity="ERROR", payload={"algorithm": algo_name, "error": str(e)}))
                    logger.error(f"Failed to train {algo_name}: {e}")
                    
            # 6. Champion Selection & Promotion Rules
            if models_trained:
                best_candidate = max(models_trained, key=lambda m: m.metrics.get('accuracy', 0))
                best_acc = best_candidate.metrics.get('accuracy', 0)
                
                # Find current active champion for this dataset
                current_champion = None
                for m_id in self.registry.list_models():
                    existing = self.registry.get(m_id)
                    if existing.dataset_version == dataset_meta.version and existing.lifecycle_state == ModelLifecycleState.CHAMPION:
                        current_champion = existing
                        break
                        
                if current_champion:
                    current_acc = current_champion.metrics.get('accuracy', 0)
                    if best_acc > current_acc:
                        # Promote new, demote old
                        self.registry.update_lifecycle_state(current_champion.model_id, ModelLifecycleState.ARCHIVED)
                        self.registry.update_lifecycle_state(best_candidate.model_id, ModelLifecycleState.CHAMPION)
                        AuditLogger.record(AuditEvent(event_name="CHAMPION_PROMOTED", component="TrainingOrchestrator", severity="INFO", payload={"new_champion": best_candidate.model_id, "accuracy": best_acc, "previous_champion": current_champion.model_id}))
                        logger.info(f"Champion promoted: {best_candidate.model_id} outperformed {current_champion.model_id}")
                    else:
                        # Archive candidate
                        self.registry.update_lifecycle_state(best_candidate.model_id, ModelLifecycleState.ARCHIVED)
                        logger.info(f"Candidate {best_candidate.model_id} ({best_acc:.4f}) failed to beat champion {current_champion.model_id} ({current_acc:.4f}). Archived.")
                else:
                    # First time training on this dataset version
                    self.registry.update_lifecycle_state(best_candidate.model_id, ModelLifecycleState.CHAMPION)
                    AuditLogger.record(AuditEvent(event_name="CHAMPION_PROMOTED", component="TrainingOrchestrator", severity="INFO", payload={"new_champion": best_candidate.model_id, "accuracy": best_acc}))
                    logger.info(f"Initial champion promoted: {best_candidate.model_id}")

        except Exception as e:
            logger.error(f"Training orchestration failed for dataset {dataset_name}: {e}")
