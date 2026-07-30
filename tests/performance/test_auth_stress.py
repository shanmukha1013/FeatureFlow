import asyncio

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.performance


@pytest.mark.asyncio
async def test_auth_rate_limiting():
    from httpx import ASGITransport

    from app.serving.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Rate limit should trigger if we do 6 requests in quick succession
        username = "rate_limit_test"

        responses = await asyncio.gather(*[
            client.post("/api/v1/auth/login", json={"username": username, "password": "abc"}, headers={"X-Forwarded-For": "10.0.0.999"})
            for _ in range(10)
        ])

        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
