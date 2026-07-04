from dataclasses import dataclass
from datetime import datetime

from src.application.dtos.publication_service import PublicationServiceDTO
from src.domain.entities.publication import Publication
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceStatus
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
    is_child: bool
    services: list[PublicationServiceDTO]
    plate_number: str | None = None
    shop_name: str | None = None

    @classmethod
    def from_entity(
        cls,
        publication: "Publication",
        plate_number: str | None = None,
        shop_name: str | None = None,
    ) -> "PublicationDTO":
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
            is_child=publication.is_child,
            services=[PublicationServiceDTO.from_entity(s) for s in publication.services],
            plate_number=plate_number,
            shop_name=shop_name,
        )
    
    @property
    def slot_display(self) -> str:
        if self.slot is None:
            return "—"
        return self.slot.to_display
    
    @property
    def display_title(self) -> str:
        if self.shop_name:
            return f"🏦 {self.shop_name}"
        return f"🚘 {self.plate_number or '—'}"
    

    @property
    def services_display(self) -> str:
        active = [
            s for s in self.services
            if s.status in (PublicationServiceStatus.ACTIVE, PublicationServiceStatus.USED)
        ]
        if not active:
            return "—"
        return "\n".join(f"  {s.type.display}" for s in active)