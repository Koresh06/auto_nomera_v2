"""
Полная сверка: сколько publish/notify задач ДОЛЖНО быть по данным БД,
и сколько их реально в Redis (schedule:*).

ЗАПУСК (read-only, ничего не меняет):
    docker compose exec -e PYTHONPATH=/app worker python scripts/full_crosscheck.py
"""

from __future__ import annotations

import asyncio
import pickle
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from sqlalchemy import select

from src.core.config import AppSettings, settings
from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.models.publication import PublicationModel
from src.infrastructure.database.sqlalchemy.connection import async_session_maker
from dishka import make_async_container
from src.core.dependencies.providers import make_base_providers


async def main() -> int:
    redis = aioredis.from_url(settings.db.redis.taskiq_url)
    container = make_async_container(*make_base_providers())

    try:
        async with container() as rc:
            app_settings = await rc.get(AppSettings)
            window_hours = app_settings.app.pre_publication_window_hours

        now = datetime.now(timezone.utc)

        # ---------- 1. Собираем факты из БД ----------
        async with async_session_maker() as session:
            rows = (
                await session.execute(
                    select(
                        PublicationModel.id,
                        PublicationModel.ad_id,
                        PublicationModel.publish_at_utc,
                        PublicationModel.scheduler_job_id,
                        PublicationModel.notify_scheduled,
                    ).where(
                        PublicationModel.status == PublicationStatus.SCHEDULED,
                    )
                )
            ).all()

        db_pub_ids = {r.id for r in rows if r.publish_at_utc and r.publish_at_utc > now}
        db_pub_ids_no_job = {
            r.id
            for r in rows
            if r.publish_at_utc and r.publish_at_utc > now and not r.scheduler_job_id
        }

        expected_notify_count = 0
        for r in rows:
            if not r.publish_at_utc or r.publish_at_utc <= now:
                continue
            notify_at = r.publish_at_utc - timedelta(hours=window_hours)
            if r.notify_scheduled and notify_at > now:
                expected_notify_count += 1

        print(f"БД: SCHEDULED с publish_at в будущем: {len(db_pub_ids)}")
        print(f"БД: из них без scheduler_job_id (MISSING): {len(db_pub_ids_no_job)}")
        print(
            f"БД: ожидается notify-задач (notify_scheduled=True и notify_at ещё впереди): {expected_notify_count}\n"
        )

        # ---------- 2. Собираем факты из Redis ----------
        redis_publish_pub_ids: dict[int, list[str]] = defaultdict(list)
        redis_notify_ad_ids: dict[int, list[str]] = defaultdict(list)
        other_tasks = 0
        total_keys = 0

        async for key in redis.scan_iter(match="schedule:*"):
            total_keys += 1
            raw = await redis.get(key)
            if raw is None:
                continue
            try:
                data = pickle.loads(raw)
            except Exception:
                continue

            task_name = data.get("task_name", "")
            args = tuple(data.get("args") or ())
            schedule_id = str(data.get("schedule_id"))

            if task_name.endswith(":publish_publication") and args:
                redis_publish_pub_ids[int(args[0])].append(schedule_id)
            elif task_name.endswith(":notify_pre_publication_users") and args:
                redis_notify_ad_ids[int(args[0])].append(schedule_id)
            else:
                other_tasks += 1

        print(f"Redis: всего ключей schedule:*: {total_keys}")
        print(
            f"Redis: уникальных publication_id с publish-задачей: {len(redis_publish_pub_ids)}"
        )
        print(
            f"Redis: всего publish-задач (с дублями): {sum(len(v) for v in redis_publish_pub_ids.values())}"
        )
        print(
            f"Redis: всего notify-задач: {sum(len(v) for v in redis_notify_ad_ids.values())}"
        )
        print(f"Redis: прочих задач (draft_reminder и т.п.): {other_tasks}\n")

        # ---------- 3. Сверка publish ----------
        redis_pub_id_set = set(redis_publish_pub_ids.keys())
        missing_in_redis = db_pub_ids - redis_pub_id_set
        extra_in_redis = redis_pub_id_set - db_pub_ids
        dupes_in_redis = {
            pid: jobs for pid, jobs in redis_publish_pub_ids.items() if len(jobs) > 1
        }

        print("=== PUBLISH: сверка БД <-> Redis ===")
        if missing_in_redis:
            print(
                f"  [!] В БД SCHEDULED, но НЕТ publish-задачи в Redis ({len(missing_in_redis)}):"
            )
            for pid in sorted(missing_in_redis):
                print(f"      pub_id={pid}")
        else:
            print(
                "  OK: у каждой будущей SCHEDULED публикации есть publish-задача в Redis."
            )

        if extra_in_redis:
            print(
                f"  [i] Publish-задачи в Redis без соответствующей будущей SCHEDULED в БД ({len(extra_in_redis)}) — "
                f"вероятно уже опубликованы/отменены, задача не была снята:"
            )
            for pid in sorted(extra_in_redis):
                print(f"      pub_id={pid}")

        if dupes_in_redis:
            print(
                f"  [i] Publish-задач с дублями (2+ job на одну pub_id) — безвредно, status-guard спасёт: {len(dupes_in_redis)}"
            )

        # ---------- 4. Сверка notify ----------
        actual_notify_count = sum(len(v) for v in redis_notify_ad_ids.values())
        print("\n=== NOTIFY: сверка БД <-> Redis ===")
        print(f"  Ожидается по БД: {expected_notify_count}")
        print(f"  Реально в Redis: {actual_notify_count}")
        diff = actual_notify_count - expected_notify_count
        if diff == 0:
            print("  OK: числа совпадают.")
        else:
            print(
                f"  [!] Расхождение: {diff:+d} — либо остались дубли, либо часть уже прошла notify_at "
                f"и taskiq вот-вот/уже их исполнил (естественный дрейф)."
            )

    finally:
        await redis.aclose()
        await container.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
