from dataclasses import dataclass

from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName


@dataclass(frozen=True)
class RegionDTO:
    id: int
    title: str
    timezone: TimezoneName
    channel_id: int
    channel_username: str
    status: RegionStatus
    metadata: RegionMetadata
    settings: RegionSettings

    @property
    def status_label(self) -> str:
        return "🟢 Активен" if self.status == RegionStatus.ACTIVE else "🔴 Отключён"

    @property
    def is_active(self) -> bool:
        return self.status == RegionStatus.ACTIVE

    @property
    def publication_limit_enabled_label(self) -> str:
        return (
            "✅ Включено" if self.settings.publication_limit_enabled else "❌ Отключено"
        )

    @classmethod
    def from_entity(cls, region: Region) -> "RegionDTO":
        return cls(
            id=region.id,
            title=region.title,
            timezone=region.timezone,
            channel_id=region.channel_id,
            channel_username=region.channel_username,
            status=region.status,
            metadata=region.metadata,
            settings=region.settings,
        )

    def to_entity(self) -> Region:
        return Region(
            id=self.id,
            title=self.title,
            timezone=self.timezone,
            channel_id=self.channel_id,
            channel_username=self.channel_username,
            status=self.status,
            settings=self.settings,
            metadata=self.metadata,
        )
