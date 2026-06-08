from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, VARCHAR, Enum as SaEnum, ForeignKey, Boolean, NUMERIC, DateTime

from src.domain.entities.user import User
from src.domain.enums.role import UserRole

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


if TYPE_CHECKING:
    from src.infrastructure.database.models import RegionModel, PaymentModel


class UserModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(VARCHAR(16), nullable=True)
    role: Mapped[UserRole] = mapped_column(SaEnum(UserRole), default=UserRole.USER)
    balance: Mapped[Decimal] = mapped_column(NUMERIC(12, 2), default=0.00, server_default="0.00")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    pre_publication_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("regions.id", ondelete="SET NULL"), 
    )

    region: Mapped["RegionModel"] = relationship(
        "RegionModel",
        back_populates="users",
    )
    payments: Mapped[list["PaymentModel"]] = relationship(
        "PaymentModel",
        back_populates="user",
    )
 
    def __repr__(self) -> str:
        return f"UserModel(id={self.id}, tg_id={self.tg_id}, username={self.username})"
    
    @classmethod
    def from_entity(cls, user: "User") -> "UserModel":
        return cls(
            tg_id=user.tg_id,
            username=user.username,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role,
            balance=user.balance,
            is_blocked=user.is_blocked,
            region_id=user.region_id,
            pre_publication_expires_at=user.pre_publication_expires_at,
        )

    def to_entity(self) -> "User":
        return User(
            id=self.id,
            tg_id=self.tg_id,
            username=self.username,
            full_name=self.full_name,
            phone=self.phone,
            role=self.role,
            balance=self.balance,
            is_blocked=self.is_blocked,
            region_id=self.region_id,
            pre_publication_expires_at=self.pre_publication_expires_at,
        )
    
    def _update_model(self, user: "User") -> None:
        self.username = user.username
        self.full_name = user.full_name
        self.phone = user.phone
        self.role = user.role
        self.balance = user.balance
        self.is_blocked = user.is_blocked
        self.region_id = user.region_id
        self.pre_publication_expires_at = user.pre_publication_expires_at