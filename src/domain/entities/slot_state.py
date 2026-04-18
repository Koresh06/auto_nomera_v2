from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.base import Entity
from src.domain.enums.slot import SlotPricing
from src.domain.value_objects.slot_key import SlotKey


@dataclass(kw_only=True)
class SlotState(Entity):
    slot_key: SlotKey
    pricing: SlotPricing = SlotPricing.FREE

    converted_at: datetime | None = None
    converted_by_user_id: int | None = None
    converted_by_ad_id: int | None = None

    def mark_converted(
        self,
        *,
        user_id: int,
        ad_id: int,
        at_utc: datetime,
    ) -> None:
        self.pricing = SlotPricing.CONVERTED
        self.converted_at = at_utc
        self.converted_by_user_id = user_id
        self.converted_by_ad_id = ad_id
        self.touch()
