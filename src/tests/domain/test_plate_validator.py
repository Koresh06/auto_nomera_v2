import pytest

from src.domain.services.ad.plate_validator import (
    normalize_plate,
    split_plate_number,
    validate_plate,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("А123ВС77", "А123ВС77"),  # авто, регион 2 цифры
        ("а123вс777", "А123ВС777"),  # авто, регион 3 цифры, нижний регистр
        ("A123BC77", "А123ВС77"),  # латиница -> кириллица
        (" а 123 вс 77 ", "А123ВС77"),  # пробелы
        ("АВ123477", "АВ123477"),  # прицеп
        ("1234АВ77", "1234АВ77"),  # мото
        ("1234ав777", "1234АВ777"),
    ],
)
def test_valid_plates(raw, expected):
    assert validate_plate(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "12345",
        "Б123ВС77",  # Б не используется в номерах
        "А123ВС7",  # регион из одной цифры
        "А123ВС7777",  # регион из четырёх цифр
        "А1234ВС77",
        "А12ВС77",
        "А123ВСXX",  # регион не цифры
        "А*23ВС77",  # маска без allow_mask
    ],
)
def test_invalid_plates(raw):
    with pytest.raises(ValueError):
        validate_plate(raw)


@pytest.mark.parametrize("raw", ["А*23ВС77", "****ВС77", "АВ**3477", "1*34АВ77"])
def test_masks_allowed_only_for_buy(raw):
    assert validate_plate(raw, allow_mask=True)
    with pytest.raises(ValueError):
        validate_plate(raw)


def test_mask_never_allowed_in_region():
    with pytest.raises(ValueError):
        validate_plate("А123ВС7*", allow_mask=True)


def test_error_message_lists_correct_formats():
    with pytest.raises(ValueError) as e:
        validate_plate("xyz")
    text = str(e.value)
    assert "— авто" in text and "— прицеп" in text and "— мото" in text
    assert "1111AA77 / AA1111777" not in text


def test_normalize_plate():
    assert normalize_plate(" a 1 2 3 bc 77") == "А123ВС77"
    with pytest.raises(TypeError):
        normalize_plate(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("А123ВС77", ("А123ВС", "77")),
        ("А123ВС777", ("А123ВС", "777")),
        ("1234АВ77", ("1234АВ", "77")),
    ],
)
def test_split_plate_number(raw, expected):
    assert split_plate_number(raw) == expected
