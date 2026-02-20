from io import BytesIO

from PIL import Image, ImageDraw

from src.application.ports.publication_service.image_processor import ImageProcessor


class PillowImageProcessor(ImageProcessor):
    async def add_red_frame_png(self, *, png_bytes: bytes) -> bytes:
        img = Image.open(BytesIO(png_bytes))
        processed = draw_debug_red_border(
            img,
            border_width=40,
            color=(255, 0, 0, 255),
            mutate=False,
        )
        out = BytesIO()
        processed.save(out, format="PNG")
        return out.getvalue()
    

def draw_debug_red_border(
    img: Image.Image,
    border_width: int = 40,
    color: tuple[int, int, int, int] = (255, 0, 0, 255),
    mutate: bool = False,
) -> Image.Image:
    if border_width <= 0:
        return img if mutate else img.copy()

    im = img if mutate else img.copy()
    orig_mode = im.mode
    if im.mode != "RGBA":
        im = im.convert("RGBA")

    w, h = im.size
    d = ImageDraw.Draw(im)
    bw = min(border_width, w // 2, h // 2)

    d.rectangle([0, 0, w, bw], fill=color)
    d.rectangle([0, h - bw, w, h], fill=color)
    d.rectangle([0, 0, bw, h], fill=color)
    d.rectangle([w - bw, 0, w, h], fill=color)

    return im.convert(orig_mode) if orig_mode != "RGBA" else im