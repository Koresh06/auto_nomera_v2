from abc import ABC, abstractmethod
from typing import Any

class DialogTeleporter(ABC):
    @abstractmethod
    async def switch_to(
        self,
        *,
        user_id: int,
        chat_id: int,
        state_key: str,
        data: dict | None = None,
    ) -> None: ...

    @abstractmethod
    async def update(
        self,
        *,
        user_id: int,
        chat_id: int,
        data: dict,
    ) -> None: ...

    @abstractmethod
    async def done(
        self,
        *,
        user_id: int,
        chat_id: int,
    ) -> None: ...