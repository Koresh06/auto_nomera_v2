from dataclasses import dataclass

from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(frozen=True, slots=True)
class ServiceDefinitionDTO:
    id: int
    title: str
    type: PublicationServiceType
    price: int
    duration_days: int | None
    description: str | None
    is_active: bool
    params_schema: dict | None = None

    @property
    def price_display(self) -> str:
        return f"{self.price:,.0f} руб.".replace(",", " ")

    @classmethod
    def from_entity(cls, s: ServiceDefinition) -> "ServiceDefinitionDTO":
        return cls(
            id=s.id,
            type=s.type,
            title=s.title,
            price=s.price,
            duration_days=s.duration_days,
            description=s.description,
            is_active=s.is_active,
            params_schema=s.params_schema,
        )