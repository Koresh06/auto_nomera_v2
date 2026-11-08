import asyncio
from io import BytesIO
from typing import Union

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, InputFile, Message

from aiogram_dialog.manager.message_manager import MessageManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId, NewMessage, OldMessage

from src.infrastructure.telegram.media_virtual_url import CUSTOM_URL_PREFIX
from src.infrastructure.images.plate_generator.plate_generator import PlateGenerator


# Telegram отвечает так, когда сохранённое в стеке диалога представление
# старого сообщения (текст/медиа) разошлось с реальным — обычно после сетевого
# таймаута, когда сообщение ушло, а стек не обновился. Редактировать такое
# сообщение бесполезно: удаляем и шлём окно заново.
_EDIT_MISMATCH_ERRORS = (
    "there is no text in the message to edit",
    "there is no caption in the message to edit",
    "there is no media in the message to edit",
)


class CustomMessageManager(MessageManager):
    """
    Поддерживает "виртуальные" изображения по URL формата:
      my://{plate_number}|{channel_username}|{chat_id}

    1) генерит PNG по номеру и username региона,
    2) грузит в Telegram через временное сообщение,
    3) сохраняет file_id в media.file_id,
    4) удаляет временное сообщение,
    5) возвращает file_id (чтобы Telegram повторно использовал уже загруженное).
    """

    def __init__(self) -> None:
        super().__init__()
        self._plate_generator = PlateGenerator.load()

    async def get_media_source(
        self,
        media: MediaAttachment,
        bot: Bot,
    ) -> Union[InputFile, str]:
        # 1) Если file_id уже есть — используем его
        if media.file_id:
            if isinstance(media.file_id, MediaId):
                return await super().get_media_source(media, bot)
            if isinstance(media.file_id, str):
                return media.file_id

        url = getattr(media, "url", None)
        if not (isinstance(url, str) and url.startswith(CUSTOM_URL_PREFIX)):
            return await super().get_media_source(media, bot)

        # 2) Парсим payload
        payload = url[len(CUSTOM_URL_PREFIX) :]
        parts = payload.split("|")
        if len(parts) != 3:
            # если сломанный формат — не падаем
            return await super().get_media_source(media, bot)

        plate_number, channel_username, chat_id_raw = parts

        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            return await super().get_media_source(media, bot)

        plate_number = plate_number.strip()
        channel_username = channel_username.strip().lstrip("@")

        if not plate_number or not channel_username:
            return await super().get_media_source(media, bot)

        # 3) Генерация PNG
        img = await asyncio.to_thread(
            self._plate_generator.generate, plate_number, channel_username
        )
        bio = BytesIO()
        img.save(bio, format="PNG")
        png_bytes = bio.getvalue()

        # 4) Загружаем в TG через временное сообщение, чтобы получить file_id
        input_file = BufferedInputFile(png_bytes, filename=f"{plate_number}.png")
        temp_msg = await bot.send_photo(chat_id=chat_id, photo=input_file)

        # 5) Сохраняем media_id и удаляем временное сообщение
        photo = temp_msg.photo[-1]  # type: ignore[index]
        media.file_id = MediaId(
            file_id=photo.file_id, file_unique_id=photo.file_unique_id
        )

        try:
            await bot.delete_message(chat_id=chat_id, message_id=temp_msg.message_id)
        except Exception:
            # если не удалилось — не критично, не валим обработку
            pass

        # 6) Возвращаем file_id, чтобы Telegram переиспользовал загруженный файл
        return photo.file_id

    async def edit_message_safe(
        self,
        bot: Bot,
        new_message: NewMessage,
        old_message: OldMessage,
    ) -> Message:
        try:
            return await super().edit_message_safe(bot, new_message, old_message)
        except TelegramBadRequest as err:
            if not any(e in err.message for e in _EDIT_MISMATCH_ERRORS):
                raise
            await self.remove_message_safe(bot, old_message, new_message)
            return await self.send_message(bot, new_message)
