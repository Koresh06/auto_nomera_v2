"""
Разовый скрипт: докатывает notify_pre_publication_users для уже существующих
SCHEDULED-публикаций (созданных до применения notify_scheduled-фикса —
включая AUTOPUBLISH-детей и родительские публикации), у которых publish_at_utc
ещё достаточно далеко в будущем, и в регионе которых есть активные подписчики
раннего доступа.

Запуск:
    docker compose exec -T bot python scripts/backfill_notify_scheduled.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from dishka import make_async_container
from sqlalchemy import select

from src.core.dependencies.providers import make_base_providers
from src.core.config import AppSettings
from src.application.ports.tasks.task_queue import TaskQueue
from src.infrastructure.database.models.publication import PublicationModel
from src.infrastructure.database.models.user import UserModel
from src.domain.enums.publication import PublicationStatus


async def main() -> None:
    container = make_async_container(*make_base_providers())
    try:
        async with container() as request_container:
            queue = await request_container.get(TaskQueue)
            settings = await request_container.get(AppSettings)
            window_hours = settings.app.pre_publication_window_hours

            from src.infrastructure.database.sqlalchemy.connection import (
                async_session_maker,
            )

            now = datetime.now(timezone.utc)
            min_publish_at = now + timedelta(hours=window_hours + 1)

            async with async_session_maker() as session:
                regions_q = await session.execute(
                    select(UserModel.region_id)
                    .where(UserModel.pre_publication_expires_at > now)
                    .distinct()
                )
                active_regions = {row[0] for row in regions_q.all()}

                if not active_regions:
                    print("Нет регионов с активными подписчиками — нечего докатывать")
                    return

                print(f"Регионы с активными подписчиками: {sorted(active_regions)}")

                pubs_q = await session.execute(
                    select(
                        PublicationModel.id,
                        PublicationModel.ad_id,
                        PublicationModel.publish_at_utc,
                    ).where(
                        PublicationModel.status == PublicationStatus.SCHEDULED,
                        PublicationModel.notify_scheduled.is_(False),
                        PublicationModel.publish_at_utc >= min_publish_at,
                        PublicationModel.region_id.in_(active_regions),
                    )
                )
                rows = pubs_q.all()

                print(f"Найдено {len(rows)} публикаций для докатки уведомлений")

                scheduled_count = 0
                for pub_id, ad_id, publish_at_utc in rows:
                    notify_at = publish_at_utc - timedelta(hours=window_hours)
                    if notify_at <= now:
                        continue

                    await queue.schedule(
                        task_name="notify_pre_publication_users",
                        args=(ad_id,),
                        run_at_utc=notify_at,
                    )

                    model = await session.get(PublicationModel, pub_id)
                    model.notify_scheduled = True
                    scheduled_count += 1

                    print(f"  pub_id={pub_id} ad_id={ad_id} notify_at={notify_at}")

                await session.commit()
                print(f"Готово. Поставлено {scheduled_count} уведомлений.")
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
