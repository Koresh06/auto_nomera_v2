from dataclasses import dataclass
from decimal import Decimal

from src.domain.entities.base import Entity
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(kw_only=True)
class ServiceDefinition(Entity):
    title: str
    type: PublicationServiceType
    price: int                          # в рублях
    duration_days: int | None = None    # для PIN и AUTOPUBLISH — сколько дней
    description: str | None = None
    is_active: bool = True
    params_schema: dict | None = None   # схема для валидации params при покупке


    @staticmethod
    def format_price(kopecks: int) -> str:
        rubles = Decimal(kopecks)
        return f"{rubles:,.0f} руб.".replace(",", " ")
    
    def activate(self) -> None:
        self.is_active = True
        self.touch()

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def update_title(self, title: str) -> None:
        self.title = title
        self.touch()

    def update_price(self, price: int) -> None:
        if price < 0:
            raise ValueError("Цена не может быть отрицательной")
        self.price = price
        self.touch()

    def update_duration(self, duration_days: int | None) -> None:
        if duration_days is not None and duration_days <= 0:
            raise ValueError("Длительность должна быть положительной")
        self.duration_days = duration_days
        self.touch()

    def update_description(self, description: str | None) -> None:
        self.description = description
        self.touch()