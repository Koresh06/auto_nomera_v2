from dataclasses import dataclass
from datetime import datetime

from src.domain.events.base import DomainEvent
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class SlotBooked(DomainEvent):
    slot: SlotKey
    ad_id: int
    user_id: int
