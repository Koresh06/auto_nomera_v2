from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class UserRegistered(DomainEvent):
    user_id: int
    tg_id: int
    username: str | None
    full_name: str | None
