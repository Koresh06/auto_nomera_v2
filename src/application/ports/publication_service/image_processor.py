from typing import Protocol


class ImageProcessor(Protocol):
    async def add_red_frame(self, *, file_id: str) -> str:
        """
        Принимает Telegram file_id,
        возвращает новый file_id обработанного изображения.
        """
        ...
