from dataclasses import dataclass

from src.domain.events.base import DomainEvent
from src.domain.value_objects.region_metadata import RegionMetadata


@dataclass(frozen=True, slots=True)
class RegionCreated(DomainEvent):
    region_id: int
    title: str
    metadata: RegionMetadata | None


@dataclass(frozen=True, slots=True)
class RegionSettingsUpdated(DomainEvent):
    region_id: int
