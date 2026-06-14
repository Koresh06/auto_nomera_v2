from typing import Protocol

from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.application.services.publication.context import ServiceContext


class PublicationServiceStrategy(Protocol):
    async def apply(
        self,
        publication: Publication,
        service: PublicationService,
        context: ServiceContext,
    ) -> None: ...