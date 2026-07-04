from abc import ABC, abstractmethod


class DialogTeleporter(ABC):
    @abstractmethod
    async def start(
        self,
        *,
        user_id: int,
        chat_id: int,
        state_key: str,
        data: dict | None = None,
    ) -> None: ...
