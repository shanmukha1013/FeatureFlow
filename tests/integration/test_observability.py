import pytest
from httpx import ASGITransport, AsyncClient

from app.serving.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/metrics")

    assert response.status_code == 200
    assert "featureflow_http_requests_total" in response.text
    assert "featureflow_process_cpu_percent" in response.text
