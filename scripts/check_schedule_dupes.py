"""
Проверка дублей в taskiq schedule:* (Redis БД 1).

Считает задачи по (task_name, args) — если для одного и того же
ad_id/publication_id стоит больше одной notify/publish задачи, это дубль.

ЗАПУСК (на проде, через exec, ЧТЕНИЕ ONLY — ничего не меняет):
    docker compose exec -e PYTHONPATH=/app worker python scripts/check_schedule_dupes.py
"""

from __future__ import annotations

import asyncio
import pickle
from collections import defaultdict

import redis.asyncio as aioredis

from src.core.config import settings


async def main() -> int:
    redis = aioredis.from_url(settings.db.redis.taskiq_url)

    counts: dict[tuple[str, tuple], list[tuple[str, str]]] = defaultdict(list)
    total = 0
    broken = 0

    try:
        async for key in redis.scan_iter(match="schedule:*"):
            total += 1
            raw = await redis.get(key)
            if raw is None:
                continue
            try:
                data = pickle.loads(raw)
            except Exception as e:
                broken += 1
                print(f"  [!] не удалось распарсить {key}: {e}")
                continue

            task_name = data.get("task_name", "?")
            args = tuple(data.get("args") or ())
            time_ = data.get("time")
            schedule_id = data.get("schedule_id")

            counts[(task_name, args)].append((str(time_), str(schedule_id)))

        print(f"Всего ключей schedule:*: {total}\n")
        if broken:
            print(f"Не распарсилось: {broken}\n")

        dupes = {k: v for k, v in counts.items() if len(v) > 1}

        if not dupes:
            print("Дублей не найдено — по (task_name, args) всё уникально.")
        else:
            print(f"НАЙДЕНО ГРУПП С ДУБЛЯМИ: {len(dupes)}\n")
            for (task_name, args), entries in sorted(dupes.items()):
                short_name = task_name.split(":")[-1]
                print(f"  {short_name} args={args} — {len(entries)} задач(и):")
                for time_, sid in entries:
                    print(f"      time={time_} schedule_id={sid}")
                print()

        # отдельная сводка по типу задачи
        by_type: dict[str, int] = defaultdict(int)
        for task_name, _args in counts:
            by_type[task_name.split(":")[-1]] += len(counts[(task_name, _args)])
        print("Итого по типам задач:")
        for name, cnt in sorted(by_type.items()):
            print(f"  {name}: {cnt}")

    finally:
        await redis.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
