from typing import Protocol

from src.domain.entities.user import User


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_id(self, user_id: int) -> User | None: ...

    async def get_by_tg_id(self, tg_id: int) -> User | None: ...
