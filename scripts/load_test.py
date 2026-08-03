"""
Быстрый нагрузочный тест: параллельно долбит выбранные use-case'ы
и печатает время выполнения + разброс (min/avg/max/p95).

Запуск (по аналогии с migrate_legacy.py):

    docker compose run --rm \
      -v ~/auto_nomera_v2/scripts:/app/scripts \
      -e PYTHONPATH=/app \
      bot python scripts/load_test.py --scenario calendar --n 100 --region-id 1

Сценарии:
    calendar    — GetCalendarUseCase (построение календаря слотов)
    schedule    — GetRegionScheduleUseCase (расписание региона)
    stats       — GetGlobalStatsUseCase (общая статистика)
    mailing     — запускает execute_mailing (ОСТОРОЖНО — реально разошлёт!)

Во время работы скрипта в соседнем терминале держи открытым:
    docker stats
чтобы видеть CPU%/RAM% каждого контейнера в реальном времени.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time

from dishka import make_async_container

from src.application.mediator import Mediator
from src.application.use_cases.slots.get_calendar import GetCalendarRequest
from src.application.use_cases.stats.globals import GetGlobalStatsRequest
from src.application.use_cases.stats.region_schedule import GetRegionScheduleRequest
from src.core.dependencies.providers import make_base_providers


async def run_scenario(mediator: Mediator, scenario: str, region_id: int, n: int):
    async def one_call():
        start = time.perf_counter()
        try:
            if scenario == "calendar":
                await mediator.handle(GetCalendarRequest(region_id=region_id))
            elif scenario == "schedule":
                await mediator.handle(GetRegionScheduleRequest(region_id=region_id))
            elif scenario == "stats":
                from src.domain.enums.period import StatsPeriod

                await mediator.handle(
                    GetGlobalStatsRequest(period=StatsPeriod.MONTH, region_id=None)
                )
            else:
                raise ValueError(f"unknown scenario {scenario}")
        except Exception as e:
            print(f"  ! error: {e}", file=sys.stderr)
            return None
        return time.perf_counter() - start

    print(f"Запускаю {n} параллельных вызовов сценария '{scenario}'...")
    overall_start = time.perf_counter()

    tasks = [one_call() for _ in range(n)]
    results = await asyncio.gather(*tasks)

    overall_elapsed = time.perf_counter() - overall_start
    durations = [r for r in results if r is not None]
    errors = n - len(durations)

    if not durations:
        print("Все вызовы упали с ошибкой.")
        return

    durations.sort()
    p95_idx = int(len(durations) * 0.95)

    print()
    print("=" * 50)
    print(f"РЕЗУЛЬТАТ: {scenario}")
    print("=" * 50)
    print(f"  Запросов:        {n}")
    print(f"  Успешно:         {len(durations)}")
    print(f"  Ошибок:          {errors}")
    print(f"  Общее время:     {overall_elapsed:.2f} сек")
    print(f"  Мин:             {durations[0] * 1000:.0f} мс")
    print(f"  Среднее:         {statistics.mean(durations) * 1000:.0f} мс")
    print(f"  Медиана:         {statistics.median(durations) * 1000:.0f} мс")
    print(f"  p95:             {durations[p95_idx] * 1000:.0f} мс")
    print(f"  Макс:            {durations[-1] * 1000:.0f} мс")
    print(f"  RPS (эффективно):{len(durations) / overall_elapsed:.1f}")
    print("=" * 50)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=["calendar", "schedule", "stats", "mailing"],
        required=True,
    )
    parser.add_argument("--n", type=int, default=50, help="кол-во параллельных вызовов")
    parser.add_argument("--region-id", type=int, default=1)
    args = parser.parse_args()

    if args.scenario == "mailing":
        confirm = input("⚠️  Это реально разошлёт сообщение! Продолжить? (yes/no): ")
        if confirm.strip().lower() != "yes":
            print("Отменено.")
            return 0

    container = make_async_container(*make_base_providers())

    try:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)

            if args.scenario == "mailing":
                # тут лучше вызвать через use-case ExecuteMailingRequest
                # с тестовым mail_type/безопасным получателем — заполни под себя
                print("Реализуй тестовый вызов ExecuteMailingRequest здесь")
            else:
                await run_scenario(mediator, args.scenario, args.region_id, args.n)
    finally:
        await container.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
