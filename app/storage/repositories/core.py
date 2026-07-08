from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.storage.repositories.base import BaseRepository
from app.storage.models import (
    Dataset, DatasetVersion, Feature, Model, ModelVersion, 
    ChampionModel, Experiment, PipelineRun, AuditLog
)

class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self, session: AsyncSession):
        super().__init__(Dataset, session)

    async def get_by_name(self, name: str) -> Optional[Dataset]:
        result = await self.session.execute(select(Dataset).filter(Dataset.name == name))
        return result.scalars().first()

class DatasetVersionRepository(BaseRepository[DatasetVersion]):
    def __init__(self, session: AsyncSession):
        super().__init__(DatasetVersion, session)

    async def get_by_dataset_and_tag(self, dataset_id: str, tag: str) -> Optional[DatasetVersion]:
        result = await self.session.execute(
            select(DatasetVersion).filter(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.version_tag == tag
            )
        )
        return result.scalars().first()

class FeatureRepository(BaseRepository[Feature]):
    def __init__(self, session: AsyncSession):
        super().__init__(Feature, session)

    async def get_by_dataset(self, dataset_id: str) -> List[Feature]:
        result = await self.session.execute(select(Feature).filter(Feature.dataset_id == dataset_id))
        return result.scalars().all()

class ModelRepository(BaseRepository[Model]):
    def __init__(self, session: AsyncSession):
        super().__init__(Model, session)

    async def get_by_dataset_and_name(self, dataset_id: str, name: str) -> Optional[Model]:
        result = await self.session.execute(
            select(Model).filter(Model.dataset_id == dataset_id, Model.name == name)
        )
        return result.scalars().first()

class ChampionModelRepository(BaseRepository[ChampionModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(ChampionModel, session)

    async def get_by_dataset(self, dataset_id: str) -> Optional[ChampionModel]:
        result = await self.session.execute(select(ChampionModel).filter(ChampionModel.dataset_id == dataset_id))
        return result.scalars().first()

class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Experiment, session)

    async def get_by_name(self, name: str) -> Optional[Experiment]:
        result = await self.session.execute(select(Experiment).filter(Experiment.name == name))
        return result.scalars().first()

class PipelineRunRepository(BaseRepository[PipelineRun]):
    def __init__(self, session: AsyncSession):
        super().__init__(PipelineRun, session)

class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def get_recent(self, limit: int = 50) -> List[AuditLog]:
        result = await self.session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
        return result.scalars().all()
