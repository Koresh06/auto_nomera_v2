import logging
from dataclasses import dataclass

from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.publication import PublicationNotFoundException
from src.application.exceptions.region import RegionNotFoundException
from src.application.exceptions.service_definition import ServiceNotAvailableException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceStatus, PublicationServiceType
from src.domain.exceptions.publication import InvalidPublicationState
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.domain.services.publication_service.context import ServiceContext
from src.domain.services.publication_service.registry import STRATEGIES
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ApplyServiceToPublishedRequest(UseCaseRequest):
    publication_id: int
    service_type: PublicationServiceType


@dataclass(kw_only=True)
class ApplyServiceToPublishedUseCase(UseCase[ApplyServiceToPublishedRequest, None]):
    publication_repo: PublicationRepository
    ad_repo: AdRepository
    region_repo: RegionRepository
    user_repo: UserRepository
    telegram: TelegramPublisher
    image_processor: ImageProcessor
    renderer: AdTextRenderer
    scheduler: Scheduler
    time_resolver: PublishTimeResolver
    transaction_manager: TransactionManager

    async def __call__(self, command: ApplyServiceToPublishedRequest) -> None:
        publication = await self.publication_repo.get_by_id(command.publication_id)
        if publication is None:
            raise PublicationNotFoundException(command.publication_id)

        if publication.status != PublicationStatus.PUBLISHED:
            raise InvalidPublicationState(
                f"Publication must be PUBLISHED to apply service, got {publication.status}"
            )

        ad = await self.ad_repo.get_by_id(publication.ad_id)
        if ad is None:
            raise AdNotFoundException(publication.ad_id)

        region = await self.region_repo.get_by_id(publication.region_id)
        if region is None:
            raise RegionNotFoundException(publication.region_id)
        
        user = await self.user_repo.get_by_id(ad.user_id)
        if user is None:
            raise AdNotFoundException(ad.user_id)

        # находим нужную услугу
        service = next(
            (
                s for s in publication.services
                if s.type == command.service_type
                and s.status == PublicationServiceStatus.ACTIVE
            ),
            None,
        )
        if service is None:
            raise ServiceNotAvailableException()
        
        text = self.renderer.render(ad=ad, region=region)

        context = ServiceContext(
            region=region,
            ad=ad,
            scheduler=self.scheduler,
            telegram=self.telegram,
            image_processor=self.image_processor,
            publication_repo=self.publication_repo,
            time_resolver=self.time_resolver,
            tg_id=user.tg_id,
            caption=text,
        )

        strategy = STRATEGIES.get(command.service_type)
        if strategy is None:
            raise ServiceNotAvailableException()

        await strategy.apply(publication, service, context)

        await self.publication_repo.save(publication)
        await self.transaction_manager.commit()

        logger.info(
            f"[ApplyServiceToPublished:done] pub_id={publication.id} "
            f"service_type={command.service_type}"
        )