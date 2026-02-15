from typing import Protocol


class TelegramMedia(Protocol):
    async def ensure_photo_file_id_from_png(
        self,
        *,
        chat_id: int,
        png_bytes: bytes,
        filename: str,
    ) -> str:
        """Загрузить png в TG, вернуть file_id, и удалить временное сообщение."""
        ...
