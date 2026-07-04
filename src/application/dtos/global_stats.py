from dataclasses import dataclass
from decimal import Decimal

from src.domain.entities.ad import AdType
from src.domain.enums.publication_service import PublicationServiceType


@dataclass(frozen=True, slots=True)
class AdTypeCountDTO:
    ad_type: AdType
    count: int

    @property
    def label(self) -> str:
        return {
            AdType.SALE: "📤 Продажа",
            AdType.BUY: "📥 Покупка",
            AdType.URGENT_BUYOUT: "⚠️ Срочный выкуп",
            AdType.STORE: "🏦 Магазин",
        }.get(self.ad_type, self.ad_type.value)


@dataclass(frozen=True, slots=True)
class ServiceCountDTO:
    type: PublicationServiceType
    count: int

    @property
    def label(self) -> str:
        return self.type.display


@dataclass(frozen=True, slots=True)
class GlobalStatsDTO:
    total_users: int
    users_with_store: int
    users_without_store: int
    total_ads: int
    scheduled_ads: int
    by_ad_type: list[AdTypeCountDTO]
    total_regions: int
    total_purchases: int
    total_amount: Decimal
    total_services: int
    by_service: list[ServiceCountDTO]

    @property
    def top_service(self) -> ServiceCountDTO | None:
        return max(self.by_service, key=lambda s: s.count) if self.by_service else None

    @property
    def amount_display(self) -> str:
        return f"{self.total_amount:.0f}"
