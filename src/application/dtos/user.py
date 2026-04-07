from dataclasses import dataclass

from src.domain.entities.user import User, UserRole


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: int
    tg_id: int
    region_id: int
    username: str | None
    full_name: str | None
    role: UserRole
    is_blocked: bool

    @classmethod
    def from_orm(cls, user: User) -> "UserDTO":
        return cls(
            id=user.id,
            tg_id=user.tg_id,
            region_id=user.region_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_blocked=user.is_blocked,
        )
