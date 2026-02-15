from datetime import datetime
from typing import Protocol


class Scheduler(Protocol):
    async def schedule_publication(
        self,
        *,
        publication_id: int,
        run_at_utc: datetime,
    ) -> None:
        """Поставить задачу на публикацию."""
        ...

    async def cancel_publication(
        self,
        *,
        publication_id: int,
    ) -> None:
        """Отменить задачу на публикацию."""
        ...

    async def schedule_publish_now(
        self,
        *,
        publication_id: int,
    ) -> None:
        """Поставить задачу на немедленную публикацию."""
        ...

    async def schedule_unpin(
        self,
        *,
        channel_id: int,
        message_id: int,
        run_at_utc: datetime,
    ) -> None: 
        """Поставить задачу на открепление сообщения."""
        ...
