"""
Разовое восстановление закрепа для В040ОН23 (pub 12123, message 2946, регион 2):
закрепить сейчас + снятие через 7 дней. Компенсация некорректной длительности
(24ч вместо 7 дней из-за бага params при оплате через YooKassa).

Запуск:
    docker compose exec -e PYTHONPATH=/app worker python scripts/manual_pin_v040.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from dishka import make_async_container
from src.core.dependencies.providers import make_base_providers
from src.application.ports.tasks.task_queue import TaskQueue

CHANNEL_ID = -1002371527987
MESSAGE_ID = 2946


async def main() -> int:
    container = make_async_container(*make_base_providers())

    from src.infrastructure.broker.instance import broker
    from src.infrastructure.broker.taskiq import register_taskiq_tasks

    register_taskiq_tasks(broker, container=container)

    try:
        async with container() as rc:
            queue = await rc.get(TaskQueue)
            unpin_at = datetime.now(timezone.utc) + timedelta(days=7)
            job_id = await queue.schedule(
                task_name="unpin_message",
                args=(CHANNEL_ID, MESSAGE_ID),
                run_at_utc=unpin_at,
            )
            print(f"unpin scheduled: job={job_id} at={unpin_at}")
    finally:
        await container.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
