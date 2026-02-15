from datetime import datetime, timezone

from src.domain.entities.slot_state import SlotState
from src.domain.events.slot import SlotConvertedToPaid
from src.domain.value_objects.slot_key import SlotKey
from datetime import date, time


def test_entity_events_pull():
    slot_key = SlotKey(
        region_id=1,
        local_day=date(2026, 2, 12),
        local_time=time(10, 0),
    )
    state = SlotState(slot_key=slot_key)

    now = datetime(2026, 2, 12, 12, 0, tzinfo=timezone.utc)
    ad_id = 123

    ev = SlotConvertedToPaid(
        occurred_at=now,
        slot=slot_key,
        user_id=1,
        ad_id=ad_id,
    )

    state.add_event(ev)
    events = state.pull_events()

    assert len(events) == 1
    assert events[0] == ev
    assert state.pull_events() == []
