import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

# For cross-compatibility with SQLite and PostgreSQL
JSONB = JSON().with_variant(PG_JSONB(), "postgresql")
from sqlalchemy.orm import relationship
from app.storage.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    inferred_dtypes = Column(JSONB, nullable=True)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")
    features = relationship("Feature", back_populates="dataset", cascade="all, delete-orphan")
    models = relationship("Model", back_populates="dataset", cascade="all, delete-orphan")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    row_count = Column(Integer, nullable=True)
    status = Column(String, default="VALIDATED", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('dataset_id', 'version_tag', name='uq_dataset_version'),)
    dataset = relationship("Dataset", back_populates="versions")
    validation_reports = relationship("ValidationReport", back_populates="dataset_version", cascade="all, delete-orphan")
    profiling_reports = relationship("ProfilingReport", back_populates="dataset_version", cascade="all, delete-orphan")

class ValidationReport(Base):
    __tablename__ = "validation_reports"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_version_id = Column(String, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    report_data = Column(JSONB, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    dataset_version = relationship("DatasetVersion", back_populates="validation_reports")

class ProfilingReport(Base):
    __tablename__ = "profiling_reports"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_version_id = Column(String, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    profile_data = Column(JSONB, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    dataset_version = relationship("DatasetVersion", back_populates="profiling_reports")

class Feature(Base):
    __tablename__ = "features"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, index=True, nullable=False)
    dtype = Column(String, nullable=False)
    transformation = Column(String, nullable=True)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('dataset_id', 'name', name='uq_dataset_feature'),)
    dataset = relationship("Dataset", back_populates="features")
    values = relationship("FeatureValue", back_populates="feature", cascade="all, delete-orphan")
    lineage = relationship("FeatureLineage", back_populates="feature", cascade="all, delete-orphan")

class FeatureRegistry(Base):
    __tablename__ = "feature_registry"
    id = Column(String, primary_key=True, default=gen_uuid)
    namespace = Column(String, nullable=False, index=True)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class FeatureValue(Base):
    __tablename__ = "feature_values"
    id = Column(String, primary_key=True, default=gen_uuid)
    feature_id = Column(String, ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    value_json = Column(JSONB, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('feature_id', 'entity_id', name='uq_feature_entity'),)
    feature = relationship("Feature", back_populates="values")

class FeatureLineage(Base):
    __tablename__ = "feature_lineage"
    id = Column(String, primary_key=True, default=gen_uuid)
    feature_id = Column(String, ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True)
    source_columns = Column(JSONB, nullable=False)
    transform_logic = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    feature = relationship("Feature", back_populates="lineage")

class Model(Base):
    __tablename__ = "models"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, index=True, nullable=False)
    algorithm = Column(String, nullable=True)
    metrics = Column(JSONB, nullable=True)
    hyperparameters = Column(JSONB, nullable=True)
    artifact_uri = Column(String, nullable=True)
    status = Column(String, default="REGISTERED", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('dataset_id', 'name', name='uq_dataset_model'),)
    dataset = relationship("Dataset", back_populates="models")
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    champions = relationship("ChampionModel", back_populates="model", cascade="all, delete-orphan")

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(String, primary_key=True, default=gen_uuid)
    model_id = Column(String, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag = Column(String, nullable=False)
    metrics = Column(JSONB, nullable=False)
    hyperparameters = Column(JSONB, nullable=True)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('model_id', 'version_tag', name='uq_model_version'),)
    model = relationship("Model", back_populates="versions")
    artifacts = relationship("ModelArtifact", back_populates="model_version", cascade="all, delete-orphan")

class ModelArtifact(Base):
    __tablename__ = "model_artifacts"
    id = Column(String, primary_key=True, default=gen_uuid)
    model_version_id = Column(String, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    model_version = relationship("ModelVersion", back_populates="artifacts")

class ChampionModel(Base):
    __tablename__ = "champion_models"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(String, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('dataset_id', name='uq_dataset_champion'),)
    model = relationship("Model", back_populates="champions")

class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, unique=False, index=True, nullable=False)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    algorithm = Column(String, nullable=True)
    hyperparameters = Column(JSONB, nullable=True)
    metrics = Column(JSONB, nullable=True)
    model_id = Column(String, nullable=True)
    status = Column(String, default="RUNNING", index=True)
    version = Column(Integer, default=1)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    status = Column(String, default="STARTED", index=True)
    stages_json = Column(JSONB, nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class TrainingMetric(Base):
    __tablename__ = "training_metrics"
    id = Column(String, primary_key=True, default=gen_uuid)
    model_version_id = Column(String, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class InferenceRequest(Base):
    __tablename__ = "inference_requests"
    id = Column(String, primary_key=True, default=gen_uuid)
    model_version_id = Column(String, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    status = Column(String, default="RECEIVED", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class InferenceResponse(Base):
    __tablename__ = "inference_responses"
    id = Column(String, primary_key=True, default=gen_uuid)
    request_id = Column(String, ForeignKey("inference_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    response_payload = Column(JSONB, nullable=False)
    latency_ms = Column(Float, nullable=False)
    status = Column(String, default="SUCCESS", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(String, primary_key=True, default=gen_uuid)
    model_version_id = Column(String, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_value = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class DriftReport(Base):
    __tablename__ = "drift_reports"
    id = Column(String, primary_key=True, default=gen_uuid)
    model_version_id = Column(String, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    drift_detected = Column(Boolean, default=False)
    report_data = Column(JSONB, nullable=False)
    status = Column(String, default="GENERATED", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class DriftMetric(Base):
    __tablename__ = "drift_metrics"
    id = Column(String, primary_key=True, default=gen_uuid)
    report_id = Column(String, ForeignKey("drift_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class RetrainingJob(Base):
    __tablename__ = "retraining_jobs"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="PENDING", index=True)
    job_metadata = Column(JSONB, nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=gen_uuid)
    event_name = Column(String, nullable=False, index=True)
    component = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)
    payload = Column(JSONB, nullable=True)
    status = Column(String, default="RECORDED", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(String, primary_key=True, default=gen_uuid)
    role_id = Column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SystemMetric(Base):
    __tablename__ = "system_metrics"
    id = Column(String, primary_key=True, default=gen_uuid)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(String, primary_key=True, default=gen_uuid)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
