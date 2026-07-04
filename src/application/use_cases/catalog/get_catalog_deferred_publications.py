import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from src.application.dtos.ad import AdDTO
from src.application.dtos.publication import PublicationDTO
from src.domain.services.region.region_guard import RegionGuard
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.core.config import AppSettings
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class GetCatalogDeferredPublicationsRequest(UseCaseRequest):
    region_id: int


@dataclass(frozen=True)
class CatalogItem:
    ad: AdDTO
    publication: PublicationDTO | None
    is_urgent: bool


@dataclass(kw_only=True)
class GetCatalogDeferredPublicationsUseCase(
    UseCase[GetCatalogDeferredPublicationsRequest, list[CatalogItem]]
):
    region_guard: RegionGuard
    ad_repo: AdRepository
    publication_repo: PublicationRepository
    settings: AppSettings

    async def __call__(
        self, command: GetCatalogDeferredPublicationsRequest
    ) -> list[CatalogItem]:
        await self.region_guard.ensure_active(command.region_id)
        logger.info("[GetCatalog] region_id=%s", command.region_id)

        now_utc = datetime.now(timezone.utc)
        before_utc = now_utc + timedelta(
            hours=self.settings.app.pre_publication_window_hours
        )

        urgent_ads: list[Ad] = await self.ad_repo.list_urgent_published(
            region_id=command.region_id
        )

        pre_publications: list[Publication] = (
            await self.publication_repo.list_pre_publication(
                region_id=command.region_id,
                now_utc=now_utc,
                before_utc=before_utc,
            )
        )
        print(pre_publications)

        pre_pub_items: list[CatalogItem] = []
        for pub in pre_publications:
            ad = await self.ad_repo.get_by_id(pub.ad_id)
            if ad is None:
                continue
            pre_pub_items.append(
                CatalogItem(
                    ad=AdDTO.from_entity(ad),
                    publication=PublicationDTO.from_entity(pub),
                    is_urgent=False,
                )
            )

        urgent_items = [
            CatalogItem(
                ad=AdDTO.from_entity(ad),
                publication=None,
                is_urgent=True,
            )
            for ad in urgent_ads
        ]

        all_items = urgent_items + pre_pub_items
        all_items.sort(key=lambda x: x.ad.created_at, reverse=True)

        logger.info(
            "[GetCatalog:done] region_id=%s urgent=%s pre_pub=%s urgent_plates=%s pre_plates=%s",
            command.region_id,
            len(urgent_items),
            len(pre_pub_items),
            [ad.content.plate_number for ad in urgent_ads if ad.content],
            [p.publish_at_utc for p in pre_publications],
        )
        return all_items
