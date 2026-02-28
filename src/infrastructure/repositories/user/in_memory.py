from src.domain.entities.user import User
from src.application.ports.user.user_repo import UserRepository
from src.infrastructure.repositories.utils import _AutoId


class InMemoryUserRepo(UserRepository):
    def __init__(self) -> None:
        self._ids = _AutoId()
        self._items: dict[int, User] = {}
        self._by_tg: dict[int, int] = {}

    async def add(self, user: User) -> None:
        user.id = self._ids.next()
        self._items[user.id] = user
        self._by_tg[user.tg_id] = user.id
        print(self._items)

    async def get_by_id(self, user_id: int) -> User | None:
        return self._items.get(user_id)

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        user_id = self._by_tg.get(tg_id)
        return None if user_id is None else self._items[user_id]