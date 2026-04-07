from typing import Protocol


class PlateImageGenerator(Protocol):
    async def generate_png_bytes(
        self,
        *,
        plate_text: str,
        channel_username: str,
        with_border: bool = False,
    ) -> bytes: ...
