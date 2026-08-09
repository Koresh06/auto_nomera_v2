import logging

from aiogram.exceptions import TelegramForbiddenError
from redis.asyncio import Redis

from src.application.mediator import Mediator
from src.application.services.notification.notification_service import (
    NotificationService,
)
from src.application.use_cases.miling.execute import ExecuteMailingRequest
from src.application.use_cases.notification.notify_pre_publication_users import (
    NotifyPrePublicationUsersRequest,
)
from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
from src.application.use_cases.payment.mark import MarkPaymentFailedRequest
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
)

from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageRequest,
)
from src.domain.enums.miling import MailingType

logger = logging.getLogger(__name__)


def register_taskiq_tasks(broker, *, container):

    @broker.task(name="publish_publication")
    async def publish_publication(publication_id: int) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(
                PublishPublicationRequest(publication_id=publication_id)
            )

    @broker.task(name="unpin_message")
    async def unpin_message(channel_id: int, message_id: int) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(
                UnpinMessageRequest(channel_id=channel_id, message_id=message_id)
            )

    @broker.task(name="notify_pre_publication_users")
    async def notify_pre_publication_users(ad_id: int) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(NotifyPrePublicationUsersRequest(ad_id=ad_id))

    @broker.task(name="confirm_payment")
    async def confirm_payment(external_id: str) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(ConfirmPaymentRequest(external_id=external_id))

    @broker.task(name="mark_payment_failed")
    async def mark_payment_failed(external_id: str) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(MarkPaymentFailedRequest(external_id=external_id))

    @broker.task(name="execute_mailing")
    async def execute_mailing(
        mail_type: str,
        from_chat_id: int,
        message_id: int,
        region_id: int | None = None,
    ) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(
                ExecuteMailingRequest(
                    mail_type=MailingType(mail_type),
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    region_id=region_id,
                )
            )

    @broker.task(name="execute_mailing_batch")
    async def execute_mailing_batch(
        chat_ids: list[int],
        from_chat_id: int,
        message_id: int,
        batch_num: int,
        total_batches: int,
        mail_type_label: str,
        mailing_id: str,
    ) -> None:
        async with container() as request_container:
            notifications = await request_container.get(NotificationService)
            redis = await request_container.get(Redis)
            result = await notifications.broadcast_copy(
                chat_ids=chat_ids,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            logger.info(
                f"[MailingBatch {batch_num}/{total_batches}] mailing_id={mailing_id} "
                f"success={result['success']} blocked={result['blocked']} "
                f"failed={result['failed']}"
            )

            key = f"mailing_result:{mailing_id}"

            await redis.hincrby(key, "success", result["success"])
            await redis.hincrby(key, "blocked", result["blocked"])
            await redis.hincrby(key, "failed", result["failed"])
            done = await redis.hincrby(key, "done_batches", 1)
            await redis.expire(key, 3600)

            if done >= total_batches:
                raw = await redis.hgetall(key)

                def _get(field: str) -> int:
                    val = raw.get(field)
                    if val is None:
                        val = raw.get(field.encode())
                    if val is None:
                        return 0
                    return int(val)

                success = _get("success")
                blocked = _get("blocked")
                failed = _get("failed")
                total = success + blocked + failed

                await notifications.notify_admins(
                    text=(
                        f"✅ Рассылка <b>{mail_type_label}</b> завершена\n\n"
                        f"📬 Доставлено: <b>{success}</b>\n"
                        f"🚫 Заблокировали бота: <b>{blocked}</b>\n"
                        f"❌ Другие ошибки: <b>{failed}</b>\n"
                        f"👥 Всего: <b>{total}</b>"
                    ),
                )
                await redis.delete(key)

    @broker.task(name="send_ad_draft_reminder")
    async def send_ad_draft_reminder(tg_id: int) -> None:
        async with container() as request_container:
            notifications = await request_container.get(NotificationService)
            try:
                await notifications.notify_user(
                    tg_id=tg_id,
                    text=(
                        "⚠️ Напоминаем: вы начали добавлять объявление, но не опубликовали его.\n"
                        "Если хотите продолжить — отправьте команду /start 🙂"
                    ),
                )
            except TelegramForbiddenError:
                logger.info(
                    "[send_ad_draft_reminder] user blocked the bot, tg_id=%s", tg_id
                )
            except Exception:
                logger.exception("[send_ad_draft_reminder] failed for tg_id=%s", tg_id)

    return {
        "publish_publication": publish_publication,
        "unpin_message": unpin_message,
        "notify_pre_publication_users": notify_pre_publication_users,
        "confirm_payment": confirm_payment,
        "mark_payment_failed": mark_payment_failed,
        "execute_mailing": execute_mailing,
        "send_ad_draft_reminder": send_ad_draft_reminder,
    }
