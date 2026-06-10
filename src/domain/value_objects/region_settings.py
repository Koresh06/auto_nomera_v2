from dataclasses import dataclass, field
from datetime import time

from src.domain.exceptions.region import (
    InvalidDaysRange,
    InvalidSlotTimes,
    InvalidSystemPaidSlotsCount,
)


@dataclass(frozen=True, slots=True)
class RegionSettings:
    slot_times: tuple[time, ...] = field(
        default=tuple(
            (
                time(10, 0),
                time(14, 0),
                time(18, 0),
            ),
        )
    )  # (10:00, 14:00, 18:00)
    days_range: int = 7
    system_paid_slots_count: int = 3
    publication_limit_enabled: bool = True

    def __post_init__(self) -> None:
        if self.days_range <= 0 or self.days_range > 31:
            raise InvalidDaysRange("days_range must be within 1..31")

        if not self.slot_times:
            raise InvalidSlotTimes("slot_times must not be empty")

        # проверим уникальность и сортируемость
        if len(set(self.slot_times)) != len(self.slot_times):
            raise InvalidSlotTimes("slot_times must be unique")

        # count не может превышать общего числа видимых слотов
        total_slots = self.days_range * len(self.slot_times)
        if (
            self.system_paid_slots_count < 0
            or self.system_paid_slots_count > total_slots
        ):
            raise InvalidSystemPaidSlotsCount(
                "system_paid_slots_count must be within 0..(days_range * len(slot_times))"
            )
