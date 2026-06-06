from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.entities.publication import Publication, PublicationStatus
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.exceptions.publication import PublicationNotFoundException
from src.infrastructure.database.models import PublicationModel


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
        model = PublicationModel.from_entity(publication)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
 
    async def list_scheduled_by_ad(self, ad_id: int) -> list[Publication]:
        query = select(PublicationModel).where(PublicationModel.ad_id == ad_id)
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [m.to_entity() for m in models]

