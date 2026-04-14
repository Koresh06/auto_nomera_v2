from dataclasses import dataclass

from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.value_objects.timezone_name import TimezoneName


@dataclass(frozen=True, slots=True)
class RegionDTO:
    id: int
    title: str
    timezone: TimezoneName
    channel_id: int
    channel_username: str
    status: RegionStatus

    @classmethod
    def from_entity(cls, region: Region) -> "RegionDTO":
        return cls(
            id=region.id,
            title=region.title,
            timezone=region.timezone,
            channel_id=region.channel_id,
            channel_username=region.channel_username,
            status=region.status,
        )
