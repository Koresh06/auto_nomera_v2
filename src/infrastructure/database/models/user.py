from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, VARCHAR, Enum as SaEnum, ForeignKey, Boolean

from src.domain.entities.user import User
from src.domain.enums.role import UserRole

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


if TYPE_CHECKING:
    from src.infrastructure.database.models import RegionModel


class UserModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(VARCHAR(16), nullable=True)
    role: Mapped[UserRole] = mapped_column(SaEnum(UserRole), default=UserRole.USER)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("regions.id", ondelete="SET NULL"), 
    )

    region: Mapped["RegionModel"] = relationship(
        "RegionModel",
        back_populates="users",
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
            is_blocked=user.is_blocked,
            region_id=user.region_id,
        )
    

    def to_entity(self) -> "User":
        return User(
            id=self.id,
            tg_id=self.tg_id,
            username=self.username,
            full_name=self.full_name,
            phone=self.phone,
            role=self.role,
            is_blocked=self.is_blocked,
            region_id=self.region_id,
        )