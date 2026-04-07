from abc import ABC
from uuid import UUID
from dataclasses import dataclass, field
from datetime import datetime

# from src.utils.uuid_v7 import uuid7
from src.utils.get_datetime_utc_now import get_datetime_utc_now


@dataclass(kw_only=True)
class Entity(ABC):
    id: int = field(default_factory=int)
    created_at: datetime = field(default_factory=get_datetime_utc_now)
    updated_at: datetime = field(default_factory=get_datetime_utc_now)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Entity) and self.id == other.id and self.id != 0

    def __hash__(self) -> int:
        return hash(self.id)

    def touch(self) -> None:
        self.updated_at = get_datetime_utc_now()
