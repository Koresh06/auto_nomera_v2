"""Магазин: создание, добавление/редактирование номеров, публикация."""

from sqlalchemy import select

from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
)
from src.domain.enums.ad import AdType
from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.region_settings import RegionSettings
from src.infrastructure.database.models import AdModel, PublicationModel

from ..factories import make_region, make_user
from .test_create_ad_flow import FREE_SLOT

CHANNEL_ID = -1001


async def _store(session) -> AdModel:
    q = (
        select(AdModel)
        .where(AdModel.ad_type == AdType.STORE)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(q)).scalar_one()


async def _pubs(session):
    q = select(PublicationModel).execution_options(populate_existing=True)
    return list((await session.execute(q)).scalars().all())


async def _new_user(world, session, *, phone=None):
    region = await make_region(
        session,
        channel_id=CHANNEL_ID,
        settings=RegionSettings(system_paid_slots_count=0),
    )
    await make_user(session, region.id, tg_id=950, username="shopper", phone=phone)
    await session.commit()
    u = world.user(950, username="shopper")
    await u.send("/start")
    return u


async def _create_store(u):
    await u.click("Создать магазин")
    await u.click("Да")
    assert "название Вашего магазина" in u.last.text
    await u.send("Номера-Плюс")
    await u.send("москва")
    await u.send("+79991112233")
    assert "Номера-Плюс" in u.last.text
    await u.click("Подтвердить")
    await u.click("Мой магазин")


async def _add_items(u, text: str):
    await u.click("Добавить номера")
    await u.send(text)


async def test_create_store_via_menu(world, session):
    u = await _new_user(world, session)

    await _create_store(u)

    store = await _store(session)
    assert (store.shop_name, store.phone) == ("Номера-Плюс", "+79991112233")
    assert store.city.lower() == "москва"
    assert store.store_items in (None, [])
    # в меню теперь «Мой магазин» вместо «Создать магазин»
    await u.click("Главное меню")
    assert any("Мой магазин" in b for b in u.last.button_texts)
    assert not any("Создать магазин" in b for b in u.last.button_texts)


async def test_add_items_parses_both_separators_and_saves(world, session):
    u = await _new_user(world, session)
    await _create_store(u)

    await _add_items(u, "x111xx01-1 000 000\nо100оо77 500000")

    assert "Проверьте введённые номера" in u.last.text
    await u.click("Сохранить")
    assert "Номера добавлены" in u.last.text

    store = await _store(session)
    assert store.store_items == [
        {"plate": "Х111ХХ01", "price": 1_000_000},
        {"plate": "О100ОО77", "price": 500_000},
    ]


async def test_add_items_reports_all_bad_lines(world, session):
    u = await _new_user(world, session)
    await _create_store(u)

    await _add_items(u, "мусор\nх111хх01-0\nх222хх01-1000")

    errors = "\n".join(m.text for m in u.messages)
    assert "1)" in errors and "2)" in errors
    assert "Проверьте введённые номера" not in u.last.text


async def test_add_duplicate_items_is_refused(world, session):
    u = await _new_user(world, session)
    await _create_store(u)
    await _add_items(u, "х111хх01-1000")
    await u.click("Сохранить")
    await u.click("Мой магазин")

    await _add_items(u, "х111хх01-2000")
    await u.click("Сохранить")

    assert u.last_alert
    store = await _store(session)
    assert store.store_items == [{"plate": "Х111ХХ01", "price": 1000}]


async def test_publish_store_end_to_end(world, session):
    u = await _new_user(world, session)
    await _create_store(u)
    await _add_items(u, "х111хх01-1000000\nо100оо77-500000")
    await u.click("Сохранить")

    await u.click("Просмотр и Публикация")
    assert "Х111ХХ01" in u.last.text
    await u.click("Публикация")
    await u.click(FREE_SLOT)
    await u.click("Подтвердить")

    # «Выделение» для магазина недоступно (AUD-19)
    assert not any("Выделение" in b for b in u.last.button_texts)
    await u.click("Пропустить")

    [pub] = await _pubs(session)
    assert pub.status == PublicationStatus.SCHEDULED
    assert pub.scheduler_job_id

    await world.mediator_call(PublishPublicationRequest(publication_id=pub.id))

    [post] = world.tg.visible(CHANNEL_ID)
    assert "Номера-Плюс" in post.text
    assert "Х111ХХ01" in post.text and "О100ОО77" in post.text


