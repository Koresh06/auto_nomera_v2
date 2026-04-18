from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Boolean, Enum as SaEnum, String, VARCHAR
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.enums.publication_service import PublicationServiceType

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


class ServiceDefinitionModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "service_definitions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    type: Mapped[PublicationServiceType] = mapped_column(
        SaEnum(PublicationServiceType),
        unique=True,
    )
    title: Mapped[str] = mapped_column(VARCHAR(128))
    price: Mapped[int] = mapped_column(Integer)  # в копейках/рублях
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )
    params_schema: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"ServiceDefinitionModel(type={self.type}, price={self.price}, active={self.is_active})"
