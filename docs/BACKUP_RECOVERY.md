# Backup & Disaster Recovery

This document describes the backup strategy and recovery procedures for FeatureFlow production deployments.

## What to Back Up

FeatureFlow has three categories of critical data:

| Data | Location | Criticality |
|---|---|---|
| Application metadata (datasets, features, models, audit logs) | PostgreSQL `public` schema | **Critical** |
| Experiment tracking (runs, metrics, params, tags) | PostgreSQL `mlflow` schema | **Critical** |
| Trained model artifacts (`.joblib` files + checksums) | `/app/models` volume | **Critical** |
| Grafana dashboards & state | `grafana_data` Docker volume | Medium |
| Prometheus time-series data | `prometheus_data` Docker volume | Low |

---

## 1. PostgreSQL Backup

### Automated Daily Backup (Recommended)

Use `pg_dump` to create a compressed, consistent snapshot:

```bash
pg_dump -U featureflow -d featureflow_production \
  -F c -f /backups/featureflow_$(date +%Y%m%d).dump
```

For both schemas in one operation:

```bash
pg_dumpall -U featureflow > /backups/featureflow_full_$(date +%Y%m%d).sql
```

### Restore PostgreSQL

```bash
# Restore from custom format dump
pg_restore -U featureflow -d featureflow_production \
  -c /backups/featureflow_20261201.dump
```

> [!CAUTION]
> Always test restores in a staging environment before applying to production.

---

## 2. Model Artifact Backup

All trained models are stored in the `/app/models` directory (mapped to a Docker named volume `featureflow_models`).

### Backup

```bash
docker run --rm \
  -v featureflow_models:/data \
  -v /backups:/backup \
  alpine tar czf /backup/models_$(date +%Y%m%d).tar.gz /data
```

### Restore

```bash
docker run --rm \
  -v featureflow_models:/data \
  -v /backups:/backup \
  alpine tar xzf /backup/models_20261201.tar.gz -C /
```

---

## 3. Recovery Procedures

### Scenario: PostgreSQL Data Loss

1. Stop the application: `docker compose down api`
2. Restore database: `pg_restore ...`
3. Run Alembic to ensure migrations are current: `alembic upgrade head`
4. Restart: `docker compose up api -d`
5. Verify health: `curl http://localhost:8000/ready`

### Scenario: Redis Data Loss

Redis is a **cache layer only**. All data stored in Redis is also available in PostgreSQL.

1. Restart Redis: `docker compose restart redis`
2. The application automatically re-populates caches from PostgreSQL on the next request.
3. Monitor cache hit rate via Grafana until it stabilizes.

### Scenario: Model Artifacts Lost

1. Restore from the model artifact backup (see Section 2).
2. Verify model checksums have been restored correctly.
3. Alternatively, re-run training for the affected dataset to regenerate the champion model.

---

## 4. RTO & RPO Targets

| Scenario | Recovery Time Objective (RTO) | Recovery Point Objective (RPO) |
|---|---|---|
| Redis failure | < 1 minute | 0 (cache is ephemeral) |
| API pod failure | < 30 seconds (container restart) | 0 |
| PostgreSQL failure | < 15 minutes | Last daily backup |
| Full datacenter failure | < 1 hour | Last daily backup |

---

## 5. Monitoring Backup Health

Use Prometheus alerting (`prometheus/alerts.yml`) to notify on-call engineers if backups are stale or storage thresholds are exceeded.

For critical production deployments, use a managed PostgreSQL service (AWS RDS, GCP Cloud SQL, Azure Database) that provides automated point-in-time recovery (PITR) with a 35-day retention window.
