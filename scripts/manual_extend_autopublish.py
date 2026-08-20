"""
Разовое доcоздание 2 дочерних публикаций серии автопубликации О777СК193
(ad_id=11790, регион 2, слот-время 18:00) на 26.08 и 27.08 —
компенсация старой логики отсчёта серии (началась с 21.08 вместо 13.08).

Запуск (сначала dry, потом --apply):
    docker compose exec -e PYTHONPATH=/app worker python scripts/manual_extend_autopublish.py
    docker compose exec -e PYTHONPATH=/app worker python scripts/manual_extend_autopublish.py --apply
"""

import argparse
import asyncio
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from dishka import make_async_container
from src.core.dependencies.providers import make_base_providers
from src.application.ports.tasks.task_queue import TaskQueue
from src.infrastructure.database.models.publication import PublicationModel
from src.infrastructure.database.sqlalchemy.connection import async_session_maker
from src.domain.enums.publication import PublicationStatus

AD_ID = 11790
REGION_ID = 2
SLOT_TIME = time(18, 0)
TZ = ZoneInfo("Europe/Moscow")
DAYS = [date(2026, 8, 26), date(2026, 8, 27)]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry = not args.apply

    container = make_async_container(*make_base_providers())
    try:
        async with container() as rc:
            queue = await rc.get(TaskQueue)

            async with async_session_maker() as session:
                for d in DAYS:
                    publish_at_utc = datetime.combine(d, SLOT_TIME, TZ).astimezone(
                        timezone.utc
                    )
                    print(
                        f"[{'DRY' if dry else 'CREATE'}] {d} {SLOT_TIME} -> publish_at={publish_at_utc}"
                    )
                    if dry:
                        continue

                    model = PublicationModel(
                        ad_id=AD_ID,
                        region_id=REGION_ID,
                        status=PublicationStatus.SCHEDULED,
                        slot_day=d,
                        slot_time=SLOT_TIME,
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
