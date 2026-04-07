from aiogram import Bot
from aiogram.types import BufferedInputFile
from PIL import Image, ImageDraw
from io import BytesIO

from src.application.ports.publication_service.image_processor import ImageProcessor


class PillowImageProcessor(ImageProcessor):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def add_red_frame(self, *, file_id: str) -> str:
        # 1. Скачать файл из Telegram
        file = await self.bot.get_file(file_id)
        file_bytes = await self.bot.download_file(file.file_path)
        image_bytes = file_bytes.read()

        # 2. Обработать через Pillow
        img = Image.open(BytesIO(image_bytes))
        processed = draw_debug_red_border(
            img,
            border_width=40,
            color=(255, 0, 0, 255),
            mutate=False,
        )

        # 3. Сохранить в память
        out = BytesIO()
        processed.save(out, format="PNG")
        out.seek(0)

        # 4. Отправить в Telegram, чтобы получить новый file_id
        input_file = BufferedInputFile(out.read(), filename="highlight.png")
        temp_msg = await self.bot.send_photo(
            chat_id=self.bot.id,  # можно любой технический чат
            photo=input_file,
        )

        new_file_id = temp_msg.photo[-1].file_id

        # (по желанию) удалить временное сообщение
        await self.bot.delete_message(
            chat_id=self.bot.id,
            message_id=temp_msg.message_id,
        )

        return new_file_id


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
