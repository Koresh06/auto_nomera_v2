import re


# Город и название магазина хранятся в VARCHAR(128).
MAX_TEXT_FIELD_LEN = 128


def capitalize_word(value: str) -> str:
    # Только первая буква: str.capitalize() понижал регистр всего остального
    # ("Нижний Новгород" -> "Нижний новгород", "BMW Club" -> "Bmw club").
    value = value.strip()
    if len(value) > MAX_TEXT_FIELD_LEN:
        raise ValueError(
            f"Слишком длинное значение (максимум {MAX_TEXT_FIELD_LEN} символов)"
        )
    return value[:1].upper() + value[1:]


def validate_phone_number(value: str) -> str:
    """
    Проверяет формат номера телефона.
    Допускается +7 или 8 и далее 10 цифр.
    """
    value = value.strip().replace(" ", "")
    pattern = r"^(?:\+7|8)\d{10}$"
    if not re.fullmatch(pattern, value):
        raise ValueError(
            "Некорректный номер телефона. Пример: <code>+79991234567</code> или <code>89001234567</code>"
        )
    return value
