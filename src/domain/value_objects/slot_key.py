from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True, slots=True)
class SlotKey:
    region_id: int
    local_day: date  # локальная дата региона
    local_time: time  # локальное время региона


    @property
    def date_display(self) -> str:
        return f"{self.local_day.day:02d}.{self.local_day.month:02d}.{self.local_day.year}"

    @property
    def time_display(self) -> str:
        return self.local_time.strftime("%H:%M")

    @property
    def to_display(self) -> str:
        return f"{self.date_display}-{self.time_display}"
    
    @staticmethod
    def decode_slot_id(slot_id: str, region_id: int) -> "SlotKey":
        y, m, d, hh, mm = map(int, slot_id.split("_"))
        return SlotKey(
            region_id=region_id,
            local_day=date(y, m, d),
            local_time=time(hh, mm),
        )