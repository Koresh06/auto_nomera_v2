from dataclasses import dataclass

from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(frozen=True, slots=True)
class ServiceDefinitionDTO:
    id: int
    type: PublicationServiceType
    title: str
    price: int
    duration_days: int | None
    description: str | None

    @property
    def price_display(self) -> str:
        return f"{self.price // 100} руб."

    @classmethod
    def from_entity(cls, s: ServiceDefinition) -> "ServiceDefinitionDTO":
        return cls(
            id=s.id,
            type=s.type,
            title=s.title,
            price=s.price,
            duration_days=s.duration_days,
            description=s.description,
        )