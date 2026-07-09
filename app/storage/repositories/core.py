from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.storage.repositories.base import BaseRepository
from app.storage.models import (
    Dataset, DatasetVersion, Feature, FeatureValue, Model, 
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

    async def get_by_name_and_version(self, name: str, version: int = None) -> Optional[Dataset]:
        query = select(Dataset).filter(Dataset.name == name, Dataset.status != 'ARCHIVED')
        if version is not None:
            query = query.filter(Dataset.version == version)
        result = await self.session.execute(query)
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

class FeatureValueRepository(BaseRepository[FeatureValue]):
    def __init__(self, session: AsyncSession):
        super().__init__(FeatureValue, session)

    async def get_by_entity(self, entity_id: str, dataset_id: Optional[str] = None) -> List[FeatureValue]:
        from sqlalchemy.orm import selectinload
        query = select(FeatureValue).options(selectinload(FeatureValue.feature)).filter(
            FeatureValue.entity_id == entity_id,
            FeatureValue.status != 'ARCHIVED'
        )
        if dataset_id:
            query = query.join(FeatureValue.feature).filter(Feature.dataset_id == dataset_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_dataset(self, dataset_id: str) -> List[FeatureValue]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(FeatureValue)
            .options(selectinload(FeatureValue.feature))
            .join(FeatureValue.feature)
            .filter(Feature.dataset_id == dataset_id, FeatureValue.status != 'ARCHIVED')
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

    async def get_by_dataset(self, dataset_id: str) -> List[Model]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Model)
            .options(selectinload(Model.dataset))
            .filter(Model.dataset_id == dataset_id, Model.status != 'ARCHIVED')
        )
        return result.scalars().all()

    async def create(self, obj_in: Dict[str, Any]) -> Model:
        db_obj = await super().create(obj_in)
        try:
            from app.cache.model_cache import get_model_registry_cache
            cache = await get_model_registry_cache()
            await cache.refresh_model_cache(db_obj.id)
        except Exception:
            pass
        return db_obj

    async def update(self, db_obj: Model, obj_in: Dict[str, Any]) -> Model:
        res = await super().update(db_obj, obj_in)
        try:
            from app.cache.model_cache import get_model_registry_cache
            cache = await get_model_registry_cache()
            if res.status == 'ARCHIVED':
                await cache.delete_model_cache(res.id, dataset=res.dataset_id)
            else:
                await cache.refresh_model_cache(res.id)
        except Exception:
            pass
        return res

    async def delete(self, id: Any) -> None:
        target_id = id.id if hasattr(id, 'id') else id
        ds_id = id.dataset_id if hasattr(id, 'dataset_id') else None
        await super().delete(id)
        try:
            from app.cache.model_cache import get_model_registry_cache
            cache = await get_model_registry_cache()
            await cache.delete_model_cache(target_id, dataset=ds_id)
        except Exception:
            pass

    async def hard_delete(self, id: Any) -> None:
        target_id = id.id if hasattr(id, 'id') else id
        ds_id = id.dataset_id if hasattr(id, 'dataset_id') else None
        try:
            from app.cache.model_cache import get_model_registry_cache
            cache = await get_model_registry_cache()
            await cache.delete_model_cache(target_id, dataset=ds_id)
        except Exception:
            pass
        await super().hard_delete(id)


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

    async def create(self, obj_in: Dict[str, Any]) -> ChampionModel:
        db_obj = await super().create(obj_in)
        try:
            from app.cache.model_cache import get_model_registry_cache
            cache = await get_model_registry_cache()
            if db_obj.dataset_id:
                await cache.refresh_champion_cache(db_obj.dataset_id)
        except Exception:
            pass
        return db_obj

    async def update(self, db_obj: ChampionModel, obj_in: Dict[str, Any]) -> ChampionModel:
        res = await super().update(db_obj, obj_in)
        try:
            from app.cache.model_cache import get_model_registry_cache
            cache = await get_model_registry_cache()
            if res.dataset_id:
                await cache.refresh_champion_cache(res.dataset_id)
        except Exception:
            pass
        return res

    async def delete(self, id: Any) -> None:
        target_obj = id if hasattr(id, 'dataset_id') else await self.get(id)
        ds_id = target_obj.dataset_id if target_obj else None
        await super().delete(id)
        if ds_id:
            try:
                from app.cache.model_cache import get_model_registry_cache
                cache = await get_model_registry_cache()
                await cache.delete_model_cache("", dataset=ds_id)
            except Exception:
                pass


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

    async def get_by_dataset(self, dataset_id: str) -> List[Experiment]:
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Experiment)
            .options(selectinload(Experiment.dataset))
            .filter(Experiment.dataset_id == dataset_id, Experiment.status != 'ARCHIVED')
        )
        return result.scalars().all()

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
