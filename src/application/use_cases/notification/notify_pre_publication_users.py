import logging
from dataclasses import dataclass

from src.domain.entities.ad import Ad
from src.domain.entities.user import User
from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
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
    user_repo: UserRepository
    notification_service: NotificationService

    async def __call__(self, command: NotifyPrePublicationUsersRequest) -> None:
        logger.info("[NotifyPrePublicationUsers] ad_id=%s", command.ad_id)

        ad: Ad | None = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        users: list[User] = await self.user_repo.find_with_active_pre_publication(
            region_id=ad.region_id
        )
        if not users:
            logger.info(
                "[NotifyPrePublicationUsers:skip] no active users in region_id=%s",
                ad.region_id,
            )
            return

        c = ad.content
        text = (
            f"🚀 <b>Новое объявление доступно по раннему доступу!</b>\n\n"
            f"🚘 <b>Номер:</b> <code>{c.plate_number}</code>"
        )
        await self.notification_service.notify_users(
            user_ids=[u.tg_id for u in users],
            text=text,
            reply_markup=await catalog_deferred_publication_kb(),
        )

        logger.info(
            "[NotifyPrePublicationUsers:done] region_id=%s ad_id=%s notified=%s",
            ad.region_id,
            command.ad_id,
            len(users),
        )
