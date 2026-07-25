# FeatureFlow API Reference

FeatureFlow exposes a RESTful API organized by functional domains. All endpoints are versioned under `/api/v1`.

## Authentication

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user | No |
| POST | `/api/v1/auth/login` | Login and receive a JWT token | No |
| POST | `/api/v1/auth/logout` | Revoke the current JWT token | Yes |
| GET | `/api/v1/auth/me` | Get the current authenticated user's profile | Yes |
| POST | `/api/v1/auth/api-keys` | Generate a long-lived API key | Yes |
| DELETE | `/api/v1/auth/api-keys/{key_id}` | Revoke an API key | Yes |

## Datasets & Features (Registry)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| GET | `/api/v1/datasets` | List all registered datasets | Yes |
| POST | `/api/v1/datasets` | Register a new dataset | Yes |
| GET | `/api/v1/datasets/{dataset_id}` | Get dataset details | Yes |
| GET | `/api/v1/features` | List all available features | Yes |
| POST | `/api/v1/features` | Create a new feature definition | Yes |

## Machine Learning & Training

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/api/v1/mlflow/train` | Trigger a new model training job | Yes |
| GET | `/api/v1/mlflow/experiments` | List all MLflow experiments | Yes |
| GET | `/api/v1/mlflow/runs/{run_id}` | Get details of a specific training run | Yes |
| GET | `/api/v1/mlflow/models` | List all registered models | Yes |
| POST | `/api/v1/mlflow/models/promote` | Promote a model version (e.g., to `champion`) | Yes |
| GET | `/api/v1/mlflow/models/{name}/latest` | Get the latest model version for a given name | Yes |

## Inference & Serving

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/api/v1/predict` | Run online inference against the champion model | Yes |
| POST | `/api/v1/predict/batch` | Run batch inference against the champion model | Yes |

## Data Quality & Monitoring

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/api/v1/data-quality/baseline` | Generate a data quality baseline | Yes |
| POST | `/api/v1/monitoring/run` | Trigger a data drift monitoring report | Yes |
| GET | `/api/v1/monitoring/reports/{report_id}` | View a specific HTML monitoring report | Yes |

## Observability & System Health

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| GET | `/health` | Application health check (Liveness probe) | No |
| GET | `/metrics` | Prometheus metrics scrape endpoint | Configurable |
| GET | `/api/v1/cache/health` | Redis connection health | Yes |
| POST | `/api/v1/cache/invalidate` | Invalidate a specific cache key | Yes |

## Response Formats

All successful API responses return a structured JSON object. Standard status codes are strictly adhered to:
- `200 OK`: Successful retrieval or update
- `201 Created`: Successful resource creation
- `400 Bad Request`: Validation failure
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource does not exist
- `500 Internal Server Error`: Unexpected system failure

---

## Example Usage: Online Inference (`/predict`)

**Endpoint**: `POST /api/v1/predict`
**Auth Required**: Yes (`Bearer <token>`)

### Request Body

```json
{
  "features": {
    "age": 34,
    "income": 75000,
    "credit_score": 720
  },
  "entity_id": "user-10293",
  "alias": "champion",
  "explain": true
}
```

### Success Response (`200 OK`)

```json
{
  "request_id": "req-xyz-123",
  "prediction": 0,
  "probability": [0.82, 0.18],
  "model_id": "fraud_model",
  "model_version": "5",
  "latency_ms": 14.5,
  "warnings": [],
  "explanation": {
    "feature_importance": {
      "income": 0.45,
      "credit_score": 0.35,
      "age": 0.20
    }
  }
}
```

## Exploring via Swagger UI

FeatureFlow comes with auto-generated, interactive OpenAPI documentation.
Once deployed, navigate to:
- **Swagger UI**: `/docs`
- **ReDoc UI**: `/redoc`
