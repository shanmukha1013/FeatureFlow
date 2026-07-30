import os
import uuid

import pandas as pd
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import Dataset, DatasetVersion


@pytest.fixture
async def setup_mlflow_data(db_session: AsyncSession):
    ds_id = f"test_ds_{uuid.uuid4().hex[:8]}"

    ds = Dataset(id=ds_id, name="mlflow_test", status="ACTIVE")
    db_session.add(ds)

    file_path = f"scratch/{ds_id}.csv"
    os.makedirs("scratch", exist_ok=True)
    df = pd.DataFrame({"f1": [1, 2, 3], "target": [0, 1, 0]})
    df.to_csv(file_path, index=False)

    ds_version = DatasetVersion(
        dataset_id=ds_id,
        version_tag="v1",
        file_path=file_path,
        row_count=3,
        status="VALIDATED"
    )
    db_session.add(ds_version)
    await db_session.commit()

    yield ds, ds_version

    await db_session.delete(ds_version)
    await db_session.delete(ds)
    await db_session.commit()
    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.mark.asyncio
async def test_run_training(client: AsyncClient, setup_mlflow_data):
    ds, ds_version = setup_mlflow_data

    payload = {
        "dataset_id": ds.id,
        "algorithm": "LogisticRegression",
        "hyperparameters": {},
        "target_column": "target"
    }

    # Needs ML_ENGINEER or ADMIN role
    response = await client.post("/api/v1/mlflow/train", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["run_id"]
    assert data["experiment_id"]
    assert data["status"] == "COMPLETED"
    assert "accuracy" in data["metrics"]

    # Test experiments list
    resp = await client.get("/api/v1/mlflow/experiments")
    assert resp.status_code == 200

    # Test get run
    run_id = data["run_id"]
    resp = await client.get(f"/api/v1/mlflow/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == run_id

    # Test get models
    resp = await client.get("/api/v1/mlflow/models")
    assert resp.status_code == 200
    models_data = resp.json()
    assert len(models_data) > 0

    model_name = models_data[-1]["name"]

    # Test promote model
    promote_payload = {
        "model_name": model_name,
        "version": "1",
        "alias": "champion"
    }
    resp = await client.post("/api/v1/mlflow/models/promote", json=promote_payload)
    assert resp.status_code == 200

    # Test latest model
    resp = await client.get(f"/api/v1/mlflow/models/{model_name}/latest")
    assert resp.status_code == 200
    assert "champion" in resp.json()["aliases"]
