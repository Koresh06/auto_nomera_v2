"""Сквозной сценарий создания объявления через бота — от кнопки в меню
до запланированной публикации в БД и задачи в очереди."""

import re
from decimal import Decimal

from sqlalchemy import select

from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.region_settings import RegionSettings
from src.infrastructure.database.models import AdModel, PublicationModel
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from ..factories import make_region, make_user

FREE_SLOT = re.compile(r"^(?!.*💰)\S.*\d{1,2}:\d{2}")
PAID_SLOT = re.compile(r"💰")


async def _setup(session, *, paid_slots: int = 0, balance=Decimal("0"), tg_id=700):
    region = await make_region(
        session, settings=RegionSettings(system_paid_slots_count=paid_slots)
    )
    user = await make_user(
        session, region.id, tg_id=tg_id, balance=balance, username="seller"
    )
    await session.commit()
    return region, user


async def _fill_sale_until_calendar(u, plate="А123ВС77"):
    await u.send("/start")
    await u.click("ПРОДАТЬ")
    await u.send(plate)
    assert "Пришлите фото" in u.last.text
    await u.click("Пропустить")
    assert "Укажите город" in u.last.text
    await u.send("москва")
    assert "номер телефона" in u.last.text
    await u.send("+79991234567")
    assert "Укажите стоимость" in u.last.text
    await u.send("150000")
    assert "Выберите дату и время" in u.last.text


async def _all_rows(session, model):
    # populate_existing: свежие данные из БД, не сбрасывая ранее загруженные
    # объекты (expire_all ломал бы доступ к ним без await)
    query = select(model).execution_options(populate_existing=True)
    return list((await session.execute(query)).scalars().all())


async def test_sale_ad_full_flow_schedules_publication(world, session):
    region, user = await _setup(session)
    u = world.user(700, username="seller")

    await _fill_sale_until_calendar(u)
    slot_button = u.find_button(FREE_SLOT)[1].text
    await u.click(FREE_SLOT)

    confirm = u.last.text
    assert "Проверьте данные" in confirm
    assert "А123ВС77" in confirm
    assert "Москва" in confirm
    assert "150 000 руб." in confirm
    assert "@seller" in confirm and "+79991234567" in confirm

    await u.click("Подтвердить")
    assert "Сделайте своё объявление заметнее" in u.last.text
    await u.click("Пропустить")
    assert "будет опубликовано" in u.last.text

    [ad] = await _all_rows(session, AdModel)
    assert (ad.ad_type, ad.plate_number, ad.city, ad.price) == (
        AdType.SALE,
        "А123ВС77",
        "Москва",
        150000,
    )
    assert ad.phone == "+79991234567"
    # Ad.status у обычных объявлений не продвигается дальше DRAFT (меняется
    # только у срочного выкупа) и нигде не фильтруется — фиксируем как есть.
    assert ad.status == AdStatus.DRAFT

    [pub] = await _all_rows(session, PublicationModel)
    assert pub.status == PublicationStatus.SCHEDULED
    assert pub.ad_id == ad.id
    assert pub.slot_day is not None and pub.publish_at_utc is not None
    assert pub.slot_time.strftime("%H:%M") in slot_button
    assert pub.scheduler_job_id

    publish_jobs = [s for s in world.tasks.scheduled if s[0] == "publish_publication"]
    assert len(publish_jobs) == 1
    _, args, run_at, job_id = publish_jobs[0]
    assert args == (pub.id,)
    assert run_at == pub.publish_at_utc
    assert job_id == pub.scheduler_job_id

    # телефон сохранился в профиль пользователя
    session.expire_all()
    saved = await SQLAlchemyUserRepo(session).get_by_tg_id(700)
    assert saved.phone == "+79991234567"
    # напоминание о брошенном черновике поставлено при входе и снято после
    reminder = [s for s in world.tasks.scheduled if s[0] == "send_ad_draft_reminder"]
    assert reminder and reminder[0][3] in world.tasks.canceled


async def test_invalid_plate_is_rejected(world, session):
    await _setup(session)
    u = world.user(700)
    await u.send("/start")
    await u.click("ПРОДАТЬ")

    await u.send("12345")

    assert "Пришлите фото" not in u.last.text
    assert await _all_rows(session, AdModel) == []


async def test_invalid_phone_and_price_are_rejected(world, session):
    await _setup(session)
    u = world.user(700)
    await u.send("/start")
    await u.click("ПРОДАТЬ")
    await u.send("А123ВС77")
    await u.click("Пропустить")
    await u.send("москва")

    await u.send("12345")
    assert any("Некорректный номер телефона" in m.text for m in u.messages)
    assert "номер телефона" in u.last.text  # остались на том же шаге

    await u.send("89991234567")
    await u.send("дорого")
    assert "Выберите дату" not in u.last.text

    await u.click("Договорная")
    assert "Выберите дату и время" in u.last.text


async def test_huge_price_is_rejected_not_crashing(world, session):
    """ads.price — INTEGER: цена > 2^31 раньше роняла подтверждение."""
    await _setup(session)
    u = world.user(700)
    await u.send("/start")
    await u.click("ПРОДАТЬ")
    await u.send("А123ВС77")
    await u.click("Пропустить")
    await u.send("москва")
    await u.send("+79991234567")

    await u.send("5000000000")

    assert any("Слишком большая сумма" in m.text for m in u.messages)
    assert "Укажите стоимость" in u.last.text


