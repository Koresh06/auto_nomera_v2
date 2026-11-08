from datetime import date, datetime, timezone

import pytest

from src.domain.value_objects.date_range import DateRange

TODAY = date(2026, 11, 1)


@pytest.mark.parametrize(
    "raw",
    [
        "01.10.2026 - 31.10.2026",
        "01.10.2026-31.10.2026",
        "01.10.2026 — 31.10.2026",
        "01.10.2026 по 31.10.2026",
        "  01.10.2026   31.10.2026 ",
    ],
)
def test_parse_range(raw):
    parsed = DateRange.parse(raw, today=TODAY)
    assert parsed == DateRange(date(2026, 10, 1), date(2026, 10, 31))


def test_single_date_is_one_day():
    parsed = DateRange.parse("15.10.2026", today=TODAY)
    assert parsed.start == parsed.end == date(2026, 10, 15)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "вчера",
        "31.02.2026",
        "2026-10-01",
        "01.10.2026 - 31.10.2026 - 01.11.2026",
        "01.10.2026 и ещё что-то",
        "31.10.2026 - 01.10.2026",  # начало позже конца
        "02.11.2026",  # начинается в будущем
    ],
)
def test_parse_rejects(raw):
    with pytest.raises(ValueError):
        DateRange.parse(raw, today=TODAY)


def test_range_may_end_in_future():
    assert DateRange.parse("01.11.2026 - 30.11.2026", today=TODAY).end.day == 30


def test_bounds_are_moscow_days_and_end_is_exclusive():
    since, until = DateRange(date(2026, 10, 1), date(2026, 10, 31)).bounds_utc()
    assert since == datetime(2026, 9, 30, 21, 0, tzinfo=timezone.utc)
    assert until == datetime(2026, 10, 31, 21, 0, tzinfo=timezone.utc)


def test_label():
    assert (
        DateRange(date(2026, 10, 1), date(2026, 10, 2)).label
        == "01.10.2026 — 02.10.2026"
    )
