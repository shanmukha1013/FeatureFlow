from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.data_quality.models import DataContractModel, ExpectationSuiteModel, ValidationRun, ExpectationResult


class DataContractRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dataset(self, dataset_name: str) -> Optional[DataContractModel]:
        stmt = select(DataContractModel).filter_by(dataset_name=dataset_name, status="ACTIVE").order_by(desc(DataContractModel.version)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, dataset_name: str, schema_def: Dict[str, Any], business_rules: Optional[Dict[str, Any]] = None, primary_keys: Optional[List[str]] = None, owner: Optional[str] = None) -> DataContractModel:
        # Determine new version
        latest = await self.get_by_dataset(dataset_name)
        new_version = (latest.version + 1) if latest else 1

        contract = DataContractModel(
            dataset_name=dataset_name,
            version=new_version,
            owner=owner,
            schema_definition=schema_def,
            business_rules=business_rules or {},
            primary_keys=primary_keys or []
        )
        self.session.add(contract)
        return contract


class ExpectationSuiteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_for_contract(self, contract_id: str) -> Optional[ExpectationSuiteModel]:
        stmt = select(ExpectationSuiteModel).filter_by(contract_id=contract_id, status="ACTIVE").order_by(desc(ExpectationSuiteModel.suite_version)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, contract_id: str, name: str, expectation_configs: List[Dict[str, Any]], created_by: Optional[str] = None) -> ExpectationSuiteModel:
        latest = await self.get_latest_for_contract(contract_id)
        new_version = (latest.suite_version + 1) if latest else 1

        suite = ExpectationSuiteModel(
            contract_id=contract_id,
            name=name,
            suite_version=new_version,
            expectation_configs=expectation_configs,
            created_by=created_by
        )
        self.session.add(suite)
        return suite


class ValidationRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, suite_id: str, dataset_version_id: str, success: bool, quality_score: float,
                     execution_time_ms: float, counts: Dict[str, int], gx_version: str, dataset_checksum: Optional[str] = None) -> ValidationRun:
        run = ValidationRun(
            suite_id=suite_id,
            dataset_version_id=dataset_version_id,
            success=success,
            quality_score=quality_score,
            execution_time_ms=execution_time_ms,
            critical_count=counts.get('critical', 0),
            error_count=counts.get('error', 0),
            warning_count=counts.get('warning', 0),
            info_count=counts.get('info', 0),
            gx_version=gx_version,
            dataset_checksum=dataset_checksum
        )
        self.session.add(run)
        return run

    async def get_latest_for_dataset(self, dataset_version_id: str) -> Optional[ValidationRun]:
        stmt = select(ValidationRun).filter_by(dataset_version_id=dataset_version_id).order_by(desc(ValidationRun.created_at)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ExpectationResultRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bulk(self, results: List[ExpectationResult]) -> None:
        self.session.add_all(results)