async def test_photo_is_attached_to_ad(world, session):
    await _setup(session)
    u = world.user(700)
    await u.send("/start")
    await u.click("ПРОДАТЬ")
    await u.send("А123ВС77")
    await u.send_photo("my-plate-photo")
    assert "Ваше фото" in u.last.text
    await u.click("Далее")
    await u.send("москва")
    await u.send("+79991234567")
    await u.send("1000")
    await u.click(FREE_SLOT)
    await u.click("Подтвердить")

    [ad] = await _all_rows(session, AdModel)
    assert ad.image_file_id == "my-plate-photo"


async def test_same_plate_published_long_ago_can_be_reused(world, session):
    from datetime import datetime, timedelta, timezone

    from ..factories import make_ad, make_publication

    _, user = await _setup(session)
    old_ad = await make_ad(session, user, plate="А123ВС77")
    await make_publication(
        session,
        old_ad,
        status=PublicationStatus.PUBLISHED,
        publish_at_utc=datetime.now(timezone.utc) - timedelta(days=30),
    )
    await session.commit()
    u = world.user(700)
    await u.send("/start")
    await u.click("ПРОДАТЬ")
    await u.send("А123ВС77")

    assert "Вы уже публиковали этот номер" in u.last.text
    await u.click("Опубликовать снова")
    assert "Выберите дату и время" in u.last.text
    await u.click(FREE_SLOT)
    await u.click("Подтвердить")

    ad_ids = [a.id for a in await _all_rows(session, AdModel)]
    pubs = await _all_rows(session, PublicationModel)
    assert ad_ids == [old_ad.id], "повтор не должен плодить объявления"
    assert len(pubs) == 2
    new_pub = max(pubs, key=lambda p: p.id)
    assert (new_pub.ad_id, new_pub.status) == (old_ad.id, PublicationStatus.SCHEDULED)


async def test_same_plate_twice_a_week_is_limited_to_paid_slots(world, session):
    await _setup(session)
    u = world.user(700)
    await _fill_sale_until_calendar(u)
    await u.click(FREE_SLOT)
    await u.click("Подтвердить")
    await u.click("Пропустить")
    await u.click("Главное меню")

    await u.click("ПРОДАТЬ")
    await u.send("А123ВС77")
    await u.click("Опубликовать снова")
    blocked_slot = u.find_button(FREE_SLOT)[1].text  # напр. «Завтра-14:00»
    await u.click(FREE_SLOT)

    assert "Этот номер публиковался недавно" in u.last_alert
    assert "Выберите дату и время" in u.last.text  # остались в календаре
    assert len(await _all_rows(session, PublicationModel)) == 1
    # холд на заблокированный слот отпущен — другой пользователь может его взять
    hh_mm = blocked_slot.rsplit("-", 1)[1]
    held = [k.decode() for k in await world.redis.keys("hold:*")]
    assert not any(k.endswith(hh_mm) for k in held), held


async def test_paid_slot_is_charged_from_balance(world, session):
    _, user = await _setup(session, paid_slots=3, balance=Decimal("1000"))
    u = world.user(700)
    await _fill_sale_until_calendar(u)

    await u.click(PAID_SLOT)

    assert "Списано 199 руб." in (u.last_alert or "")
    await u.click("Подтвердить")

    session.expire_all()
    saved = await SQLAlchemyUserRepo(session).get_by_id(user.id)
    assert saved.balance == Decimal("801")
    [pub] = await _all_rows(session, PublicationModel)
    assert pub.status == PublicationStatus.SCHEDULED


async def test_paid_slot_without_balance_opens_payment(world, session):
    await _setup(session, paid_slots=3, balance=Decimal("0"))
    u = world.user(700)
    await _fill_sale_until_calendar(u)

    await u.click(PAID_SLOT)

    assert "способ оплаты" in u.last.text.lower()
    # черновик объявления сохранён, чтобы вернуться к нему после оплаты
    [ad] = await _all_rows(session, AdModel)
    assert ad.status == AdStatus.DRAFT
    assert await _all_rows(session, PublicationModel) == []


async def test_urgent_buyout_goes_to_admin_moderation(world, session):
    from .conftest import ADMIN_TG_ID

    await _setup(session)
    u = world.user(700)
    await u.send("/start")
    await u.click("Срочный выкуп")
    await u.send("А123ВС77")
    await u.click("Пропустить")
    await u.send("москва")
    await u.send("+79991234567")
    await u.send("100")
    assert "Выберите дату" not in u.last.text  # для выкупа цена обязательна,
    await u.send("500000")  # слот не выбирается
    assert "срочный выкуп" in u.last.text.lower()
    await u.click("Подтвердить")

    assert "Спасибо за Вашу заявку" in u.last.text
    [ad] = await _all_rows(session, AdModel)
    assert (ad.ad_type, ad.status) == (
        AdType.URGENT_BUYOUT,
        AdStatus.PENDING_MODERATION,
    )
    admin_msgs = world.tg.visible(ADMIN_TG_ID)
    assert admin_msgs, "админ должен получить заявку на модерацию"
    assert "А123ВС77" in admin_msgs[-1].text
    assert admin_msgs[-1].buttons, "у заявки должны быть кнопки модерации"
