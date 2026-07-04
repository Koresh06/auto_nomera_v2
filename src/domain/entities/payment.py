from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime

from src.domain.entities.base import Entity
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus


@dataclass(kw_only=True)
class Payment(Entity):
    external_id: str
    user_id: int
    method: PaymentMethod
    amount: Decimal  # в рублях
    currency: str = "RUB"
    status: PaymentStatus = PaymentStatus.PENDING
    purpose: PaymentPurpose
    purpose_id: int | None = None
    description: str | None = None
    meta: dict = field(default_factory=dict)
    expires_at: datetime | None = None
    paid_at: datetime | None = None

    @property
    def method_label(self) -> str:
        return {
            PaymentMethod.YOOKASSA: "🏦 ЮKassa",
            PaymentMethod.TELEGRAM_STARS: "⭐ Telegram Stars",
            PaymentMethod.CRYPTO: "🪙 Криптовалюта",
            PaymentMethod.MANUAL_CARD: "💳 Карта (вручную)",
        }.get(self.method, self.method.value)

    def mark_paid(self, now: datetime) -> None:
        self.status = PaymentStatus.PAID
        self.paid_at = now
        self.touch()

    def mark_failed(self) -> None:
        self.status = PaymentStatus.FAILED
        self.touch()

    def mark_expired(self) -> None:
        self.status = PaymentStatus.EXPIRED
        self.touch()
