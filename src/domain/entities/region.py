from dataclasses import dataclass, field

from src.domain.entities.base import Entity
from src.domain.enums.region import RegionStatus
from src.domain.events.region import RegionCreated, RegionSettingsUpdated
from src.domain.exceptions.region import InvalidChannelId
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName
from src.utils.get_datetime_utc_now import get_datetime_utc_now


@dataclass(kw_only=True)
class Region(Entity):
    title: str
    timezone: TimezoneName
    channel_id: int
    status: RegionStatus = RegionStatus.ACTIVE
    settings: RegionSettings | None = None
    metadata: RegionMetadata | None = None

    @classmethod
    def create(
        cls,
        *,
        title: str,
        timezone: str,
        channel_id: int,
        settings: RegionSettings,
    ) -> "Region":
        if not title.strip():
            raise ValueError("Название региона не может быть пустым")

        if channel_id == 0:
            raise InvalidChannelId("Channel_id не может быть 0")

        region = cls(
            title=title.strip(),
            timezone=TimezoneName(timezone),
            channel_id=channel_id,
            settings=settings,
            
        )
        region.add_event(
            RegionCreated(
                occurred_at=get_datetime_utc_now(),
                region_id=region.id,
                title=region.title,
                metadata=region.metadata,
            )
        )
        return region

    def disable(self) -> None:
        self.status = RegionStatus.DISABLED
        self.touch()

    def enable(self) -> None:
        self.status = RegionStatus.ACTIVE
        self.touch()

    def update_settings(self, *, settings: RegionSettings) -> None:
        self.settings = settings
        self.touch()
        self.add_event(
            RegionSettingsUpdated(
                occurred_at=get_datetime_utc_now(),
                region_id=self.id,
            )
        )
