# Changelog

All notable changes to FeatureFlow are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-07-25

### 🎉 Initial Production Release — PostgreSQL Gold Edition

This is the first stable, certified release of FeatureFlow v1.0.0.

---

### Added — Core Platform (Phases 1–7)

- **Dataset Discovery Engine**: Automatic introspection and registration of raw CSV datasets with schema inference
- **Data Validation Layer**: Column-level schema contracts, null checks, and cardinality validation via Great Expectations
- **Baseline Profiling**: Statistical distribution analysis stored in PostgreSQL for drift comparison
- **Feature Engineering Pipeline**: Automated binning, encoding, and wide-table feature registry
- **Multi-Algorithm Training**: Unified training pipeline supporting Logistic Regression, Decision Tree, and Random Forest
- **Evaluation Framework**: Precision, Recall, F1, ROC-AUC metrics logged per-run
- **Champion Selection**: Automated model promotion to `champion` alias using best F1 score
- **Artifact Store**: Joblib-backed binary model persistence with SHA-256 integrity checksums
- **Prediction Engine**: Low-latency real-time and batch inference with dynamic champion/challenger routing
- **Audit Logging**: Immutable event log for every lifecycle event (`TRAINING_STARTED`, `MODEL_LOADED`, `PREDICTION_FINISHED`, etc.)

---

### Added — Infrastructure & Storage (Phase 8–9)

- **Async PostgreSQL Backend**: SQLAlchemy 2.0 with asyncpg for fully non-blocking I/O
- **Repository Pattern**: `DatasetRepository`, `FeatureRepository`, `ModelRepository`, `ChampionModelRepository`
- **Redis Online Store**: Sub-millisecond feature serving from Redis with TTL management and PostgreSQL fallback
- **Redis Prediction Cache**: Deduplication of identical inference requests with SHA-256 cache keys
- **Redis Model Cache**: In-memory caching of serialized champion models to eliminate cold-start latency
- **Enterprise Redis Client**: Connection pooling, auto-reconnection, circuit breaking, health monitoring, and recovery manager

---

### Added — Security (Phase 10)

- **JWT Authentication**: RS256/HS256 signed tokens with configurable expiry
- **API Key Management**: Long-lived programmatic API keys with bcrypt-secured storage
- **RBAC**: Role-based access control with permission enforcement on sensitive endpoints
- **Rate Limiting**: Configurable per-endpoint request throttling
- **Security Headers Middleware**: `X-Content-Type-Options`, `X-Frame-Options`, `HSTS`, `CSP`
- **Dynamic CORS**: Environment-variable-driven `CORS_ORIGINS` configuration
- **Stack Trace Redaction**: Internal errors masked in production responses

---

### Added — MLflow Integration (Phase 11)

- **Experiment Tracking**: All training runs tracked with full hyperparameter and metric logging
- **MLflow Aliases**: Modern alias-based model lifecycle management (`development`, `staging`, `champion`, `challenger`)
- **PostgreSQL Schema Isolation**: MLflow uses a dedicated `mlflow` schema, isolated from application tables
- **MLflow Service Layer**: Pydantic-validated response models for all MLflow API interactions

---

### Added — Observability (Phase 12)

- **Prometheus Metrics**: Custom `featureflow_*` metrics for HTTP requests, predictions, training, and system resources
- **Grafana Dashboards**: Auto-provisioned dashboards (Platform Overview, API, ML, Data Quality, Redis, System)
- **Prometheus Alerting**: Pre-configured alert rules for error rates, latency, and Redis memory
- **Background System Metrics**: `psutil`-based CPU/memory metrics collected asynchronously every 10 seconds
- **Configurable Metrics Auth**: `ENABLE_METRICS_AUTH` flag to protect `/metrics` endpoint in production
- **Observability Middleware**: Per-request latency, status code, and active request tracking

---

### Added — Production Infrastructure (Phase 13A)

- **Multi-Stage Dockerfile**: Optimized production image with non-root user, health check, and minimal footprint
- **Dockerfile.dev**: Hot-reload development container
- **docker-compose.yml / docker-compose.prod.yml**: Dev and production stack with restart policies and resource limits
- **.dockerignore**: Excludes `venv/`, `.env*`, `__pycache__`, and test artifacts
- **GitHub Actions CI**: Automated lint, test, and certification pipeline on every push/PR
- **GitHub Actions Docker**: Docker image build and compose validation
- **GitHub Actions Release**: Semantic version enforcement and artifact packaging on git tags
- **Alembic Migrations**: Async SQLAlchemy migration support with full `upgrade`/`downgrade`/`history` support
- **Initial Migration**: Auto-generated baseline migration from current SQLAlchemy models
- **Startup Validation**: Application validates PostgreSQL, Redis, MLflow, and storage paths on boot
- **Environment Management**: `.env.example`, `.env.development`, `.env.production` templates
- **Secrets Hardening**: No secrets in code defaults; all secrets from environment only

---

### Added — Security & Reliability (Phase 13B)

- **Liveness Probe** (`GET /live`): Confirms process is alive for Kubernetes liveness checks
- **Readiness Probe** (`GET /ready`): Confirms all dependencies ready; returns `503` when unready
- **Health Endpoint** (`GET /health`): Full component health aggregation
- **JSON Structured Logging**: Production environments emit JSON log lines for ELK/Datadog/GCP ingestion
- **OpenAPI Enhancements**: Rich Swagger UI with platform description, version, and contact metadata
- **API Documentation**: Full endpoint reference with cURL examples in `docs/API.md`

---

### Added — Documentation (Phase 13C)

- `docs/ARCHITECTURE.md` — System design and component interactions
- `docs/API.md` — Full API reference with examples
- `docs/DEPLOYMENT.md` — Local, Docker, and cloud deployment guide
- `docs/OBSERVABILITY.md` — Metrics, dashboards, and alerting
- `docs/RELEASE_CHECKLIST.md` — Pre-production verification checklist
- `docs/CONTRIBUTING.md` — Contributor guide
- `docs/BACKUP_RECOVERY.md` — Backup and disaster recovery procedures
- `CHANGELOG.md` — This file

---

### Infrastructure

- Python 3.12+
- FastAPI 0.115+, Pydantic v2
- PostgreSQL 15+, SQLAlchemy 2.0 (async)
- Redis 7.0+
- MLflow 2.x
- Prometheus, Grafana
- Docker, Docker Compose
- Alembic
- GitHub Actions

---

## [Unreleased]

### Planned for v1.1+
- gRPC feature serving endpoint
- S3/MinIO artifact store integration
- Kubernetes Helm chart
- A/B testing traffic split for champion/challenger
- Kafka streaming feature ingestion
