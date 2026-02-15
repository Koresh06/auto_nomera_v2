from datetime import date, time

from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.value_objects.slot_key import SlotKey


def test_system_paid_first_n_slots():
    policy = SlotPricingPolicy(system_paid_count=3)

    region_id = 1
    future = [
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(10, 0)
        ),
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(14, 0)
        ),
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(18, 0)
        ),
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 13), local_time=time(10, 0)
        ),
    ]

    assert policy.is_system_paid(ordered_future_slots=future, slot=future[0]) is True
    assert policy.is_system_paid(ordered_future_slots=future, slot=future[1]) is True
    assert policy.is_system_paid(ordered_future_slots=future, slot=future[2]) is True
    assert policy.is_system_paid(ordered_future_slots=future, slot=future[3]) is False
