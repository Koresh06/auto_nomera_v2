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

from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.slot_key import SlotKey

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
        back_populates="publication_rel",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"PublicationModel(id={self.id}, status={self.status})"

    @classmethod
    def from_entity(cls, pub: "Publication") -> "PublicationModel":
        model = PublicationModel(
            ad_id=pub.ad_id,
            region_id=pub.region_id,
        )
        cls._update_model(model, pub)
        return model
    
    def to_entity(self) -> Publication:
        slot = None
        if self.slot_day is not None and self.slot_time is not None:
            slot = SlotKey(
                region_id=self.region_id,
                local_day=self.slot_day,
                local_time=self.slot_time,
            )
    
        services = [
            PublicationService(
                id=s.id,
                type=s.type,
                status=s.status,
                params=s.params or {},
            )
            for s in (self.services or [])
        ]
    
        return Publication(
            id=self.id,
            ad_id=self.ad_id,
            region_id=self.region_id,
            status=self.status,
            slot=slot,
            publish_at_utc=self.publish_at_utc,
            channel_message_id=self.channel_message_id,
            published_at_utc=self.published_at_utc,
            scheduler_job_id=self.scheduler_job_id,
            services=services,
        )

    @staticmethod
    def _update_model(model: "PublicationModel", pub: "Publication") -> None:
        model.status = pub.status
        model.slot_day = pub.slot.local_day if pub.slot else None
        model.slot_time = pub.slot.local_time if pub.slot else None
        model.publish_at_utc = pub.publish_at_utc
        model.scheduler_job_id = pub.scheduler_job_id
        model.channel_message_id = pub.channel_message_id
        model.published_at_utc = pub.published_at_utc

        # синхронизируем services
        existing = {s.id: s for s in (model.services or [])}
        new_services = []
        for svc in pub.services:
            if svc.id and svc.id in existing:
                # обновляем существующую
                existing[svc.id].status = svc.status
                existing[svc.id].params = svc.params
                new_services.append(existing[svc.id])
            else:
                # добавляем новую
                new_services.append(
                    PublicationServiceModel(
                        type=svc.type,
                        status=svc.status,
                        params=svc.params or {},
                    )
                )
        model.services = new_services
