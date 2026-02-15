from dataclasses import dataclass

from src.domain.enums.slot import SlotAvailability, SlotPricing
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class CalendarSlotDTO:
    id: str                 # удобно для callback_data (строка ключа)
    text: str
    slot: SlotKey
    availability: SlotAvailability
    pricing: SlotPricing
    disabled: bool


@dataclass(frozen=True, slots=True)
class CalendarDTO:
    region_id: int
    slots: list[CalendarSlotDTO]
