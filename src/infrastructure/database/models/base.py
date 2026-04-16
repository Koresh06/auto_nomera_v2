from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import MetaData, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs

from src.utils.get_datetime_utc_now import get_datetime_utc_now


convention: Mapping[str, str] = {
    "ix": "ix__%(column_0_label)s",
    "uq": "uq__%(table_name)s__%(column_0_name)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "pk__%(table_name)s",
}
meta = MetaData(naming_convention=convention)


class BaseModel(AsyncAttrs, DeclarativeBase):
    metadata = meta


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=get_datetime_utc_now,
        server_default=func.now(),
    )
 
 
class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),   
        default=get_datetime_utc_now,
        onupdate=get_datetime_utc_now,
        server_default=func.now(),
    )