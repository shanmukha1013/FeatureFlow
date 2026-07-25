# Deployment Guide

This document outlines how to deploy FeatureFlow into production. FeatureFlow leverages a modern microservice architecture designed for container orchestration (Docker/Kubernetes).

## 1. Environment Configuration

FeatureFlow relies heavily on environment variables for configuration. All available keys are documented below:

| Variable | Description | Required | Default |
|---|---|---|---|
| `PROJECT_NAME` | Name of the API service | No | FeatureFlow |
| `ENVIRONMENT` | Must be `production` in prod. | Yes | development |
| `LOG_LEVEL` | Application logging level | No | INFO |
| `DATA_DIR` | Base directory for datasets | No | /app/datasets |
| `DATABASE_URL` | PostgreSQL connection string | Yes | None |
| `REDIS_URL` | Redis cache connection string | Yes | None |
| `JWT_SECRET_KEYS` | Cryptographically strong secret | Yes | None |
| `JWT_ALGORITHM` | Token signing algorithm | No | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of an auth token | No | 30 |
| `DEFAULT_ADMIN_EMAIL` | Default admin user email | Yes | None |
| `DEFAULT_ADMIN_PASSWORD` | Default admin user password | Yes | None |
| `ENABLE_METRICS_AUTH` | Protect `/metrics` endpoint | No | true |

### 1.1 Securely Managing Secrets
For production, copy `.env.production` to your deployment environment and **replace all placeholder secrets**. Never commit the actual secrets to the repository.

## 2. Local Setup (Development)

For rapid iteration without building full Docker images:
```bash
# Copy local development configuration
cp .env.development .env

# Start backing services
docker compose up redis postgres -d

# Run local API
pip install -r requirements.txt
uvicorn app.serving.main:app --reload
```

## 3. Docker Deployment (Development)

To run the full stack locally via Docker (using `Dockerfile.dev` with hot-reloading):
```bash
cp .env.development .env
docker compose up --build
```

## 4. Production Deployment

In a production environment, use `docker-compose.prod.yml` and the standard `Dockerfile`.

1. **Configure Environment:** Ensure your `.env.production` is correctly set.
2. **Start Services:**
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```
This configuration uses strict restart policies, sets memory limits, and drops local volume bindings for maximum security.

## 5. Running Database Migrations

FeatureFlow uses Alembic for asynchronous schema migrations. Migrations run automatically against the configured `DATABASE_URL`.

**To create a new migration after updating models:**
```bash
alembic revision --autogenerate -m "description_of_change"
```

**To apply pending migrations:**
```bash
alembic upgrade head
```

**To rollback the last migration:**
```bash
alembic downgrade -1
```

## 6. Troubleshooting

### Startup Validation Fails
If the API crashes immediately on startup, check the container logs. FeatureFlow performs aggressive startup validation. It will fail cleanly if:
- `JWT_SECRET_KEYS` is insecure.
- PostgreSQL cannot be reached.
- Redis cannot be pinged.
- Storage directories (e.g., `/app/models`) are missing or read-only.

### Redis Connectivity Drops
If the application loses connection to Redis, it will automatically fallback to the PostgreSQL database for serving predictions. However, cache hits will be 0%. Monitor the `GET /api/v1/cache/health` endpoint.

### Model Loading Issues
Ensure the `/app/models` volume is persistent across restarts. If a worker fails to load a `champion` model, verify the persistent volume configuration in your orchestrator (EFS/PVC).
