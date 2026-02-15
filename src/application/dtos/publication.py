from dataclasses import dataclass

from src.domain.enums.publication import PublicationStatus


@dataclass(frozen=True, slots=True)
class PublicationDTO:
    id: int
    ad_id: int
    region_id: int
    status: PublicationStatus
