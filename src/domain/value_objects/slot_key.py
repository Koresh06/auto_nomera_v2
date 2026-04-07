from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True, slots=True)
class SlotKey:
    region_id: int
    local_day: date  # локальная дата региона
    local_time: time  # локальное время региона

    def to_redis_key(self) -> str:
        # стабильный ключ
        return f"slot_hold:{self.region_id}:{self.local_day.isoformat()}:{self.local_time.strftime('%H:%M')}"
