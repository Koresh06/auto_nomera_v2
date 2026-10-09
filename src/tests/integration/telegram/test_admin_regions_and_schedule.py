"""Админка: настройки слотов и соцсети региона, расписание и отмена
публикации пользователя админом."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.models import PublicationModel, RegionModel

from ..factories import make_ad, make_publication, make_region, make_user, slot
from .conftest import ADMIN_TG_ID


async def _setup(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=ADMIN_TG_ID)
    await session.commit()
    admin = world.admin()
    await admin.send("/admin")
    return region, admin


async def _region(session, region_id) -> RegionModel:
    q = (
        select(RegionModel)
        .where(RegionModel.id == region_id)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(q)).scalar_one()


async def _open_settings(admin):
    await admin.click("Регионы")
    await admin.click("Список регионов")
    await admin.click("Москва")
    await admin.click("Настройки слотов")


async def test_toggle_publication_limit_flips_once_per_click(world, session):
    region, admin = await _setup(world, session)
    assert (await _region(session, region.id)).settings["publication_limit_enabled"]
    await _open_settings(admin)

    await admin.click("Лимит публикаций")
    assert (await _region(session, region.id)).settings[
        "publication_limit_enabled"
    ] is False

    await admin.click("Лимит публикаций")
    assert (await _region(session, region.id)).settings[
        "publication_limit_enabled"
    ] is True


async def test_slot_times_toggle_keeps_other_times(world, session):
    region, admin = await _setup(world, session)
    await _open_settings(admin)
    await admin.click("Изменить время слотов")

    await admin.click("12:00")
    assert (await _region(session, region.id)).settings["slot_times"] == [
        "10:00",
        "12:00",
        "14:00",
        "18:00",
    ]

    await admin.click("10:00")
    assert (await _region(session, region.id)).settings["slot_times"] == [
        "12:00",
        "14:00",
        "18:00",
    ]


async def test_cannot_remove_the_last_slot_time(world, session):
    from src.domain.value_objects.region_settings import RegionSettings
    from datetime import time

    region = await make_region(
        session, settings=RegionSettings(slot_times=(time(10, 0),))
    )
    await make_user(session, region.id, tg_id=ADMIN_TG_ID)
    await session.commit()
    admin = world.admin()
    await admin.send("/admin")
    await _open_settings(admin)
    await admin.click("Изменить время слотов")

    await admin.click("10:00")

    assert "хотя бы одно время" in admin.last_alert
    assert (await _region(session, region.id)).settings["slot_times"] == ["10:00"]


async def test_reset_settings_to_defaults(world, session):
    region, admin = await _setup(world, session)
    await _open_settings(admin)
    await admin.click("Горизонт календаря")
    await admin.send("20")

    await admin.click("По умолчанию")
    if "ещё раз" in (admin.last_alert or ""):
        await admin.click("По умолчанию")

    assert (await _region(session, region.id)).settings["days_range"] == 7


async def test_region_metadata_links(world, session):
    region, admin = await _setup(world, session)
    await admin.click("Регионы")
    await admin.click("Список регионов")
    await admin.click("Москва")
    await admin.click("Соцсети/каналы")

    await admin.click("VK-группа")
    await admin.send("not a link")
    assert any("Некорректная ссылка" in m.text for m in admin.messages)

    await admin.send("https://vk.com/nomera")
    assert (await _region(session, region.id)).metadata_["vk_group_url"] == (
        "https://vk.com/nomera"
    )

    await admin.click("Telegram-чат")
    await admin.send("-")
    assert (await _region(session, region.id)).metadata_["tg_group_url"] is None


# ------------------------------------------- расписание и отмена публикации


async def test_admin_sees_schedule_and_cancels_users_publication(world, session):
    region, admin = await _setup(world, session)
    owner = await make_user(session, region.id, tg_id=701, username="owner")
    ad = await make_ad(session, owner, plate="К777КК77")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    pub = await make_publication(
        session,
        ad,
        slot_key=slot(region.id, tomorrow, 10),
        publish_at_utc=datetime.now(timezone.utc) + timedelta(days=1),
    )
    pub.set_scheduler_job("job-owner")
    from src.infrastructure.repositories.publication.sqlalchemy import (
        SQLAlchemyPublicationRepo,
    )

    await SQLAlchemyPublicationRepo(session).save(pub)
    await session.commit()

    await admin.click("Статистика публикаций")
    await admin.click("Расписание по регионам")
    await admin.click("Москва")
    assert "К777КК77" in admin.last.text

    await admin.click("Каталог отложенных публикаций")
    assert "К777КК77" in admin.last.text  # сразу карточка публикации
    await admin.click("Отменить публикацию")
    if "ещё раз" in (admin.last_alert or ""):
        await admin.click("Отменить публикацию")

    q = select(PublicationModel).where(PublicationModel.id == pub.id)
    status = (
        (await session.execute(q.execution_options(populate_existing=True)))
        .scalar_one()
        .status
    )
    assert status == PublicationStatus.CANCELED
    assert "job-owner" in world.tasks.canceled


async def test_owner_is_told_when_admin_cancels_publication(world, session):
    await test_admin_sees_schedule_and_cancels_users_publication(world, session)

    owner_msgs = world.tg.visible(701)
    assert owner_msgs, "владелец должен узнать об отмене"
    assert "К777КК77" in owner_msgs[-1].text or "отмен" in owner_msgs[-1].text.lower()
