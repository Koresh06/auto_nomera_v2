from dataclasses import dataclass
from decimal import Decimal

from src.domain.entities.payment import PaymentMethod


_METHOD_LABELS = {
    PaymentMethod.MANUAL_CARD: "💳 Вручную",
    PaymentMethod.CRYPTO: "🪙 Крипта",
    PaymentMethod.TELEGRAM_STARS: "⭐ Stars",
    PaymentMethod.YOOKASSA: "🏦 ЮKassa",
}


@dataclass(frozen=True, slots=True)
class MethodStatDTO:
    method: PaymentMethod
    count: int
    amount: Decimal

    @property
    def label(self) -> str:
        return _METHOD_LABELS.get(self.method, self.method.value)

    @property
    def amount_display(self) -> str:
        return f"{self.amount:.0f}"


@dataclass(frozen=True, slots=True)
class RegionStatDTO:
    region_id: int
    region_title: str
    count: int
    amount: Decimal

    @property
    def amount_display(self) -> str:
        return f"{self.amount:.0f}"


@dataclass(frozen=True, slots=True)
class PaymentStatsDTO:
    total_count: int
    total_amount: Decimal
    by_method: list[MethodStatDTO]
    top_region: RegionStatDTO | None

    @property
    def top_method(self) -> MethodStatDTO | None:
        if not self.by_method:
            return None
        return max(self.by_method, key=lambda m: m.count)

    @property
    def total_amount_display(self) -> str:
        return f"{self.total_amount:.0f}"
