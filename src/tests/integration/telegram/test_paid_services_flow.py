"""Платные услуги после создания объявления и публикация воркером в канал.

Пользователь проходит создание объявления через бота; «воркер» — это вызов
того же use case, который исполняет taskiq-задача publish_publication."""

from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from aiogram.methods import PinChatMessage
from sqlalchemy import select

from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
)
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.infrastructure.database.models import PaymentModel, PublicationModel
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from ..factories import make_region, make_user
from .test_create_ad_flow import FREE_SLOT

CHANNEL_ID = -1001


async def _pubs(session) -> list[PublicationModel]:
    q = (
        select(PublicationModel)
        .order_by(PublicationModel.id)
        .execution_options(populate_existing=True)
    )
    return list((await session.execute(q)).scalars().all())


async def _balance(session, tg_id: int) -> Decimal:
    session.expire_all()
    return (await SQLAlchemyUserRepo(session).get_by_tg_id(tg_id)).balance


async def _create_ad_until_services(world, session, *, balance="0", photo=None):
    from decimal import Decimal as D

    from src.domain.value_objects.region_settings import RegionSettings

    region = await make_region(
        session,
        channel_id=CHANNEL_ID,
        settings=RegionSettings(system_paid_slots_count=0),
    )
    await make_user(
        session, region.id, tg_id=900, balance=D(balance), username="seller"
    )
    await session.commit()
    u = world.user(900)
    await u.send("/start")
    await u.click("ПРОДАТЬ")
    await u.send("А123ВС77")
    if photo:
        await u.send_photo(photo)
        await u.click("Далее")
    else:
        await u.click("Пропустить")
    await u.send("москва")
    await u.send("+79991234567")
    await u.send("150000")
    await u.click(FREE_SLOT)
    await u.click("Подтвердить")
    assert "Сделайте своё объявление заметнее" in u.last.text
    return u


async def _run_publish_worker(world, pub_id: int) -> None:
    await world.mediator_call(PublishPublicationRequest(publication_id=pub_id))


def _channel(world):
    return world.tg.visible(CHANNEL_ID)


