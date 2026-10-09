"""«Мои объявления»: список, редактирование полей, удаление."""

from sqlalchemy import select

from src.domain.enums.publication import PublicationStatus
from src.infrastructure.database.models import AdModel

from .test_paid_services_flow import (
    CHANNEL_ID,
    _create_ad_until_services,
    _pubs,
    _run_publish_worker,
)


async def _ad(session) -> AdModel:
    q = select(AdModel).execution_options(populate_existing=True)
    [ad] = (await session.execute(q)).scalars().all()
    return ad


async def _open_my_ad(u):
    await u.click("Главное меню")
    await u.click("Мои объявления")
    assert "Мои объявления" in u.last.text
    await u.click("А123ВС77")
    assert "Номер:</b> А123ВС77" in u.last.text


async def _edit(u, button: str, value: str):
    await u.click(button)
    await u.send(value)
    assert "Подтвердите изменение" in u.last.text, u.last.text
    await u.click("Применить")


async def test_my_ads_lists_created_ad(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    await _open_my_ad(u)
    assert any("Изменить номер" in b for b in u.last.button_texts)


async def test_edit_city_phone_and_plate_of_scheduled_ad(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    await _open_my_ad(u)

    await _edit(u, "Изменить город", "казань")
    await _edit(u, "Изменить телефон", "89990000000")
    await _edit(u, "Изменить номер", "В777ОР199")

    ad = await _ad(session)
    assert ad.city == "казань" or ad.city == "Казань"
    assert ad.phone == "89990000000"
    assert ad.plate_number == "В777ОР199"
    assert "В777ОР199" in u.last.text


async def test_edit_price_uses_same_rules_as_creation(world, session):
    """При создании «150» означает 150 000 ₽ (validate_price умножает
    1..999 на 1000). Редактирование обязано трактовать ввод так же."""
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    await _open_my_ad(u)

    await _edit(u, "Изменить цену", "150")

    assert (await _ad(session)).price == 150_000


async def test_edit_price_with_separators_does_not_crash(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    await _open_my_ad(u)

    await _edit(u, "Изменить цену", "1.200.000")

    assert (await _ad(session)).price == 1_200_000


async def test_edit_same_value_is_refused(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    await _open_my_ad(u)

    await u.click("Изменить город")
    await u.send("Москва")

    assert any("то же самое значение" in m.text for m in u.messages)


async def test_edit_from_finish_screen(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    await u.click("Редактировать объявление")
    assert "Номер:</b> А123ВС77" in u.last.text

    await _edit(u, "Изменить город", "тверь")

    assert (await _ad(session)).city.lower() == "тверь"


async def test_published_ad_edit_updates_channel_post(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    [pub] = await _pubs(session)
    await _run_publish_worker(world, pub.id)
    await _open_my_ad(u)

    # номер опубликованного объявления менять нельзя — кнопки нет
    assert not any("Изменить номер" in b for b in u.last.button_texts)

    await _edit(u, "Изменить город", "сочи")

    [post] = world.tg.visible(CHANNEL_ID)
    assert "Сочи" in post.text or "сочи" in post.text, post.text


async def test_delete_requires_confirmation_and_cancels_job(world, session):
    u = await _create_ad_until_services(world, session)
    await u.click("Пропустить")
    [pub] = await _pubs(session)
    job = pub.scheduler_job_id
    await _open_my_ad(u)

    await u.click("Удалить")
    assert "Нажмите ещё раз" in u.last_alert
    [pub] = await _pubs(session)
    assert pub.status == PublicationStatus.SCHEDULED

    await u.click("Удалить")

    [pub] = await _pubs(session)
    assert pub.status == PublicationStatus.CANCELED
    assert job in world.tasks.canceled
    assert "нет объявлений" in u.last.text


async def test_delete_after_priority_publish_cancels_the_live_job(world, session):
    """Регрессия: после «Вне очереди» в БД оставался id отменённой задачи,
    и удаление снимало не ту задачу."""
    u = await _create_ad_until_services(world, session, balance="1000")
    await u.click("Вне очереди")
    await u.click("Пропустить")
    await u.click("Главное меню")
    [pub] = await _pubs(session)
    live_job = pub.scheduler_job_id
    await u.click("Мои объявления")
    await u.click("А123ВС77")

    await u.click("Удалить")
    await u.click("Удалить")

    assert live_job in world.tasks.canceled


async def test_delete_ad_cancels_autopublish_series(world, session):
    u = await _create_ad_until_services(world, session, balance="1000")
    await u.click("Автопубликация")
    await u.click("Пропустить")
    [parent] = await _pubs(session)
    await _run_publish_worker(world, parent.id)
    children = (await _pubs(session))[1:]
    assert children
    await _open_my_ad(u)

    await u.click("Удалить")
    await u.click("Удалить")

    pubs = await _pubs(session)
    alive = [p.id for p in pubs if p.status == PublicationStatus.SCHEDULED]
    assert alive == [], "удалённое объявление не должно продолжать выходить"
    assert {c.scheduler_job_id for c in children} <= set(world.tasks.canceled)
