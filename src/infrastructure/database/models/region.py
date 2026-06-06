from dataclasses import asdict
from typing import TYPE_CHECKING
from datetime import time

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Integer, VARCHAR, Enum as SaEnum
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.entities.region import Region
from src.domain.enums.region import RegionStatus
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.timezone_name import TimezoneName

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
    

    @classmethod
    def from_entity(cls, region: "Region"):
        settings_dict = asdict(region.settings)
        settings_dict["slot_times"] = [
            t.strftime("%H:%M") for t in region.settings.slot_times
        ]
        return cls(
            title=region.title,
            timezone=region.timezone.value,
            channel_id=region.channel_id,
            channel_username=region.channel_username,
            status=region.status,
            settings=settings_dict,
            metadata_=asdict(region.metadata),
        )
    
    def to_entity(self) -> "Region":
        settings_data = dict(self.settings or {})
        settings_data["slot_times"] = tuple(
            time.fromisoformat(t) for t in settings_data.get("slot_times", [])
        )
        return Region(
            id=self.id,
            title=self.title,
            timezone=TimezoneName(self.timezone),
            channel_id=self.channel_id,
            channel_username=self.channel_username,
            status=self.status,
            settings=RegionSettings(**settings_data),
            metadata=RegionMetadata(**(self.metadata_ or {})),
        )