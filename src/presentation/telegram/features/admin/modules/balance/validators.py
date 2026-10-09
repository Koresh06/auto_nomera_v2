from decimal import Decimal

from src.presentation.telegram.utils.price_validators import parse_money


def validate_signed_amount(raw: str) -> Decimal:
    value = raw.strip()

    if not value or value[0] not in ("+", "-"):
        raise ValueError("Сумма должна начинаться со знака + или −")

    # parse_money отсекает NaN/Infinity: "+NaN" проходил проверку "!= 0"
    # и мог записать NaN в баланс пользователя (NUMERIC в Postgres его хранит)
    amount = parse_money(value)

    if amount == 0:
        raise ValueError("Сумма не может быть нулевой")

    return amount
