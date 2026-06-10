from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from src.domain.entities.publication import Publication
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.exceptions.publication import PublicationNotFoundException
from src.domain.enums.ad import AdType
from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.models import PublicationModel
from src.infrastructure.database.models.ad import AdModel


class SQLAlchemyPublicationRepo(PublicationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
 
    async def get_by_id(self, publication_id: int) -> Publication | None:
        query = select(PublicationModel).where(PublicationModel.id == publication_id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None
 
    async def create(self, publication: Publication) -> Publication:
        model = PublicationModel.from_entity(publication)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()
 
    async def save(self, publication: Publication) -> None:
        query = select(PublicationModel).where(PublicationModel.id == publication.id)
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            raise PublicationNotFoundException(publication.id)
        PublicationModel._update_model(model, publication)
        await self._session.flush()
 
    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]:
        query = select(PublicationModel).where(PublicationModel.ad_id == ad_id)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [m.to_entity() for m in models]
    
    async def list_by_user(
        self,
        user_id: int,
        region_id: int,
    ) -> list[tuple[Publication, str | None]]:
        query = (
            select(PublicationModel, AdModel.plate_number)
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                PublicationModel.status.notin_([
                    PublicationStatus.CANCELED,
                    PublicationStatus.REPLACED,
                ])
            )
            .order_by(PublicationModel.created_at.desc())
        )
        result = await self._session.execute(query)
        return [
            (pub_model.to_entity(), plate)
            for pub_model, plate in result.all()
        ]

    async def count_scheduled_by_user(
        self,
        user_id: int,
        region_id: int,
        ad_type: AdType,
        from_utc: datetime,
    ) -> int:
        query = (
            select(func.count(PublicationModel.id))
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                AdModel.ad_type == ad_type,
                PublicationModel.status.in_([
                    PublicationStatus.SCHEDULED,
                    PublicationStatus.PUBLISHED,
                    PublicationStatus.PUBLISHING,
                ]),
                PublicationModel.publish_at_utc >= from_utc,
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one() or 0
    
    async def find_last_by_plate(
        self,
        user_id: int,
        region_id: int,
        plate: str,
        from_utc: datetime,
    ) -> Publication | None:
        query = (
            select(PublicationModel)
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .where(
                AdModel.user_id == user_id,
                AdModel.region_id == region_id,
                AdModel.plate_number == plate,
                PublicationModel.status.in_([
                    PublicationStatus.SCHEDULED,
                    PublicationStatus.PUBLISHED,
                    PublicationStatus.PUBLISHING,
                ]),
                PublicationModel.publish_at_utc >= from_utc,
            )
            .order_by(PublicationModel.publish_at_utc.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None