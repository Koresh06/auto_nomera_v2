from typing import Protocol


class ImageProcessor(Protocol):
    async def add_red_frame(self, *, file_id: str) -> str:
        """Возвращает новый file_id (уже с рамкой)."""
        ...
