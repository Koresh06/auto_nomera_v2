from datetime import date, datetime, time, timezone

from src.domain.entities.slot_state import SlotState
from src.domain.enums.slot import SlotPricing
from src.domain.value_objects.slot_key import SlotKey


def test_slot_state_mark_converted_paid():
    slot_key = SlotKey(
        region_id=20,
        local_day=date(2026, 2, 12),
        local_time=time(14, 0),
    )
    state = SlotState(slot_key=slot_key)

    assert state.pricing == SlotPricing.FREE
    assert state.converted_at is None

    now = datetime(2026, 2, 12, 12, 0, tzinfo=timezone.utc)
    ad_id = 123

    state.mark_converted(
        user_id=777,
        ad_id=ad_id,
        at_utc=now,
    )

    assert state.pricing == SlotPricing.CONVERTED
    assert state.converted_at == now
    assert state.converted_by_user_id == 777
    assert state.converted_by_ad_id == ad_id
