import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.ad import Ad
from src.domain.entities.publication import Publication

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class GetCatalogDeferredPublicationsRequest(UseCaseRequest):
    region_id: int
    pre_publication_window_hours: int = 2


@dataclass(frozen=True)
class CatalogItem:
    ad: Ad
    publication: Publication | None  # None для urgent_buyout
    is_urgent: bool


@dataclass(kw_only=True)
class GetCatalogDeferredPublicationsUseCase(UseCase[GetCatalogDeferredPublicationsRequest, list[CatalogItem]]):
    ad_repo: AdRepository
    publication_repo: PublicationRepository

    async def __call__(self, command: GetCatalogDeferredPublicationsRequest) -> list[CatalogItem]:
        logger.info("[GetCatalog] region_id=%s", command.region_id)

        now_utc = datetime.now(timezone.utc)
        before_utc = now_utc + timedelta(hours=command.pre_publication_window_hours)

        # Срочные выкупы — подтверждённые админом
        urgent_ads: list[Ad] = await self.ad_repo.list_urgent_published(
            region_id=command.region_id
        )
        
        # Запланированные публикации в окне 2 часа
        pre_publications: list[Publication] = await self.publication_repo.list_pre_publication(
            region_id=command.region_id,
            before_utc=before_utc,
        )

        # Подгружаем Ad для каждой публикации
        pre_pub_items: list[CatalogItem] = []
        for pub in pre_publications:
            ad = await self.ad_repo.get_by_id(pub.ad_id)
            if ad is None:
                continue
            pre_pub_items.append(
                CatalogItem(
                    ad=ad,
                    publication=pub,
                    is_urgent=False,
                )
            )

        urgent_items = [
            CatalogItem(ad=ad, publication=None, is_urgent=True) for ad in urgent_ads
        ]

        # Мержим: новые в начале — сортируем по created_at desc
        all_items = urgent_items + pre_pub_items
        all_items.sort(key=lambda x: x.ad.created_at, reverse=True)

        logger.info(
            "[GetCatalog:done] region_id=%s urgent=%s pre_pub=%s",
            command.region_id,
            len(urgent_items),
            len(pre_pub_items),
        )
        return all_items
