import os

import pandas as pd
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import Dataset, DatasetVersion


@pytest.fixture
async def setup_monitoring_data(db_session: AsyncSession):
    # Create two datasets and CSV files
    ref_df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
    curr_df = pd.DataFrame({"col1": [1, 2, 30], "col2": [4, 5, 60]})

    os.makedirs("tests/data", exist_ok=True)
    ref_path = "tests/data/ref_mock.csv"
    curr_path = "tests/data/curr_mock.csv"

    ref_df.to_csv(ref_path, index=False)
    curr_df.to_csv(curr_path, index=False)

    ref_ds = Dataset(name="ref_dataset", description="ref")
    curr_ds = Dataset(name="curr_dataset", description="curr")

    db_session.add_all([ref_ds, curr_ds])
    await db_session.commit()

    ref_ver = DatasetVersion(dataset_id=ref_ds.id, version_tag="v1", file_path=ref_path)
    curr_ver = DatasetVersion(dataset_id=curr_ds.id, version_tag="v1", file_path=curr_path)

    db_session.add_all([ref_ver, curr_ver])
    await db_session.commit()

    yield ref_ds, curr_ds

    # Teardown
    try:
        os.remove(ref_path)
        os.remove(curr_path)
    except Exception:
        pass

    await db_session.delete(ref_ver)
    await db_session.delete(curr_ver)
    await db_session.delete(ref_ds)
    await db_session.delete(curr_ds)
    await db_session.commit()


@pytest.mark.asyncio
async def test_run_monitoring(client: AsyncClient, setup_monitoring_data):
    ref_ds, curr_ds = setup_monitoring_data

    response = await client.post("/api/v1/monitoring/run", json={
        "reference_dataset_id": ref_ds.id,
        "current_dataset_id": curr_ds.id
    })

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["reference_dataset_id"] == ref_ds.id
    assert data["current_dataset_id"] == curr_ds.id
    assert "drift_detected" in data
    assert data["status"] == "COMPLETED"

    report_id = data["id"]

    # Check history
    history_resp = await client.get(f"/api/v1/monitoring/history?dataset_id={curr_ds.id}")
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert len(history_data) == 1
    assert history_data[0]["id"] == report_id

    # Check latest
    latest_resp = await client.get(f"/api/v1/monitoring/latest?dataset_id={curr_ds.id}")
    assert latest_resp.status_code == 200
    assert "html" in latest_resp.text.lower()
