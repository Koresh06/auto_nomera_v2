"""
Regression test for AUD-20: validate_price()/validate_price_urgent_buyout()
only stripped the ASCII space (U+0020) via .replace(" ", ""), so a price like
"1 550 000" typed/pasted with a non-breaking space (U+00A0) -- common on
mobile keyboards -- failed .isdigit() and was rejected as invalid, even though
it's a perfectly reasonable price. store_validator.py already handled this
correctly via a digits-only regex; price_validators.py now does the same.
"""

import pytest

from src.presentation.telegram.utils.price_validators import (
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
