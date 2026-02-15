from io import BytesIO

from src.application.ports.ad.plate_image_generator import PlateImageGenerator
from src.infrastructure.images.plate_generator.plate_generator import PlateGenerator


class PillowPlateImageGenerator(PlateImageGenerator):
    def __init__(self) -> None:
        self._gen = PlateGenerator.load()

    async def generate_png_bytes(
        self,
        *,
        plate_text: str,
        channel_username: str,
        with_border: bool = False,
    ) -> bytes:
        img = self._gen.generate(plate_text, channel_username, with_border=with_border)
        bio = BytesIO()
        img.save(bio, format="PNG")
        return bio.getvalue()
