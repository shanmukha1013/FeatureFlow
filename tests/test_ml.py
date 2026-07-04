"""
Why this file exists: Unit tests for ML engine components.
Responsibility: Verify model training, metrics generation, and inference logic.
How it interacts: Directly instantiates ML classes without the API layer.
Suggestions for future extensions: Add data drift detection tests on synthetic skewed data.
"""
import pytest
from app.ml.training import ModelTrainer
from app.ml.inference import InferenceEngine
from app.core.exceptions import TrainingError, ModelNotFoundError
import pandas as pd

def test_model_trainer_success(synthetic_dataset_path):
    trainer = ModelTrainer(models_dir="tests/models/")
    df = pd.read_csv(synthetic_dataset_path)
    
    artifact_path, metrics = trainer.train_churn_model(df, "v1")
    
    assert "accuracy" in metrics
    assert "f1_score" in metrics
    assert artifact_path.endswith("churn_model_v1.joblib")

def test_model_trainer_missing_target(synthetic_dataset_path):
    trainer = ModelTrainer(models_dir="tests/models/")
    df = pd.read_csv(synthetic_dataset_path)
    df = df.drop(columns=["churn"])
    
    with pytest.raises(TrainingError):
        trainer.train_churn_model(df, "v2")

def test_inference_engine(synthetic_dataset_path):
    # Train a model first
    trainer = ModelTrainer(models_dir="tests/models/")
    df = pd.read_csv(synthetic_dataset_path)
    artifact_path, _ = trainer.train_churn_model(df, "v_infer")
    
    # Test Inference
    engine = InferenceEngine()
    engine.load_model("test_model", artifact_path)
    
    features = {"age": 45, "account_balance": 2000.0, "num_logins": 5}
    prediction = engine.predict("test_model", features)
    
    assert prediction in [0, 1]

def test_inference_engine_model_not_found():
    engine = InferenceEngine()
    with pytest.raises(ModelNotFoundError):
        engine.predict("nonexistent_model", {"feature": 1})
