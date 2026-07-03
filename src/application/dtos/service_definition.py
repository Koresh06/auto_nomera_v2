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
    
    @property
    def duration_display(self) -> str:
        return f"{self.duration_days} дн." if self.duration_days else "—"
    
    @property
    def description_display(self) -> str:
        return self.description or "— не задано"
    
    @property
    def has_duration(self) -> bool:
        return self.duration_days is not None
    
    @property
    def toggle_label(self) -> str:
        return "🔴 Снять с продажи" if self.is_active else "🟢 Вернуть в продаж"
    
    @property
    def status_label(self) -> str:
        return "🟢 Доступна для покупки" if self.is_active else "🔴 Недоступна"

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