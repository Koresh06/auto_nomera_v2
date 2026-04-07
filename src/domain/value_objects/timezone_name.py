from dataclasses import dataclass
from zoneinfo import ZoneInfo

from src.domain.exceptions.region import InvalidTimezone


@dataclass(frozen=True, slots=True)
class TimezoneName:
    value: str

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.value)
        except ValueError:
            raise InvalidTimezone(f"Unknown timezone: {self.value}")
