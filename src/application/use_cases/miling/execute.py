import logging
from dataclasses import dataclass

from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.user.user_repo import UserRepository
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.miling import MailingType

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=False)
class ExecuteMailingRequest(UseCaseRequest):
    mail_type: MailingType
    from_chat_id: int
    message_id: int
    region_id: int | None = None


@dataclass(kw_only=True)
class ExecuteMailingUseCase(UseCase[ExecuteMailingRequest, None]):
    user_repo: UserRepository
    region_repo: RegionRepository
    notification_service: NotificationService

    async def __call__(self, command: ExecuteMailingRequest) -> None:
        try:
            if command.mail_type == MailingType.TO_ALL:
                users = await self.user_repo.get_all()
                chat_ids = [u.tg_id for u in users]
                result = await self.notification_service.broadcast_copy(
                    chat_ids=chat_ids,
                    from_chat_id=command.from_chat_id,
                    message_id=command.message_id,
                )

            elif command.mail_type == MailingType.TO_REGION:
                if command.region_id is None:
                    raise ValueError("region_id required")
                users = await self.user_repo.get_by_region(command.region_id)
                chat_ids = [u.tg_id for u in users if not u.is_blocked]
                result = await self.notification_service.broadcast_copy(
                    chat_ids=chat_ids,
                    from_chat_id=command.from_chat_id,
                    message_id=command.message_id,
                )

            elif command.mail_type == MailingType.TO_ALL_REGIONS:
                regions = await self.region_repo.get_all()
                chat_ids = [r.channel_id for r in regions if r.channel_id]
                result = await self.notification_service.broadcast_copy(
                    chat_ids=chat_ids,
                    from_chat_id=command.from_chat_id,
                    message_id=command.message_id,
                )
            else:
                logger.warning(f"Unhandled: {command.mail_type}")
                return

            logger.info(f"Mailing done: {result}")
            await self._notify_admin_result(command, result)

        except Exception as e:
            logger.exception(f"Mailing failed: {e}")
            await self._notify_admin_error(command, e)

    async def _notify_admin_result(
        self,
        command: ExecuteMailingRequest,
        result: dict,
    ) -> None:
        await self.notification_service.notify_admins(
            text=(
                f"✅ Рассылка <b>{command.mail_type.label()}</b> завершена\n"
                f"📬 Успешно: <b>{result['success']}</b>\n"
                f"❌ Ошибок: <b>{result['fail']}</b>"
            ),
        )

    async def _notify_admin_error(
        self,
        command: ExecuteMailingRequest,
        error: Exception,
    ) -> None:
        await self.notification_service.notify_admins(
            text=f"❌ Ошибка рассылки ({command.mail_type.label()}):\n<code>{error}</code>",
        )
