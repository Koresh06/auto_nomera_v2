"""
Regression test for AUD-11: list_overdue_scheduled_today() used to compute
"today" using a hardcoded Europe/Moscow timezone for every region, so the
admin "overdue publications" screen could misreport publications in regions
with a notably different offset from Moscow. is_within_regional_today() is
the extracted, pure piece of that logic.
"""

from datetime import datetime, timezone

from src.infrastructure.repositories.publication.sqlalchemy import (
    is_within_regional_today,
)


def test_moscow_publication_within_moscow_today():
    now_utc = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)  # 12:00 MSK
    publish_at_utc = datetime(2026, 2, 12, 7, 0, tzinfo=timezone.utc)  # 10:00 MSK

    assert is_within_regional_today(
        publish_at_utc, tz_name="Europe/Moscow", now_utc=now_utc
    )


def test_publication_just_before_moscow_midnight_is_not_moscow_today():
    now_utc = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)  # 12:00 MSK on the 12th
    # 2026-02-11 23:00 MSK == 2026-02-11 20:00 UTC -- yesterday in Moscow
    publish_at_utc = datetime(2026, 2, 11, 20, 0, tzinfo=timezone.utc)

    assert not is_within_regional_today(
        publish_at_utc, tz_name="Europe/Moscow", now_utc=now_utc
    )


def test_region_far_ahead_of_moscow_has_its_own_today():
    """AUD-11's actual bug: a region far from Moscow (here, Kamchatka,
    UTC+12) has a "today" that the old hardcoded-Moscow logic would get wrong
    near the day boundary."""
    # 2026-02-12 09:00 UTC == 2026-02-12 21:00 Kamchatka (already evening,
    # still the 12th there) but == 2026-02-12 12:00 MSK (still the 12th there too)
    now_utc = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)

    # A publication at 2026-02-12 15:00 UTC == 2026-02-13 03:00 Kamchatka —
    # that's "tomorrow" for Kamchatka, so it must NOT count as Kamchatka's
    # "today", even though it's still 2026-02-12 in Moscow/UTC.
    publish_at_utc = datetime(2026, 2, 12, 15, 0, tzinfo=timezone.utc)

    assert is_within_regional_today(
        publish_at_utc, tz_name="Europe/Moscow", now_utc=now_utc
    )
    assert not is_within_regional_today(
        publish_at_utc, tz_name="Asia/Kamchatka", now_utc=now_utc
    )


def test_missing_tz_name_falls_back_to_moscow():
    now_utc = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)
    publish_at_utc = datetime(2026, 2, 12, 7, 0, tzinfo=timezone.utc)

    assert is_within_regional_today(publish_at_utc, tz_name=None, now_utc=now_utc)


def test_naive_publish_at_is_treated_as_utc():
    now_utc = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)
    naive_publish_at = datetime(2026, 2, 12, 7, 0)  # no tzinfo

    assert is_within_regional_today(
        naive_publish_at, tz_name="Europe/Moscow", now_utc=now_utc
    )
