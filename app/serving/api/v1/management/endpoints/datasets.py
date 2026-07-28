"""
Dataset Upload and Management API.
"""
import os
import io
import uuid
import hashlib
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.storage.database import get_db
from app.storage.models import Dataset, DatasetVersion, Feature
from app.monitoring.audit import AuditLogger, AuditEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/datasets", tags=["datasets"])

DATASETS_DIR = os.environ.get("DATA_DIR", "datasets")


def _compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _compute_profile(df: pd.DataFrame) -> dict:
    profile = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": {},
        "null_counts": {},
        "null_percentage_max": 0.0,
        "duplicate_count": int(df.duplicated().sum()),
        "estimated_memory_bytes": int(df.memory_usage(deep=True).sum()),
    }
    max_null_pct = 0.0
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = (null_count / len(df) * 100) if len(df) > 0 else 0.0
        max_null_pct = max(max_null_pct, null_pct)
        col_info = {
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_pct": round(null_pct, 2),
            "unique_count": int(df[col].nunique()),
        }
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info.update({
                "min": float(df[col].min()) if not df[col].isnull().all() else None,
                "max": float(df[col].max()) if not df[col].isnull().all() else None,
                "mean": float(df[col].mean()) if not df[col].isnull().all() else None,
                "std": float(df[col].std()) if not df[col].isnull().all() else None,
            })
        profile["columns"][col] = col_info
        profile["null_counts"][col] = null_count
    profile["null_percentage_max"] = round(max_null_pct, 2)
    return profile


async def _auto_train_background(dataset_id: str, dataset_name: str, file_path: str):
    """Trigger the training orchestrator as a background task."""
    from app.storage.database import AsyncSessionLocal
    from app.training.orchestrator import TrainingOrchestrator
    import asyncio
    # Small delay to ensure DB commit is fully visible
    await asyncio.sleep(0.5)
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy.future import select as sa_select
            from app.storage.models import Dataset as DatasetModel
            result = await session.execute(sa_select(DatasetModel).filter(DatasetModel.id == dataset_id))
            dataset_record = result.scalars().first()
            if dataset_record:
                # Use absolute path as data_dir, pass just filename as relative_path
                data_dir = os.path.dirname(file_path)
                filename = os.path.basename(file_path)
                orchestrator = TrainingOrchestrator(data_dir=data_dir)
                await orchestrator.execute(session, dataset_record, relative_path=filename)
                await session.commit()
        except Exception as e:
            logger.error(f"Background training failed for dataset {dataset_name}: {e}")
            await session.rollback()


