from typing import Protocol


class ImageProcessor(Protocol):
    async def add_red_frame(self, chat_id: int, file_id: str) -> str:
        """
        Принимает Telegram file_id,
        возвращает новый file_id обработанного изображения.
        """
        ...
