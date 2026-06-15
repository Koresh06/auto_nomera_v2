import logging
from typing import Any
from dataclasses import dataclass
from src.application.exceptions.ad import AdNotFoundException
from src.application.ports.ad.ad_repo import AdRepository
from src.application.services.notification.notification_service import NotificationService
from src.application.use_cases.base import UseCase, UseCaseRequest


logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class NotifyAdminsAboutUrgentRequest(UseCaseRequest):
    ad_id: int
    reply_markup: Any | None = None


@dataclass(kw_only=True)
class NotifyAdminsAboutUrgentUseCase(UseCase[NotifyAdminsAboutUrgentRequest, None]):
    ad_repo: AdRepository
    notification_service: NotificationService

    async def __call__(self, command: NotifyAdminsAboutUrgentRequest) -> None:
        logger.info("[NotifyAdminsAboutUrgent] ad_id=%s", command.ad_id)

        ad = await self.ad_repo.get_by_id(command.ad_id)
        if ad is None:
            raise AdNotFoundException(command.ad_id)

        c = ad.content
        text = (
            f"🚀 <b>СРОЧНЫЙ ВЫКУП</b>\n\n"
            f"🌎 <b>Город:</b> {c.city}\n"
            f"🚘 <b>Номер:</b> <code>{c.plate_number}</code>\n"
            f"💰 <b>Сумма:</b> {c.price.display}\n"
            f"📲 <b>Связь:</b> {c.contacts.display}\n"
        )

        await self.notification_service.notify_admins(
            text=text,
            photo_id=c.image_file_id,
            reply_markup=command.reply_markup,
        )

        logger.info("[NotifyAdminsAboutUrgent:done] ad_id=%s", command.ad_id)