"""Что делает воркер (taskiq) и подписка «Ранний доступ».

Задачи исполняются настоящим taskiq-брокером (InMemoryBroker) с настоящим
DI-контейнером бота — как в процессе воркера."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from aiogram.methods import CopyMessage, UnpinChatMessage
from taskiq import InMemoryBroker

from src.application.use_cases.miling.execute import ExecuteMailingRequest
from src.domain.enums.miling import MailingType
from src.domain.value_objects.region_settings import RegionSettings
from src.infrastructure.broker.taskiq import register_taskiq_tasks
from src.infrastructure.repositories.region.sqlalchemy import (
    SQLAlchemyRegionRepository,
)
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo
from src.infrastructure.tasks.taskiq_queue import TaskiqTaskQueue

from ..factories import make_region, make_user
from .conftest import ADMIN_TG_ID
from .harness import settle
from .test_create_ad_flow import FREE_SLOT

SUB = datetime.now(timezone.utc) + timedelta(days=5)


@pytest.fixture
def worker(world):
    """Выполнить задачу так, как её выполнит процесс воркера."""
    broker = InMemoryBroker(await_inplace=True)
    register_taskiq_tasks(broker, container=world.container)
    queue = TaskiqTaskQueue(broker, schedule_source=None)

    async def run(task_name: str, args: tuple) -> None:
        await queue.enqueue(task_name=task_name, args=args)

    return run


async def _subscription_until(session, tg_id):
    session.expire_all()
    return (
        await SQLAlchemyUserRepo(session).get_by_tg_id(tg_id)
    ).pre_publication_expires_at


# ------------------------------------------------- уведомление подписчиков


async def test_subscribers_are_notified_before_publication_and_open_catalog(
    world, session, worker
):
    region = await make_region(
        session, settings=RegionSettings(system_paid_slots_count=0)
    )
    await make_user(session, region.id, tg_id=601, username="seller")
    await make_user(session, region.id, tg_id=602, pre_publication_expires_at=SUB)
    await make_user(session, region.id, tg_id=603)  # без подписки
    other = await make_region(session, title="СПб", channel_id=-2)
    await make_user(session, other.id, tg_id=604, pre_publication_expires_at=SUB)
    await session.commit()

    seller = world.user(601, username="seller")
    await seller.send("/start")
    await seller.click("ПРОДАТЬ")
    await seller.send("А123ВС77")
    await seller.click("Пропустить")
    await seller.send("москва")
    await seller.send("+79991234567")
    await seller.send("150000")
    await seller.click(FREE_SLOT)
    await seller.click("Подтвердить")

    [(_, args, notify_at, _)] = [
        s for s in world.tasks.scheduled if s[0] == "notify_pre_publication_users"
    ]
    publish_at = next(
        s[2] for s in world.tasks.scheduled if s[0] == "publish_publication"
    )
    assert publish_at - notify_at == timedelta(hours=2)

    await worker("notify_pre_publication_users", args)

    subscriber = world.user(602)
    assert "А123ВС77" in subscriber.last.text
    assert world.tg.visible(603) == [], "без подписки уведомлений нет"
    assert world.tg.visible(604) == [], "другой регион не уведомляется"

    # кнопка в уведомлении ведёт в каталог раннего доступа (само объявление
    # появится в нём в окне «за 2 часа» — задачу здесь запустили раньше)
    await subscriber.click(subscriber.last.button_texts[0])
    assert "Каталог срочных выкупов" in subscriber.last.text


# ------------------------------------------------------------- рассылка


async def test_mailing_reaches_active_users_and_reports_to_admin(
    world, session, worker
):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=ADMIN_TG_ID)
    for tg in (611, 612, 613):
        await make_user(session, region.id, tg_id=tg)
    await make_user(session, region.id, tg_id=614, is_blocked=True)
    await session.commit()

    await world.mediator_call(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_ALL, from_chat_id=ADMIN_TG_ID, message_id=5
        )
    )
    for name, args in list(world.tasks.enqueued):
        assert name == "execute_mailing_batch"
        await worker(name, args)

    copied_to = {int(c.chat_id) for c in world.tg.calls_of(CopyMessage)}
    assert {611, 612, 613} <= copied_to
    assert 614 not in copied_to, "заблокированным рассылка не уходит"
    report = world.tg.visible(ADMIN_TG_ID)[-1].text
    assert "Рассылка" in report and "завершена" in report


async def test_mailing_to_region_only(world, session, worker):
    msk = await make_region(session)
    spb = await make_region(session, title="СПб", channel_id=-2)
    await make_user(session, msk.id, tg_id=621)
    await make_user(session, spb.id, tg_id=622)
    await session.commit()

    await world.mediator_call(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_REGION,
            from_chat_id=ADMIN_TG_ID,
            message_id=5,
            region_id=spb.id,
        )
    )
    for name, args in list(world.tasks.enqueued):
        await worker(name, args)

    assert {int(c.chat_id) for c in world.tg.calls_of(CopyMessage)} == {622}


async def test_mailing_to_all_channels(world, session, worker):
    await make_region(session, channel_id=-100)
    off = await make_region(session, title="Выкл", channel_id=-200)
    off.disable()
    await SQLAlchemyRegionRepository(session).update(off)
    await session.commit()

    await world.mediator_call(
        ExecuteMailingRequest(
            mail_type=MailingType.TO_ALL_REGIONS, from_chat_id=ADMIN_TG_ID, message_id=5
        )
    )
    for name, args in list(world.tasks.enqueued):
        await worker(name, args)

    copied_to = {int(c.chat_id) for c in world.tg.calls_of(CopyMessage)}
    assert -100 in copied_to
    # NB: отключённые регионы сейчас тоже получают рассылку «во все каналы»
    assert -200 in copied_to


# ------------------------------------------------------------- открепление


async def test_unpin_task_unpins_channel_message(world, worker):
    await worker("unpin_message", (-1001, 555))

    [call] = world.tg.calls_of(UnpinChatMessage)
    assert (int(call.chat_id), call.message_id) == (-1001, 555)


# ------------------------------------------------------- подписка


async def test_buy_subscription_from_balance(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=631, balance=Decimal("5000"))
    await session.commit()
    u = world.user(631)
    await u.send("/start")
    await u.click("Ранний доступ")
    await u.click("Получить доступ")
    assert "1 999" in u.last.text or "1999" in u.last.text

    await u.click("Подключить подписку")

    assert "подключена" in u.last_alert
    until = await _subscription_until(session, 631)
    assert until is not None
    assert timedelta(days=29) < until - datetime.now(timezone.utc) <= timedelta(days=30)
    session.expire_all()
    assert (await SQLAlchemyUserRepo(session).get_by_tg_id(631)).balance == Decimal(
        "3001"
    )

    await u.send("/start")
    await u.click("Ранний доступ")
    assert "Получить доступ" not in " ".join(u.last.button_texts)


async def test_extend_active_subscription_adds_days(world, session):
    region = await make_region(session)
    await make_user(
        session,
        region.id,
        tg_id=632,
        balance=Decimal("5000"),
        pre_publication_expires_at=SUB,
    )
    await session.commit()
    u = world.user(632)
    await u.send("/start")
    await u.click("Продать быстрее")
    await u.click("до публикации")

    await u.click("Подключить подписку")

    assert "продлена" in u.last_alert
    until = await _subscription_until(session, 632)
    assert until - SUB == timedelta(days=30)


async def test_buy_subscription_via_stars_when_balance_is_low(world, session):
    from sqlalchemy import select

    from src.infrastructure.database.models import PaymentModel

    region = await make_region(session)
    await make_user(session, region.id, tg_id=633)
    await session.commit()
    u = world.user(633)
    await u.send("/start")
    await u.click("Ранний доступ")
    await u.click("Получить доступ")
    await u.click("Подключить подписку")
    assert "Выберите способ оплаты" in u.last.text
    await u.click("TG Stars")
    q = select(PaymentModel).execution_options(populate_existing=True)
    [payment] = (await session.execute(q)).scalars().all()

    await u.pay_stars(payload=payment.external_id, stars=1)
    await settle()

    until = await _subscription_until(session, 633)
    assert until is not None and until > datetime.now(timezone.utc) + timedelta(days=29)


# ------------------------------------------------------------- профиль


async def test_profile_shows_balance_and_subscription(world, session):
    region = await make_region(session)
    await make_user(
        session,
        region.id,
        tg_id=641,
        balance=Decimal("1234"),
        pre_publication_expires_at=SUB,
        username="me",
    )
    await session.commit()
    u = world.user(641)
    await u.send("/start")

    await u.click("Мой профиль")

    assert "1 234" in u.last.text or "1234" in u.last.text
