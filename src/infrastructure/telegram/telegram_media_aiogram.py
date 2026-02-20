from aiogram import Bot
from aiogram.types import BufferedInputFile

from src.application.ports.telegram.telegram_media import TelegramMedia


class TelegramMediaAiogram(TelegramMedia):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def ensure_photo_file_id_from_png(
        self,
        *,
        chat_id: int,
        png_bytes: bytes,
        filename: str,
    ) -> str:
        input_file = BufferedInputFile(png_bytes, filename=filename)
        temp_msg = await self._bot.send_photo(chat_id=chat_id, photo=input_file)
        photo = temp_msg.photo[-1]  # type: ignore[index]
        file_id = photo.file_id
        await self._bot.delete_message(chat_id=chat_id, message_id=temp_msg.message_id)
        return file_id
