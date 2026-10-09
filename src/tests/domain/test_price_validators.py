"""
Regression test for AUD-20: validate_price()/validate_price_urgent_buyout()
only stripped the ASCII space (U+0020) via .replace(" ", ""), so a price like
"1 550 000" typed/pasted with a non-breaking space (U+00A0) -- common on
mobile keyboards -- failed .isdigit() and was rejected as invalid, even though
it's a perfectly reasonable price. store_validator.py already handled this
correctly via a digits-only regex; price_validators.py now does the same.
"""

from decimal import Decimal

import pytest

from src.presentation.telegram.utils.price_validators import (
    parse_money,
    validate_price,
    validate_price_urgent_buyout,
)


def test_validate_price_handles_regular_space():
    assert validate_price("1 550 000") == 1_550_000


def test_validate_price_handles_non_breaking_space():
    assert validate_price("1\u00a0550\u00a0000") == 1_550_000


def test_validate_price_handles_narrow_no_break_space():
    assert validate_price("1\u202f550\u202f000") == 1_550_000


def test_validate_price_small_numbers_multiplied_by_1000():
    assert validate_price("150") == 150_000


def test_validate_price_zero_stays_zero():
    assert validate_price("0") == 0


def test_validate_price_rejects_non_numeric_garbage():
    with pytest.raises(ValueError):
        validate_price("not a number")


def test_validate_price_urgent_buyout_handles_non_breaking_space():
    assert validate_price_urgent_buyout("1\u00a0550\u00a0000") == 1_550_000


def test_validate_price_urgent_buyout_rejects_zero():
    with pytest.raises(ValueError):
        validate_price_urgent_buyout("0")


# --- Потолок цены: ads.price — INTEGER (< 2^31), без потолка ввод вроде
# "5000000000" доходил до INSERT и ронял обработчик подтверждения.


@pytest.mark.parametrize("fn", [validate_price, validate_price_urgent_buyout])
def test_price_above_integer_column_is_rejected(fn):
    with pytest.raises(ValueError):
        fn("5000000000")


@pytest.mark.parametrize("fn", [validate_price, validate_price_urgent_buyout])
def test_price_at_ceiling_is_accepted(fn):
    assert fn("1000000000") == 1_000_000_000


# --- parse_money: суммы в рублях, которые вводятся руками


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("500", Decimal("500")),
        ("1 000", Decimal("1000")),
        ("1 000,50", Decimal("1000.50")),
        ("199.99", Decimal("199.99")),
        ("-150", Decimal("-150")),
        ("+20", Decimal("20")),
        ("1000000", Decimal("1000000")),
    ],
)
def test_parse_money_accepts(raw, expected):
    assert parse_money(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "abc",
        "NaN",
        "+NaN",
        "sNaN",
        "Infinity",
        "-inf",
        "1e12",
        "1000000.01",
        "100.555",
    ],
)
def test_parse_money_rejects(raw):
    with pytest.raises(ValueError):
        parse_money(raw)


def test_admin_signed_amount_rejects_nan_and_infinity():
    from src.presentation.telegram.features.admin.modules.balance.validators import (
        validate_signed_amount,
    )

    for raw in ("+NaN", "-NaN", "+Infinity", "+1e12"):
        with pytest.raises(ValueError):
            validate_signed_amount(raw)
    assert validate_signed_amount("-50,5") == Decimal("-50.5")
    with pytest.raises(ValueError):
        validate_signed_amount("50")  # без знака
    with pytest.raises(ValueError):
        validate_signed_amount("+0")
