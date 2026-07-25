# Production Release Checklist

Before deploying a new version of FeatureFlow to production, ensure every step in this checklist is verified.

## 1. Build Verification
- [ ] Ensure `requirements.txt` is strictly pinned and updated (`pip freeze > requirements.txt`).
- [ ] Verify `Dockerfile` and `backend.Dockerfile` build successfully without caching issues.
- [ ] Confirm no `.env` or sensitive files are included in the Docker image (checked via `.dockerignore`).

## 2. Testing & Quality Verification
- [ ] Run `$env:PYTHONPATH="."; pytest tests/ -v` — Ensure 100% pass rate.
- [ ] Run `flake8` across the entire codebase — Ensure exactly 0 errors or warnings.
- [ ] Run `scripts/certify_production.py` — Ensure an Enterprise Certification Score of 100 / 100.
- [ ] Confirm all tests are deterministic (idempotent setup/teardown using UUIDs).

## 3. Deployment Verification
- [ ] Apply database migrations if the PostgreSQL schema was altered.
- [ ] Verify MLflow is connected to the dedicated `mlflow` PostgreSQL schema, NOT the public application schema.
- [ ] Verify Redis connection settings (`REDIS_URL`) point to the production cluster.
- [ ] Set `ENVIRONMENT=production` in the production environment variables.

## 4. Security Verification
- [ ] Confirm `JWT_SECRET_KEYS` is a strong, cryptographically secure hash in the production `.env`.
- [ ] Confirm `ENABLE_METRICS_AUTH=true` is set in production to protect the `/metrics` endpoint.
- [ ] Verify default passwords (e.g., admin credentials) are overridden.
- [ ] Confirm CORS settings (`allow_origins`) are strictly set to expected frontend domains.

## 5. Observability Verification
- [ ] Verify Prometheus is actively scraping `/metrics`.
- [ ] Check Grafana dashboards to confirm data flow (e.g., HTTP request rates and prediction latency).
- [ ] Verify alerts are configured and routed to the correct on-call channel.

## 6. Backup & Rollback Checklist
- [ ] Take a snapshot of the PostgreSQL metadata database before applying migrations.
- [ ] Verify MLflow artifact storage (e.g., S3 or EFS) has versioning enabled.
- [ ] In case of a critical failure:
  - Immediately revert the Docker image tag to the previous stable release.
  - Monitor logs for dependency or schema mismatches.
  - If a schema mismatch occurs, restore the PostgreSQL snapshot taken prior to deployment.
