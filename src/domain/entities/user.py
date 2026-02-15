from dataclasses import dataclass

from src.domain.entities.base import Entity
from src.domain.enums.user import UserRole
from src.domain.events.user import UserRegistered
from src.domain.exceptions.user import InvalidTelegramId, EmptyUsername
from src.utils.get_datetime_utc_now import get_datetime_utc_now


@dataclass(kw_only=True)
class User(Entity):
    tg_id: int
    username: str | None = None
    full_name: str | None = None
    role: UserRole = UserRole.USER
    is_blocked: bool = False

    @classmethod
    def register(cls, *, tg_id: int, username: str | None = None) -> "User":
        if tg_id <= 0:
            raise InvalidTelegramId("tg_id должен быть положительным.")

        if username is not None and not username.strip():
            raise EmptyUsername("Имя пользователя не может быть пустым.")

        user = cls(tg_id=tg_id, username=username)
        user.add_event(
            UserRegistered(
                occurred_at=get_datetime_utc_now(),
                user_id=user.id,
                tg_id=tg_id,
                username=username,
                full_name=user.full_name,
            )
        )
        return user

    def promote_to_admin(self) -> None:
        self.role = UserRole.ADMIN
        self.touch()

    def block(self) -> None:
        self.is_blocked = True
        self.touch()

    def unblock(self) -> None:
        self.is_blocked = False
        self.touch()