async def test_store_without_items_cannot_be_published(world, session):
    u = await _new_user(world, session)
    await _create_store(u)

    await u.click("Просмотр и Публикация")

    assert not any("Публикация" == b.strip("✅ ") for b in u.last.button_texts)


async def test_edit_store_name(world, session):
    u = await _new_user(world, session)
    await _create_store(u)

    await u.click("Редактировать магазин")
    await u.click("Изменить название")
    await u.send("Новое Имя")
    await u.click("Сохранить")

    assert (await _store(session)).shop_name == "Новое Имя"


async def test_edit_and_delete_store_item(world, session):
    u = await _new_user(world, session)
    await _create_store(u)
    await _add_items(u, "х111хх01-1000\nо100оо77-2000")
    await u.click("Сохранить")
    await u.click("Мой магазин")

    await u.click("Редактировать номера")
    await u.click("Х111ХХ01")
    await u.click("Изменить цену")
    await u.send("5000")
    await u.click("Сохранить")

    store = await _store(session)
    prices = {i["plate"]: i["price"] for i in store.store_items}
    assert prices["Х111ХХ01"] == 5000  # число, а не строка из ввода

    # после сохранения бот остаётся в карточке этой позиции
    await u.click("Удалить")

    store = await _store(session)
    assert [i["plate"] for i in store.store_items] == ["О100ОО77"]


async def test_edit_item_price_with_spaces_keeps_store_usable(world, session):
    """Раньше в JSONB уходил сырой ввод «1 000 000» строкой, и каждая
    последующая загрузка магазина падала на int() — ломалось даже меню."""
    u = await _new_user(world, session)
    await _create_store(u)
    await _add_items(u, "х111хх01-1000")
    await u.click("Сохранить")
    await u.click("Мой магазин")
    await u.click("Редактировать номера")
    await u.click("Х111ХХ01")
    await u.click("Изменить цену")

    await u.send("1 000 000")
    await u.click("Сохранить")

    store = await _store(session)
    assert store.store_items == [{"plate": "Х111ХХ01", "price": 1_000_000}]
    await u.send("/start")
    assert "Выберите действие" in u.last.text


async def test_edit_item_price_follows_store_rules(world, session):
    """Цена позиции при редактировании — по тем же правилам, что при
    добавлении: как ввели (без «150 -> 150 000»), ноль недопустим."""
    u = await _new_user(world, session)
    await _create_store(u)
    await _add_items(u, "х111хх01-1000")
    await u.click("Сохранить")
    await u.click("Мой магазин")
    await u.click("Редактировать номера")
    await u.click("Х111ХХ01")
    await u.click("Изменить цену")

    await u.send("0")
    assert "Сохранить" not in " ".join(u.last.button_texts)

    await u.send("500")
    await u.click("Сохранить")
    store = await _store(session)
    assert store.store_items == [{"plate": "Х111ХХ01", "price": 500}]


async def test_rename_item_to_existing_plate_is_refused(world, session):
    u = await _new_user(world, session)
    await _create_store(u)
    await _add_items(u, "х111хх01-1000\nо100оо77-2000")
    await u.click("Сохранить")
    await u.click("Мой магазин")
    await u.click("Редактировать номера")
    await u.click("Х111ХХ01")
    await u.click("Изменить номер")
    await u.send("о100оо77")
    await u.click("Сохранить")

    store = await _store(session)
    plates = [i["plate"] for i in store.store_items]
    assert sorted(plates) == sorted(["Х111ХХ01", "О100ОО77"]), "дубли номеров"
    assert "уже есть" in u.last_alert
