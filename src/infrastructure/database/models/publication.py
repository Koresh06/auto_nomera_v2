from typing import TYPE_CHECKING
from datetime import datetime, date, time

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer,
    BigInteger,
    Enum as SaEnum,
    ForeignKey,
    String,
    Date,
    Time,
    DateTime,
)

from src.domain.enums.publication import PublicationStatus

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


if TYPE_CHECKING:
    from src.infrastructure.database.models import PublicationServiceModel, AdModel


class PublicationModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    ad_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "ads.id",
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

    # статус
    status: Mapped[PublicationStatus] = mapped_column(
        SaEnum(PublicationStatus),
        default=PublicationStatus.DRAFT,
    )

    # слот (локальное время региона)
    slot_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    slot_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # планировщик
    publish_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scheduler_job_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # результат публикации
    channel_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    published_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ad: Mapped["AdModel"] = relationship(
        "AdModel",
        back_populates="publications",
    )
    services: Mapped[list["PublicationServiceModel"]] = relationship(
        "PublicationServiceModel",
        back_populates="publication",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"PublicationModel(id={self.id}, status={self.status})"
