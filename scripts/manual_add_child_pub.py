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
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

from dishka import make_async_container
from sqlalchemy import select

from src.core.dependencies.providers import make_base_providers
from src.application.ports.tasks.task_queue import TaskQueue
from src.infrastructure.database.models.publication import PublicationModel
from src.infrastructure.database.models.region import RegionModel
from src.infrastructure.database.sqlalchemy.connection import async_session_maker
from src.domain.enums.publication import PublicationStatus


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ad-id", type=int, required=True)
    parser.add_argument("--region-id", type=int, required=True)
    parser.add_argument("--time", required=True, help="HH:MM local")
    parser.add_argument("--dates", nargs="+", required=True, help="YYYY-MM-DD ...")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry = not args.apply

    slot_time = dtime.fromisoformat(args.time)

    container = make_async_container(*make_base_providers())
    from src.infrastructure.broker.instance import broker
    from src.infrastructure.broker.taskiq import register_taskiq_tasks

    register_taskiq_tasks(broker, container=container)

    try:
        async with container() as rc:
            queue = await rc.get(TaskQueue)
            async with async_session_maker() as session:
                region = await session.get(RegionModel, args.region_id)
                tz = ZoneInfo(
                    region.timezone.value
                    if hasattr(region.timezone, "value")
                    else region.timezone
                )

                for d_raw in args.dates:
                    d = datetime.fromisoformat(d_raw).date()
                    publish_at_utc = datetime.combine(d, slot_time, tz).astimezone(
                        timezone.utc
                    )

                    # защита от дубля: уже есть публикация этого ad на этот день?
                    existing = (
                        await session.execute(
                            select(PublicationModel.id).where(
                                PublicationModel.ad_id == args.ad_id,
                                PublicationModel.slot_day == d,
                                PublicationModel.status.in_(
                                    [
                                        PublicationStatus.SCHEDULED,
                                        PublicationStatus.PUBLISHED,
                                    ]
                                ),
                            )
                        )
                    ).scalar_one_or_none()
                    if existing:
                        print(f"[SKIP] {d}: уже есть публикация id={existing}")
                        continue

                    print(
                        f"[{'DRY' if dry else 'CREATE'}] {d} {slot_time} -> {publish_at_utc}"
                    )
                    if dry:
                        continue

                    model = PublicationModel(
                        ad_id=args.ad_id,
                        region_id=args.region_id,
                        status=PublicationStatus.SCHEDULED,
                        slot_day=d,
                        slot_time=slot_time,
                        publish_at_utc=publish_at_utc,
                        is_child=True,
                    )
                    session.add(model)
                    await session.flush()

                    job_id = await queue.schedule(
                        task_name="publish_publication",
                        args=(model.id,),
                        run_at_utc=publish_at_utc,
                    )
                    model.scheduler_job_id = job_id
                    print(f"  pub_id={model.id} job={job_id}")

                if not dry:
                    await session.commit()
    finally:
        await container.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
