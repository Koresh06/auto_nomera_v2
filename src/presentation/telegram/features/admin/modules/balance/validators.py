from decimal import Decimal, InvalidOperation


def validate_signed_amount(raw: str) -> Decimal:
    value = raw.strip()

    if not value or value[0] not in ("+", "-"):
        raise ValueError("Сумма должна начинаться со знака + или −")

    try:
        amount = Decimal(value.replace(",", "."))
    except InvalidOperation:
        raise ValueError("Некорректная сумма")

    if amount == 0:
        raise ValueError("Сумма не может быть нулевой")

    return amount