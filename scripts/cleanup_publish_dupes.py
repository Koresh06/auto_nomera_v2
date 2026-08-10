"""
Чистка дублей publish_publication в Redis schedule:* (Redis БД 1).

ЛОГИКА:
  Источник правды — БД (publications.scheduler_job_id).
  Для каждого ключа schedule:* с task_name=publish_publication:
    - если его schedule_id СОВПАДАЕТ с publications.scheduler_job_id для
      этой publication_id — оставляем (это актуальная задача);
    - если НЕ совпадает (значит это "сирота" — старая задача, что была
      в Redis ДО того, как job_id сломался/восстановился) — удаляем.

  notify_pre_publication_users НЕ трогаем вообще — там нет единого
  job_id в БД для сверки, и трогать их руками рискованно (риск удалить
  легитимную будущую задачу серии). По факту проверки дублей там нет.

БЕЗОПАСНОСТЬ:
  - Dry-run по умолчанию, только печатает план.
  - --apply необходим для реального удаления.
  - Трогает СТРОГО только publish_publication с args, для которых
    publication_id есть в БД и её scheduler_job_id заполнен и не совпадает
    с данным ключом. Если publication_id из Redis не найдена в БД вообще —
    ключ НЕ трогаем (печатаем предупреждение) — на случай если это
    публикация в другом статусе (PUBLISHED и т.п.), тогда trust не полный.

ЗАПУСК:
    docker compose exec -e PYTHONPATH=/app worker python scripts/cleanup_publish_dupes.py            # dry-run
    docker compose exec -e PYTHONPATH=/app worker python scripts/cleanup_publish_dupes.py --apply     # боевой
"""

from __future__ import annotations

import argparse
import asyncio
import pickle
from collections import defaultdict

import redis.asyncio as aioredis
from sqlalchemy import select

from src.core.config import settings
from src.infrastructure.database.models.publication import PublicationModel
from src.infrastructure.database.sqlalchemy.connection import async_session_maker


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="применить (по умолчанию dry-run)"
    )
    args_ns = parser.parse_args()
    dry = not args_ns.apply

    redis = aioredis.from_url(settings.db.redis.taskiq_url)

    try:
        # 1) БД: publication_id -> актуальный scheduler_job_id
        async with async_session_maker() as session:
            rows = (
                await session.execute(
                    select(PublicationModel.id, PublicationModel.scheduler_job_id)
                )
            ).all()
        db_job_id_by_pub: dict[int, str | None] = {
            r.id: r.scheduler_job_id for r in rows
        }

        # 2) Redis: собираем все publish_publication ключи, группируем по pub_id
        by_pub: dict[int, list[tuple[str, str]]] = defaultdict(
            list
        )  # pub_id -> [(schedule_id, redis_key)]

        async for key in redis.scan_iter(match="schedule:*"):
            raw = await redis.get(key)
            if raw is None:
                continue
            try:
                data = pickle.loads(raw)
            except Exception:
                continue

            task_name = data.get("task_name", "")
            if not task_name.endswith(":publish_publication"):
                continue
            args = data.get("args") or ()
            if not args:
                continue
            pub_id = int(args[0])
            schedule_id = str(data.get("schedule_id"))
            by_pub[pub_id].append(
                (schedule_id, key.decode() if isinstance(key, bytes) else key)
            )

        to_delete: list[tuple[int, str, str]] = []  # (pub_id, schedule_id, redis_key)
        unknown_pub: list[int] = []
        kept_report: list[tuple[int, str]] = []

        for pub_id, entries in by_pub.items():
            if len(entries) < 2:
                continue  # нет дублей, не трогаем

            if pub_id not in db_job_id_by_pub:
                unknown_pub.append(pub_id)
                continue

            correct_job_id = db_job_id_by_pub[pub_id]
            if not correct_job_id:
                # в БД нет job_id вообще — не знаем, что оставить, не трогаем
                unknown_pub.append(pub_id)
                continue

            found_correct = False
            for schedule_id, redis_key in entries:
                if schedule_id == correct_job_id:
                    found_correct = True
                else:
                    to_delete.append((pub_id, schedule_id, redis_key))

            if found_correct:
                kept_report.append((pub_id, correct_job_id))
            else:
                # ни один schedule_id в Redis не совпал с БД — подозрительно,
                # откатываем решение по этой группе целиком (ничего не трогаем)
                to_delete = [t for t in to_delete if t[0] != pub_id]
                unknown_pub.append(pub_id)

        print(f"{'СУХОЙ ПРОГОН' if dry else 'УДАЛЕНИЕ'}\n")
        print(
            f"Групп с дублями обработано: {len([p for p in by_pub if len(by_pub[p]) >= 2])}"
        )
        print(f"К удалению (сирот): {len(to_delete)}")
        print(f"Пропущено (нет однозначного соответствия с БД): {len(unknown_pub)}")
        if unknown_pub:
            print(f"  pub_id без ясного job_id в БД: {sorted(unknown_pub)}")

        print()
        for pub_id, schedule_id, redis_key in to_delete:
            print(f"  [DEL] pub_id={pub_id} schedule_id={schedule_id}")
            if not dry:
                await redis.delete(redis_key)

        print(
            f"\n{'[ПЛАН]' if dry else '[ГОТОВО]'} удалено бы/удалено: {len(to_delete)}"
        )
        if dry:
            print(
                "\nЭто сухой прогон, ничего не изменено. Для применения запусти с --apply"
            )

    finally:
        await redis.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
