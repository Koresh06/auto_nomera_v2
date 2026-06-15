import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup


logger = logging.getLogger(__name__)


class AiogramNotificationService:
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
                    admin_id, e,
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
                    user_id, e,
                )