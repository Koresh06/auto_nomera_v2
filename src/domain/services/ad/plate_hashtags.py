import re

RUS = "АВЕКМНОРСТУХ"
ENG = "ABEKMHOPCTYX"
MAP = {RUS[i]: ENG[i] for i in range(len(RUS))}


def normalize_plate_for_tags(num: str) -> str:
    """Убирает пробелы, в верхний регистр, русские буквы → латинские."""
    num = num.replace(" ", "").upper()
    return "".join(MAP.get(c, c) for c in num)


def split_plate(num: str) -> tuple[str, str]:
    """Возвращает (номерная часть, регион)."""
    m = re.search(r"(\d{2,3})$", num)
    if not m:
        return num, ""
    region = m.group(1)
    return num[: -len(region)], region


def detect_number_tags(main: str) -> list[str]:
    tags: list[str] = []

    letters = "".join(re.findall(r"[A-Z]", main))
    digits = "".join(re.findall(r"\d", main))

    # 1) одинаковые буквы
    if len(letters) >= 2 and len(set(letters)) == 1:
        tags.append("#одинаковыебуквы")

    # 2) анализ цифр (последние 3)
    last3 = digits[-3:] if len(digits) >= 3 else digits

    if len(last3) == 3:
        if re.fullmatch(r"[1-9]00", last3):
            tags.append("#круглые")

        if re.fullmatch(r"00[1-9]|010", last3):
            tags.append("#перваядесятка")

        if re.fullmatch(r"(\d)\1\1", last3):
            tags.append("#одинаковыецифры")

    # зеркальные
    is_mirror = False

    # 3 цифры ABA
    match3 = re.findall(r"(\d)(\d)(\d)", digits)
    for a, b, c in match3:
        if a == c and a != b:
            is_mirror = True
            break

    # 4 цифры ABBA
    match4 = re.findall(r"(\d)(\d)(\d)(\d)", digits)
    for a, b, c, d in match4:
        if a == d and b == c and a != b:
            is_mirror = True
            break

    # буквы ABA
    matchL = re.findall(r"([A-Z])([A-Z])([A-Z])", letters)
    for a, b, c in matchL:
        if a == c and a != b:
            is_mirror = True
            break

    if is_mirror:
        tags.append("#зеркальные")

    return tags


def generate_hashtags(number: str) -> list[str]:
    if not number:
        return []

    normalized = normalize_plate_for_tags(number)
    main, _ = split_plate(normalized)
    tags = detect_number_tags(main)

    # preserve order, unique
    return list(dict.fromkeys(tags))
