import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

from app.storage.database import Base

JSONB = JSON().with_variant(PG_JSONB(), "postgresql")


def gen_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class DataContractModel(Base):
    __tablename__ = "data_contracts"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_name = Column(String, index=True, nullable=False)
    version = Column(Integer, default=1)
    owner = Column(String, nullable=True)
    schema_definition = Column(JSONB, nullable=False)
    business_rules = Column(JSONB, nullable=True)
    primary_keys = Column(JSONB, nullable=True)
    status = Column(String, default="ACTIVE", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('dataset_name', 'version', name='uq_contract_version'),)
    expectation_suites = relationship("ExpectationSuiteModel", back_populates="contract", cascade="all, delete-orphan")


class ExpectationSuiteModel(Base):
    __tablename__ = "expectation_suites"
    id = Column(String, primary_key=True, default=gen_uuid)
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, index=True, nullable=False)
    suite_version = Column(Integer, default=1)
    expectation_configs = Column(JSONB, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    contract = relationship("DataContractModel", back_populates="expectation_suites")
    validation_runs = relationship("ValidationRun", back_populates="suite", cascade="all, delete-orphan")


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    id = Column(String, primary_key=True, default=gen_uuid)
    suite_id = Column(String, ForeignKey("expectation_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_version_id = Column(String, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_run_id = Column(String, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True, index=True)

    success = Column(Boolean, nullable=False)
    quality_score = Column(Float, nullable=False)

    critical_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)

    execution_time_ms = Column(Float, nullable=False)
    gx_version = Column(String, nullable=True)
    dataset_checksum = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    suite = relationship("ExpectationSuiteModel", back_populates="validation_runs")
    dataset_version = relationship("DatasetVersion", backref="validation_runs")
    pipeline_run = relationship("PipelineRun", backref="validation_runs")
    results = relationship("ExpectationResult", back_populates="validation_run", cascade="all, delete-orphan")


class ExpectationResult(Base):
    __tablename__ = "expectation_results"
    id = Column(String, primary_key=True, default=gen_uuid)
    validation_run_id = Column(String, ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    expectation_type = Column(String, nullable=False, index=True)
    severity = Column(String, default="ERROR", index=True)  # CRITICAL, ERROR, WARNING, INFO
    success = Column(Boolean, nullable=False)
    kwargs = Column(JSONB, nullable=True)
    observed_value = Column(String, nullable=True)
    result_data = Column(JSONB, nullable=True)
    exception_info = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    validation_run = relationship("ValidationRun", back_populates="results")


class ValidationReplayJob(Base):
    __tablename__ = "validation_replay_jobs"
    id = Column(String, primary_key=True, default=gen_uuid)
    dataset_version_id = Column(String, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    suite_id = Column(String, ForeignKey("expectation_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="PENDING", index=True)  # PENDING, RUNNING, COMPLETED, FAILED
    result_validation_run_id = Column(String, ForeignKey("validation_runs.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
