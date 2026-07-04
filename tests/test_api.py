"""
Why this file exists: Integration tests for FastAPI endpoints.
Responsibility: Ensure API routing, dependency injection, and HTTP status codes are correct.
How it interacts: Sends requests to the TestClient and asserts responses.
Suggestions for future extensions: Add property-based testing (Hypothesis) for fuzzing API inputs.
"""
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_register_feature_group(client):
    payload = {
        "name": "user_demographics",
        "description": "Basic user info",
        "metadata": {"columns": ["age", "account_balance"]}
    }
    response = client.post("/api/v1/features/groups", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "registered"
    assert data["name"] == "user_demographics"

def test_ingest_and_get_online_features(client):
    payload = {
        "entity_id": "user_123",
        "features": {"age": 30, "account_balance": 1500.5}
    }
    # Ingest
    post_resp = client.post("/api/v1/features/online", json=payload)
    assert post_resp.status_code == 200

    # Retrieve
    get_resp = client.get("/api/v1/features/online/user_123")
    assert get_resp.status_code == 200
    assert get_resp.json()["features"]["age"] == 30
