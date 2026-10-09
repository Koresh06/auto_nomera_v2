"""Веб-сервис (FastAPI): вебхук ЮKassa и страница возврата после оплаты.

Настоящее приложение из create_app(), запросы идут по HTTP через ASGI;
подменены только БД (тестовый Postgres), очередь задач и поход в API ЮKassa."""

from collections.abc import AsyncIterator
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from aiogram import Bot, Dispatcher
from aiogram_dialog import BgManagerFactory
from redis.asyncio import Redis
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src.application.ports.tasks.task_queue import TaskQueue
from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
from src.core.dependencies.providers import make_base_providers
from src.domain.enums.payment import PaymentMethod, PaymentStatus
from src.infrastructure.database.models import PaymentModel
from src.infrastructure.payment.providers.yookassa import YooKassaProvider
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from ..factories import make_payment, make_region, make_user
from .harness import RecordingTaskQueue, settle


class _WebOverrides(Provider):
    def __init__(self, db_url: str, tasks: RecordingTaskQueue, bot_world) -> None:
        super().__init__()
        self._engine = create_async_engine(db_url, poolclass=NullPool)
        self._tasks = tasks
        self._bot_world = bot_world

    # Веб-процесс в проде собирает свой Dispatcher из тех же роутеров (нужен
    # телепорту после оплаты). В одном тестовом процессе роутеры уже
    # подключены к диспетчеру бота, поэтому отдаём его же.
    @provide(scope=Scope.APP)
    def bot(self) -> Bot:
        return self._bot_world.bot

    @provide(scope=Scope.APP)
    def dispatcher(self) -> Dispatcher:
        return self._bot_world.dp

    @provide(scope=Scope.APP)
    async def bg_manager_factory(self) -> BgManagerFactory:
        return await self._bot_world.container.get(BgManagerFactory)

    @provide(scope=Scope.APP)
    def redis(self) -> Redis:
        return self._bot_world.redis

    @provide(scope=Scope.REQUEST)
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(self._engine, expire_on_commit=False) as s:
            yield s

    @provide(scope=Scope.REQUEST)
    def task_queue(self) -> TaskQueue:
        return self._tasks


@pytest.fixture
async def web(migrated_db, monkeypatch, _bot_world):
    from src.presentation.web import app as web_app

    tasks = RecordingTaskQueue()
    container = make_async_container(
        *make_base_providers(),
        FastapiProvider(),
        _WebOverrides(migrated_db, tasks, _bot_world),
    )
    monkeypatch.setattr(web_app, "container", container)
    monkeypatch.setattr(web_app, "setup_logging", lambda: None)
    app = web_app.create_app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://web") as client:
        yield client, tasks
    await container.close()


@pytest.fixture
def yookassa_says(monkeypatch):
    """Ответ API ЮKassa на серверную сверку платежа (verify_payment)."""
    state: dict = {}

    async def verify_payment(self, *, yookassa_payment_id):
        return state.get(yookassa_payment_id)

    monkeypatch.setattr(YooKassaProvider, "verify_payment", verify_payment)

    def set_(payment_id, *, status, paid, external_id):
        state[payment_id] = SimpleNamespace(
            status=status, paid=paid, metadata={"external_id": external_id}
        )

    return set_


def _webhook(payment_id: str, event: str = "payment.succeeded") -> dict:
    return {"type": "notification", "event": event, "object": {"id": payment_id}}


async def test_webhook_confirms_only_what_yookassa_verified(web, yookassa_says):
    client, tasks = web
    yookassa_says("yk-1", status="succeeded", paid=True, external_id="ext-1")

    r = await client.post("/webhook/yookassa", json=_webhook("yk-1"))

    assert r.status_code == 200
    assert tasks.enqueued == [("confirm_payment", ("ext-1",))]


async def test_forged_webhook_for_unpaid_payment_is_ignored(web, yookassa_says):
    client, tasks = web
    # злоумышленник шлёт «payment.succeeded», но ЮKassa говорит: не оплачен
    yookassa_says("yk-2", status="pending", paid=False, external_id="ext-2")

    r = await client.post("/webhook/yookassa", json=_webhook("yk-2"))

    assert r.status_code == 200
    assert tasks.enqueued == []


async def test_canceled_payment_is_marked_failed(web, yookassa_says):
    client, tasks = web
    yookassa_says("yk-3", status="canceled", paid=False, external_id="ext-3")

    await client.post("/webhook/yookassa", json=_webhook("yk-3", "payment.canceled"))

    assert tasks.enqueued == [("mark_payment_failed", ("ext-3",))]


async def test_webhook_asks_for_retry_when_yookassa_unreachable(web, yookassa_says):
    client, tasks = web  # verify_payment вернёт None — как при таймауте API

    r = await client.post("/webhook/yookassa", json=_webhook("yk-unknown"))

    assert r.status_code == 502
    assert tasks.enqueued == []


async def test_webhook_rejects_payload_without_id(web, yookassa_says):
    client, _ = web
    r = await client.post("/webhook/yookassa", json={"event": "payment.succeeded"})
    assert r.status_code == 400


@pytest.mark.parametrize(
    "status,page",
    [
        (PaymentStatus.PAID, "success"),
        (PaymentStatus.PENDING, "pending"),
        (PaymentStatus.FAILED, "cancel"),
    ],
)
async def test_payment_return_page(web, session, status, page):
    client, _ = web
    region = await make_region(session)
    user = await make_user(session, region.id)
    await make_payment(session, user, external_id=f"ret-{page}", status=status)
    await session.commit()

    r = await client.get("/payment/return", params={"external_id": f"ret-{page}"})

    assert r.status_code == 200, r.text[:300]
    assert "<html" in r.text.lower()


async def test_payment_return_without_or_unknown_id_shows_cancel(web):
    client, _ = web
    assert (await client.get("/payment/return")).status_code == 200
    r = await client.get("/payment/return", params={"external_id": "nope"})
    assert r.status_code == 200


async def test_full_yookassa_topup_through_bot_webhook_and_worker(
    world, session, web, yookassa_says, monkeypatch
):
    """Пользователь пополняет баланс через ЮKassa в боте → ЮKassa шлёт
    вебхук в веб-сервис → воркер выполняет confirm_payment → баланс
    зачислен, пользователь получил сообщение в боте."""
    client, web_tasks = web

    async def create_invoice(self, **kw):
        return {"confirmation_url": "https://yoomoney.ru/checkout/x"}

    monkeypatch.setattr(YooKassaProvider, "create_invoice", create_invoice)
    region = await make_region(session)
    await make_user(session, region.id, tg_id=880, phone="+79990000000")
    await session.commit()
    u = world.user(880)
    await u.send("/start")
    await u.click("Пополнить баланс")
    await u.send("700")
    await u.click("СБП")
    q = select(PaymentModel).execution_options(populate_existing=True)
    [payment] = (await session.execute(q)).scalars().all()
    assert payment.method == PaymentMethod.YOOKASSA

    yookassa_says(
        "yk-real", status="succeeded", paid=True, external_id=payment.external_id
    )
    r = await client.post("/webhook/yookassa", json=_webhook("yk-real"))
    assert r.status_code == 200
    [(task, args)] = web_tasks.enqueued

    # воркер taskiq исполняет задачу confirm_payment
    assert task == "confirm_payment"
    await world.mediator_call(ConfirmPaymentRequest(external_id=args[0]))
    await settle()

    session.expire_all()
    assert (await SQLAlchemyUserRepo(session).get_by_tg_id(880)).balance == Decimal(
        "700"
    )
    assert any("700" in m.text for m in u.messages)
