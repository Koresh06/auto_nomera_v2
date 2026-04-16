from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, VARCHAR, Enum as SaEnum
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.enums.region import RegionStatus

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


if TYPE_CHECKING:
    from src.infrastructure.database.models import UserModel, AdModel


class RegionModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(VARCHAR(64))
    timezone: Mapped[str] = mapped_column(VARCHAR(64))
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    channel_username: Mapped[str] = mapped_column(VARCHAR(64))
    status: Mapped[RegionStatus] = mapped_column(SaEnum(RegionStatus), default=RegionStatus.ACTIVE)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    users: Mapped[list["UserModel"]] = relationship(
        "UserModel",
        back_populates="region",
    )
    ads: Mapped[list["AdModel"]] = relationship(
        "AdModel",
        back_populates="region",
    )
 
    def __repr__(self) -> str:
        return f"RegionModel(id={self.id}, title={self.title})"