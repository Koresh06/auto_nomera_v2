"""Продовые DI-контейнеры собираются так же, как в процессах бота, воркера
и веб-сервиса, и каждый запрос, который код отправляет в медиатор, имеет
обработчик. Иначе ошибка всплыла бы только в рантайме конкретного сценария
(ValueError: No handler registered ...).

Каждый процесс проверяется в отдельном интерпретаторе: роутеры aiogram —
синглтоны модулей, и второй Dispatcher в одном процессе собрать нельзя
(в проде у каждого процесса он свой)."""

import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

_SCRIPT = r"""
import asyncio, importlib, json, os, pkgutil, sys
os.environ["APP_CONFIG__APP__SENTRY_DSN"] = ""
from dishka import make_async_container
from src.application.mediator import Mediator
from src.application.use_cases.base import UseCaseRequest
import src.application.use_cases as pkg
from src.core.dependencies.providers import make_base_providers

kind = sys.argv[1]
extra = []
if kind == "bot":
    from dishka.integrations.aiogram import AiogramProvider
    extra = [AiogramProvider()]
elif kind == "web":
    from dishka.integrations.fastapi import FastapiProvider
    extra = [FastapiProvider()]

for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
    importlib.import_module(m.name)

async def main():
    container = make_async_container(*make_base_providers(), *extra)
    try:
        async with container() as scope:
            mediator = await scope.get(Mediator)
    finally:
        await container.close()
    seen, stack = set(), list(UseCaseRequest.__subclasses__())
    while stack:
        c = stack.pop(); seen.add(c); stack.extend(c.__subclasses__())
    handled = [c.__name__ for c in seen if any(k in mediator._handlers for k in c.mro())]
    print(json.dumps({"handled": handled, "all": [c.__name__ for c in seen]}))

asyncio.run(main())
"""


def _requests_sent_by_code() -> set[str]:
    """Имена запросов, экземпляры которых создаются где-то вне модуля,
    где они объявлены (т.е. реально отправляются в медиатор)."""
    sources = {
        p: p.read_text() for p in (ROOT / "src").rglob("*.py") if "tests" not in p.parts
    }
    declared = {}
    for path, text in sources.items():
        for name in re.findall(r"^class (\w+(?:Request|Command))\(", text, re.M):
            declared[name] = path
    used = set()
    for name, home in declared.items():
        pattern = re.compile(rf"\b{name}\(")
        if any(p != home and pattern.search(t) for p, t in sources.items()):
            used.add(name)
    return used


@pytest.mark.parametrize("kind", ["bot", "web", "worker"])
def test_production_container_wires_every_sent_request(kind):
    env = {
        **os.environ,
        "APP_CONFIG__APP__SENTRY_DSN": "",
        # фиктивный токен корректного формата: в CI нет .env, а реальный
        # токен проверке не нужен (сеть не используется)
        "APP_CONFIG__TELEGRAM__BOT_TOKEN": "42:TEST",
    }
    proc = subprocess.run(
        [sys.executable, "-c", _SCRIPT, kind],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    result = json.loads(proc.stdout.strip().splitlines()[-1])

    missing = _requests_sent_by_code() - set(result["handled"])
    assert not missing, f"Нет обработчика в медиаторе для: {sorted(missing)}"
