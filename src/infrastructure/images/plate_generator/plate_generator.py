import os
from typing import Self, Tuple
from PIL import Image, ImageDraw, ImageFont

from src.infrastructure.images.plate_generator.plate_license import create_license_plate


class PlateGenerator:
    """Генератор номеров по шаблону"""

    def __init__(self, template_path: str, font_path: str) -> None:
        """
        Args:
            template_path: Путь к шаблону номера
            font_path: Путь к шрифту
        """
        self.template = Image.open(template_path)
        self.font_path = font_path

        self.font_size = 170
        self.region_font_size_3 = 110
        self.region_font_size_2 = 120

        self.main_area = (110, 75, 600, 195)  # x1, y1, x2, y2
        self.region_area = (670, 45, 770, 195)

        # Отступ между символами
        self.letter_spacing = 15
        self.region_letter_spacing = 6

        self.border_color = (255, 0, 0)
        self.border_size = 20

        self.main_areas = {
            "auto": (110, 75, 600, 195),
            "trailer": (110, 75, 600, 195),
            "moto": (110, 90, 600, 210)
        }

    def _get_font(self, size: int) -> ImageFont.truetype:
        """Загружает шрифт"""
        return ImageFont.truetype(self.font_path, size)

    def _get_text_width_with_spacing(
        self, text: str, font: ImageFont.truetype, spacing: int
    ) -> int:
        """Вычисляет ширину текста с учетом отступов"""
        if not text:
            return 0

        total_width = 0
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

        for i, char in enumerate(text):
            bbox = draw.textbbox((0, 0), char, font=font)
            char_width = bbox[2] - bbox[0]
            total_width += char_width

            # Добавляем отступ между символами (кроме последнего)
            if i < len(text) - 1:
                total_width += spacing

        return total_width

    def _draw_text_with_spacing(
        self,
        draw: ImageDraw.Draw,
        text: str,
        start_x: int,
        y: int,
        font: ImageFont.truetype,
        spacing: int,
    ) -> None:
        """Рисует текст с отступами между символами"""
        current_x = start_x

        for char in text:
            draw.text((current_x, y), char, fill=(0, 0, 0), font=font)

            # Вычисляем ширину символа для следующей позиции
            bbox = draw.textbbox((0, 0), char, font=font)
            char_width = bbox[2] - bbox[0]

            # Переходим к следующей позиции
            current_x += char_width + spacing

    def _center_text_with_spacing(
        self,
        text: str,
        area: Tuple[int, ...],
        font: ImageFont.truetype,
    ) -> Tuple[int, int]:
        """Центрирует текст с учетом отступов между символами"""
        x1, y1, x2, y2 = area

        # Вычисляем общую ширину с отступами
        text_width = self._get_text_width_with_spacing(text, font, self.letter_spacing)

        # Высота текста
        if text:
            bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox(
                (0, 0), text[0], font=font
            )
            text_height = bbox[3] - bbox[1]
        else:
            text_height = 0

        x = x1 + (x2 - x1 - text_width) // 2
        y = y1 + (y2 - y1 - text_height) // 2

        return x, y

    def _center_text(
        self,
        draw: ImageDraw.Draw,
        text: str,
        area: Tuple[int, ...],
        font: ImageFont.truetype,
    ) -> Tuple[int, int]:
        """Центрирует текст в заданной области"""
        x1, y1, x2, y2 = area
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = x1 + (x2 - x1 - text_width) // 2
        y = y1 + (y2 - y1 - text_height) // 2

        return x, y

    def generate(
        self, plate_text: str, channel_username: str, with_border: bool = False
    ) -> Image.Image:
        """
        Генерирует номер

        Args:
            plate_text: Текст номера (например "А123ВС77") или None для случайного
        """

        # Определяем количество цифр в регионе (последние 2-3 символа - цифры)
        plate_license = create_license_plate(plate_text)
        main_part = plate_license.get_main_part()
        region_digits = plate_license.get_region_digits()

        img = self.template.copy()
        draw = ImageDraw.Draw(img)

        font = self._get_font(self.font_size)

        plate_type = type(plate_license).__name__.lower().replace("licenseplate", "")
        main_area: tuple[int, int, int, int] = self.main_areas.get(plate_type, self.main_area)

        # Рисуем основной номер с отступами
        x, y = self._center_text_with_spacing(main_part, main_area, font)
        self._draw_text_with_spacing(draw, main_part, x, y, font, self.letter_spacing)

        # ---------- Отрисовка региона ----------
        region_font = self._get_font(
            self.region_font_size_2
            if len(region_digits) == 2
            else self.region_font_size_3
        )

        x, y = self._center_text(draw, region_digits, self.region_area, region_font)
        x -= 6

        current_x = x
        for char in region_digits:
            shift_x = -4 if char == "1" else 0 
            draw.text((current_x + shift_x, y), char, fill=(0, 0, 0), font=region_font)
            bbox = draw.textbbox((0, 0), char, font=region_font)
            char_width = bbox[2] - bbox[0]
            current_x += char_width + self.region_letter_spacing

        if channel_username:
            img = draw_footer_link(
                img,
                channel_username=channel_username,
                font_paths=(
                    "src/generator_photo/static/Arial.ttf",
                    self.font_path,
                ),
                max_font_size=56,  # как на примере — крупнее
                margin_xy=(70, 100),  # чуть ниже от края, как на картинке
                text_color=(122, 122, 122, 255),  # тот самый серый
                backdrop_alpha=0,  # без белой подложки
            )

        if not with_border:
            return img

        new_width = img.width + self.border_size * 2
        new_height = img.height + self.border_size * 2

        bordered_img = Image.new("RGB", (new_width, new_height), self.border_color)

        bordered_img.paste(img, (self.border_size, self.border_size))

        return bordered_img

    @classmethod
    def load(cls) -> Self:
        return cls(
            template_path=os.path.join("src/infrastructure/images/plate_generator/static", "plate_template.png"),
            font_path=os.path.join("src/infrastructure/images/plate_generator/static", "RoadNumbers2.0_fix.otf"),
        )


