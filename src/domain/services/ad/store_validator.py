import re
from collections import Counter
from dataclasses import dataclass

from src.domain.value_objects.price import Price
from src.domain.services.ad.plate_validator import validate_plate


TG_MESSAGE_LIMIT = 4096
APPROX_LINE_LENGTH = 45
RESERVE = 250
MAX_ITEMS = max(5, min(200, (TG_MESSAGE_LIMIT - RESERVE) // APPROX_LINE_LENGTH))

# Целое число из ASCII-цифр; допускаются разделители разрядов (пробелы,
# включая неразрывные U+00A0/U+202F от мобильных клавиатур, точка, запятая,
# апостроф) только между группами по три цифры: «1 550 000», «1.200.000».
# Раньше из строки просто выкидывалось всё, кроме цифр, — «-5», «abc12»,
# «12 тыс» молча превращались в число.
_PRICE_RE = re.compile(r"[0-9]+|[0-9]{1,3}(?:[ \u00a0\u202f.,'][0-9]{3})+")


def parse_price_digits(raw: str) -> int:
    value = raw.strip()
    if not _PRICE_RE.fullmatch(value):
        raise ValueError("Введите цену цифрами, например 150000")
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) > 1 and digits[0] == "0":
        raise ValueError("Цена не может начинаться с нуля")
    return int(digits)


@dataclass(frozen=True, slots=True)
class ParsedStoreItem:
    plate: str
    price: Price


@dataclass(frozen=True, slots=True)
class StoreInputParseResult:
    items: list[ParsedStoreItem]
    skipped_count: int  # сколько строк отрезано из-за лимита Telegram


def _parse_price(raw: str) -> Price:
    try:
        return Price(parse_price_digits(raw))
    except ValueError:
        raise ValueError(f"не удалось распознать цену: «{raw}»") from None


def parse_store_price(raw: str) -> Price:
    """Цена одной позиции магазина — те же правила, что при добавлении
    списком: только цифры (разделители игнорируются), ноль недопустим."""
    price = _parse_price(raw)
    if price.value == 0:
        raise ValueError("⚠️ Цена не может быть равна <b>0 руб.</b>")
    return price


def parse_store_validator(raw_text: str) -> StoreInputParseResult:
    """
    Парсит текст вида:
        x111xx01-1000000
        о100оо01-500000

    Бросает ValueError с готовым (на русском, с <code> для Telegram HTML)
    сообщением, описывающим все найденные ошибки сразу — чтобы пользователь
    не правил по одной строке за раз.
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError(
            "Вы ничего не ввели. Пожалуйста, введите хотя бы один номер и цену.\n\n"
            "<code>x111xx01-1000000</code>"
        )

    parsed: list[ParsedStoreItem] = []
    errors: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if "-" in line:
            plate_part, price_part = line.rsplit("-", 1)
        else:
            parts = line.rsplit(maxsplit=1)
            if len(parts) != 2:
                errors.append(f"{idx}) не удалось определить цену: «{line}»")
                continue
            plate_part, price_part = parts

        try:
            plate = validate_plate(plate_part, allow_mask=False)
        except ValueError as e:
            errors.append(f"{idx}) {e}")
            continue

        try:
            price = _parse_price(price_part)
        except ValueError:
            errors.append(f"{idx}) некорректная цена: «{line}»")
            continue

        if price.value == 0:
            errors.append(f"{idx}) цена не может быть равна <b>0 руб.</b>: «{line}»")
            continue

        parsed.append(ParsedStoreItem(plate=plate, price=price))

    if errors:
        raise ValueError("⚠️ Обнаружены ошибки:\n\n" + "\n".join(errors))

    plates_only = [item.plate for item in parsed]
    duplicates = {p for p, cnt in Counter(plates_only).items() if cnt > 1}
    if duplicates:
        raise ValueError(
            "⚠️ В вашем вводе обнаружены дубликаты:\n\n"
            + "\n".join(f"• {p}" for p in duplicates)
            + "\n\nУдалите их и попробуйте снова."
        )

    if len(parsed) > MAX_ITEMS:
        skipped = len(parsed) - MAX_ITEMS
        parsed = parsed[:MAX_ITEMS]
    else:
        skipped = 0

    return StoreInputParseResult(items=parsed, skipped_count=skipped)
