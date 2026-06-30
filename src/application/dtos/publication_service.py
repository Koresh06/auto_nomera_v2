from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication_service import PublicationServiceStatus, PublicationServiceType



@dataclass(frozen=True)
class PublicationServiceDTO:
    id: str
    type: PublicationServiceType
    status: PublicationServiceStatus
    price_paid: int | None
    params: dict | None
    created_at: datetime

    @property
    def price_paid_display(self) -> str:
        if self.price_paid is None:
            return "—"
        return f"{self.price_paid:,.0f} руб.".replace(",", " ")
    
    @property
    def created_at_display(self) -> str:
        return f"{self.created_at:%d.%m.%Y %H:%M}"

    @classmethod
    def from_entity(cls, s: "PublicationService") -> "PublicationServiceDTO":
        return cls(
            id=str(s.id),
            type=s.type,
            status=s.status,
            price_paid=s.price_paid,
            params=s.params,
            created_at=s.created_at,
        )