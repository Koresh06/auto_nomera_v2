from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.publication import Publication
from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True)
class PublicationDTO:
    id: int
    ad_id: int
    region_id: int
    status: PublicationStatus
    slot: SlotKey | None
    publish_at_utc: datetime | None
    channel_message_id: int | None
    published_at_utc: datetime | None
    scheduler_job_id: str | None
    services: list
    plate_number: str | None = None


    @classmethod
    def from_entity(cls, publication: "Publication", plate_number: str | None = None) -> "PublicationDTO":
        return cls(
            id=publication.id,
            ad_id=publication.ad_id,
            region_id=publication.region_id,
            status=publication.status,
            slot=publication.slot,
            publish_at_utc=publication.publish_at_utc,
            channel_message_id=publication.channel_message_id,
            published_at_utc=publication.published_at_utc,
            scheduler_job_id=publication.scheduler_job_id,
            services=[s.to_dict() for s in publication.services],
            plate_number=plate_number,
        )
    
    @property
    def slot_display(self) -> str:
        if self.slot is None:
            return "—"
        return self.slot.to_display