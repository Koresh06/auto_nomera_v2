from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.application.dtos.ad import Ad
from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.domain.enums.ad import AdType
from src.infrastructure.database.models import AdModel



class SQLAlchemyAdRepo(AdRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
 
    async def get_by_id(self, ad_id: int) -> Ad | None:
        query = select(AdModel).where(AdModel.id == ad_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None
        
 
    async def create(self, ad: Ad) -> Ad:
        model = AdModel.from_entity(ad)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()
        
 
    async def save(self, ad: Ad) -> None:
        query = select(AdModel).where(AdModel.id == ad.id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            raise AdNotFoundException(ad.id)
        AdModel._update_model(model, ad)
        await self._session.flush()

    async def find_by_plate(
        self,
        user_id: int,
        region_id: int,
        plate_number: str,
    ) -> Ad | None:
        query = (
            select(AdModel)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                AdModel.plate_number == plate_number,
                AdModel.ad_type != AdType.STORE,
            )
            .order_by(AdModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None