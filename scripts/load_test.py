"""
Нагрузочный тест: параллельно долбит use-case через ОБЩИЙ DI-контейнер
(как в реальном проде — контейнер живёт постоянно, каждый вызов получает
свой request-scope с собственной AsyncSession из общего пула соединений).

Запуск:
    docker compose run --rm \
      -v ~/auto_nomera_v2/scripts:/app/scripts \
      -e PYTHONPATH=/app \
      bot python scripts/load_test.py --scenario calendar --n 100 --region-id 1
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

from src.application.use_cases.stats.region_schedule import GetRegionScheduleRequest
from src.core.dependencies.providers import make_base_providers


async def one_call(container, scenario: str, region_id: int):
    start = time.perf_counter()
    try:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            if scenario == "calendar":
                await mediator.handle(GetCalendarRequest(region_id=region_id))
            elif scenario == "schedule":
                await mediator.handle(GetRegionScheduleRequest(region_id=region_id))
            else:
                raise ValueError(f"unknown scenario {scenario}")
    except Exception as e:
        print(f"  ! error: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    return time.perf_counter() - start


async def run_scenario(container, scenario: str, region_id: int, n: int):
    print(f"Запускаю {n} параллельных вызовов сценария '{scenario}'...")
    overall_start = time.perf_counter()

    tasks = [one_call(container, scenario, region_id) for _ in range(n)]
    results = await asyncio.gather(*tasks)

    overall_elapsed = time.perf_counter() - overall_start
    durations = [r for r in results if r is not None]
    errors = n - len(durations)

    if not durations:
        print("Все вызовы упали с ошибкой.")
        return

    durations.sort()
    p95_idx = min(int(len(durations) * 0.95), len(durations) - 1)

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
    parser.add_argument("--scenario", choices=["calendar", "schedule"], required=True)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--region-id", type=int, default=1)
    args = parser.parse_args()

    container = make_async_container(*make_base_providers())
    try:
        await run_scenario(container, args.scenario, args.region_id, args.n)
    finally:
        await container.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
