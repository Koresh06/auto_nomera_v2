"""Сквозные сценарии: первый вход, регистрация, смена региона, блокировка."""

from src.domain.enums.region import RegionStatus
from src.infrastructure.repositories.region.sqlalchemy import (
    SQLAlchemyRegionRepository,
)
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from ..factories import make_region, make_user


async def test_new_user_sees_region_choice_and_registers(world, session):
    msk = await make_region(session, title="Москва")
    await make_region(session, title="Казань", channel_id=-5)
    await session.commit()
    alice = world.user(501, username="alice")

    await alice.send("/start")

    assert "Выберите регион" in alice.last.text
    assert any("Москва" in b for b in alice.last.button_texts)

    await alice.click("Москва")

    user = await SQLAlchemyUserRepo(session).get_by_tg_id(501)
    assert user is not None
    assert user.region_id == msk.id
    assert user.username == "alice"
    assert "Выберите действие" in alice.last.text
    assert any("ПРОДАТЬ" in b for b in alice.last.button_texts)
    assert any("Смена региона (Москва)" in b for b in alice.last.button_texts)


async def test_no_regions_message(world):
    bob = world.user(502)
    await bob.send("/start")
    assert "доступных регионов нет" in bob.last.text


async def test_registered_user_goes_straight_to_menu(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=503)
    await session.commit()
    u = world.user(503)

    await u.send("/start")

    assert "Выберите действие" in u.last.text


async def test_change_region_from_menu(world, session):
    msk = await make_region(session, title="Москва")
    kzn = await make_region(session, title="Казань", channel_id=-5)
    await make_user(session, msk.id, tg_id=504)
    await session.commit()
    u = world.user(504)

    await u.send("/start")
    await u.click("Смена региона")
    assert "Выберите регион" in u.last.text
    await u.click("Казань")

    session.expire_all()
    user = await SQLAlchemyUserRepo(session).get_by_tg_id(504)
    assert user.region_id == kzn.id
    assert any("Смена региона (Казань)" in b for b in u.last.button_texts)


async def test_disabled_region_forces_reselect(world, session):
    region = await make_region(session)
    await make_region(session, title="Казань", channel_id=-5)
    await make_user(session, region.id, tg_id=505)
    region.disable()
    await SQLAlchemyRegionRepository(session).update(region)
    await session.commit()
    u = world.user(505)

    await u.send("/start")

    texts = [m.text for m in u.messages]
    assert any("регион был отключён" in t for t in texts)
    assert "Выберите регион" in u.last.text
    # отключённый регион не предлагается к выбору
    assert not any("Москва" in b for b in u.last.button_texts)


async def test_blocked_user_gets_only_block_notice(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=506, is_blocked=True)
    await session.commit()
    u = world.user(506)

    await u.send("/start")

    assert [m.text for m in u.messages] == ["🚫 Вы заблокированы в этом боте."]


async def test_group_chat_updates_are_ignored(world, session):
    from aiogram.types import Chat, Message, Update
    from datetime import datetime, timezone

    await make_region(session)
    await session.commit()
    u = world.user(507)
    await world.dp.feed_update(
        world.bot,
        Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=datetime.now(timezone.utc),
                chat=Chat(id=-100500, type="supergroup"),
                from_user=u.user,
                text="/start",
            ),
        ),
    )
    assert world.tg.calls == []


async def test_regions_disabled_are_hidden_for_new_user(world, session):
    active = await make_region(session, title="Активный")
    off = await make_region(session, title="Выключенный", channel_id=-9)
    off.disable()
    await SQLAlchemyRegionRepository(session).update(off)
    await session.commit()
    u = world.user(508)

    await u.send("/start")

    buttons = u.last.button_texts
    assert any(active.title in b for b in buttons)
    assert not any(off.title in b for b in buttons)
    assert off.status == RegionStatus.DISABLED
