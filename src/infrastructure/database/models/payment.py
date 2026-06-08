from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Enum as SaEnum, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    amount: Mapped[int] = mapped_column(BigInteger)  # в копейках
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
