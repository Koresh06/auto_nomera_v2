"""
Разовый фикс таймзонного сдвига publish_at_utc.

resync_schedule.py при переносе из старого Redis записал publish_at_utc = run_at
(МСК-based score старого бота) вместо честного пересчёта из slot_time в таймзоне
региона. В результате для немосковских регионов publish_at_utc сдвинут на разницу
их зоны с Москвой, и taskiq-задача выстрелит в неправильное время (хендлер публикации
НЕ сверяет время — публикует по факту срабатывания задачи).

Скрипт для каждой затронутой SCHEDULED-публикации:
  1) отменяет старую (кривую) taskiq-задачу по сохранённому scheduler_job_id
  2) пересчитывает publish_at_utc = (slot_day + slot_time) в tz региона -> UTC
  3) UPDATE publish_at_utc (+ commit ДО планирования — гонка bot/worker)
  4) ставит задачу publish_publication заново с корректным run_at_utc
  5) сохраняет новый scheduler_job_id

Идемпотентен: если publish_at_utc уже корректен — запись пропускается.

Запуск (в контейнере, как resync_schedule.py):
    # сухой прогон (ничего не меняет, только показывает план):
    docker compose run --rm -e PYTHONPATH=/app bot python scripts/fix_tz_schedule.py
    # боевой прогон:
    docker compose run --rm -e PYTHONPATH=/app bot python scripts/fix_tz_schedule.py --apply

Область: чинит ВСЕ SCHEDULED с publish_at_utc != корректного (не хардкодит id),
поэтому безопасен к повторному запуску и поймает любые пропущенные записи.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import settings


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="применить изменения (по умолчанию — сухой прогон)",
    )
    args = parser.parse_args()
    dry = not args.apply

    engine = create_async_engine(settings.db.postgres.url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # taskiq queue — как в resync_schedule.py
    from dishka import make_async_container

    from src.application.ports.tasks.task_queue import TaskQueue
    from src.core.dependencies.providers import make_base_providers
    from src.infrastructure.broker.instance import broker
    from src.infrastructure.broker.taskiq import register_taskiq_tasks

    container = make_async_container(*make_base_providers())
    register_taskiq_tasks(broker, container=container)

    print(f"{'СУХОЙ ПРОГОН' if dry else 'ПРИМЕНЕНИЕ'} починки таймзон...\n")

    fixed = 0
    skipped_ok = 0
    errors = 0

    try:
        async with session_factory() as session:
            async with container() as request_container:
                queue = await request_container.get(TaskQueue)

                # все SCHEDULED со слотом, с текущим publish_at_utc и tz региона
                rows = await session.execute(
                    sa_text(
                        """
                        SELECT p.id,
                               p.slot_day,
                               p.slot_time,
                               p.publish_at_utc,
                               p.scheduler_job_id,
                               r.timezone
                        FROM publications p
                        JOIN regions r ON r.id = p.region_id
                        WHERE p.status = 'SCHEDULED'
                          AND p.slot_day IS NOT NULL
                          AND p.slot_time IS NOT NULL
                        ORDER BY p.publish_at_utc
                        """
                    )
                )

                for (
                    pub_id,
                    slot_day,
                    slot_time,
                    old_utc,
                    old_job_id,
                    tz_name,
                ) in rows.all():
                    # корректный UTC из локального слота региона
                    local = datetime.combine(
                        slot_day, slot_time, tzinfo=ZoneInfo(tz_name)
                    )
                    correct_utc = local.astimezone(timezone.utc)

                    # уже правильно — пропускаем
                    if old_utc == correct_utc:
                        skipped_ok += 1
                        continue

                    drift = old_utc - correct_utc
                    print(
                        f"pub {pub_id} [{tz_name}] {slot_day} {slot_time}: "
                        f"{old_utc} -> {correct_utc}  (drift {drift}, "
                        f"job={old_job_id})"
                    )

                    if dry:
                        fixed += 1
                        continue

                    try:
                        # 1) снять старую задачу
                        if old_job_id:
                            await queue.cancel(job_id=old_job_id)

                        # 2) поправить время + commit ДО планирования
                        await session.execute(
                            sa_text(
                                "UPDATE publications "
                                "SET publish_at_utc = :u, updated_at = now() "
                                "WHERE id = :i"
                            ),
                            {"u": correct_utc, "i": pub_id},
                        )
                        await session.commit()

                        # 3) поставить задачу заново
                        new_job_id = await queue.schedule(
                            task_name="publish_publication",
                            args=(pub_id,),
                            run_at_utc=correct_utc,
                        )

                        # 4) сохранить новый job_id
                        if new_job_id:
                            await session.execute(
                                sa_text(
                                    "UPDATE publications "
                                    "SET scheduler_job_id = :j WHERE id = :i"
                                ),
                                {"j": new_job_id, "i": pub_id},
                            )
                            await session.commit()

                        print(f"    -> OK, new job={new_job_id}")
                        fixed += 1
                    except Exception as e:  # noqa: BLE001
                        await session.rollback()
                        errors += 1
                        print(f"    -> ОШИБКА: {e}")

        print(
            f"\n{'[план]' if dry else '[готово]'} "
            f"к починке: {fixed}, уже верных: {skipped_ok}, ошибок: {errors}"
        )
    finally:
        await engine.dispose()
        await container.close()

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
