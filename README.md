<div align="center">

# FeatureFlow
### Enterprise-Grade Machine Learning & Feature Store Platform
**Gold Release Certified Edition (PostgreSQL Production Architecture)**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.0+-316192.svg)](https://www.postgresql.org/)
[![SQLAlchemy Async](https://img.shields.io/badge/SQLAlchemy-2.0%20Async-red.svg)](https://docs.sqlalchemy.org/)
[![Docker Compatibility](https://img.shields.io/badge/Docker-Certified-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## Overview

**FeatureFlow** is an autonomous, end-to-end Machine Learning Operations (MLOps) and Feature Store platform engineered to bridge the gap between raw data ingestion and real-time production serving. Built from the ground up to prevent **training-serving skew**, FeatureFlow orchestrates the entire ML lifecycle through an automated 11-stage pipeline governed by strict data validation, feature computation, cryptographic artifact verification, and audit logging.

This repository represents the **PostgreSQL Gold Release**—a certified production architecture providing unified feature management, multi-algorithm model training, automated champion selection, and deterministic low-latency batch and real-time inference using a fully async PostgreSQL backend.

---

## Architecture & Core Pipeline

FeatureFlow processes datasets autonomously through an **11-Stage Production Pipeline**:

```mermaid
graph TD
    A[1. Dataset Discovery] -->|Introspect raw CSVs| B[2. Schema Registration]
    B -->|Strict Column Contracts| C[3. Data Validation]
    C -->|Null Check & Cardinality| D[4. Baseline Profiling]
    D -->|Statistical Distributions| E[5. Feature Engineering]
    E -->|Automated Transformations| F[6. Feature Registry]
    F -->|Wide-Table Persistence| G[7. Multi-Algorithm Training]
    G -->|LR, DT, RF Models| H[8. Evaluation & Metrics]
    H -->|Precision, Recall, F1| I[9. Champion Selection]
    I -->|Automated Promotion| J[10. Prediction Engine]
    J -->|Low-Latency Serving| K[11. Observability & Audit]
```

### Key Architectural Highlights
1. **Zero Training-Serving Skew**: Features transformed during training (`FeatureTransformer`) are dynamically executed with identical parameters during real-time inference (`ModelPredictor`).
2. **Asynchronous PostgreSQL Storage**: Fully reactive persistence layer utilizing `SQLAlchemy AsyncSession`, declarative models (`app.storage.models`), and strict Repository Pattern implementations (`DatasetRepository`, `FeatureRepository`, `ModelRepository`, `ChampionModelRepository`).
3. **Cryptographic Artifact Integrity**: Every trained model serialized via `LocalArtifactStore` generates a deterministic SHA-256 checksum, verified automatically upon model loading.
4. **Traffic Routing & Fallbacks**: The `PredictionEngine` integrates dynamic traffic routing between `CHAMPION` and `CHALLENGER` models with automatic fallback capabilities if primary execution encounters validation warnings.
5. **Full System Observability**: Every lifecycle event (`DATASET_DISCOVERED`, `TRAINING_STARTED`, `MODEL_LOADED`, `PREDICTION_FINISHED`) is immutably logged to PostgreSQL via `AuditLogger`.

---

## Tech Stack

### Core Service & API Layer
- **Python 3.12+**: Modern asynchronous runtime utilizing strict type annotations and frozen data contracts.
- **FastAPI & Pydantic v2**: High-performance RESTful API endpoints with automated OpenAPI documentation and payload validation.
- **Uvicorn & AnyIO**: Asynchronous ASGI server and event loop management.

### Storage & Persistence Layer
- **PostgreSQL 16**: Primary relational engine for metadata, feature registries, model lineage, and audit logs.
- **SQLAlchemy 2.0 (asyncio + asyncpg)**: Asynchronous ORM utilizing non-blocking connection pooling and eager loading (`selectinload`).
- **Local File Artifacts**: Joblib-backed binary model storage (`models/`) secured with SHA-256 checksums.

### Machine Learning & Feature Computation
- **Scikit-Learn**: Multi-algorithm training (`LogisticRegression`, `DecisionTreeClassifier`, `RandomForestClassifier`).
- **Pandas & NumPy**: High-throughput tabular data processing, discretization, and statistical profiling.

### DevOps & Infrastructure
- **Docker & Docker Compose**: Multi-stage container builds (`Dockerfile`) and unified stack orchestration (`docker-compose.yml`).
- **Nginx**: Reverse proxy supporting CORS, health checks, and API routing.
- **GitHub Actions**: Continuous integration running static analysis (`flake8`) and test validation across Python 3.12+.

---

## Directory Structure

```text
FeatureFlow/
├── app/
│   ├── data/           # Dataset discovery, loaders, validation, schema, and baseline profiling
│   ├── features/       # Automated feature engineering, transformers, and wide-table registry
│   ├── training/       # Multi-algorithm trainers, splitters, evaluators, orchestrator & SHA-256 artifacts
│   ├── inference/      # Low-latency prediction engine, request/response contracts, traffic router & fallbacks
│   ├── storage/        # SQLAlchemy async models, database connection pool & repository layer
│   ├── serving/        # FastAPI application, CORS middleware, API v1 endpoints & health checks
│   ├── monitoring/     # Audit logging system and drift detection triggers
│   └── utils/          # Standardized logging and system configuration utilities
├── datasets/raw/       # Domain-agnostic raw CSV datasets ingested by discovery engine
├── models/             # Persisted joblib model binaries with integrity checksums
├── scripts/            # Production acceptance certification runner & diagnostics
├── tests/              # Pytest verification suites (unit, API integration, and database performance)
├── .github/workflows/  # CI/CD pipelines for automated testing and code quality
├── Dockerfile          # Production backend container build definition
├── docker-compose.yml  # Complete multi-container orchestration (PostgreSQL + FastAPI + Nginx)
└── requirements.txt    # Locked production Python dependencies
```

---

## Setup & Local Development

### 1. Prerequisites
- Python 3.12 or higher
- PostgreSQL 16+ running locally or via Docker
- Git

### 2. Environment Variables
Create a `.env` file in the project root (or export directly in your shell):
```env
# PostgreSQL Connection String (Async format)
POSTGRES_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/featureflow"

# Application Settings
ENVIRONMENT="production"
LOG_LEVEL="INFO"
ARTIFACT_STORAGE_PATH="./models"
```

### 3. Installation & Virtual Environment
```bash
# Clone the repository
git clone https://github.com/shanmukha1013/FeatureFlow.git
cd FeatureFlow

# Create and activate virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Running the Server Locally
Launch the FastAPI backend server with Uvicorn:
```bash
python -m uvicorn app.serving.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **ReDoc Schema**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## Running with Docker Compose

FeatureFlow is container-ready. To launch the entire platform (PostgreSQL Database + Backend API + Nginx Proxy) in an isolated container stack:

```bash
# Build and start services in detached mode
docker-compose up --build -d

# Check container health and logs
docker-compose ps
docker-compose logs -f backend
```
- The backend API will be accessible at `http://localhost:8000` (and `http://localhost:80` via Nginx).
- The PostgreSQL container automatically initializes the `featureflow` database with persistent volume storage.

---

## Testing & Production Certification

FeatureFlow includes a comprehensive testing and certification harness that guarantees zero regressions before production deployment.

### 1. Pytest Unit & Integration Suite
Run our automated test suites (`test_api.py`, `test_ml.py`, `perf_database.py`):
```bash
pytest -v
```

### 2. Static Analysis & Code Quality
Run `flake8` across all application and test modules:
```bash
flake8 app/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
```

### 3. Production Acceptance Test Script (`scripts/production_acceptance_test.py`)
This standalone audit script executes the complete 11-stage pipeline from scratch across raw datasets, testing database connectivity, discovery, feature transformations, training, champion selection, inference routing, and audit logs:
```bash
python scripts/production_acceptance_test.py
```

**Expected Certification Summary:**
```text
========================================
FEATUREFLOW PRODUCTION ACCEPTANCE TEST
========================================
Database ................. PASS
Dataset Discovery ........ PASS
Validation ............... PASS
Profiling ............... PASS
Feature Engineering ...... PASS
Training ................ PASS
Champion Selection ....... PASS
Inference ............... PASS
Audit Logging ........... PASS
Dashboard ............... PASS
Health Checks ........... PASS
Overall Result .......... PASS
========================================
```

---

## Deployment Guide

When deploying FeatureFlow to a cloud provider (AWS ECS, GCP Cloud Run, Azure App Service, or Kubernetes):
1. **Database Provisioning**: Provision a managed PostgreSQL instance (e.g., AWS RDS PostgreSQL 16) and configure `POSTGRES_URL` using `postgresql+asyncpg://...`.
2. **Persistent Artifact Storage**: Mount a shared volume (AWS EFS or PVC) to `/app/models` to ensure all API replicas share trained `.joblib` model artifacts cleanly.
3. **Health Probes**: Configure Kubernetes/Container health checks against `GET /health` (`status: 200 OK`).
4. **CORS & Reverse Proxy**: In production, update `allow_origins` in `app/serving/main.py` or let Nginx handle SSL termination and domain whitelisting.

---

## Connect

**Portfolio**  
https://shanmukha-portfolio-six.vercel.app

**LinkedIn**  
https://linkedin.com/in/marellashanmukhareddy

---

<div align="center">

**From Ideas to Products.**

</div>