@router.post("/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    auto_train: bool = Form(True),
    session: AsyncSession = Depends(get_db)
):
    """
    Upload a CSV or Parquet dataset.
    Automatically profiles, validates, registers features, and triggers training.
    """
    content = await file.read()
    filename = file.filename or "dataset.csv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"

    if ext not in ("csv", "parquet"):
        raise HTTPException(status_code=400, detail="Only CSV and Parquet files are supported.")

    # Parse the dataframe
    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_parquet(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    if df.empty:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    # Dataset name
    dataset_name = name or filename.rsplit(".", 1)[0].replace(" ", "_").lower()

    # We will no longer save the file to local disk (DATASETS_DIR)
    # Instead, we will store the raw bytes in the PostgreSQL Database
    save_path = f"db://datasets/{dataset_name}.csv"

    # Compute profile
    profile = _compute_profile(df)
    checksum = _compute_checksum(content)

    # Detect or generate Entity ID column
    entity_key_col = None
    candidate_cols = ["user_id", "customer_id", "account_id", "transaction_id", "entity_id", "id"]
    for col in candidate_cols:
        if col in df.columns:
            entity_key_col = col
            break
            
    if not entity_key_col:
        entity_key_col = "_entity_id"
        df["_entity_id"] = [str(uuid.uuid4()) for _ in range(len(df))]

    # Inferred dtypes dict (do this AFTER adding _entity_id)
    inferred_dtypes = {col: str(df[col].dtype) for col in df.columns}

    # Get or create Dataset
    result = await session.execute(select(Dataset).filter(Dataset.name == dataset_name))
    dataset_record = result.scalars().first()

    if dataset_record:
        # Update version
        dataset_record.version = dataset_record.version + 1
        dataset_record.inferred_dtypes = inferred_dtypes
        dataset_record.entity_key_column = entity_key_col
        dataset_record.status = "ACTIVE"
        dataset_record.description = description or dataset_record.description
        dataset_record.updated_at = datetime.now(timezone.utc)
    else:
        dataset_record = Dataset(
            id=str(uuid.uuid4()),
            name=dataset_name,
            description=description or f"Uploaded from {filename}",
            inferred_dtypes=inferred_dtypes,
            entity_key_column=entity_key_col,
            status="ACTIVE",
            version=1
        )
        session.add(dataset_record)

    await session.flush()

    # Convert DataFrame back to CSV bytes for storage
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue()

    # Create DatasetVersion
    dv_result = await session.execute(
        select(DatasetVersion).filter(
            DatasetVersion.dataset_id == dataset_record.id,
            DatasetVersion.version_tag == checksum
        )
    )
    dataset_version = dv_result.scalars().first()
    if not dataset_version:
        dataset_version = DatasetVersion(
            id=str(uuid.uuid4()),
            dataset_id=dataset_record.id,
            version_tag=checksum,
            file_path=save_path,
            raw_data=csv_bytes,
            row_count=profile["row_count"],
            status="ACTIVE",
            version=dataset_record.version
        )
        session.add(dataset_version)
    await session.flush()

    await session.commit()
    
    # Fire EventBus Event for Lifecycle Orchestrator
    try:
        from app.events import get_event_bus
        from app.events.schema import Event, EventType, EventSeverity
        bus = get_event_bus()
        if bus:
            await bus.publish(Event(
                type=EventType.DATASET_UPLOADED,
                source="datasets.api",
                severity=EventSeverity.INFO,
                payload={
                    "dataset_id": dataset_record.id,
                    "dataset_name": dataset_name,
                    "version": dataset_record.version
                }
            ))
    except Exception as e:
        logger.warning(f"Failed to publish DATASET_UPLOADED event: {e}")

    # Audit log
    await AuditLogger.record(session, AuditEvent(
        event_name="DATASET_UPLOADED",
        component="DatasetUploadAPI",
        severity="INFO",
        payload={
            "dataset_id": dataset_record.id,
            "dataset_name": dataset_name,
            "file_name": filename,
            "row_count": profile["row_count"],
            "column_count": profile["column_count"],
            "checksum": checksum
        }
    ))

    return {
        "status": "success",
        "dataset_id": dataset_record.id,
        "dataset_name": dataset_name,
        "version": dataset_record.version,
        "row_count": profile["row_count"],
        "column_count": profile["column_count"],
        "columns": list(df.columns),
        "profile": profile,
        "message": f"Dataset '{dataset_name}' uploaded successfully. Lifecycle pipeline triggered via EventBus."
    }


@router.get("")
async def list_datasets(
    page: int = 1,
    size: int = 50,
    session: AsyncSession = Depends(get_db)
):
    """Lists all registered datasets with their profiling stats."""
    result = await session.execute(
        select(Dataset)
        .filter(Dataset.status != "ARCHIVED")
        .order_by(desc(Dataset.created_at))
    )
    datasets = result.scalars().all()

    items = []
    for d in datasets:
        # Get latest version
        dv_res = await session.execute(
            select(DatasetVersion)
            .filter(DatasetVersion.dataset_id == d.id)
            .order_by(desc(DatasetVersion.created_at))
            .limit(1)
        )
        dv = dv_res.scalars().first()

        # Get feature count
        feat_res = await session.execute(
            select(Feature)
            .filter(Feature.dataset_id == d.id, Feature.status == "ACTIVE")
        )
        features = feat_res.scalars().all()

        # Compute profile stats from inferred_dtypes
        dtypes = d.inferred_dtypes or {}
        numeric_cols = [col for col, dtype in dtypes.items() if 'int' in str(dtype) or 'float' in str(dtype)]

        items.append({
            "id": d.id,
            "dataset_name": d.name,
            "name": d.name,
            "description": d.description,
            "status": d.status,
            "validation_status": dv.status if dv else "PENDING",
            "profiling_status": "COMPLETE" if d.inferred_dtypes else "PENDING",
            "schema_status": "INFERRED" if d.inferred_dtypes else "PENDING",
            "version": d.version,
            "row_count": dv.row_count if dv else 0,
            "column_count": len(dtypes),
            "numeric_column_count": len(numeric_cols),
            "feature_count": len(features),
            "inferred_dtypes": dtypes,
            "columns": list(dtypes.keys()),
            "null_percentage_max": 0.0,
            "duplicate_count": 0,
            "estimated_memory_bytes": (dv.row_count or 0) * len(dtypes) * 8 if dv else 0,
            "last_profile_time": d.updated_at.isoformat() if d.updated_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    total = len(items)
    start = (page - 1) * size
    sliced = items[start: start + size]
    return {"items": sliced, "total": total, "page": page, "size": size, "has_next": (start + size) < total}


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Gets a single dataset with full detail."""
    result = await session.execute(select(Dataset).filter(Dataset.id == dataset_id))
    d = result.scalars().first()
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dv_res = await session.execute(
        select(DatasetVersion)
        .filter(DatasetVersion.dataset_id == d.id)
        .order_by(desc(DatasetVersion.created_at))
        .limit(1)
    )
    dv = dv_res.scalars().first()

    feat_res = await session.execute(
        select(Feature).filter(Feature.dataset_id == d.id, Feature.status == "ACTIVE")
    )
    features = feat_res.scalars().all()

    return {
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "status": d.status,
        "version": d.version,
        "inferred_dtypes": d.inferred_dtypes or {},
        "columns": list((d.inferred_dtypes or {}).keys()),
        "row_count": dv.row_count if dv else 0,
        "column_count": len(d.inferred_dtypes or {}),
        "features": [{"id": f.id, "name": f.name, "dtype": f.dtype} for f in features],
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Archives a dataset."""
    result = await session.execute(select(Dataset).filter(Dataset.id == dataset_id))
    d = result.scalars().first()
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    d.status = "ARCHIVED"
    await AuditLogger.record(session, AuditEvent(
        event_name="DATASET_ARCHIVED",
        component="DatasetAPI",
        severity="INFO",
        payload={"dataset_id": dataset_id, "dataset_name": d.name}
    ))
    await session.commit()
    return {"status": "archived", "dataset_id": dataset_id}
