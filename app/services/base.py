from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

ModelType = TypeVar("ModelType", bound=SQLModel)

class BaseService(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.session = session
        self.model = model

    async def _get(self, id: UUID) -> ModelType | None:
        return await self.session.get(self.model, id)  

    async def _add(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def _update(self, entity: ModelType) -> ModelType:
        return await self._add(entity)

    async def _delete(self, entity: ModelType) -> None:
        await self.session.delete(entity)
        await self.session.commit()