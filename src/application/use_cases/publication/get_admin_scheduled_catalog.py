from dataclasses import dataclass
from datetime import datetime

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.use_cases.catalog.get_catalog_deferred_publications import (
    CatalogItem,
)


@dataclass(frozen=True, eq=False)
class GetAdminScheduledCatalogRequest(UseCaseRequest):
    region_id: int


@dataclass(kw_only=True)
class GetAdminScheduledCatalogUseCase(
    UseCase[GetAdminScheduledCatalogRequest, list[CatalogItem]]
):
    publication_repo: PublicationRepository
    ad_repo: AdRepository

    async def __call__(self, command) -> list[CatalogItem]:
        rows = await self.publication_repo.list_scheduled_for_catalog(command.region_id)
        return [
            CatalogItem(
                ad=AdDTO.from_entity(ad),
                publication=PublicationDTO.from_entity(pub),
                is_urgent=False,
            )
            for pub, ad, _tg in rows
        ]