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


def validate_price_urgent_buyout(value: str) -> int:
    value = value.strip().replace(" ", "")
    if not value.isdigit():
        raise ValueError("Введите корректное число (только цифры).")

    num = int(value)
    if num == 0:
        raise ValueError("Цена не может быть 0. Укажите сумму по примеру.")

    if 1 <= num < 1000:
        num *= 1000

    return num
