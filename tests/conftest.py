"""
Why this file exists: Pytest configuration and fixtures.
Responsibility: Setup mock databases, test clients, and shared test data.
How it interacts: Automatically loaded by Pytest before running tests.
Suggestions for future extensions: Add test containers for isolated PostgreSQL and Redis testing.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock
import pandas as pd
import numpy as np
import os

from app.main import app
from app.db.session import Base, get_db
from app.db.redis_client import get_redis_client

# Use SQLite for fast in-memory testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def mock_redis():
    mock = MagicMock()
    # Basic mock for redis get/set
    cache = {}
    def mock_set(key, val):
        cache[key] = val
    def mock_get(key):
        return cache.get(key)
    mock.set.side_effect = mock_set
    mock.get.side_effect = mock_get
    return mock

@pytest.fixture(scope="function")
def client(db_session, mock_redis):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def synthetic_dataset_path():
    path = "tests/synthetic_churn.csv"
    np.random.seed(42)
    n_samples = 200
    df = pd.DataFrame({
        "age": np.random.randint(18, 70, n_samples),
        "account_balance": np.random.uniform(100, 10000, n_samples),
        "num_logins": np.random.randint(1, 100, n_samples),
        "churn": np.random.choice([0, 1], n_samples, p=[0.8, 0.2])
    })
    os.makedirs("tests", exist_ok=True)
    df.to_csv(path, index=False)
    yield path
    if os.path.exists(path):
        os.remove(path)
