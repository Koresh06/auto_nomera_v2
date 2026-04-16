from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, VARCHAR, Enum as SaEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.enums.ad import AdType

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


if TYPE_CHECKING:
    from src.infrastructure.database.models import (
        UserModel,
        RegionModel,
        PublicationModel,
    )


class AdModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
    )
    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "regions.id",
            ondelete="CASCADE",
        ),
    )
    ad_type: Mapped[AdType] = mapped_column(SaEnum(AdType))

    plate_number: Mapped[str | None] = mapped_column(VARCHAR(16), nullable=True)
    city: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(VARCHAR(16), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    store_items: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel")
    region: Mapped["RegionModel"] = relationship(
        "RegionModel",
        back_populates="ads",
    )
    publications: Mapped[list["PublicationModel"]] = relationship(
        "PublicationModel",
        back_populates="ad",
    )

    def __repr__(self) -> str:
        return (
            f"AdModel(id={self.id}, ad_type={self.ad_type}, plate={self.plate_number})"
        )
