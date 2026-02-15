from dataclasses import dataclass

from src.domain.enums.slot import SlotPricing
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class SlotPricingPolicy:
    system_paid_count: int

    def is_system_paid(
        self,
        *,
        ordered_future_slots: list[SlotKey],
        slot: SlotKey,
    ) -> bool:
        # ordered_future_slots должны быть отсортированы "от ближайшего"
        if self.system_paid_count <= 0:
            return False
        return slot in set(ordered_future_slots[: self.system_paid_count])

    def resolve_pricing(
        self,
        *,
        is_system_paid: bool,
        is_converted_paid: bool,
    ) -> SlotPricing:
        if is_converted_paid:
            return SlotPricing.CONVERTED
        if is_system_paid:
            return SlotPricing.SYSTEM
        return SlotPricing.FREE
