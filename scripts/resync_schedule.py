"""
Ресинхронизация отложенных публикаций из старого Redis (APScheduler)
в новую систему (Publication + taskiq).

Читает aps_run_times из старого Redis, для каждой будущей задачи публикации
создаёт Publication(SCHEDULED) и ставит задачу publish_publication в новый
taskiq на то же время.

Запуск (после того как отработал ETL и подняты новый db/redis):

    docker compose run --rm \
      -v ~/auto_nomera_v2/scripts:/app/scripts \
      -e PYTHONPATH=/app \
      -e LEGACY_DSN="postgresql://my_user:12345@legacy_db:5432/auto_db" \
      -e LEGACY_REDIS="redis://legacy_redis:6379/2" \
      bot python scripts/resync_schedule.py --dry-run

Переносим:
    publish_ad_{old}        -> Publication(SCHEDULED) + задача
    publish_store_{old}     -> Publication(SCHEDULED) для Ad(STORE) + задача
    autopost_{old}_{date}   -> Publication(SCHEDULED, is_child=True) + задача
    store_autopost_{old}_.. -> то же для магазина

Пропускаем (логика переехала / пересоздаётся кодом):
    early_access_*, unpin_*, remove_service_*, publish_reminder_*,
    apply_services_store_*
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, time, timezone

import redis.asyncio as aioredis
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import settings
from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.models import PublicationModel

APS_ZSET = "aps_run_times"

# какие префиксы переносим
PUB_PREFIXES = ("publish_ad_", "publish_store_")
AUTO_PREFIXES = ("autopost_", "store_autopost_")

SKIP_PREFIXES = (
    "early_access_",
    "unpin_",
    "remove_service_",
    "publish_reminder_",
    "apply_services_store_",
)


class Resyncer:
    def __init__(self, src_pool, redis_client, session, task_queue, dry_run):
        self.src = src_pool
        self.redis = redis_client
        self.dst = session
        self.queue = task_queue
        self.dry = dry_run

        self.counts: dict[str, int] = {}
        self.warnings: list[str] = []

        # старый ads.id -> новый ads.id
        self.ad_map: dict[int, int] = {}
        # старый ads.id -> (region_id, slot_day, slot_time) из slot_settings
        self.slot_info: dict[int, tuple[int, object, object]] = {}
        # старый ads.id -> ad_type
        self.ad_type: dict[int, str] = {}

    def add(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    # ------------------------------------------------------------------

    async def build_maps(self) -> None:
        """Строим маппинг старых ads.id -> новых по legacy_id и user_id (STORE)."""
        # 1. обычные объявления: legacy_id -> new id
        rows = await self.dst.execute(
            sa_text("SELECT id, legacy_id FROM ads WHERE legacy_id IS NOT NULL")
        )
        legacy_to_new: dict[int, int] = {}
        for new_id, legacy_id in rows.all():
            legacy_to_new[legacy_id] = new_id

        # 2. все старые объявления с типом и владельцем
        old_ads = await self.src.fetch(
            "SELECT id, user_id, ad_type, region_id FROM ads"
        )
        # новые STORE-объявления по владельцу
        store_new = await self.dst.execute(
            sa_text("SELECT id, user_id FROM ads WHERE ad_type = 'STORE'")
        )
        store_by_user: dict[int, int] = {}
        for new_id, user_id in store_new.all():
            store_by_user[user_id] = new_id

        for a in old_ads:
            self.ad_type[a["id"]] = a["ad_type"]
            if a["ad_type"] == "STORE":
                new_id = store_by_user.get(a["user_id"])
                if new_id:
                    self.ad_map[a["id"]] = new_id
            else:
                new_id = legacy_to_new.get(a["id"])
                if new_id:
                    self.ad_map[a["id"]] = new_id

        self.add("ad_map_built", len(self.ad_map))

        # 3. слоты старых объявлений
        slots = await self.src.fetch(
            'SELECT ad_id, region_id, _date, "time" FROM slot_settings '
            "WHERE ad_id IS NOT NULL"
        )
        for s in slots:
            t = self._parse_time(s["time"])
            if t:
                self.slot_info[s["ad_id"]] = (s["region_id"], s["_date"], t)

    # ------------------------------------------------------------------

    async def run(self) -> None:
        await self.build_maps()

        # читаем все задачи с временем
        raw = await self.redis.zrange(APS_ZSET, 0, -1, withscores=True)
        now_ts = datetime.now(timezone.utc).timestamp()

        for job_id_b, score in raw:
            job_id = job_id_b.decode() if isinstance(job_id_b, bytes) else job_id_b

            # только будущее
            if score <= now_ts:
                self.add("skipped_past")
                continue

            if any(job_id.startswith(p) for p in SKIP_PREFIXES):
                self.add("skipped_service")
                continue

            run_at = datetime.fromtimestamp(score, tz=timezone.utc)

            if job_id.startswith("publish_ad_"):
                await self._handle_publish(
                    job_id, "publish_ad_", run_at, is_child=False
                )
            elif job_id.startswith("publish_store_"):
                await self._handle_publish(
                    job_id, "publish_store_", run_at, is_child=False
                )
            elif job_id.startswith("store_autopost_"):
                await self._handle_autopost(job_id, "store_autopost_", run_at)
            elif job_id.startswith("autopost_"):
                await self._handle_autopost(job_id, "autopost_", run_at)
            else:
                self.add("skipped_unknown")
                self.warn(f"неизвестный ключ: {job_id}")

        await self.dst.flush()

    # ------------------------------------------------------------------

    async def _handle_publish(self, job_id, prefix, run_at, is_child):
        old_id = self._extract_id(job_id[len(prefix) :])
        if old_id is None:
            self.warn(f"{job_id}: не разобрал id")
            self.add("errors")
            return

        new_ad_id = self.ad_map.get(old_id)
        if new_ad_id is None:
            self.warn(f"{job_id}: ad {old_id} не найден в новой базе")
            self.add("skipped_no_ad")
            return

        await self._create_scheduled(old_id, new_ad_id, run_at, is_child)
        self.add(f"{prefix}created")

    async def _handle_autopost(self, job_id, prefix, run_at):
        # autopost_{id}_{date}  или  store_autopost_{id}_{date}
        rest = job_id[len(prefix) :]
        m = re.match(r"^(\d+)_(\d{4}-\d{2}-\d{2})$", rest)
        if not m:
            self.warn(f"{job_id}: не разобрал autopost")
            self.add("errors")
            return

        old_id = int(m.group(1))
        new_ad_id = self.ad_map.get(old_id)
        if new_ad_id is None:
            self.warn(f"{job_id}: ad {old_id} не найден")
            self.add("skipped_no_ad")
            return

        # autopost-даты — дочерние публикации серии
        await self._create_scheduled(old_id, new_ad_id, run_at, is_child=True)
        self.add(f"{prefix}created")

    async def _create_scheduled(self, old_id, new_ad_id, run_at, is_child):
        info = self.slot_info.get(old_id)
        # region_id: из slot_settings, иначе из нового объявления
        if info:
            _, slot_day, slot_time = info

        # регион берём у нового объявления (надёжнее)
        region_row = await self.dst.execute(
            sa_text("SELECT region_id FROM ads WHERE id = :id"),
            {"id": new_ad_id},
        )
        region_id = region_row.scalar_one()

        slot_day = slot_time = None
        if info:
            _, slot_day, slot_time = info
            # slot = SlotKey(
            #     region_id=region_id,
            #     local_day=slot_day,
            #     local_time=slot_time,
            # )

        if self.dry:
            return

        model = PublicationModel(
            ad_id=new_ad_id,
            region_id=region_id,
            status=PublicationStatus.SCHEDULED,
            slot_day=slot_day,
            slot_time=slot_time,
            publish_at_utc=run_at,
            is_child=is_child,
            created_at=datetime.now(timezone.utc),
        )
        self.dst.add(model)
        await self.dst.flush()

        # ставим задачу в новый taskiq
        job_id = await self.queue.schedule(
            task_name="publish_publication",
            args=(model.id,),
            run_at_utc=run_at,
        )
        if job_id:
            await self.dst.execute(
                sa_text("UPDATE publications SET scheduler_job_id = :j WHERE id = :i"),
                {"j": job_id, "i": model.id},
            )

    # ------------------------------------------------------------------

    @staticmethod
    def _extract_id(s: str) -> int | None:
        m = re.match(r"^(\d+)", s)
        return int(m.group(1)) if m else None

    @staticmethod
    def _parse_time(raw) -> time | None:
        if not raw:
            return None
        try:
            hh, mm = str(raw).split(":")
            return time(int(hh), int(mm))
        except (ValueError, AttributeError):
            return None

    def render(self) -> str:
        lines = ["", "=" * 54, "РЕСИНХРОНИЗАЦИЯ РАСПИСАНИЯ", "=" * 54]
        for k in sorted(self.counts):
            lines.append(f"  {k:<36} {self.counts[k]:>8}")
        if self.warnings:
            lines.append(f"\nПРЕДУПРЕЖДЕНИЯ ({len(self.warnings)}):")
            for w in self.warnings[:30]:
                lines.append(f"  ! {w}")
            if len(self.warnings) > 30:
                lines.append(f"  ... ещё {len(self.warnings) - 30}")
        lines.append("=" * 54)
        return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    legacy_dsn = os.getenv("LEGACY_DSN")
    legacy_redis = os.getenv("LEGACY_REDIS", "redis://legacy_redis:6379/2")
    if not legacy_dsn:
        print("LEGACY_DSN не задан", file=sys.stderr)
        return 1

    import asyncpg

    src = await asyncpg.connect(legacy_dsn)
    redis_client = aioredis.from_url(legacy_redis)
    engine = create_async_engine(settings.db.postgres.url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # taskiq queue — переиспользуем инфраструктуру проекта
    from dishka import make_async_container

    from src.application.ports.tasks.task_queue import TaskQueue
    from src.core.dependencies.providers import make_base_providers

    container = make_async_container(*make_base_providers())

    from src.infrastructure.broker.instance import broker
    from src.infrastructure.broker.taskiq import register_taskiq_tasks

    register_taskiq_tasks(broker, container=container)

    print(f"{'СУХОЙ ПРОГОН' if args.dry_run else 'РЕСИНХРОНИЗАЦИЯ'} начата...")

    try:
        async with session_factory() as session:
            async with container() as request_container:
                queue = await request_container.get(TaskQueue)
                r = Resyncer(src, redis_client, session, queue, args.dry_run)
                try:
                    await r.run()
                    if args.dry_run:
                        await session.rollback()
                        print("\n[dry-run] откачено")
                    else:
                        await session.commit()
                        print("\n[commit] сохранено")
                except Exception:
                    await session.rollback()
                    print(r.render())
                    raise
                print(r.render())
    finally:
        await src.close()
        await redis_client.aclose()
        await engine.dispose()
        await container.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
