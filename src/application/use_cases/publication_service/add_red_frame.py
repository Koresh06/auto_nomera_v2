from dataclasses import dataclass

from src.application.ports.publication_service.image_processor import ImageProcessor


@dataclass(frozen=True, slots=True)
class AddFrameResult:
    png_bytes: bytes

class AddRedFrameUseCase:
    def __init__(self, image_processor: ImageProcessor) -> None:
        self._image_processor = image_processor

    async def execute(self, *, image_bytes: bytes) -> AddFrameResult:
        png_bytes = await self._image_processor.add_red_frame_png(png_bytes=image_bytes)
        return AddFrameResult(png_bytes=png_bytes)