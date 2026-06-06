from dataclasses import dataclass

from src.domain.enums.slot import SlotAvailability, SlotPricing
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class CalendarSlotView:
    slot_key: SlotKey
    text: str
    availability: SlotAvailability
    pricing: SlotPricing

    @property
    def is_disabled(self) -> bool:
        return self.availability == SlotAvailability.BOOKED

    @property
    def is_paid(self) -> bool:
        return self.pricing != SlotPricing.FREE
