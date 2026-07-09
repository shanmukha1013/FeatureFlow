from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from app.storage.database import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: str) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).filter(self.model.id == id, self.model.status != 'ARCHIVED')
        )
        return result.scalars().first()
        
    async def get_including_archived(self, id: str) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).filter(self.model.id == id)
        )
        return result.scalars().first()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await self.session.execute(
            select(self.model).filter(self.model.status != 'ARCHIVED').offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_all(self) -> List[ModelType]:
        return await self.get_multi(skip=0, limit=100000)

    async def get_active(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return await self.get_multi(skip, limit)
        
    async def get_archived(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await self.session.execute(
            select(self.model).filter(self.model.status == 'ARCHIVED').offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(self.model.id)).filter(self.model.status != 'ARCHIVED')
        )
        return result.scalar() or 0

    async def count_all(self) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(self.model.id))
        )
        return result.scalar() or 0

    async def exists(self, id: str) -> bool:
        obj = await self.get(id)
        return obj is not None

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: Any) -> None:
        """Soft delete the record by setting status to ARCHIVED."""
        target_id = id.id if hasattr(id, 'id') else id
        await self.session.execute(
            update(self.model).where(self.model.id == target_id).values(status='ARCHIVED')
        )
        await self.session.flush()
        
    async def restore(self, id: Any) -> None:
        """Restore an archived record back to ACTIVE status."""
        target_id = id.id if hasattr(id, 'id') else id
        await self.session.execute(
            update(self.model).where(self.model.id == target_id).values(status='ACTIVE')
        )
        await self.session.flush()
        
    async def hard_delete(self, id: Any) -> None:
        """Permanently remove a record from the database. Use with extreme caution."""
        target_id = id.id if hasattr(id, 'id') else id
        await self.session.execute(delete(self.model).where(self.model.id == target_id))
        await self.session.flush()

