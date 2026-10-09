import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

import fakeredis
import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_dialog import BgManagerFactory
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from dishka.integrations.aiogram import AiogramProvider, setup_dishka
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.application.mediator import Mediator
from src.application.ports.tasks.task_queue import TaskQueue
from src.core.config import settings
from src.core.dependencies.providers import make_base_providers
from src.infrastructure.seeds.runner import run_seeds
from src.presentation.telegram.middlewares.setup import setup_middlewares

from .harness import FakeTelegramSession, RecordingTaskQueue, TgUser

ADMIN_TG_ID = settings.telegram.admin_ids[0]


@dataclass
class BotWorld:
    dp: Dispatcher
    bot: Bot
    tg: FakeTelegramSession
    tasks: RecordingTaskQueue
    redis: fakeredis.FakeAsyncRedis
    container: AsyncContainer

    def user(self, tg_id: int, **kw) -> TgUser:
        return TgUser(dp=self.dp, bot=self.bot, tg=self.tg, id=tg_id, **kw)

    def admin(self) -> TgUser:
        return self.user(ADMIN_TG_ID, username="admin")

    async def mediator_call(self, request):
        """Прямой вызов use case через тот же контейнер — для подготовки
        данных и проверок состояния, когда UI-путь уже покрыт отдельно."""
        async with self.container() as rc:
            mediator = await rc.get(Mediator)
            return await mediator.handle(request)


class _TestOverrides(Provider):
    def __init__(self, db_url, tg, tasks, redis) -> None:
        super().__init__()
        self._engine = create_async_engine(db_url, poolclass=NullPool)
        self._tg = tg
        self._tasks = tasks
        self._redis = redis

    @provide(scope=Scope.REQUEST)
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(self._engine, expire_on_commit=False) as s:
            yield s

    @provide(scope=Scope.APP)
    def redis(self) -> Redis:
        return self._redis

    @provide(scope=Scope.APP)
    def bot(self) -> Bot:
        return Bot(
            token="42:TEST",
            session=self._tg,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    @provide(scope=Scope.REQUEST)
    def task_queue(self) -> TaskQueue:
        return self._tasks


@pytest_asyncio.fixture(scope="session")
async def _bot_world(migrated_db) -> AsyncIterator[BotWorld]:
    tg = FakeTelegramSession()
    tasks = RecordingTaskQueue()
    redis = fakeredis.FakeAsyncRedis()
    container = make_async_container(
        *make_base_providers(),
        AiogramProvider(),
        _TestOverrides(migrated_db, tg, tasks, redis),
    )
    bot = await container.get(Bot)
    dp = await container.get(Dispatcher)
    setup_dishka(container=container, router=dp)
    setup_middlewares(dp=dp, container=container)
    await container.get(BgManagerFactory)
    yield BotWorld(dp=dp, bot=bot, tg=tg, tasks=tasks, redis=redis, container=container)
    await container.close()


_SWALLOWED_MARKERS = ("[UnhandledError]", "[UnknownIntent]", "[UserNotFound]")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "allow_bot_errors: тест ожидает, что глобальный error-хендлер сработает",
    )


@pytest.fixture
async def world(_bot_world: BotWorld, caplog, request) -> AsyncIterator[BotWorld]:
    """Чистый мир на каждый тест: БД обнуляется autouse-фикстурой
    интеграционных тестов, здесь — Redis, записи Telegram и очереди.

    Глобальный ``handle_error`` бота глушит любые исключения хендлеров
    (лог + «Произошла ошибка» пользователю). Чтобы тест не прошёл молча
    поверх упавшего хендлера, такие срабатывания валят тест."""
    await _bot_world.redis.flushall()
    _bot_world.tg.reset()
    _bot_world.tasks.reset()
    async with _bot_world.container() as rc:
        await run_seeds(await rc.get(Mediator))
    caplog.set_level(logging.INFO)
    yield _bot_world
    if request.node.get_closest_marker("allow_bot_errors"):
        return
    swallowed = [
        r.getMessage()
        for r in caplog.get_records("call")
        if any(m in r.getMessage() for m in _SWALLOWED_MARKERS)
        or (r.name.startswith("aiogram") and r.levelno >= logging.ERROR)
    ]
    assert not swallowed, "Бот проглотил ошибку:\n" + "\n\n".join(swallowed)
