from src.domain.entities.slot_state import SlotState
from src.domain.value_objects.slot_key import SlotKey
from datetime import date, time


def test_entity_events_pull():
    slot_key = SlotKey(
        region_id=1,
        local_day=date(2026, 2, 12),
        local_time=time(10, 0),
    )
    state = SlotState(slot_key=slot_key)

    events = state.pull_events()

    assert len(events) == 1
    assert state.pull_events() == []
