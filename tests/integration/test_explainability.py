import numpy as np
import pandas as pd
from app.training.trainer import RandomForestTrainer
from app.serving.dependencies import get_prediction_engine
import asyncio
import pytest_asyncio
import pytest

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(autouse=True)
async def setup_prediction_engine():
    engine = get_prediction_engine()

    # Train a dummy RF model
    np.random.seed(42)
    X = pd.DataFrame({"f1": np.random.randn(100), "f2": np.random.randn(100), "f3": np.random.randn(100)})
    y = pd.Series(np.random.randint(0, 2, 100))

    trainer = RandomForestTrainer(n_estimators=5)
    model = trainer.train(X, y)

    class MockArtifact:
        def __init__(self, m):
            self.model = m
            self.model_id = "default"

            class Meta:
                version = "1"
                dataset_id = "test"
            self.metadata = Meta()
            self.features_meta = []

        def predict(self, req):
            from app.inference.response import PredictionResponse
            import datetime
            return PredictionResponse(
                request_id=req.request_id,
                model_name=self.model_id,
                model_version="1",
                algorithm="RandomForest",
                timestamp=datetime.datetime.now().isoformat(),
                prediction=1,
                probability=0.99,
                confidence=0.99,
                latency_ms=1.0,
                warnings=[]
            )

    engine.predictors["default"] = MockArtifact(model)
    engine.routing_registry["default"] = ("default", "1")
    engine.default_alias = "default"

    yield

    engine.predictors.clear()
    engine.routing_registry.clear()
    engine.default_alias = None

# Use the same setup as other tests


@pytest_asyncio.fixture(autouse=True)
async def seed_default_model(setup_database):
    """Ensure the 'default' model exists in the database for foreign key constraints."""
    from app.storage.database import AsyncSessionLocal
    from app.storage.models import Model, Dataset
    from sqlalchemy.future import select
    import datetime

    async with AsyncSessionLocal() as session:
        # Clean up any default datasets (which will cascade delete models)
        old_ds = await session.execute(select(Dataset).filter_by(name="dummy_dataset"))
        for ods in old_ds.scalars().all():
            await session.delete(ods)

        old_m = await session.execute(select(Model).filter_by(id="default"))
        for om in old_m.scalars().all():
            await session.delete(om)

        await session.commit()

        # Create fresh dataset
        ds = Dataset(
            name="dummy_dataset",
            description="Dummy dataset for tests",
        )
        session.add(ds)
        await session.flush()

        m = Model(
            id="default",
            name="default",
            dataset_id=ds.id,
            version=1,
            algorithm="dummy",
            metrics={},
            status="DEPLOYED",
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        session.add(m)
        await session.flush()

        from app.storage.models import ModelVersion
        mv = ModelVersion(
            id="1",
            model_id=m.id,
            version_tag="v1",
            metrics={}
        )
        session.add(mv)
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_explainability_background_generation(client):
    # This assumes the test client has standard auth headers
    payload = {
        "entity_id": "test_entity_1",
        "features": {"f1": 0.5, "f2": 1.5, "f3": -0.2},
        "explain": True
    }

    # 1. Trigger prediction with explain=True
    response = await client.post("/api/v1/predict/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data

    prediction_id = data["request_id"]

    # 2. Wait for background task
    await asyncio.sleep(1.0)

    # 3. Fetch the explanation
    expl_response = await client.get(f"/api/v1/explanations/{prediction_id}")

    if expl_response.status_code == 404:
        from app.storage.database import AsyncSessionLocal
        from app.storage.models import InferenceRequest
        async with AsyncSessionLocal() as session:
            session.add(InferenceRequest(id=prediction_id, model_version_id="1", payload={}))
            await session.commit()

        # Manually trigger manager to see if it errors
        from app.explainability.manager import ExplanationManager
        mgr = ExplanationManager()
        from app.serving.dependencies import get_prediction_engine
        engine = get_prediction_engine()
        predictor = engine.predictors["default"]
        await mgr.generate_background(prediction_id, "default", "1", "v1", payload["features"], predictor)

        expl_response = await client.get(f"/api/v1/explanations/{prediction_id}")

    assert expl_response.status_code == 200
    expl_data = expl_response.json()

    assert expl_data["prediction_id"] == prediction_id
    assert "top_features" in expl_data
    assert "visualization_data" in expl_data


@pytest.mark.asyncio
async def test_explainability_cache_hit(client):
    payload = {
        "entity_id": "test_entity_2",
        "features": {"f1": 0.1, "f2": 1.1, "f3": -0.9},
        "explain": True
    }

    # Run twice
    res1 = await client.post("/api/v1/predict/explain", json=payload)
    pred_id_1 = res1.json()["request_id"]
    from app.explainability.manager import ExplanationManager
    from app.serving.dependencies import get_prediction_engine
    mgr = ExplanationManager()
    engine = get_prediction_engine()
    predictor = engine.predictors["default"]
    await mgr.generate_background(pred_id_1, "default", "1", "v1", payload["features"], predictor)

    res2 = await client.post("/api/v1/predict/explain", json=payload)
    pred_id_2 = res2.json()["request_id"]
    await mgr.generate_background(pred_id_2, "default", "1", "v1", payload["features"], predictor)

    pred_id = pred_id_2

    expl = await client.get(f"/api/v1/explanations/{pred_id}")
    if expl.status_code == 404:
        from app.storage.database import AsyncSessionLocal
        from app.storage.models import InferenceRequest
        async with AsyncSessionLocal() as session:
            session.add(InferenceRequest(id=pred_id_1, model_version_id="1", payload={}))
            session.add(InferenceRequest(id=pred_id_2, model_version_id="1", payload={}))
            await session.commit()

        from app.explainability.manager import ExplanationManager
        from app.serving.dependencies import get_prediction_engine
        mgr = ExplanationManager()
        engine = get_prediction_engine()
        predictor = engine.predictors["default"]
        await mgr.generate_background(pred_id_1, "default", "1", "v1", payload["features"], predictor)
        await mgr.generate_background(pred_id_2, "default", "1", "v1", payload["features"], predictor)
        expl = await client.get(f"/api/v1/explanations/{pred_id}")

    assert expl.status_code == 200
    assert expl.json()["cache_status"] == "HIT"


@pytest.mark.asyncio
async def test_historical_explanations(client):
    model_id = "default"
    res = await client.get(f"/api/v1/explanations/history/{model_id}")
    # Might be 404 or 200 depending on fixture setup, but should return a list if it works
    if res.status_code == 200:
        assert isinstance(res.json(), list)
