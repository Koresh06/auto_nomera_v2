from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.domain.entities.user import User
from src.domain.enums.role import UserRole


@dataclass(frozen=True)
class UserDTO:
    id: int
    tg_id: int
    full_name: str | None
    username: str | None
    role: UserRole
    phone: str | None
    region_id: int
    balance: Decimal
    is_blocked: bool
    pre_publication_expires_at: datetime | None

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id,
            tg_id=user.tg_id,
            full_name=user.full_name,
            username=user.username,
            role=user.role,
            phone=user.phone,
            region_id=user.region_id,
            balance=user.balance,
            is_blocked=user.is_blocked,
            pre_publication_expires_at=user.pre_publication_expires_at,
        )


@dataclass(frozen=True)
class UpdateUserDTO:
    region_id: int | None = None
    username: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    phone: str | None = None
    balance: Decimal | None = None
    is_blocked: bool | None = None
    pre_publication_expires_at: datetime | None = None