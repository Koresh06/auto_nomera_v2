from dataclasses import dataclass

from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication_service import PublicationServiceStatus, PublicationServiceType



@dataclass(frozen=True)
class PublicationServiceDTO:
    id: str
    type: PublicationServiceType
    status: PublicationServiceStatus
    price_paid: int | None
    params: dict | None

    @property
    def price_paid_display(self) -> str:
        if self.price_paid is None:
            return "—"
        return f"{self.price_paid:,.0f} руб.".replace(",", " ")

    @classmethod
    def from_entity(cls, s: "PublicationService") -> "PublicationServiceDTO":
        return cls(
            id=str(s.id),
            type=s.type,
            status=s.status,
            price_paid=s.price_paid,
            params=s.params,
        )