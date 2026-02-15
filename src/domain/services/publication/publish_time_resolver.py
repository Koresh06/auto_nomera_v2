from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.domain.entities.region import Region
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class PublishTimeResolver:
    """
    Конвертирует локальные дату/время слота региона в publish_at_utc.
    """

    def resolve_publish_at_utc(self, *, region: Region, slot: SlotKey) -> datetime:
        tz = ZoneInfo(region.timezone.value)
        local_dt = datetime.combine(
            slot.local_day,
            slot.local_time,
            tzinfo=tz,
        )
        return local_dt.astimezone(timezone.utc)
