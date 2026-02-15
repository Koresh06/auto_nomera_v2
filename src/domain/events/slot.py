from dataclasses import dataclass
from datetime import datetime

from src.domain.events.base import DomainEvent
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class SlotHeld(DomainEvent):
    slot_key: SlotKey
    user_id: int
    ad_id: int
    hold_until_utc: datetime


@dataclass(frozen=True, slots=True)
class SlotHoldReleased(DomainEvent):
    slot: SlotKey
    user_id: int
    ad_id: int


@dataclass(frozen=True, slots=True)
class SlotConvertedToPaid(DomainEvent):
    slot: SlotKey
    user_id: int
    ad_id: int