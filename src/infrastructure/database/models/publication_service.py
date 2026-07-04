from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer,
    Enum as SaEnum,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


if TYPE_CHECKING:
    from src.infrastructure.database.models import PublicationModel


class PublicationServiceModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "publication_services"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    publication_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "publications.id",
            ondelete="CASCADE",
        ),
    )
    type: Mapped[PublicationServiceType] = mapped_column(SaEnum(PublicationServiceType))
    status: Mapped[PublicationServiceStatus] = mapped_column(
        SaEnum(PublicationServiceStatus)
    )
    price_paid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    params: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
    )

    publication_rel: Mapped["PublicationModel"] = relationship(
        "PublicationModel",
        back_populates="services",
    )

    def __repr__(self) -> str:
        return f"PublicationServiceModel(id={self.id}, type={self.type}, status={self.status})"
