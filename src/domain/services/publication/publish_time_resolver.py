from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.timezone_name import TimezoneName


@dataclass(frozen=True, slots=True)
class PublishTimeResolver:
    """
    Конвертирует локальные дату/время слота региона в publish_at_utc.
    """

    def resolve_publish_at_utc(
        self,
        tz: TimezoneName,
        slot: SlotKey,
    ) -> datetime:
        zone = ZoneInfo(tz.value)

        local_naive = datetime.combine(slot.local_day, slot.local_time)
        local_aware = local_naive.replace(tzinfo=zone)

        return local_aware.astimezone(timezone.utc)

    def resolve_unpin_time(self, now_utc: datetime, params: dict) -> datetime:
        if "hours" in params:
            return now_utc + timedelta(hours=int(params["hours"]))
        if "days" in params:
            return now_utc + timedelta(days=int(params["days"]))
        # дефолт: 24 часа
        return now_utc + timedelta(hours=24)
