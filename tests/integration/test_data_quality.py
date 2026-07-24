from app.storage.models import Dataset, DatasetVersion
from app.storage.database import AsyncSessionLocal
from app.data_quality.service import DataQualityService
import uuid
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_data_quality_service_baseline_creation():
    # Setup
    dataset_name = f"test_quality_dataset_{uuid.uuid4().hex[:8]}"
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "value": [10.5, 20.2, 30.0],
        "category": ["A", "B", "A"]
    })

    async with AsyncSessionLocal() as session:
        # Create dummy dataset and version
        ds = Dataset(name=dataset_name, inferred_dtypes={"id": "int64", "value": "float64", "category": "object"})
        session.add(ds)
        await session.flush()

        dv = DatasetVersion(dataset_id=ds.id, version_tag="v1_quality", file_path="dummy.csv", row_count=3)
        session.add(dv)
        await session.flush()

        # Act
        service = DataQualityService(session)
        should_halt, health_score = await service.validate_dataset(dataset_name, dv, df)

        # Assertions
        assert should_halt is False
        assert health_score == 100.0

        # Verify suite was persisted
        from app.data_quality.repositories import ExpectationSuiteRepository
        suite_repo = ExpectationSuiteRepository(session)

        from app.data_quality.repositories import DataContractRepository, ValidationRunRepository
        contract_repo = DataContractRepository(session)
        contract = await contract_repo.get_by_dataset(dataset_name)
        assert contract is not None

        suite = await suite_repo.get_latest_for_contract(contract.id)
        assert suite is not None
        assert len(suite.expectation_configs) > 0

        # Verify ValidationRun
        run_repo = ValidationRunRepository(session)
        run = await run_repo.get_latest_for_dataset(dv.id)
        assert run is not None
        assert run.success is True
        assert run.quality_score == 100.0
        assert run.critical_count == 0


@pytest.mark.asyncio
async def test_data_quality_critical_failure():
    # Setup dataframe with missing primary keys and type mismatches
    dataset_name = f"test_failing_dataset_{uuid.uuid4().hex[:8]}"
    df = pd.DataFrame({
        "id": [None, 2, 3],  # Null primary key!
        "value": ["not_a_float", 20.2, 30.0],  # Wrong type!
        "category": ["A", "B", "A"]
    })

    async with AsyncSessionLocal() as session:
        ds = Dataset(name=dataset_name)
        session.add(ds)
        await session.flush()

        dv = DatasetVersion(dataset_id=ds.id, version_tag="v1_fail", file_path="fail.csv")
        session.add(dv)
        await session.flush()

        service = DataQualityService(session)

        # Force a specific data contract that expects 'id' to be not null
        from app.data_quality.repositories import DataContractRepository
        repo = DataContractRepository(session)
        await repo.create(
            dataset_name=dataset_name,
            schema_def={"id": "int64", "value": "float64", "category": "object"},
            primary_keys=["id"]
        )
        await session.flush()

        # Act
        should_halt, health_score = await service.validate_dataset(dataset_name, dv, df)

        # Assert
        assert should_halt is True  # CRITICAL failure due to null primary key
        assert health_score < 100.0
        await session.rollback()