def _safe_load_font(
    candidates: Tuple[str, ...], size: int
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Пробует несколько путей к шрифту; при неудаче возвращает дефолт PIL."""
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

def draw_footer_link(
    img: Image.Image,
    channel_username: str,
    *,
    font_paths: Tuple[str, ...] = (
        "src/infrastructure/images/plate_generator/static/Arial-Bold.ttf",
        "src/infrastructure/images/plate_generator/static/Arial.ttf",
    ),
    max_font_size: int = 48,
    min_font_size: int = 14,
    margin_xy: Tuple[int, int] = (70, 80),  # (mx, my): mx влияет на доступную ширину
    text_color=(122, 122, 122, 255),
    backdrop_alpha: int = 0,
    use_stroke: bool = True,
    lift_px: int = 3,  # небольшой подъём для визуального выравнивания
) -> Image.Image:
    """
    Рисует 'https://t.me/{channel}' по центру кадра по X, с опорой по центру текста (anchor='mm').
    Размер уменьшается, пока текст не поместится в (W - 2*mx).
    """
    channel = channel_username.lstrip("@").strip()
    if not channel:
        return img.copy()

    text = f"https://t.me/{channel}"

    base = img.copy()
    original_mode = base.mode
    if base.mode != "RGBA":
        base = base.convert("RGBA")

    draw = ImageDraw.Draw(base)
    W, H = base.size
    mx, my = margin_xy

    # подбор размера под полезную ширину
    size = max_font_size
    font = _safe_load_font(font_paths, size)

    # опорная точка текста (центр X, чуть выше, чем H - my)
    x = W / 2
    y = H - my - lift_px

    bbox = draw.textbbox((x, y), text, font=font, anchor="mm")
    tw = bbox[2] - bbox[0]

    while (tw > W - 2 * mx) and (size > min_font_size):
        size -= 1
        font = _safe_load_font(font_paths, size)
        bbox = draw.textbbox((x, y), text, font=font, anchor="mm")
        tw = bbox[2] - bbox[0]

    # (опционально) подложка
    if backdrop_alpha > 0:
        pad = 6
        rect = (
            max(0, int(bbox[0] - pad)),
            max(0, int(bbox[1] - pad)),
            min(W, int(bbox[2] + pad)),
            min(H, int(bbox[3] + pad)),
        )
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rectangle(rect, fill=(255, 255, 255, backdrop_alpha))
        base = Image.alpha_composite(base, overlay)
        draw = ImageDraw.Draw(base)

    # отрисовка (по центру)
    if use_stroke:
        draw.text((x, y), text, font=font, fill=text_color, anchor="mm",
                  stroke_width=1, stroke_fill=text_color)
    else:
        draw.text((x, y), text, font=font, fill=text_color, anchor="mm")

    return base.convert(original_mode) if original_mode != "RGBA" else base




def draw_debug_red_border(
    img: Image.Image,
    border_width: int = 40,
    color: Tuple[int, int, int, int] = (255, 0, 0, 255),
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