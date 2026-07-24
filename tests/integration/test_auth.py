import uuid
import pytest_asyncio
from httpx import AsyncClient
import pytest

pytestmark = pytest.mark.integration


# Skip tests if not using async context properly (simplified for now)
# We will use actual app endpoints


@pytest_asyncio.fixture(scope="function")
async def async_client():
    from app.serving.main import app
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_register_and_login(async_client):
    username = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"

    # 1. Register
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": "EnterprisePassword1!"
    })
    assert reg_resp.status_code == 201

    # 2. Login
    login_resp = await async_client.post("/api/v1/auth/login", json={
        "username": username,
        "password": "EnterprisePassword1!"
    }, headers={"X-Forwarded-For": "10.0.0.100"})
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_me_endpoint(async_client):
    username = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"

    await async_client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": "EnterprisePassword1!"
    })

    login_resp = await async_client.post("/api/v1/auth/login", json={
        "username": username,
        "password": "EnterprisePassword1!"
    }, headers={"X-Forwarded-For": "10.0.0.101"})
    token = login_resp.json()["access_token"]

    me_resp = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == username
    assert me_resp.json()["role"] == "VIEWER"


@pytest.mark.asyncio
async def test_api_keys(async_client):
    username = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    await async_client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": "EnterprisePassword1!"})
    login_resp = await async_client.post("/api/v1/auth/login", json={"username": username, "password": "EnterprisePassword1!"}, headers={"X-Forwarded-For": "10.0.0.102"})
    token = login_resp.json()["access_token"]

    # Create API Key
    create_resp = await async_client.post("/api/v1/api-keys", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Test Key"
    })
    assert create_resp.status_code == 201
    api_key = create_resp.json()["api_key"]

    # Use API Key to access protected route (e.g., /auth/me)
    me_resp = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {api_key}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == username
