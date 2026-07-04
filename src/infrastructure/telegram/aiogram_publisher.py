from aiogram import Bot
from aiogram.types import InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest

from src.application.ports.telegram.telegram_publisher import (
    TelegramPublisher,
    PublishResult,
)


class AiogramTelegramPublisher(TelegramPublisher):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def publish_photo(
        self,
        *,
        channel_id: int,
        image_file_id: str,
        caption: str,
    ) -> PublishResult:
        msg = await self.bot.send_photo(
            chat_id=channel_id,
            photo=image_file_id,
            caption=caption,
        )
        return PublishResult(channel_id=channel_id, message_id=msg.message_id)

    async def publish_text(
        self,
        *,
        channel_id: int,
        text: str,
    ) -> PublishResult:
        msg = await self.bot.send_message(
            chat_id=channel_id,
            text=text,
            disable_web_page_preview=True,
        )
        return PublishResult(
            channel_id=channel_id,
            message_id=msg.message_id,
        )

    async def edit_caption(
        self,
        *,
        channel_id: int,
        message_id: int,
        caption: str,
    ) -> None:
        try:
            await self.bot.edit_message_caption(
                chat_id=channel_id,
                message_id=message_id,
                caption=caption,
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
            raise

    async def pin_message(
        self,
        *,
        channel_id: int,
        message_id: int,
    ) -> None:
        try:
            await self.bot.pin_chat_message(
                chat_id=channel_id,
                message_id=message_id,
            )
        except TelegramBadRequest as e:
            if "message to pin not found" in str(e):
                return
            raise

    async def unpin_message(
        self,
        *,
        channel_id: int,
        message_id: int,
    ) -> None:
        try:
            await self.bot.unpin_chat_message(
                chat_id=channel_id,
                message_id=message_id,
            )
        except TelegramBadRequest as e:
            if "message to unpin not found" in str(e):
                return
            raise

    async def edit_media(
        self,
        *,
        channel_id: int,
        message_id: int,
        file_id: str,
        caption: str,
    ) -> None:
        try:
            await self.bot.edit_message_media(
                chat_id=channel_id,
                message_id=message_id,
                media=InputMediaPhoto(
                    media=file_id,
                    caption=caption,
                ),
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(
                e
            ) or "message to edit not found" in str(e):
                return
            raise
