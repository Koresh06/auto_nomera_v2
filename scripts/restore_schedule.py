"""
Восстановление taskiq-задач публикаций и уведомлений из БД в Redis.

КОГДА НУЖЕН:
  - после пересоздания redis-контейнера (деплой, где у redis появился/сменился
    том — новый том стартует ПУСТЫМ, задачи надо залить из БД заново);
  - после любой потери schedule:* ключей из Redis (рестарт без персистентности).

ЧТО ДЕЛАЕТ:
  Источник правды — БД (publish_at_utc у SCHEDULED публикаций).
  1. Берёт все будущие SCHEDULED публикации.
  2. Для каждой проверяет, есть ли её publish-задача в Redis (по scheduler_job_id).
     Если НЕТ — ставит publish_publication на publish_at_utc и сохраняет новый job_id.
  3. Для notify: считает notify_at = publish_at_utc - window_hours; если ещё в
     будущем — ставит notify_pre_publication_users.

ИДЕМПОТЕНТНОСТЬ:
  - publish: проверяет EXISTS перед постановкой — повторный запуск НЕ плодит дубли.
  - notify: job_id уведомлений нигде не хранится, проверить наличие нельзя.
    Повторный запуск МОЖЕТ поставить notify повторно (придёт дважды). Поэтому
    notify-часть запускать ОДИН раз. publish-часть повторять безопасно.

ЗАПУСК (через exec, НЕ run --rm — чтобы не передёргивать redis/db):
    docker compose exec worker python scripts/restore_schedule.py            # dry-run
    docker compose exec worker python scripts/restore_schedule.py --apply    # боевой
    docker compose exec worker python scripts/restore_schedule.py --apply --no-notify  # только publish (повторный прогон)

ПРОВЕРКА ПОСЛЕ:
    docker compose exec worker python scripts/restore_schedule.py            # снова dry: MISSING должно быть 0
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from dishka import make_async_container
from sqlalchemy import select

from src.application.ports.tasks.task_queue import TaskQueue
from src.core.config import AppSettings, settings
from src.core.dependencies.providers import make_base_providers
from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.models.publication import PublicationModel
from src.infrastructure.database.sqlalchemy.connection import async_session_maker


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="применить (по умолчанию — dry-run)"
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="не ставить notify (для повторного прогона без дублей уведомлений)",
    )
    args = parser.parse_args()
    dry = not args.apply

    redis = aioredis.from_url(settings.db.redis.taskiq_url)

    container = make_async_container(*make_base_providers())

    from src.infrastructure.broker.instance import broker
    from src.infrastructure.broker.taskiq import register_taskiq_tasks

    register_taskiq_tasks(broker, container=container)

    print(
        f"{'СУХОЙ ПРОГОН' if dry else 'ВОССТАНОВЛЕНИЕ'}"
        f"{' (без notify)' if args.no_notify else ''}\n"
    )

    restored_pub = 0
    ok_pub = 0
    set_notify = 0

    try:
        async with container() as rc:
            queue = await rc.get(TaskQueue)
            app_settings = await rc.get(AppSettings)
            window_hours = app_settings.app.pre_publication_window_hours

            now = datetime.now(timezone.utc)

            async with async_session_maker() as session:
                rows = (
                    await session.execute(
                        select(
                            PublicationModel.id,
                            PublicationModel.ad_id,
                            PublicationModel.publish_at_utc,
                            PublicationModel.scheduler_job_id,
                        ).where(
                            PublicationModel.status == PublicationStatus.SCHEDULED,
                            PublicationModel.publish_at_utc > now,
                        )
                    )
                ).all()

                print(f"Будущих SCHEDULED публикаций в БД: {len(rows)}\n")

                for pub_id, ad_id, publish_at_utc, job_id in rows:
                    exists = False
                    if job_id:
                        exists = bool(await redis.exists(f"schedule:{job_id}"))

                    if not exists:
                        print(
                            f"  [publish] pub={pub_id} ad={ad_id} "
                            f"at={publish_at_utc} — ОТСУТСТВУЕТ, ставим"
                        )
                        if not dry:
                            new_job = await queue.schedule(
                                task_name="publish_publication",
                                args=(pub_id,),
                                run_at_utc=publish_at_utc,
                            )
                            if new_job:
                                await session.execute(
                                    PublicationModel.__table__.update()
                                    .where(PublicationModel.id == pub_id)
                                    .values(scheduler_job_id=new_job)
                                )
                                await session.commit()
                        restored_pub += 1
                    else:
                        ok_pub += 1

                    if not args.no_notify:
                        notify_at = publish_at_utc - timedelta(hours=window_hours)
                        if notify_at > now:
                            if not dry:
                                await queue.schedule(
                                    task_name="notify_pre_publication_users",
                                    args=(ad_id,),
                                    run_at_utc=notify_at,
                                )
                            set_notify += 1

        print(
            f"\n{'[ПЛАН]' if dry else '[ГОТОВО]'} "
            f"publish восстановлено: {restored_pub}, уже было: {ok_pub}"
            f"{'' if args.no_notify else f', notify поставлено: {set_notify}'}"
        )
        if dry:
            print(
                "\nЭто сухой прогон, ничего не изменено. "
                "Для применения запусти с --apply"
            )
    finally:
        await redis.aclose()
        await container.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
