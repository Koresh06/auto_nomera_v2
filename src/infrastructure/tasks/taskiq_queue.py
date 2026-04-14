from datetime import datetime
from typing import Any

from src.application.ports.tasks.task_queue import TaskQueue


class TaskiqTaskQueue(TaskQueue):
    def __init__(self, broker) -> None:
        self._broker = broker

    def _get_task(self, task_name: str):
        registry = getattr(self._broker, "state", None)
        if registry:
            tasks = getattr(registry, "tasks", {})
            task = tasks.get(task_name)
            if task:
                return task
        raise RuntimeError(f"Task '{task_name}' not found in broker registry.")

    async def enqueue(self, *, task_name: str, args: tuple[Any, ...]) -> str | None:
        task = self._get_task(task_name)
        job = await task.kiq(*args)
        return getattr(job, "task_id", None)

    async def schedule(
        self, *, task_name: str, args: tuple[Any, ...], run_at_utc: datetime
    ) -> str | None:
        task = self._get_task(task_name)
        job = await task.kiq.with_labels(eta=run_at_utc)(*args)
        return getattr(job, "task_id", None)

    async def cancel(self, *, job_id: str) -> None:
        result_backend = getattr(self._broker, "result_backend", None)
        if result_backend and hasattr(result_backend, "abort"):
            await result_backend.abort(job_id)