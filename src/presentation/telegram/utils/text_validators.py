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
        raise ValueError("Некорректный номер телефона. Пример: <code>+79991234567</code> или <code>89001234567</code>")
    return value