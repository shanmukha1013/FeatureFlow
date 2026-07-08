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
        result = await self.session.execute(
            select(Dataset)
            .filter(Dataset.name == name, Dataset.status != 'ARCHIVED')
        )
        return result.scalars().first()

class DatasetVersionRepository(BaseRepository[DatasetVersion]):
    def __init__(self, session: AsyncSession):
        super().__init__(DatasetVersion, session)

    async def get_by_dataset_and_tag(self, dataset_id: str, tag: str) -> Optional[DatasetVersion]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(DatasetVersion)
            .options(selectinload(DatasetVersion.dataset))
            .filter(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.version_tag == tag,
                DatasetVersion.status != 'ARCHIVED'
            )
        )
        return result.scalars().first()

class FeatureRepository(BaseRepository[Feature]):
    def __init__(self, session: AsyncSession):
        super().__init__(Feature, session)

    async def get_by_dataset(self, dataset_id: str) -> List[Feature]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Feature)
            .options(selectinload(Feature.dataset))
            .filter(Feature.dataset_id == dataset_id, Feature.status != 'ARCHIVED')
        )
        return result.scalars().all()

class ModelRepository(BaseRepository[Model]):
    def __init__(self, session: AsyncSession):
        super().__init__(Model, session)

    async def get_by_dataset_and_name(self, dataset_id: str, name: str) -> Optional[Model]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Model)
            .options(selectinload(Model.dataset))
            .filter(
                Model.dataset_id == dataset_id, 
                Model.name == name,
                Model.status != 'ARCHIVED'
            )
        )
        return result.scalars().first()

class ChampionModelRepository(BaseRepository[ChampionModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(ChampionModel, session)

    async def get_by_dataset(self, dataset_id: str) -> Optional[ChampionModel]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(ChampionModel)
            .options(selectinload(ChampionModel.model))
            .filter(
                ChampionModel.dataset_id == dataset_id,
                ChampionModel.status != 'ARCHIVED'
            )
        )
        return result.scalars().first()

class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Experiment, session)

    async def get_by_name(self, name: str) -> Optional[Experiment]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Experiment)
            .options(selectinload(Experiment.dataset))
            .filter(Experiment.name == name, Experiment.status != 'ARCHIVED')
        )
        return result.scalars().first()

class PipelineRunRepository(BaseRepository[PipelineRun]):
    def __init__(self, session: AsyncSession):
        super().__init__(PipelineRun, session)

class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def get_recent(self, limit: int = 50) -> List[AuditLog]:
        result = await self.session.execute(
            select(AuditLog)
            .filter(AuditLog.status != 'ARCHIVED')
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
