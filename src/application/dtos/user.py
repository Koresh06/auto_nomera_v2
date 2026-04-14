from dataclasses import dataclass

from src.domain.entities.user import User
from src.domain.enums.user import UserRole


@dataclass(frozen=True, slots=True)
class BaseUserDTO:
    username: str | None
    full_name: str | None
    phone: str | None
    region_id: int


@dataclass(frozen=True, slots=True)
class UserDTO(BaseUserDTO):
    id: int
    tg_id: int
    role: UserRole
    is_blocked: bool

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id,
            tg_id=user.tg_id,
            region_id=user.region_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            phone=user.phone,
            is_blocked=user.is_blocked,
        )


@dataclass(frozen=True, slots=True)
class UpdateUserDTO(BaseUserDTO):
    region_id: int | None = None
    username: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    phone: str | None = None
    is_blocked: bool | None = None