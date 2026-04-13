import re
from dataclasses import dataclass

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import TextInput


RUS_LETTERS = "АВЕКМНОРСТУХ"

LATIN_TO_CYRIL = str.maketrans(
    {
        "A": "А",
        "B": "В",
        "E": "Е",
        "K": "К",
        "M": "М",
        "H": "Н",
        "O": "О",
        "P": "Р",
        "C": "С",
        "T": "Т",
        "X": "Х",
        "Y": "У",
    }
)

PLATE_PATTERNS_WITH_MASK = {
    "auto": re.compile(
        rf"^[{RUS_LETTERS}\*][0-9\*]{{3}}[{RUS_LETTERS}\*]{{2}}$"
    ),  # X111XX
    "trailer": re.compile(rf"^[{RUS_LETTERS}\*]{{2}}[0-9\*]{{4}}$"),  # XX1111
    "moto": re.compile(rf"^[0-9\*]{{4}}[{RUS_LETTERS}\*]{{2}}$"),  # 1111XX
}

PLATE_BASE_PATTERNS = {
    "auto": re.compile(rf"^[{RUS_LETTERS}]\d{{3}}[{RUS_LETTERS}]{{2}}$"),  # X111XX
    "trailer": re.compile(rf"^[{RUS_LETTERS}]{{2}}\d{{4}}$"),  # XX1111
    "moto": re.compile(rf"^\d{{4}}[{RUS_LETTERS}]{{2}}$"),  # 1111XX
}


def normalize_plate(plate: str) -> str:
    """Удаляет пробелы, переводит латиницу в кириллицу и в верхний регистр."""
    if not isinstance(plate, str):
        raise TypeError("plate must be a string")
    plate = plate.strip().replace(" ", "").upper()
    return plate.translate(LATIN_TO_CYRIL)


def validate_plate(plate: str, *, allow_mask: bool = False) -> str:
    """
    Универсальная валидация номера (авто, прицеп, мото).
    Поддерживает '*' в основной части, но не в регионе.
    Регион допускает 2 или 3 цифры.
    Возвращает нормализованную строку (кириллица, uppercase, без пробелов).
    """
    original = plate.strip()
    p = normalize_plate(plate)

    patterns = PLATE_PATTERNS_WITH_MASK if allow_mask else PLATE_BASE_PATTERNS

    # Проверяем все варианты длины региона — 2 и 3 цифры
    for region_length in (2, 3):
        if len(p) <= region_length:
            continue

        main_part = p[:-region_length]
        region = p[-region_length:]

        # регион должен быть только цифрами
        if not region.isdigit():
            continue

        # Проверяем основную часть по шаблонам
        for rx in patterns.values():
            if rx.fullmatch(main_part):
                return p  # ✅ валидный номер

    # --- Ошибка валидации ---
    if allow_mask:
        raise ValueError(
            f"⚠️ '{original}' не соответствует допустимым шаблонам.\n\n"
            "Допустимые форматы (буквы рус/лат, '*' допускается в номере):\n"
            "• A111AA77 / A111AA777 — авто\n"
            "• AA111177 / AA1111777 — прицеп\n"
            "• 1111AA77 / 1111AA777 — мото"
        )
    raise ValueError(
        f"⚠️ '{original}' не соответствует структуре номера по ГОСТ Р 50577–93.\n"
        "Допустимые форматы:\n"
        "• A111AA77 / A111AA777 — авто\n"
        "• AA111177 / AA1111777 — прицеп\n"
        "• 1111AA77 / AA1111777 — прицеп\n"
        "• 1111AA77 / 1111AA777 — мото"
    )


def split_plate_number(plate: str, *, allow_mask: bool = False) -> tuple[str, str]:
    """
    Разбивает номер на (number_part, region).

    allow_mask=True — допускаем '*' в основной части (для покупки),
    allow_mask=False — строго без масок (для продажи)
    """
    p = normalize_plate(plate)

    # Подготовим набор шаблонов под режим
    if allow_mask:
        patterns = list(PLATE_PATTERNS_WITH_MASK.values())
    else:
        # из масочных шаблонов убираем '*'
        patterns = [
            re.compile(rx.pattern.replace(r"\*", ""))
            for rx in PLATE_PATTERNS_WITH_MASK.values()
        ]

    for region_length in (2, 3):
        if len(p) <= region_length:
            continue

        number_part = p[:-region_length]
        region = p[-region_length:]

        if not region.isdigit():
            continue

        if any(rx.fullmatch(number_part) for rx in patterns):
            return number_part, region

    # Сообщение об ошибке — разное для режимов
    if allow_mask:
        raise ValueError(
            f"⚠️ '{plate}' не соответствует допустимым шаблонам.\n\n"
            "Допустимые форматы (буквы рус/лат, '*' как маска только в номере):\n"
            "• x111xx77 — автомобиль\n"
            "• xx111177 — прицеп\n"
            "• 9999yy77 — мото"
        )
    raise ValueError(
        f"⚠️ '{plate}' не соответствует допустимым структурам по ГОСТ Р 50577–93.\n"
        "Допустимые форматы:\n"
        "• A111AA — авто\n"
        "• AA111 — прицеп\n"
        "• 1111AA — мото"
    )


@dataclass(frozen=True, slots=True)
class PlateValidationResult:
    normalized: str
    main_part: str
    region: str


def validate_and_split(
    plate: str,
    *,
    allow_mask: bool = False,
) -> PlateValidationResult:
    normalized = validate_plate(plate, allow_mask=allow_mask)
    main_part, region = split_plate_number(normalized, allow_mask=allow_mask)

    return PlateValidationResult(
        normalized=normalized,
        main_part=main_part,
        region=region,
    )