"""
Unit tests for FeatureFlow ML Training and Inference components.
Tests real trainers, evaluators, artifact store, and prediction engine.
"""
import pytest
import os
import pandas as pd
import numpy as np

from app.training.trainer import LogisticRegressionTrainer, RandomForestTrainer
from app.training.evaluator import ClassificationEvaluator
from app.training.artifacts import LocalArtifactStore
from app.inference.engine import PredictionEngine
from app.inference.exceptions import InferenceError, PredictionError


@pytest.fixture
def sample_dataset():
    """Create a synthetic tabular dataset for binary classification."""
    np.random.seed(42)
    X = pd.DataFrame({
        "feature1": np.random.randn(100),
        "feature2": np.random.randn(100) * 10,
        "feature3": np.random.randint(0, 5, 100)
    })
    y = pd.Series(np.random.randint(0, 2, 100))
    return X, y


@pytest.fixture
def temp_artifact_store(tmp_path):
    store = LocalArtifactStore(base_dir=str(tmp_path / "models"))
    yield store


def test_logistic_regression_trainer_success(sample_dataset):
    X, y = sample_dataset
    trainer = LogisticRegressionTrainer(max_iter=100)
    assert trainer.algorithm_name == "LogisticRegression"
    
    model = trainer.train(X, y)
    assert model is not None
    assert hasattr(model, "predict")
    assert hasattr(model, "predict_proba")


def test_random_forest_trainer_success(sample_dataset):
    X, y = sample_dataset
    trainer = RandomForestTrainer(n_estimators=10, random_state=42)
    assert trainer.algorithm_name == "RandomForest"
    
    model = trainer.train(X, y)
    assert model is not None
    preds = model.predict(X)
    assert len(preds) == len(y)


def test_classification_evaluator_success(sample_dataset):
    X, y = sample_dataset
    trainer = LogisticRegressionTrainer()
    model = trainer.train(X, y)
    
    evaluator = ClassificationEvaluator()
    metrics = evaluator.evaluate(model, X, y)
    
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "classification_report" in metrics


def test_local_artifact_store_save_and_load(sample_dataset, temp_artifact_store):
    X, y = sample_dataset
    trainer = LogisticRegressionTrainer()
    model = trainer.train(X, y)
    
    model_id = "test_model_01"
    version = "1"
    
    path, checksum = temp_artifact_store.save(model, model_id, version)
    assert os.path.exists(path)
    assert checksum is not None
    assert temp_artifact_store.exists(model_id, version)
    
    loaded_model = temp_artifact_store.load(model_id, version, expected_checksum=checksum)
    assert hasattr(loaded_model, "predict")
    
    temp_artifact_store.delete(model_id, version)
    assert not temp_artifact_store.exists(model_id, version)


@pytest.mark.asyncio
async def test_prediction_engine_no_model_error(temp_artifact_store):
    engine = PredictionEngine(artifact_store=temp_artifact_store)
    with pytest.raises((InferenceError, PredictionError)):
        await engine.predict_single({"feature1": 1.0}, alias="nonexistent")


def test_local_artifact_store_path_traversal(temp_artifact_store):
    from app.training.exceptions import ArtifactError
    with pytest.raises(ArtifactError):
        temp_artifact_store._build_path("../../evil_model", "v1")


def test_local_artifact_store_corrupted_checksum(sample_dataset, temp_artifact_store):
    from app.training.exceptions import ArtifactError
    X, y = sample_dataset
    trainer = LogisticRegressionTrainer()
    model = trainer.train(X, y)
    
    model_id = "test_model_corrupt"
    version = "v1"
    
    path, checksum = temp_artifact_store.save(model, model_id, version)
    assert os.path.exists(path)
    
    # Try loading with mismatched checksum
    with pytest.raises(ArtifactError, match="checksum verification failed"):
        temp_artifact_store.load(model_id, version, expected_checksum="0000000000000000000000000000000000000000000000000000000000000000")


def test_local_artifact_store_missing_file(temp_artifact_store):
    from app.training.exceptions import ArtifactError
    with pytest.raises(ArtifactError, match="Artifact not found"):
        temp_artifact_store.load("nonexistent_model", "v99")


@pytest.mark.asyncio
async def test_prediction_engine_batch_prediction(temp_artifact_store):
    engine = PredictionEngine(artifact_store=temp_artifact_store)
    with pytest.raises((InferenceError, PredictionError)):
        await engine.predict_batch([{"feature1": 1.0}, {"feature1": 2.0}], alias="nonexistent")