async def test_worker_publishes_scheduled_ad_to_channel(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    [pub] = await _pubs(session)

    await _run_publish_worker(world, pub.id)

    [post] = _channel(world)
    assert "А123ВС77" in post.text
    assert "150 000" in post.text
    [pub] = await _pubs(session)
    assert pub.status == PublicationStatus.PUBLISHED
    assert pub.channel_message_id == post.message.message_id
    assert pub.published_at_utc is not None

    # повторный запуск задачи (ретрай taskiq) не публикует второй раз
    await _run_publish_worker(world, pub.id)
    assert len(_channel(world)) == 1


async def test_service_list_hides_pre_publication_and_shows_prices(world, session):
    u = await _create_ad_until_services(world, session)
    labels = u.last.button_texts
    assert any("Вне очереди — 299 руб." in b for b in labels)
    assert any("Выделение — 299 руб." in b for b in labels)
    assert any("Закрепление — 499 руб." in b for b in labels)
    assert any("Автопубликация — 499 руб." in b for b in labels)
    assert not any("до публикации" in b for b in labels)


async def test_priority_publish_from_balance(world, session):
    u = await _create_ad_until_services(world, session, balance="1000")
    [pub] = await _pubs(session)
    old_job = pub.scheduler_job_id

    await u.click("Вне очереди")

    assert "Вне очереди активирована" in u.last_alert
    assert await _balance(session, 900) == Decimal("701")
    [pub] = await _pubs(session)
    assert old_job in world.tasks.canceled, "старая задача по слоту должна сниматься"
    # в БД — id именно новой (немедленной) задачи, а не отменённой
    latest_publish_job = [
        s for s in world.tasks.scheduled if s[0] == "publish_publication"
    ][-1]
    assert pub.scheduler_job_id == latest_publish_job[3] != old_job
    svc_status = {s.type: s.status for s in pub.services}
    assert (
        svc_status[PublicationServiceType.PRIORITY_PUBLISH]
        == PublicationServiceStatus.USED
    )
    svc = {s.type: s for s in pub.services}
    assert PublicationServiceType.PRIORITY_PUBLISH in svc

    publish_jobs = [
        s for s in world.tasks.scheduled if s[0] == "publish_publication"
    ] + [e for e in world.tasks.enqueued if e[0] == "publish_publication"]
    assert len(publish_jobs) >= 2  # слот + немедленная

    await _run_publish_worker(world, pub.id)
    assert len(_channel(world)) == 1
    [pub] = await _pubs(session)
    assert pub.status == PublicationStatus.PUBLISHED


async def test_buying_same_service_twice_is_refused(world, session):
    u = await _create_ad_until_services(world, session, balance="5000")
    await u.click("Закрепление")
    assert "активирована" in u.last_alert

    await u.click("Закрепление")

    assert "уже активна" in u.last_alert
    assert await _balance(session, 900) == Decimal("4501")


async def test_pin_is_applied_when_worker_publishes(world, session):
    u = await _create_ad_until_services(world, session, balance="1000")
    await u.click("Закрепление")
    [pub] = await _pubs(session)

    await _run_publish_worker(world, pub.id)

    [post] = _channel(world)
    [pin] = world.tg.calls_of(PinChatMessage)
    assert (int(pin.chat_id), pin.message_id) == (CHANNEL_ID, post.message.message_id)
    [pub] = await _pubs(session)
    [svc] = [s for s in pub.services if s.type == PublicationServiceType.PIN]
    assert svc.status == PublicationServiceStatus.USED
    unpins = [s for s in world.tasks.scheduled if s[0] == "unpin_message"]
    assert len(unpins) == 1
    _, args, run_at, _ = unpins[0]
    assert args == (CHANNEL_ID, post.message.message_id)
    assert run_at - pub.published_at_utc == timedelta(days=3)
    assert svc.params.get("unpin_at_utc") == run_at.isoformat()


async def test_highlight_publishes_photo_with_red_frame(world, session):
    u = await _create_ad_until_services(
        world, session, balance="1000", photo="original-photo"
    )
    await u.click("Выделение")
    [pub] = await _pubs(session)

    await _run_publish_worker(world, pub.id)

    [post] = _channel(world)
    assert post.message.photo, "объявление с фото публикуется фото"
    assert post.message.photo[-1].file_id != "original-photo", (
        "в канал должна уйти копия с красной рамкой"
    )
    [pub] = await _pubs(session)
    [svc] = [s for s in pub.services if s.type == PublicationServiceType.HIGHLIGHT]
    assert svc.status == PublicationServiceStatus.USED


async def test_autopublish_creates_daily_series_when_parent_is_published(
    world, session
):
    """Родитель выходит раньше своего слота (здесь «воркер» запущен сразу,
    как при «Вне очереди»): серия всё равно должна дать все 7 оплаченных
    постов, начиная со следующего дня после фактического выхода."""
    u = await _create_ad_until_services(world, session, balance="1000")
    await u.click("Автопубликация")
    assert "активирована" in u.last_alert
    [parent] = await _pubs(session)
    assert len(await _pubs(session)) == 1, "серия создаётся при выходе родителя"

    await _run_publish_worker(world, parent.id)

    pubs = await _pubs(session)
    parent, children = pubs[0], pubs[1:]
    assert parent.status == PublicationStatus.PUBLISHED
    assert len(children) == 7, "автопубликация на 7 дней"
    assert all(c.is_child and c.status == PublicationStatus.SCHEDULED for c in children)
    days = [c.slot_day for c in children]
    assert days == sorted(days) and len(set(days)) == 7, "по одному посту в день"
    assert {c.slot_time for c in children} == {parent.slot_time}
    published_local_day = parent.published_at_utc.astimezone(
        ZoneInfo("Europe/Moscow")
    ).date()
    assert days[0] == published_local_day + timedelta(days=1)
    assert all(c.scheduler_job_id for c in children)
    [svc] = [s for s in parent.services if s.type == PublicationServiceType.AUTOPUBLISH]
    assert svc.status == PublicationServiceStatus.USED

    # повторный запуск задачи родителя не плодит дубли серии (AUD-21)
    await _run_publish_worker(world, parent.id)
    assert len(await _pubs(session)) == 8

    # «воркер» публикует первую дочернюю запись — второй пост в канале
    await _run_publish_worker(world, children[0].id)
    assert len(_channel(world)) == 2


async def test_service_without_balance_opens_payment_for_its_price(world, session):
    u = await _create_ad_until_services(world, session, balance="0")

    await u.click("Закрепление")

    assert "Выберите способ оплаты" in u.last.text
    assert "499 руб." in u.last.text
    await u.click("TG Stars")
    q = select(PaymentModel).execution_options(populate_existing=True)
    [payment] = (await session.execute(q)).scalars().all()
    assert payment.purpose.value == "publication_service"
    assert payment.meta["service_type"] == "pin"

    from src.tests.integration.telegram.harness import settle

    await u.pay_stars(payload=payment.external_id, stars=1)
    await settle()

    [pub] = await _pubs(session)
    assert PublicationServiceType.PIN in {s.type for s in pub.services}
    # после оплаты пользователь снова в выборе услуг, закреп отмечен
    assert any("Закрепление ✅" in b for b in u.last.button_texts)
