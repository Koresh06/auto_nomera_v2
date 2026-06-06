from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.region import Region
from src.application.ports.region.region_repo import RegionRepository
from src.infrastructure.database.models import RegionModel


class SQLAlchemyRegionRepository(RegionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, region_id: int) -> Region | None:
        query = select(RegionModel).where(RegionModel.id == region_id)
        result = await self._session.execute(query)
        region_model = result.scalar_one_or_none()
        return region_model.to_entity() if region_model else None
    
    async def get_all(self) -> list[Region]:
        query = select(RegionModel)
        result = await self._session.execute(query)
        return [region_model.to_entity() for region_model in result.scalars().all()]
    
    async def create(self, region: Region) -> Region:
        region_model = RegionModel.from_entity(region)
        self._session.add(region_model)
        await self._session.flush()
        await self._session.refresh(region_model)
        return region_model.to_entity()
