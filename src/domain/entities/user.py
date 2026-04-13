from dataclasses import dataclass

from src.domain.entities.base import Entity
from src.domain.enums.user import UserRole
from src.domain.exceptions.user import InvalidTelegramId, EmptyUsername


@dataclass(kw_only=True)
class User(Entity):
    tg_id: int
    username: str | None = None
    full_name: str | None = None
    role: UserRole = UserRole.USER
    phone: str | None
    region_id: int
    is_blocked: bool = False

    @classmethod
    def register(
        cls,
        *,
        tg_id: int,
        region_id: int,
        username: str | None = None,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> "User":
        if tg_id <= 0:
            raise InvalidTelegramId(tg_id)

        if username is not None and not username.strip():
            raise EmptyUsername()

        user = cls(
            tg_id=tg_id,
            username=username,
            full_name=full_name,
            phone=phone,
            region_id=region_id,
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

    def change_region(self, region_id: int) -> None:
        self.region_id = region_id
        self.touch()
