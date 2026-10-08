import re


def _digits_only(value: str) -> str:
    # Убирает любые не-цифровые символы, включая неразрывный пробел (U+00A0)
    # и узкий неразрывный пробел (U+202F), которые обычный .replace(" ", "")
    # не ловит — такие пробелы часто вставляются мобильными клавиатурами при
    # копировании форматированных чисел вида "1 550 000".
    return re.sub(r"[^\d]", "", value)


def validate_price(value: str) -> int:
    """Валидирует и форматирует цену. Возвращает округлённое значение."""
    value = _digits_only(value)
    if not value:
        raise ValueError("Введите корректное число")

    num = int(value)
    if num == 0:
        return 0

    if 1 <= num <= 999:
        num *= 1000

    return num


def validate_price_urgent_buyout(value: str) -> int:
    value = _digits_only(value)
    if not value:
        raise ValueError("Введите корректное число (только цифры).")

    num = int(value)
    if num == 0:
        raise ValueError("Цена не может быть 0. Укажите сумму по примеру.")

    if 1 <= num < 1000:
        num *= 1000

    return num
