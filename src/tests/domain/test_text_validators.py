import pytest

from src.presentation.telegram.utils.text_validators import (
    capitalize_word,
    validate_phone_number,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("москва", "Москва"),
        ("  казань ", "Казань"),
        ("Нижний Новгород", "Нижний Новгород"),
        ("санкт-Петербург", "Санкт-Петербург"),
        ("BMW Club", "BMW Club"),
        ("", ""),
    ],
)
def test_capitalize_word_keeps_the_rest_of_the_case(raw, expected):
    assert capitalize_word(raw) == expected


@pytest.mark.parametrize("ok", ["+79991234567", "89991234567", " +7 999 123 45 67 "])
def test_phone_ok(ok):
    assert validate_phone_number(ok).startswith(("+7", "8"))


@pytest.mark.parametrize("bad", ["12345", "+19991234567", "7999123456", "+7999123456a"])
def test_phone_bad(bad):
    with pytest.raises(ValueError):
        validate_phone_number(bad)


def test_capitalize_word_rejects_values_longer_than_column():
    assert capitalize_word("я" * 128) == "Я" + "я" * 127
    with pytest.raises(ValueError):
        capitalize_word("я" * 129)


def test_store_name_respects_column_length_and_case():
    from src.presentation.telegram.features.user.modules.store.create.validators import (
        validate_store,
    )

    assert validate_store("Номера-Плюс") == "Номера-Плюс"
    assert len(validate_store("а" * 128)) == 128
    with pytest.raises(ValueError):
        validate_store("а" * 129)
