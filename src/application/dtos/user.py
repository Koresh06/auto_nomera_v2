from dataclasses import dataclass

from src.domain.entities.user import UserRole


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: int
    tg_id: int
    username: str | None
    full_name: str | None
    role: UserRole
    is_blocked: bool
