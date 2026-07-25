# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build — compile all Python wheels
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install OS build dependencies (needed for C-extension wheels)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
        gcc \
        g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Production — minimal runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO

# Install runtime OS libraries only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r featureflow && useradd -r -g featureflow featureflow

# Copy pre-compiled wheels and install — no network access needed
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy application code
COPY . .

# Ensure required runtime directories exist and are owned by non-root user
RUN mkdir -p /app/models /app/datasets /app/reports && \
    chown -R featureflow:featureflow /app

USER featureflow

EXPOSE 8000

# Kubernetes / Docker liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/live || exit 1

# Production ASGI server
CMD ["uvicorn", "app.serving.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
