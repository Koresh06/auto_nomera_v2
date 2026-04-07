from dataclasses import dataclass

from src.application.ports.publication_service.image_processor import ImageProcessor


@dataclass(frozen=True, slots=True)
class AddFrameResult:
    image_file_id: str


class AddRedFrameUseCase:
    def __init__(self, image_processor: ImageProcessor) -> None:
        self._image_processor = image_processor

    async def execute(self, *, image_file_id: str) -> AddFrameResult:
        image_file_id = await self._image_processor.add_red_frame(file_id=image_file_id)
        return AddFrameResult(image_file_id=image_file_id)
