"""
Integration tests for FeatureFlow FastAPI endpoints.
Tests run against the real async PostgreSQL infrastructure and endpoints.
"""
import pytest

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
