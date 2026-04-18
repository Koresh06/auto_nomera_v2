from datetime import datetime
from typing import Protocol, Any


class TaskQueue(Protocol):
    async def enqueue(self, *, task_name: str, args: tuple[Any, ...]) -> str | None: ...

    async def schedule(
        self,
        *,
        task_name: str,
        args: tuple[Any, ...],
        run_at_utc: datetime,
    ) -> str | None: ...

    async def cancel(self, *, job_id: str) -> None: ...
