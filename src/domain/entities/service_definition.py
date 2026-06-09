from dataclasses import dataclass
from decimal import Decimal

from src.domain.entities.base import Entity
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(kw_only=True)
class ServiceDefinition(Entity):
    title: str
    type: PublicationServiceType
    price: int                          # в копейках
    duration_days: int | None = None    # для PIN и AUTOPUBLISH — сколько дней
    description: str | None = None
    is_active: bool = True
    params_schema: dict | None = None   # схема для валидации params при покупке


    @staticmethod
    def format_price(kopecks: int) -> str:
        rubles = Decimal(kopecks) / 100
        return f"{rubles:,.0f} руб.".replace(",", " ")