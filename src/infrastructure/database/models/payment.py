from decimal import Decimal
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String, Enum as SaEnum, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.infrastructure.database.models.base import (
    BaseModel,
    CreatedAtMixin,
    UpdatedAtMixin,
)

if TYPE_CHECKING:
    from src.infrastructure.database.models import UserModel


class PaymentModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    method: Mapped[PaymentMethod] = mapped_column(SaEnum(PaymentMethod))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    status: Mapped[PaymentStatus] = mapped_column(
        SaEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
        index=True,
    )
    purpose: Mapped[PaymentPurpose] = mapped_column(SaEnum(PaymentPurpose))
    purpose_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="payments")


    @classmethod
    def from_entity(self, payment: "Payment") -> "PaymentModel":
        return self(
            external_id=payment.external_id,
            user_id=payment.user_id,
            method=payment.method,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            purpose=payment.purpose,
            purpose_id=payment.purpose_id,
            description=payment.description,
            meta=payment.meta,
            expires_at=payment.expires_at,
            paid_at=payment.paid_at,
        )

    def to_entity(self) -> "Payment":
        return Payment(
            external_id=self.external_id,
            user_id=self.user_id,
            method=self.method,
            amount=self.amount,
            currency=self.currency,
            status=self.status,
            purpose=self.purpose,
            purpose_id=self.purpose_id,
            description=self.description,
            meta=self.meta,
            expires_at=self.expires_at,
            paid_at=self.paid_at,
        )
    
    def _update_model(self, payment: "Payment") -> None:
        self.external_id = payment.external_id
        self.user_id = payment.user_id
        self.method = payment.method
        self.amount = payment.amount
        self.currency = payment.currency
        self.status = payment.status
        self.purpose = payment.purpose
        self.purpose_id = payment.purpose_id
        self.description = payment.description
        self.meta = payment.meta
        self.expires_at = payment.expires_at
        self.paid_at = payment.paid_at