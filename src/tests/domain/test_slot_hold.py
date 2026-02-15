from datetime import date, datetime, time, timezone, timedelta

from src.domain.entities.slot_hold import SlotHold
from src.domain.value_objects.slot_key import SlotKey


def test_slot_hold_expiration():
    slot = SlotKey(
        region_id=1,
        local_day=date(2026, 2, 12),
        local_time=time(10, 0),
    )
    now = datetime(
        2026,
        2,
        12,
        12,
        0,
        tzinfo=timezone.utc,
    )

    hold = SlotHold(
        slot=slot,
        user_id=10,
        ad_id=123,
        hold_until_utc=now + timedelta(minutes=15),
    )

    assert hold.is_expired(now) is False
    assert hold.is_expired(now + timedelta(minutes=16)) is True
