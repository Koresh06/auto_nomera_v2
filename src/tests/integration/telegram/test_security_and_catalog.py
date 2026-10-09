"""Права доступа и «Ранний доступ».

Видимость кнопки (`when=`) в aiogram-dialog не защищает: скрытые кнопки
обрабатывают callback, а callback_data модифицированный клиент может
прислать любой. Тесты ниже подделывают нажатия так же, как это сделал бы
злоумышленник, и проверяют, что права проверяются на сервере."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication_service import PublicationServiceType
from src.infrastructure.database.models import AdModel, PublicationModel
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo
from src.presentation.telegram.keyboards.urgent_moderation import (
    UrgentModerationAction,
    UrgentModerationCD,
    build_urgent_moderation_kb,
)

from ..factories import make_ad, make_publication, make_region, make_user
from .conftest import ADMIN_TG_ID
from .harness import forge_click, forge_raw_callback

SUBSCRIBED = datetime.now(timezone.utc) + timedelta(days=10)


async def _world_with_urgent(session, *, viewer_sub=None):
    region = await make_region(session)
    seller = await make_user(session, region.id, tg_id=1)
    ad = await make_ad(
        session,
        seller,
        plate="Е001КХ77",
        ad_type=AdType.URGENT_BUYOUT,
        status=AdStatus.PUBLISHED,
    )
    await make_user(
        session, region.id, tg_id=990, pre_publication_expires_at=viewer_sub
    )
    await session.commit()
    return region, seller, ad


async def _ad_status(session, ad_id):
    q = (
        select(AdModel.status)
        .where(AdModel.id == ad_id)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(q)).scalar_one()


# ------------------------------------------------------------ каталог


async def test_subscriber_browses_early_access_catalog(world, session):
    await _world_with_urgent(session, viewer_sub=SUBSCRIBED)
    u = world.user(990)
    await u.send("/start")
    await u.click("Ранний доступ")

    assert "Список объявлений" in u.last.text
    await u.click("Е001КХ77")

    assert "СРОЧНЫЙ ВЫКУП" in u.last.text
    assert "+79990000000" in u.last.text
    assert not any("Удалить" in b for b in u.last.button_texts)


async def test_catalog_shows_upcoming_publications_in_window(world, session):
    region = await make_region(session)
    seller = await make_user(session, region.id, tg_id=1)
    ad = await make_ad(session, seller, plate="М555ММ77")
    await make_publication(
        session, ad, publish_at_utc=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    await make_user(
        session, region.id, tg_id=990, pre_publication_expires_at=SUBSCRIBED
    )
    await session.commit()
    u = world.user(990)
    await u.send("/start")
    await u.click("Ранний доступ")

    assert any("М555ММ77" in b for b in u.last.button_texts)


async def test_non_subscriber_sees_paywall(world, session):
    await _world_with_urgent(session)
    u = world.user(990)
    await u.send("/start")
    await u.click("Ранний доступ")

    assert "Получить доступ" in " ".join(u.last.button_texts)
    assert "Е001КХ77" not in " ".join(u.last.button_texts)


async def test_non_subscriber_cannot_open_card_by_forged_click(world, session):
    await _world_with_urgent(session)
    u = world.user(990)
    await u.send("/start")
    await u.click("Ранний доступ")

    await forge_click(u, "catalog_select:0")

    texts = "\n".join(m.text for m in u.messages)
    assert "+79990000000" not in texts, "контакты продавца утекли без подписки"
    assert "Е001КХ77" not in texts


async def test_non_admin_cannot_delete_catalog_ad_by_forged_click(world, session):
    _, _, ad = await _world_with_urgent(session, viewer_sub=SUBSCRIBED)
    u = world.user(990)
    await u.send("/start")
    await u.click("Ранний доступ")
    await u.click("Е001КХ77")

    await forge_click(u, "delete_current_ad")
    await forge_click(u, "delete_current_ad")

    assert await _ad_status(session, ad.id) == AdStatus.PUBLISHED
    assert "Недостаточно прав" in u.last_alert


async def test_admin_can_delete_catalog_ad(world, session):
    region, _, ad = await _world_with_urgent(session)
    await make_user(
        session, region.id, tg_id=ADMIN_TG_ID, pre_publication_expires_at=SUBSCRIBED
    )
    await session.commit()
    admin = world.admin()
    await admin.send("/start")
    await admin.click("Ранний доступ")
    await admin.click("Е001КХ77")

    await admin.click("Удалить")
    await admin.click("Удалить")

    assert await _ad_status(session, ad.id) == AdStatus.ARCHIVED


# ------------------------------------------------- модерация срочного выкупа


async def _pending_urgent(session):
    region = await make_region(session)
    seller = await make_user(session, region.id, tg_id=1)
    ad = await make_ad(
        session,
        seller,
        ad_type=AdType.URGENT_BUYOUT,
        status=AdStatus.PENDING_MODERATION,
    )
    await make_user(session, region.id, tg_id=990)
    await session.commit()
    return ad


async def test_admin_approves_urgent_buyout(world, session):
    ad = await _pending_urgent(session)
    admin = world.admin()
    # заявка, которую бот прислал админу (как в NotifyAdminsAboutUrgent)
    world.tg._new_message(
        ADMIN_TG_ID, text="заявка", reply_markup=await build_urgent_moderation_kb(ad.id)
    )

    await admin.click("Одобрить")

    assert await _ad_status(session, ad.id) == AdStatus.PUBLISHED
    assert "одобрена" in admin.last_alert
    # подписчики получают уведомление через очередь
    assert ("notify_pre_publication_users", (ad.id,)) in world.tasks.enqueued


async def test_admin_rejects_urgent_buyout(world, session):
    ad = await _pending_urgent(session)
    admin = world.admin()
    world.tg._new_message(
        ADMIN_TG_ID, text="заявка", reply_markup=await build_urgent_moderation_kb(ad.id)
    )

    await admin.click("Отклонить")

    assert await _ad_status(session, ad.id) == AdStatus.ARCHIVED


async def test_non_admin_cannot_moderate_urgent_buyout(world, session):
    ad = await _pending_urgent(session)
    u = world.user(990)
    await u.send("/start")

    data = UrgentModerationCD(action=UrgentModerationAction.APPROVE, ad_id=ad.id)
    await forge_raw_callback(u, data.pack())

    assert await _ad_status(session, ad.id) == AdStatus.PENDING_MODERATION
    assert world.tasks.enqueued == []


# ------------------------------------------------- «Продать быстрее» (IDOR)


async def test_cannot_buy_service_for_someone_elses_publication(world, session):
    region = await make_region(session)
    victim = await make_user(session, region.id, tg_id=1)
    victim_ad = await make_ad(session, victim, plate="Х001ХХ77")
    victim_pub = await make_publication(
        session,
        victim_ad,
        publish_at_utc=datetime.now(timezone.utc) + timedelta(days=2),
    )
    attacker = await make_user(session, region.id, tg_id=991, balance=Decimal("5000"))
    my_ad = await make_ad(session, attacker, plate="А002АА77")
    await make_publication(
        session, my_ad, publish_at_utc=datetime.now(timezone.utc) + timedelta(days=2)
    )
    await session.commit()
    u = world.user(991)
    await u.send("/start")
    await u.click("Продать быстрее")
    await u.click("Вне очереди")
    assert any("А002АА77" in b for b in u.last.button_texts)

    await forge_click(u, f"ad_select:{victim_pub.id}")
    if any("Подключить" in b for b in u.last.button_texts):
        await u.click("Подключить")

    q = select(PublicationModel).where(PublicationModel.id == victim_pub.id)
    pub = (
        await session.execute(q.execution_options(populate_existing=True))
    ).scalar_one()
    assert PublicationServiceType.PRIORITY_PUBLISH not in {s.type for s in pub.services}
    session.expire_all()
    me = await SQLAlchemyUserRepo(session).get_by_tg_id(991)
    assert me.balance == Decimal("5000")


async def test_buy_priority_from_services_menu_for_own_ad(world, session):
    region = await make_region(session)
    me = await make_user(session, region.id, tg_id=991, balance=Decimal("5000"))
    my_ad = await make_ad(session, me, plate="А002АА77")
    pub = await make_publication(
        session, my_ad, publish_at_utc=datetime.now(timezone.utc) + timedelta(days=2)
    )
    pub.set_scheduler_job("old-job")
    from src.infrastructure.repositories.publication.sqlalchemy import (
        SQLAlchemyPublicationRepo,
    )

    await SQLAlchemyPublicationRepo(session).save(pub)
    await session.commit()
    u = world.user(991)
    await u.send("/start")
    await u.click("Продать быстрее")
    await u.click("Вне очереди")
    await u.click("А002АА77")
    await u.click("Подключить")

    assert "подключена" in u.last_alert
    session.expire_all()
    assert (await SQLAlchemyUserRepo(session).get_by_tg_id(991)).balance == Decimal(
        "4701"
    )
    assert "old-job" in world.tasks.canceled


# ------------------------------------------- прочие скрытые кнопки (when=)


async def test_forged_click_cannot_register_into_disabled_region(world, session):
    from src.infrastructure.repositories.region.sqlalchemy import (
        SQLAlchemyRegionRepository,
    )

    await make_region(session, title="Активный")
    off = await make_region(session, title="Выключенный", channel_id=-9)
    off.disable()
    await SQLAlchemyRegionRepository(session).update(off)
    await session.commit()
    u = world.user(992)
    await u.send("/start")

    await forge_click(u, f"region_id:{off.id}")

    session.expire_all()
    user = await SQLAlchemyUserRepo(session).get_by_tg_id(992)
    assert user is None or user.region_id != off.id
    assert "недоступен" in u.last_alert


@pytest.mark.allow_bot_errors  # use case отказывает исключением — это и защищает
async def test_forged_click_cannot_publish_empty_store(world, session):
    from .test_create_ad_flow import FREE_SLOT
    from .test_store_flow import _create_store, _new_user

    u = await _new_user(world, session)
    await _create_store(u)
    await u.click("Просмотр и Публикация")
    assert not any("Публикация" in b for b in u.last.button_texts)

    await forge_click(u, "__next__")  # «✅ Публикация» скрыта без номеров
    assert "Выберите дату" in u.last.text
    await u.click(FREE_SLOT)
    await u.click("Подтвердить")

    assert "Произошла ошибка" in u.last_alert
    q = select(PublicationModel).execution_options(populate_existing=True)
    assert (await session.execute(q)).scalars().all() == []


async def test_forged_click_cannot_create_second_store(world, session):
    from .test_store_flow import _create_store, _new_user

    u = await _new_user(world, session)
    await _create_store(u)
    await u.click("Главное меню")
    assert "Выберите действие" in u.last.text

    await forge_click(u, "create_store")  # кнопка скрыта: магазин уже есть
    assert "Создание Вашего магазина" in u.last.text
    await u.click("Да")
    await u.send("Второй Магазин")
    await u.send("москва")
    await u.send("+79991112233")
    await u.click("Подтвердить")

    assert u.last_alert == "⚠️ У вас уже есть магазин."
    q = (
        select(AdModel)
        .where(AdModel.ad_type == AdType.STORE)
        .execution_options(populate_existing=True)
    )
    assert len((await session.execute(q)).scalars().all()) == 1


async def test_urgent_buyout_cannot_be_negotiable_by_forged_click(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=993)
    await session.commit()
    u = world.user(993)
    await u.send("/start")
    await u.click("Срочный выкуп")
    await u.send("А123ВС77")
    await u.click("Пропустить")
    await u.send("москва")
    await u.send("+79991234567")

    await forge_click(u, "negotiable_price")

    assert "укажите сумму" in u.last_alert
    assert "Укажите примерную сумму" in u.last.text


async def test_existing_user_cannot_switch_into_disabled_region(world, session):
    from src.infrastructure.repositories.region.sqlalchemy import (
        SQLAlchemyRegionRepository,
    )

    home = await make_region(session, title="Дом")
    off = await make_region(session, title="Выключенный", channel_id=-9)
    off.disable()
    await SQLAlchemyRegionRepository(session).update(off)
    await make_user(session, home.id, tg_id=994)
    await session.commit()
    u = world.user(994)
    await u.send("/start")
    await u.click("Смена региона")

    await forge_click(u, f"region_id:{off.id}")

    session.expire_all()
    user = await SQLAlchemyUserRepo(session).get_by_tg_id(994)
    assert user.region_id == home.id
