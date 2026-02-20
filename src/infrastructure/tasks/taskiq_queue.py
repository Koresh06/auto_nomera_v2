from datetime import datetime
from typing import Any

from src.application.ports.tasks.task_queue import TaskQueue


class TaskiqTaskQueue(TaskQueue):
    def __init__(self, broker) -> None:
        self._broker = broker

    async def enqueue(self, *, task_name: str, args: tuple[Any, ...]) -> str | None:
        # отправка задачи по имени (имя задаёшь в @broker.task(name="..."))
        if hasattr(self._broker, "kick"):
            job = await self._broker.kick(task_name, *args)
            return getattr(job, "task_id", None) or getattr(job, "id", None)

        # fallback: если kick нет, попробуем через реестр задач (зависит от taskiq версии)
        task = getattr(self._broker, "task_registry", {}).get(task_name) if hasattr(self._broker, "task_registry") else None
        if task is None:
            raise RuntimeError(f"Task '{task_name}' not found and broker has no kick().")
        job = await task.kiq(*args)
        return getattr(job, "task_id", None) or getattr(job, "id", None)

    async def schedule(self, *, task_name: str, args: tuple[Any, ...], run_at_utc: datetime) -> str | None:
        # если у брокера есть планирование по времени
        if hasattr(self._broker, "kick_by_time"):
            job = await self._broker.kick_by_time(run_at_utc, task_name, *args)
            return getattr(job, "task_id", None) or getattr(job, "id", None)

        # иначе — планирование делай НЕ в taskiq, а своим планировщиком (apscheduler/redis), а тут только enqueue
        return await self.enqueue(task_name=task_name, args=args)

    async def cancel(self, *, job_id: str) -> None:
        if hasattr(self._broker, "cancel"):
            await self._broker.cancel(job_id)
        elif hasattr(self._broker, "revoke"):
            await self._broker.revoke(job_id)
        # иначе no-op