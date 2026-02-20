from typing import Protocol


class ImageProcessor(Protocol):
    async def add_red_frame_png(self, *, png_bytes: bytes) -> bytes:
        """Возвращает новый file_id (уже с рамкой)."""
        ...
