from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Boolean, Enum as SaEnum, String, VARCHAR
from sqlalchemy.dialects.postgresql import JSONB

from src.domain.entities.service_definition import ServiceDefinition
from src.domain.enums.publication_service import PublicationServiceType

from .base import BaseModel, CreatedAtMixin, UpdatedAtMixin


class ServiceDefinitionModel(BaseModel, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "service_definitions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(VARCHAR(128))
    type: Mapped[PublicationServiceType] = mapped_column(
        SaEnum(PublicationServiceType),
        unique=True,
    )
    price: Mapped[int] = mapped_column(Integer)  # в копейках/рублях
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    params_schema: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"ServiceDefinitionModel(type={self.type}, price={self.price}, active={self.is_active})"
    
    @classmethod
    def from_entity(cls, service: "ServiceDefinition") -> "ServiceDefinitionModel":
        return cls(
            title=service.title,
            type=service.type,
            price=service.price,
            duration_days=service.duration_days,
            description=service.description,
            is_active=service.is_active,
            params_schema=service.params_schema,
        )
    
    def to_entity(self) -> "ServiceDefinition":
        return ServiceDefinition(
            id=self.id,
            title=self.title,
            type=self.type,
            price=self.price,
            duration_days=self.duration_days,
            description=self.description,
            is_active=self.is_active,
            params_schema=self.params_schema,
        )