import re
from decimal import Decimal, InvalidOperation


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
    if num > MAX_AD_PRICE:
        raise ValueError("Слишком большая сумма")

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
    if num > MAX_AD_PRICE:
        raise ValueError("Слишком большая сумма")

    if 1 <= num < 1000:
        num *= 1000

    return num


# Потолок для денежных сумм, вводимых руками (пополнение, корректировка
# баланса админом, цена платного слота). Колонки денег в БД — NUMERIC(12, 2)
# (< 10^10), но разумная сумма на порядки меньше; без потолка ввод вроде
# "1e12" доходил до INSERT и ронял обработчик (а Stars-инвойс к тому моменту
# уже был создан).
MAX_MONEY_AMOUNT = Decimal("1000000")

# Цена номера в объявлении: колонка ads.price — INTEGER (< 2^31).
MAX_AD_PRICE = 1_000_000_000


def parse_money(raw: str, *, max_amount: Decimal = MAX_MONEY_AMOUNT) -> Decimal:
    """Строка -> сумма в рублях. Отклоняет то, что Decimal() принимает, но
    деньгами не является: NaN/Infinity, экспоненту за пределами копеек
    ("100.555"), суммы выше потолка. Знак сохраняет — проверка знака на
    вызывающей стороне."""
    value = re.sub(r"[\s  ]", "", raw).replace(",", ".")
    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ValueError("Введите корректную сумму, например 500") from None

    if not amount.is_finite():
        raise ValueError("Введите корректную сумму, например 500")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Сумма может содержать не больше двух знаков после запятой")
    if abs(amount) > max_amount:
        raise ValueError(f"Сумма не может превышать {max_amount:.0f} руб.")
    return amount
