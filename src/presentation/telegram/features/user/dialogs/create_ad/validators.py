import re


def capitalize_word(value: str) -> str:
    return value.strip().capitalize() 


def validate_phone_number(value: str) -> str:
    """
    Проверяет формат номера телефона.
    Допускается +7 или 8 и далее 10 цифр.
    """
    value = value.strip().replace(" ", "")
    pattern = r"^(?:\+7|8)\d{10}$"
    if not re.fullmatch(pattern, value):
        raise ValueError("Некорректный номер телефона. Пример: +79991234567 или 89001234567")
    return value


def validate_price(value: str) -> int:
    """Валидирует и форматирует цену. Возвращает округлённое значение."""
    value = value.strip().replace(" ", "")
    if not value.isdigit():
        raise ValueError("Введите корректное число")

    num = int(value)
    if num == 0:
        return 0

    if 1 <= num <= 999:
        num *= 1000

    return num