from datetime import date, time

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Date, Time, UniqueConstraint, ForeignKey

from .base import BaseModel, CreatedAtMixin


class SlotBookingModel(BaseModel, CreatedAtMixin):
    __tablename__ = "slot_bookings"
    __table_args__ = (
        UniqueConstraint(
            "region_id",
            "slot_day",
            "slot_time",
            name="uq__slot_bookings__slot",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("regions.id", ondelete="CASCADE"),
    )
    slot_day: Mapped[date] = mapped_column(Date, nullable=False)
    slot_time: Mapped[time] = mapped_column(Time, nullable=False)
    ad_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ads.id", ondelete="CASCADE"),
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    def __repr__(self) -> str:
        return f"SlotBookingModel(region={self.region_id}, day={self.slot_day}, time={self.slot_time})"


class SlotConvertedModel(BaseModel, CreatedAtMixin):
    __tablename__ = "slot_converted"
    __table_args__ = (
        UniqueConstraint(
            "region_id",
            "slot_day",
            "slot_time",
            name="uq__slot_converted__slot",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "regions.id",
            ondelete="CASCADE",
        ),
    )
    slot_day: Mapped[date] = mapped_column(Date)
    slot_time: Mapped[time] = mapped_column(Time)
    ad_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "ads.id",
            ondelete="CASCADE",
        ),
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
    )

    def __repr__(self) -> str:
        return f"SlotConvertedModel(region={self.region_id}, day={self.slot_day}, time={self.slot_time})"
