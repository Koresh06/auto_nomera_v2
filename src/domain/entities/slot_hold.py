from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.entities.base import Entity
from src.domain.value_objects.slot_key import SlotKey


@dataclass(kw_only=True)
class SlotHold(Entity):
    slot: SlotKey
    user_id: int
    ad_id: int
    hold_until_utc: datetime

    def is_expired(self, now_utc: datetime) -> bool:
        return now_utc >= self.hold_until_utc