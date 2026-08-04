import logging
from dataclasses import dataclass

from src.application.exceptions.region import RegionNotFoundException
from src.application.ports.region.region_repo import RegionRepository
from src.core.config import AppSettings
from src.domain.entities.ad import Ad
from src.domain.entities.user import User
from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.presentation.telegram.keyboards.deferred_publication import (
    catalog_deferred_publication_kb,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class NotifyPrePublicationUsersRequest(UseCaseRequest):
    ad_id: int


@dataclass(kw_only=True)
class NotifyPrePublicationUsersUseCase(UseCase[NotifyPrePublicationUsersRequest, None]):
    ad_repo: AdRepository
    region_repo: RegionRepository
    user_repo: UserRepository
    notification_service: NotificationService
    settings: AppSettings

    async def __call__(self, command: NotifyPrePublicationUsersRequest) -> None:
        logger.info("[NotifyPrePublicationUsers] ad_id=%s", command.ad_id)

        ad: Ad | None = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        region = await self.region_repo.get_by_id(ad.region_id)
        if region is None:
            raise RegionNotFoundException(ad.region_id)

        users: list[User] = await self.user_repo.find_with_active_pre_publication(
            region_id=ad.region_id
        )
        if not users:
            logger.info(
                "[NotifyPrePublicationUsers:skip] no active users in region_id=%s",
                ad.region_id,
            )
            return

        renderer = AdTextRenderer(
            bot_url=self.settings.telegram.bot_url,
            buyout_url=self.settings.telegram.buyout_url,
        )
        ad_text = renderer.render(ad=ad, region=region)

        text = f"🚀 <b>Новое объявление доступно по раннему доступу!</b>\n\n{ad_text}"

        photo_id = None
        if ad.content and ad.content.image_file_id:
            photo_id = ad.content.image_file_id
        elif ad.store_content is None:
            photo_id = None

        await self.notification_service.notify_users(
            user_ids=[u.tg_id for u in users],
            text=text,
            photo_id=photo_id,
            reply_markup=await catalog_deferred_publication_kb(),
        )

        logger.info(
            "[NotifyPrePublicationUsers:done] region_id=%s ad_id=%s notified=%s",
            ad.region_id,
            command.ad_id,
            len(users),
        )
