from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select

from src.application.dtos.ad import Ad
from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.domain.enums.ad import AdStatus, AdType
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

    async def find_store_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> Ad | None:
        query = (
            select(AdModel)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                AdModel.ad_type == AdType.STORE,
            )
            .order_by(AdModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def list_urgent_published(self, region_id: int) -> list[Ad]:
        query = (
            select(AdModel)
            .where(
                AdModel.region_id == region_id,
                AdModel.ad_type == AdType.URGENT_BUYOUT,
                AdModel.status == AdStatus.PUBLISHED,
            )
            .order_by(AdModel.created_at.desc())
        )
        result = await self._session.execute(query)
        return [m.to_entity() for m in result.scalars().all()]

    async def count_ads_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> int:
        query = select(func.count(AdModel.id)).where(
            AdModel.user_id == user_id,
            AdModel.region_id == region_id,
        )
        result = await self._session.execute(query)
        return result.scalar_one()

    async def count_ads(self, since_utc=None, region_id=None) -> int:
        q = select(func.count(AdModel.id))
        conds = []
        if since_utc is not None:
            conds.append(AdModel.created_at >= since_utc)
        if region_id is not None:
            conds.append(AdModel.region_id == region_id)
        if conds:
            q = q.where(and_(*conds))
        return (await self._session.execute(q)).scalar() or 0

    async def count_by_type(self, since_utc=None, region_id=None):
        conds = []
        if since_utc is not None:
            conds.append(AdModel.created_at >= since_utc)
        if region_id is not None:
            conds.append(AdModel.region_id == region_id)
        q = select(AdModel.ad_type, func.count().label("cnt"))
        if conds:
            q = q.where(and_(*conds))
        q = q.group_by(AdModel.ad_type)
        rows = (await self._session.execute(q)).all()
        return [(r.ad_type, r.cnt) for r in rows]
