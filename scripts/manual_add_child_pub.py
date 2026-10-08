"""
Универсальное досоздание дочерних публикаций серии автопубликации.

Запуск (dry по умолчанию):
    docker compose exec -e PYTHONPATH=/app worker python scripts/manual_add_child_pub.py \
        --ad-id 401 --region-id 12 --time 14:00 --dates 2026-08-22
    ... --apply  # применить

Несколько дат: --dates 2026-08-26 2026-08-27
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from dishka import make_async_container

from src.core.dependencies.providers import make_base_providers
from src.application.ports.tasks.task_queue import TaskQueue
from src.infrastructure.database.models.publication import PublicationModel
from src.infrastructure.database.sqlalchemy.connection import async_session_maker
from src.domain.enums.publication import PublicationStatus


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pub-ids", type=int, nargs="+", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    container = make_async_container(*make_base_providers())
    from src.infrastructure.broker.instance import broker
    from src.infrastructure.broker.taskiq import register_taskiq_tasks

    register_taskiq_tasks(broker, container=container)

    try:
        async with container() as rc:
            queue = await rc.get(TaskQueue)
            async with async_session_maker() as session:
                for pid in args.pub_ids:
                    model = await session.get(PublicationModel, pid)
                    if model is None or model.status != PublicationStatus.SCHEDULED:
                        print(f"[SKIP] {pid}: нет или статус не SCHEDULED")
                        continue
                    if model.scheduler_job_id:
                        print(f"[SKIP] {pid}: job уже есть {model.scheduler_job_id}")
                        continue
                    run_at = datetime.now(timezone.utc) + timedelta(seconds=15)
                    print(
                        f"[{'CREATE' if args.apply else 'DRY'}] pub={pid} run_at={run_at}"
                    )
                    if not args.apply:
                        continue
                    model.publish_at_utc = run_at
                    job_id = await queue.schedule(
                        task_name="publish_publication",
                        args=(pid,),
                        run_at_utc=run_at,
                    )
                    model.scheduler_job_id = job_id
                    await session.commit()
                    print(f"  job={job_id}")
    finally:
        await container.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
