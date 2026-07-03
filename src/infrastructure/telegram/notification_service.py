import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardMarkup

from src.application.services.notification.notification_service import (
    NotificationService,
)

logger = logging.getLogger(__name__)


class AiogramNotificationService(NotificationService):
    def __init__(self, bot: Bot, admin_ids: list[int]) -> None:
        self.bot = bot
        self.admin_ids = admin_ids

    async def notify_admins(
        self,
        *,
        text: str,
        photo_id: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        for admin_id in self.admin_ids:
            try:
                if photo_id:
                    await self.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_id,
                        caption=text,
                        reply_markup=reply_markup,
                    )
                else:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=text,
                        reply_markup=reply_markup,
                    )
            except TelegramBadRequest as e:
                logger.warning(
                    "[NotificationService] failed to notify admin_id=%s: %s",
                    admin_id,
                    e,
                )

    async def notify_users(
        self,
        *,
        user_ids: list[int],
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        for user_id in user_ids:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                )
            except TelegramBadRequest as e:
                logger.warning(
                    "[NotificationService] failed to notify user_id=%s: %s",
                    user_id,
                    e,
                )

    async def notify_user(
        self,
        *,
        tg_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        try:
            await self.bot.send_message(
                chat_id=tg_id,
                text=text,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest as e:
            logger.warning(
                "[NotificationService] failed to notify tg_id=%s: %s", tg_id, e
            )

    async def broadcast_copy(
        self,
        *,
        chat_ids: list[int],
        from_chat_id: int,
        message_id: int,
        throttle_seconds: float = 0.05,
    ) -> dict:
        success, fail = 0, 0

        for chat_id in chat_ids:
            try:
                await self.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
                success += 1
                await asyncio.sleep(throttle_seconds)
            except TelegramRetryAfter as e:
                logger.warning(f"Flood wait {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
                try:
                    await self.bot.copy_message(
                        chat_id=chat_id,
                        from_chat_id=from_chat_id,
                        message_id=message_id,
                    )
                    success += 1
                except Exception:
                    fail += 1
            except TelegramForbiddenError:
                fail += 1
            except Exception as e:
                logger.error(f"broadcast_copy to {chat_id} failed: {e}")
                fail += 1

        return {"success": success, "fail": fail}
