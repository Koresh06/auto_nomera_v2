from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.publication import PublicationNotFoundException
from src.application.exceptions.region import RegionNotFoundException
from src.application.exceptions.user import UserNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.publication.publication_repo import PublicationRepository
from src.application.ports.publication.scheduler import Scheduler
from src.application.ports.publication_service.image_processor import ImageProcessor
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.telegram.telegram_publisher import TelegramPublisher
from src.application.ports.user.user_repo import UserRepository
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.ad import AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceStatus, PublicationServiceType
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.services.publication.publish_time_resolver import PublishTimeResolver
from src.application.services.publication.context import ServiceContext
from src.application.services.publication.registry import STRATEGIES
from src.infrastructure.database.transaction_manager.base import TransactionManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class PublishPublicationRequest(UseCaseRequest):
    publication_id: int
    now_utc: datetime | None = None


@dataclass(kw_only=True)
class PublishPublicationUseCase(UseCase[PublishPublicationRequest, None]):
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

    async def __call__(self, command: PublishPublicationRequest) -> None:
        now = command.now_utc or datetime.now(timezone.utc)

        pub = await self.publication_repo.get_by_id(command.publication_id)
        logger.info(f"[Publish] pub_id={command.publication_id} status={pub.status if pub else None}")
    
        if pub is None:
            logger.warning("[Publish] publication_id=%s not found, skipping", command.publication_id)
            return
    
        if pub.status in (
            PublicationStatus.PUBLISHED,
            PublicationStatus.CANCELED,
            PublicationStatus.REPLACED,
        ):
            logger.info(f"[Publish:skip] pub_id={pub.id} status={pub.status} — already done")
            return

        pub.mark_publishing()
        await self.publication_repo.save(pub)

        ad = await self.ad_repo.get_by_id(pub.ad_id)
        if ad is None:
            raise AdNotFoundException(pub.ad_id)

        region = await self.region_repo.get_by_id(pub.region_id)
        if region is None:
            raise RegionNotFoundException(pub.region_id)
        
        user = await self.user_repo.get_by_id(ad.user_id)
        if user is None:
            raise UserNotFoundException(ad.user_id)
        
        text = self.renderer.render(ad=ad, region=region)

        ctx = ServiceContext(
            region=region,
            ad=ad,
            scheduler=self.scheduler,
            telegram=self.telegram,
            publication_repo=self.publication_repo,
            time_resolver=self.time_resolver,
            image_processor=self.image_processor,
            tg_id=user.tg_id,
            caption=text,
        )

        # 1) HIGHLIGHT — до публикации
        highlight_svc = _get_active_service(pub, PublicationServiceType.HIGHLIGHT)
        if highlight_svc is not None and ad.ad_type != AdType.STORE:
            await STRATEGIES[PublicationServiceType.HIGHLIGHT].apply(pub, highlight_svc, ctx)
            await self.publication_repo.save(pub)

        # 2) публикация в канал
        if ad.ad_type == AdType.STORE:
            result = await self.telegram.publish_text(
                channel_id=region.channel_id,
                text=text,
            )
        else:
            image_file_id = ctx.highlight_file_id or (ad.content.image_file_id if ad.content else None)
            if not image_file_id:
                pub.mark_failed()
                await self.publication_repo.save(pub)
                await self.transaction_manager.commit()
                return

            result = await self.telegram.publish_photo(
                channel_id=region.channel_id,
                image_file_id=image_file_id,
                caption=text,
            )

        pub.mark_published(message_id=result.message_id, published_at_utc=now)
        await self.publication_repo.save(pub)

        # 3) PIN — после публикации
        pin_svc = _get_active_service(pub, PublicationServiceType.PIN)
        if pin_svc is not None:
            await STRATEGIES[PublicationServiceType.PIN].apply(pub, pin_svc, ctx)
            await self.publication_repo.save(pub)

        # 4) AUTOPUBLISH — создаём серию после первой публикации
        auto_svc = _get_active_service(pub, PublicationServiceType.AUTOPUBLISH)
        if auto_svc is not None:
            await STRATEGIES[PublicationServiceType.AUTOPUBLISH].apply(pub, auto_svc, ctx)
            await self.publication_repo.save(pub)

        await self.transaction_manager.commit()
        logger.info(f"[Publish:done] pub_id={pub.id} message_id={result.message_id}")


def _get_active_service(
    pub: Publication,
    service_type: PublicationServiceType,
) -> PublicationService | None:
    for s in pub.services:
        if s.type == service_type and s.status == PublicationServiceStatus.ACTIVE:
            return s
    return None
