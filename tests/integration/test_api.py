import pytest

pytestmark = pytest.mark.integration

"""
Integration tests for FeatureFlow FastAPI endpoints.
Tests run against the real async PostgreSQL infrastructure and endpoints.
"""


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_version_check(client):
    response = await client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert "platform_version" in data
    assert data["api_version"] == "v1"


@pytest.mark.asyncio
async def test_list_models(client):
    response = await client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "aliases" in data
    assert isinstance(data["aliases"], list)


@pytest.mark.asyncio
async def test_management_overview(client):
    response = await client.get("/api/v1/management/platform")
    assert response.status_code == 200
    data = response.json()
    assert "registered_datasets" in data
    assert "registered_models" in data


@pytest.mark.asyncio
async def test_management_registries_datasets_pagination(client):
    response = await client.get("/api/v1/management/registries/datasets?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "page" in data
    assert "size" in data
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_management_registries_features(client):
    response = await client.get("/api/v1/management/registries/features?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_management_registries_models(client):
    response = await client.get("/api/v1/management/registries/models?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_management_pipelines_runs(client):
    response = await client.get("/api/v1/management/pipelines/runs?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_management_observability_events(client):
    response = await client.get("/api/v1/management/observability/events?limit=20")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_predict_endpoint_validation_error(client):
    # Missing required payload structure
    response = await client.post("/api/v1/predict", json={})
    assert response.status_code in (400, 422, 500)
