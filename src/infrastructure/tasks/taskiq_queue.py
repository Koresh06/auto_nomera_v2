import uuid
from datetime import datetime
from typing import Any

from taskiq_redis import RedisScheduleSource

from src.application.ports.tasks.task_queue import TaskQueue


class TaskiqTaskQueue(TaskQueue):
    def __init__(self, broker, schedule_source: RedisScheduleSource) -> None:
        self._broker = broker
        self._schedule_source = schedule_source

    def _get_task(self, task_name: str):
        all_tasks = self._broker.get_all_tasks()
        for full_name, task in all_tasks.items():
            if full_name.endswith(f":{task_name}"):
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
        job = await task.kicker().with_schedule_id(
            str(uuid.uuid4())
        ).schedule_by_time(self._schedule_source, run_at_utc, *args)
        return getattr(job, "task_id", None) or getattr(job, "schedule_id", None)

    async def cancel(self, *, job_id: str) -> None:
        result_backend = getattr(self._broker, "result_backend", None)
        if result_backend and hasattr(result_backend, "abort"):
            await result_backend.abort(job_id)