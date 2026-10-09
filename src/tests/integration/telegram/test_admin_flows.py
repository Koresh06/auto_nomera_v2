"""Админ-панель (/admin) — сквозные сценарии через бота."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.domain.enums.payment import PaymentMethod, PaymentPurpose
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.enums.region import RegionStatus
from src.domain.enums.role import UserRole
from src.infrastructure.database.models import (
    PublicationModel,
    RegionModel,
    ServiceDefinitionModel,
)
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from ..factories import (
    make_ad,
    make_payment,
    make_publication,
    make_region,
    make_user,
)
from .conftest import ADMIN_TG_ID


async def _user(session, tg_id):
    session.expire_all()
    return await SQLAlchemyUserRepo(session).get_by_tg_id(tg_id)


async def _admin_world(world, session, **user_kw):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=ADMIN_TG_ID)
    target = await make_user(session, region.id, tg_id=777, **user_kw)
    await session.commit()
    admin = world.admin()
    await admin.send("/admin")
    assert "Админ-панель" in admin.last.text
    return region, target, admin


# ---------------------------------------------------------------- доступ


async def test_non_admin_has_no_admin_panel(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=777)
    await session.commit()
    u = world.user(777)

    await u.send("/admin")

    assert not any("Админ-панель" in m.text for m in u.messages)


async def test_promoted_admin_gets_panel_and_loses_it_after_revoke(world, session):
    _, _, admin = await _admin_world(world, session)
    await admin.click("Управление админами")
    await admin.click("Добавить администратора")
    await admin.send("777")
    await admin.click("Назначить администратором")
    assert (await _user(session, 777)).role == UserRole.ADMIN

    promoted = world.user(777)
    await promoted.send("/admin")
    assert "Админ-панель" in promoted.last.text

    await admin.send("/admin")
    await admin.click("Управление админами")
    await admin.click("777")
    await admin.click("Снять права")
    assert (await _user(session, 777)).role == UserRole.USER

    world.tg.reset()
    await promoted.send("/admin")
    assert not any("Админ-панель" in m.text for m in promoted.messages)


async def test_revoked_admin_cannot_use_already_open_admin_dialog(world, session):
    """Права проверяются на каждое действие: бывший админ с открытой
    админ-панелью не может, например, начислить себе баланс."""
    _, _, admin = await _admin_world(world, session)
    await admin.click("Управление админами")
    await admin.click("Добавить администратора")
    await admin.send("777")
    await admin.click("Назначить администратором")
    ex_admin = world.user(777)
    await ex_admin.send("/admin")
    await ex_admin.click("Рассылки")  # диалог открыт, пока права есть
    await ex_admin.click("Внутри бота")

    await admin.send("/admin")
    await admin.click("Управление админами")
    await admin.click("777")
    await admin.click("Снять права")

    await ex_admin.send("Спам всем пользователям")  # ввод в открытом диалоге

    assert any("Доступ к админ-панели закрыт" in m.text for m in ex_admin.messages)
    assert world.tasks.enqueued == []


# ---------------------------------------------------------------- баланс


async def _open_balance(admin, tg_id="777"):
    await admin.click("Баланс пользователей")
    await admin.send(tg_id)


async def test_admin_tops_up_and_charges_balance(world, session):
    _, _, admin = await _admin_world(world, session, balance=Decimal("100"))
    await _open_balance(admin)
    assert "100" in admin.last.text

    await admin.click("Изменить баланс")
    await admin.send("+500")
    await admin.click("Подтвердить")
    assert (await _user(session, 777)).balance == Decimal("600")

    await admin.send("/admin")
    await _open_balance(admin)
    await admin.click("Изменить баланс")
    await admin.send("-1000")
    await admin.click("Подтвердить")
    assert "Недостаточно средств" in admin.last_alert
    assert (await _user(session, 777)).balance == Decimal("600")


@pytest.mark.parametrize("bad", ["500", "+NaN", "+Infinity", "+0", "abc"])
async def test_admin_balance_rejects_bad_amounts(world, session, bad):
    _, _, admin = await _admin_world(world, session, balance=Decimal("100"))
    await _open_balance(admin)
    await admin.click("Изменить баланс")

    await admin.send(bad)

    assert "Подтвердить" not in " ".join(admin.last.button_texts)
    assert (await _user(session, 777)).balance == Decimal("100")


async def test_admin_balance_unknown_user(world, session):
    _, _, admin = await _admin_world(world, session)
    await _open_balance(admin, "123456")
    assert any("не найден" in m.text for m in admin.messages)


# ---------------------------------------------------------------- блокировка


async def test_block_takes_effect_immediately_despite_cache(world, session):
    _, _, admin = await _admin_world(world, session)
    victim = world.user(777)
    await victim.send("/start")  # флаги блокировки попали в кеш
    assert "Выберите действие" in victim.last.text

    await admin.click("Блокировка пользователя")
    await admin.send("777")
    await admin.click("Заблокировать")
    assert (await _user(session, 777)).is_blocked

    await victim.send("/start")
    assert victim.last.text == "🚫 Вы заблокированы в этом боте."

    await admin.click("Разблокировать")
    await victim.send("/start")
    assert "Выберите действие" in victim.last.text


async def test_block_payments_only(world, session):
    _, _, admin = await _admin_world(world, session)
    await admin.click("Блокировка пользователя")
    await admin.send("777")
    await admin.click("Заблокировать платежи")

    u = world.user(777)
    await u.send("/start")
    await u.click("Пополнить баланс")
    await u.send("500")
    await u.click("TG Stars")
    assert "Платежи для вашего аккаунта заблокированы" in u.last_alert


# ---------------------------------------------------------------- услуги


async def test_admin_changes_service_price_and_users_see_it(world, session):
    _, _, admin = await _admin_world(world, session)
    await admin.click("Платные услуги")
    await admin.click("Закрепление")
    await admin.click("Изменить цену")
    await admin.send("777")

    q = select(ServiceDefinitionModel).where(
        ServiceDefinitionModel.type == PublicationServiceType.PIN
    )
    pin = (
        await session.execute(q.execution_options(populate_existing=True))
    ).scalar_one()
    assert pin.price == 777

    await admin.send("/admin")
    await admin.click("Платные услуги")
    assert any("Закрепление — 777 руб." in b for b in admin.last.button_texts)


async def test_admin_disables_service(world, session):
    _, _, admin = await _admin_world(world, session)
    await admin.click("Платные услуги")
    await admin.click("Закрепление")
    await admin.click("Снять с продажи")
    assert "ещё раз" in admin.last_alert  # двойное подтверждение
    await admin.click("Снять с продажи")

    q = select(ServiceDefinitionModel).where(
        ServiceDefinitionModel.type == PublicationServiceType.PIN
    )
    pin = (
        await session.execute(q.execution_options(populate_existing=True))
    ).scalar_one()
    assert pin.is_active is False


# ---------------------------------------------------------------- регионы


async def _create_region_steps(
    admin,
    *,
    title="Тверь",
    tz="Europe/Moscow",
    channel="-1009999",
    username="tver_nomera",
):
    await admin.click("Регионы")
    await admin.click("Создать регион")
    await admin.send(title)
    await admin.send(tz)
    await admin.send(channel)
    await admin.send(username)


async def test_admin_creates_region(world, session):
    _, _, admin = await _admin_world(world, session)

    await _create_region_steps(admin)
    await admin.click("Пропустить")
    await admin.click("Пропустить")
    await admin.click("Пропустить")
    await admin.click("Подтвердить")

    q = select(RegionModel).where(RegionModel.title == "Тверь")
    region = (await session.execute(q)).scalar_one()
    assert (region.channel_id, region.channel_username) == (-1009999, "tver_nomera")
    assert region.status == RegionStatus.ACTIVE


@pytest.mark.parametrize(
    "step,value",
    [
        ("tz", "Mars/Olympus"),
        ("tz", "../../etc/passwd"),
        ("channel", "12345"),
        ("channel", "0"),
        ("username", "ab"),
        ("username", "a" * 65),
        ("title", "Т" * 65),
    ],
)
async def test_region_creation_validates_input(world, session, step, value):
    _, _, admin = await _admin_world(world, session)
    kw = {
        "title": "Тверь",
        "tz": "Europe/Moscow",
        "channel": "-1009999",
        "username": "tver_nomera",
    }
    kw[step] = value

    await _create_region_steps(admin, **kw)
    if "Пропустить" in " ".join(admin.last.button_texts):
        await admin.click("Пропустить")
        await admin.click("Пропустить")
        await admin.click("Пропустить")
        await admin.click("Подтвердить")

    q = select(RegionModel).where(RegionModel.channel_id == -1009999)
    assert (await session.execute(q)).scalars().all() == []


async def _open_region_settings(admin, title="Москва"):
    await admin.click("Регионы")
    await admin.click("Список регионов")
    await admin.click(title)
    await admin.click("Настройки слотов")


async def _region(session, region_id):
    q = (
        select(RegionModel)
        .where(RegionModel.id == region_id)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(q)).scalar_one()


async def test_admin_edits_region_settings(world, session):
    region, _, admin = await _admin_world(world, session)
    await _open_region_settings(admin)

    await admin.click("Горизонт календаря")
    await admin.send("14")
    await admin.click("Цена платного слота")
    await admin.send("349,50")
    await admin.click("Кол-во платных слотов")
    await admin.send("5")

    s = (await _region(session, region.id)).settings
    assert (s["days_range"], s["paid_slot_price"], s["system_paid_slots_count"]) == (
        14,
        "349.50",
        5,
    )


@pytest.mark.parametrize(
    "button,value",
    [
        ("Горизонт календаря", "0"),
        ("Горизонт календаря", "99"),
        ("Горизонт календаря", "abc"),
        ("Цена платного слота", "-1"),
        ("Цена платного слота", "Infinity"),
        ("Цена платного слота", "NaN"),
        ("Кол-во платных слотов", "-3"),
    ],
)
async def test_region_settings_reject_bad_values(world, session, button, value):
    region, _, admin = await _admin_world(world, session)
    before = (await _region(session, region.id)).settings
    await _open_region_settings(admin)

    await admin.click(button)
    await admin.send(value)

    assert any("⚠️" in m.text for m in admin.messages)
    assert (await _region(session, region.id)).settings == before


async def test_changed_paid_slot_price_is_charged(world, session):
    """Цена платного слота из настроек региона реально списывается."""
    from .test_create_ad_flow import PAID_SLOT, _fill_sale_until_calendar

    region, _, admin = await _admin_world(world, session, balance=Decimal("1000"))
    await _open_region_settings(admin)
    await admin.click("Цена платного слота")
    await admin.send("250")

    u = world.user(777)
    await _fill_sale_until_calendar(u)
    await u.click(PAID_SLOT)

    assert "Списано 250" in u.last_alert
    assert (await _user(session, 777)).balance == Decimal("750")


# ---------------------------------------------------------------- рассылка


async def test_mailing_to_all_users_is_enqueued(world, session):
    _, _, admin = await _admin_world(world, session)
    await admin.click("Рассылки")
    await admin.click("Внутри бота")
    await admin.send("Привет всем!")
    await admin.click("Отправить")

    [(name, args)] = world.tasks.enqueued
    assert name == "execute_mailing"
    assert args[0] == "to_all" or "all" in str(args[0])


async def test_mailing_to_region(world, session):
    region, _, admin = await _admin_world(world, session)
    await admin.click("Рассылки")
    await admin.click("В регион")
    await admin.click("Москва")
    await admin.send("Новости региона")
    await admin.click("Отправить")

    [(name, args)] = world.tasks.enqueued
    assert name == "execute_mailing"
    assert args[3] == region.id


# ---------------------------------------------------------------- статистика


@pytest.mark.parametrize(
    "button", ["Статистика пополнений", "Статистика публикаций", "Общая статистика"]
)
async def test_stats_screens_render_with_data(world, session, button):
    region, target, admin = await _admin_world(world, session)
    await make_payment(session, target, external_id="p1", amount=Decimal("500"))
    await make_payment(
        session,
        target,
        external_id="p2",
        amount=Decimal("300"),
        method=PaymentMethod.TELEGRAM_STARS,
        meta={"stars_amount": 180},
        purpose=PaymentPurpose.PUBLICATION_SERVICE,
    )
    ad = await make_ad(session, target)
    await make_publication(session, ad)
    await session.commit()

    await admin.click(button)
    assert admin.last.text

    # переключатели периода: выбранный помечается 🟢, поэтому кликаем по
    # «чистому» названию
    for period in ("Сегодня", "Неделя", "Месяц", "Всё"):
        await admin.click(period)
        assert admin.last.text


# ------------------------------------------------- неопубликованные вовремя


async def test_overdue_publications_can_be_published_by_admin(world, session):
    region, target, admin = await _admin_world(world, session)
    from zoneinfo import ZoneInfo

    from src.domain.value_objects.slot_key import SlotKey

    ad = await make_ad(session, target)
    # «просрочена сегодня» по местному времени: середина между местной
    # полуночью и текущим моментом (тест не должен зависеть от времени суток)
    now_local = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Moscow"))
    midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    local = midnight + (now_local - midnight) / 2
    publish_at = local.astimezone(timezone.utc)
    overdue = await make_publication(
        session,
        ad,
        publish_at_utc=publish_at,
        slot_key=SlotKey(
            region_id=region.id,
            local_day=local.date(),
            local_time=local.time().replace(second=0, microsecond=0),
        ),
    )
    await session.commit()

    await admin.send("/admin")
    await admin.click("Не опубликованные")
    slot_buttons = [b for b in admin.last.button_texts if "Назад" not in b]
    assert slot_buttons, admin.last.text
    await admin.click(slot_buttons[0])
    assert "А123ВС77" in admin.last.text
    await admin.click("Опубликовать всё")

    assert "Опубликовано: 1" in admin.last_alert
    q = select(PublicationModel).where(PublicationModel.id == overdue.id)
    pub = (
        await session.execute(q.execution_options(populate_existing=True))
    ).scalar_one()
    assert pub.status == PublicationStatus.PUBLISHED
    [post] = world.tg.visible(region.channel_id)
    assert "А123ВС77" in post.text


async def test_regular_admin_cannot_open_super_admin_sections(world, session):
    """Назначенный через бота админ видит урезанное меню, но скрытые
    кнопки обрабатывают подделанные нажатия — разделы супер-админа
    (балансы, блокировки, назначение админов...) проверяются на сервере."""
    from .harness import forge_click

    _, _, admin = await _admin_world(world, session, balance=Decimal("0"))
    await admin.click("Управление админами")
    await admin.click("Добавить администратора")
    await admin.send("777")
    await admin.click("Назначить администратором")
    regular = world.user(777)
    await regular.send("/admin")
    assert not any("Баланс" in b for b in regular.last.button_texts)

    await forge_click(regular, "user_balance")  # скрытая кнопка меню
    await regular.send("777")  # первое же действие в разделе — отказ

    assert "Доступ к админ-панели закрыт" in regular.last.text
    assert not any("Изменить баланс" in b for b in regular.last.button_texts)
    assert (await _user(session, 777)).balance == Decimal("0")


def test_every_admin_dialog_is_guarded():
    """Каждый диалог из features/admin должен быть в get_admin_dialogs(),
    иначе на него не повесится AdminDialogGuardMiddleware."""
    from src.presentation.telegram.features import get_admin_dialogs, get_all_dialogs

    guarded = {id(d) for d in get_admin_dialogs()}
    for d in get_all_dialogs():
        under_admin = ".features.admin." in d.states_group().__module__
        assert under_admin == (id(d) in guarded), d.states_group_name()


def test_super_admin_dialogs_match_menu_visibility():
    """Разделы, скрытые в меню для обычных админов (when=is_super_admin),
    должны быть ровно теми, что охраняются как супер-админские."""
    import inspect
    import re

    from src.presentation.telegram.features import get_super_admin_dialogs
    from src.presentation.telegram.features.admin.modules.menu import dialogs

    source = inspect.getsource(dialogs)
    hidden = set(
        re.findall(r"state=(\w+)\.\w+,\s*when=F\[\"is_super_admin\"\]", source)
    )
    guarded = {d.states_group().__name__ for d in get_super_admin_dialogs()}
    assert hidden, "не нашли скрытых супер-админских разделов"
    assert hidden <= guarded, hidden - guarded


@pytest.mark.parametrize(
    "button,value",
    [
        ("Изменить цену", "99999999999"),
        ("Изменить цену", "-5"),
        ("Изменить длительность", "100000000000"),
        ("Изменить длительность", "0"),
        ("Изменить название", "Н" * 129),
        ("Изменить описание", "о" * 257),
    ],
)
async def test_service_fields_reject_out_of_range_values(world, session, button, value):
    _, _, admin = await _admin_world(world, session)
    await admin.click("Платные услуги")
    await admin.click("Закрепление")
    await admin.click(button)

    await admin.send(value)

    assert any("⚠️" in m.text for m in admin.messages)
    q = select(ServiceDefinitionModel).where(
        ServiceDefinitionModel.type == PublicationServiceType.PIN
    )
    pin = (
        await session.execute(q.execution_options(populate_existing=True))
    ).scalar_one()
    assert (pin.price, pin.duration_days) == (499, 3)
