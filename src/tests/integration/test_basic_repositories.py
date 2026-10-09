"""SQLAlchemy-репозитории пользователей, регионов, услуг, объявлений и слотов
против настоящего Postgres: маппинг entity <-> model туда-обратно, фильтры,
агрегаты и ON CONFLICT-семантика бронирования слотов."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest

from src.application.dtos.user import UpdateUserDTO
from src.application.exceptions.ad import AdNotFoundException
from src.application.exceptions.region import RegionNotFoundException
from src.application.exceptions.service_definition import ServiceDefinitionException
from src.application.exceptions.user import UserNotFoundException
from src.domain.entities.ad import Ad
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.entities.user import User
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.enums.region import RegionStatus
from src.domain.enums.role import UserRole
from src.domain.value_objects.region_settings import RegionSettings
from src.infrastructure.repositories.ad.sqlalchemy import SQLAlchemyAdRepo
from src.infrastructure.repositories.region.sqlalchemy import (
    SQLAlchemyRegionRepository,
)
from src.infrastructure.repositories.service_def.sqlalchemy import (
    SQLAlchemyServiceDefinitionRepo,
)
from src.infrastructure.repositories.slot.sqlalchemy import (
    SQLAlchemySlotBookingRepo,
    SQLAlchemySlotConvertedRepo,
)
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from .factories import make_ad, make_region, make_user, slot


# ---------------------------------------------------------------- regions


async def test_region_roundtrip_preserves_settings_and_metadata(session):
    settings = RegionSettings(
        slot_times=(time(9, 30), time(21, 0)),
        days_range=5,
        system_paid_slots_count=1,
        publication_limit_enabled=False,
        paid_slot_price=Decimal("249.50"),
    )
    created = await make_region(session, tz="Asia/Yekaterinburg", settings=settings)
    await session.commit()

    loaded = await SQLAlchemyRegionRepository(session).get_by_id(created.id)

    assert loaded is not None
    assert loaded.settings == settings
    assert loaded.timezone.value == "Asia/Yekaterinburg"
    assert loaded.metadata.tg_group_url == "https://t.me/g"
    assert loaded.status == RegionStatus.ACTIVE


async def test_region_update_and_count(session):
    repo = SQLAlchemyRegionRepository(session)
    region = await make_region(session)
    await make_region(session, title="СПб", channel_id=-1002)

    region.disable()
    region.update_settings(settings=RegionSettings(days_range=3))
    updated = await repo.update(region)

    assert updated.status == RegionStatus.DISABLED
    assert updated.settings.days_range == 3
    assert await repo.count_regions() == 2
    assert {r.title for r in await repo.get_all()} == {"Москва", "СПб"}
    assert await repo.get_by_id(999) is None


async def test_region_update_missing_raises(session):
    region = await make_region(session)
    region.id = 999
    with pytest.raises(RegionNotFoundException):
        await SQLAlchemyRegionRepository(session).update(region)


# ---------------------------------------------------------------- users


async def test_user_add_get_save_roundtrip(session):
    region = await make_region(session)
    repo = SQLAlchemyUserRepo(session)
    user = await make_user(
        session, region.id, tg_id=42, username="bob", balance=Decimal("10.50")
    )

    assert user.id > 0
    by_tg = await repo.get_by_tg_id(42)
    assert by_tg is not None and by_tg.id == user.id
    assert by_tg.balance == Decimal("10.50")

    user.top_up(Decimal("5"))
    user.activate_pre_publication(days=3)
    await repo.save(user)
    await session.commit()

    reloaded = await repo.get_by_id(user.id)
    assert reloaded.balance == Decimal("15.50")
    assert reloaded.has_pre_publication


async def test_user_save_and_update_missing_raise(session):
    region = await make_region(session)
    repo = SQLAlchemyUserRepo(session)
    ghost = User(id=777, tg_id=777, region_id=region.id, phone=None)
    with pytest.raises(UserNotFoundException):
        await repo.save(ghost)
    with pytest.raises(UserNotFoundException):
        await repo.update(777, UpdateUserDTO())


async def test_user_update_only_overwrites_provided_fields(session):
    region = await make_region(session)
    repo = SQLAlchemyUserRepo(session)
    await make_user(session, region.id, tg_id=5, username="old", phone="+7111")

    updated = await repo.update(5, UpdateUserDTO(username="new"))

    assert updated.username == "new"
    assert updated.phone == "+7111"


async def test_user_queries_by_role_region_activity_and_pre_publication(session):
    r1 = await make_region(session)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    repo = SQLAlchemyUserRepo(session)

    admin = await make_user(session, r1.id, role=UserRole.ADMIN)
    blocked = await make_user(session, r1.id, is_blocked=True)
    subscriber = await make_user(session, r1.id)
    subscriber.activate_pre_publication(days=1)
    await repo.save(subscriber)
    expired = await make_user(
        session,
        r1.id,
        pre_publication_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    other_region_sub = await make_user(session, r2.id)
    other_region_sub.activate_pre_publication(days=1)
    await repo.save(other_region_sub)

    assert [u.id for u in await repo.get_by_role(UserRole.ADMIN)] == [admin.id]
    assert blocked.id not in {u.id for u in await repo.get_all_active()}
    assert len(await repo.get_all()) == 5
    assert {u.id for u in await repo.get_by_region(r2.id)} == {other_region_sub.id}
    active_pre = await repo.find_with_active_pre_publication(region_id=r1.id)
    assert [u.id for u in active_pre] == [subscriber.id]
    assert expired.id not in {u.id for u in active_pre}


async def test_user_counts(session):
    r1 = await make_region(session)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    repo = SQLAlchemyUserRepo(session)
    u1 = await make_user(session, r1.id)
    u2 = await make_user(session, r2.id)
    await make_ad(session, u1, ad_type=AdType.STORE)
    await make_ad(session, u1, ad_type=AdType.STORE, plate="В1")
    await make_ad(session, u2)

    assert await repo.count_users() == 2
    assert await repo.count_users(region_id=r1.id) == 1
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    assert await repo.count_users(since_utc=future) == 0
    # магазин u1 считается один раз, хоть объявлений-магазинов два
    assert await repo.count_users_with_store() == 1
    assert await repo.count_users_with_store(region_id=r2.id) == 0


# ---------------------------------------------------------------- service defs


async def test_service_definition_crud(session):
    repo = SQLAlchemyServiceDefinitionRepo(session)
    pin = await repo.create(
        ServiceDefinition(
            title="Закреп",
            type=PublicationServiceType.PIN,
            price=300,
            duration_days=2,
            params_schema={"hours": "int"},
        )
    )
    await repo.create(
        ServiceDefinition(
            title="Выделение",
            type=PublicationServiceType.HIGHLIGHT,
            price=100,
            is_active=False,
        )
    )

    assert (await repo.get_by_type(PublicationServiceType.PIN)).id == pin.id
    assert (await repo.get_by_id(pin.id)).params_schema == {"hours": "int"}
    assert [s.type for s in await repo.get_all_active()] == [PublicationServiceType.PIN]
    assert len(await repo.get_all()) == 2
    assert [s.type for s in await repo.get_all(is_active=False)] == [
        PublicationServiceType.HIGHLIGHT
    ]

    pin.update_price(450)
    pin.deactivate()
    saved = await repo.save(pin)
    assert saved.price == 450 and saved.is_active is False


async def test_service_definition_missing_raise(session):
    repo = SQLAlchemyServiceDefinitionRepo(session)
    with pytest.raises(ServiceDefinitionException):
        await repo.get_by_type(PublicationServiceType.PIN)
    with pytest.raises(ServiceDefinitionException):
        await repo.get_by_id(1)
    with pytest.raises(ServiceDefinitionException):
        await repo.save(
            ServiceDefinition(id=5, title="x", type=PublicationServiceType.PIN, price=1)
        )


# ---------------------------------------------------------------- ads


async def test_ad_regular_content_roundtrip(session):
    region = await make_region(session)
    user = await make_user(session, region.id)
    ad = await make_ad(session, user, plate="Е777КХ199")

    loaded = await SQLAlchemyAdRepo(session).get_by_id(ad.id)

    assert loaded.content == ad.content
    assert loaded.content.price.value == 100_000
    assert loaded.store_content is None


async def test_ad_store_content_roundtrip(session):
    region = await make_region(session)
    user = await make_user(session, region.id)
    ad = await make_ad(session, user, ad_type=AdType.STORE, plate="М001ММ77")

    loaded = await SQLAlchemyAdRepo(session).get_by_id(ad.id)

    assert loaded.content is None
    assert loaded.store_content.shop_name == "Shop"
    assert loaded.store_content.items[0].plate == "М001ММ77"
    assert loaded.store_content.items[0].price.value == 500


async def test_ad_draft_without_content_roundtrip(session):
    region = await make_region(session)
    user = await make_user(session, region.id)
    repo = SQLAlchemyAdRepo(session)
    ad = await repo.create(
        Ad(
            user_id=user.id,
            region_id=region.id,
            ad_type=AdType.SALE,
            status=AdStatus.DRAFT,
        )
    )
    loaded = await repo.get_by_id(ad.id)
    assert loaded.content is None and loaded.store_content is None


async def test_ad_save_updates_status_and_content(session):
    region = await make_region(session)
    user = await make_user(session, region.id)
    repo = SQLAlchemyAdRepo(session)
    ad = await make_ad(session, user)

    ad.status = AdStatus.PUBLISHED
    from .factories import ad_content

    ad.fill_content(ad_content(plate="Х999ХХ99", price=5))
    await repo.save(ad)
    await session.commit()

    loaded = await repo.get_by_id(ad.id)
    assert loaded.status == AdStatus.PUBLISHED
    assert loaded.content.plate_number == "Х999ХХ99"
    assert loaded.content.price.value == 5

    ad.id = 999
    with pytest.raises(AdNotFoundException):
        await repo.save(ad)


async def test_ad_finders(session):
    r1 = await make_region(session)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    user = await make_user(session, r1.id)
    repo = SQLAlchemyAdRepo(session)

    sale = await make_ad(session, user, plate="А1")
    store = await make_ad(session, user, ad_type=AdType.STORE, plate="А1")
    await make_ad(session, user, plate="А1", region_id=r2.id)
    urgent = await make_ad(
        session, user, ad_type=AdType.URGENT_BUYOUT, status=AdStatus.PUBLISHED
    )
    await make_ad(session, user, ad_type=AdType.URGENT_BUYOUT, status=AdStatus.ARCHIVED)

    # find_by_plate игнорирует магазины с тем же номером
    assert (await repo.find_by_plate(user.id, r1.id, "А1")).id == sale.id
    assert await repo.find_by_plate(user.id, r1.id, "НЕТ") is None
    assert (await repo.find_store_by_user(user.id, r1.id)).id == store.id
    assert await repo.find_store_by_user(user.id, r2.id) is None
    assert [a.id for a in await repo.list_urgent_published(r1.id)] == [urgent.id]
    assert await repo.count_ads_by_user(user.id, r1.id) == 4


async def test_ad_stats(session):
    r1 = await make_region(session)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    u1 = await make_user(session, r1.id)
    u2 = await make_user(session, r2.id)
    await make_ad(session, u1)
    await make_ad(session, u1, ad_type=AdType.BUY)
    await make_ad(session, u2)
    repo = SQLAlchemyAdRepo(session)

    assert await repo.count_ads() == 3
    assert await repo.count_ads(region_id=r2.id) == 1
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    assert await repo.count_ads(since_utc=future) == 0
    assert dict(await repo.count_by_type()) == {AdType.SALE: 2, AdType.BUY: 1}
    assert dict(await repo.count_by_type(region_id=r1.id)) == {
        AdType.SALE: 1,
        AdType.BUY: 1,
    }
    assert await repo.top_regions_by_activity() == [("Москва", 2), ("СПб", 1)]
    assert await repo.top_regions_by_activity(limit=1) == [("Москва", 2)]


# ---------------------------------------------------------------- slots


async def test_slot_booking_is_exclusive(session):
    region = await make_region(session)
    u1 = await make_user(session, region.id)
    u2 = await make_user(session, region.id)
    ad1 = await make_ad(session, u1)
    ad2 = await make_ad(session, u2)
    repo = SQLAlchemySlotBookingRepo(session)
    key = slot(region.id, date(2030, 1, 1))

    assert await repo.is_booked(key) is False
    assert await repo.book(key, ad_id=ad1.id, user_id=u1.id) is True
    # второй — даже тот же пользователь — не может перебронировать
    assert await repo.book(key, ad_id=ad2.id, user_id=u2.id) is False
    assert await repo.book(key, ad_id=ad1.id, user_id=u1.id) is False
    assert await repo.is_booked(key) is True
    assert await repo.get_booking_owner(key) == u1.id
    assert await repo.get_booking_owner(slot(region.id, date(2030, 1, 2))) is None


async def test_slot_booked_set_matches_exact_day_time_pairs(session):
    region = await make_region(session)
    user = await make_user(session, region.id)
    ad = await make_ad(session, user)
    repo = SQLAlchemySlotBookingRepo(session)
    d1, d2 = date(2030, 1, 1), date(2030, 1, 2)
    await repo.book(slot(region.id, d1, 10), ad_id=ad.id, user_id=user.id)
    await repo.book(slot(region.id, d2, 14), ad_id=ad.id, user_id=user.id)

    candidates = [
        slot(region.id, d1, 10),
        slot(region.id, d1, 14),  # день и время по отдельности заняты, пара — нет
        slot(region.id, d2, 10),
        slot(region.id, d2, 14),
    ]
    booked = await repo.get_booked_set(candidates)

    assert booked == {slot(region.id, d1, 10), slot(region.id, d2, 14)}
    assert await repo.get_booked_set([]) == set()


async def test_slot_converted_owner_semantics(session):
    region = await make_region(session)
    u1 = await make_user(session, region.id)
    u2 = await make_user(session, region.id)
    ad1 = await make_ad(session, u1)
    ad1b = await make_ad(session, u1, plate="В2")
    repo = SQLAlchemySlotConvertedRepo(session)
    key = slot(region.id, date(2030, 1, 1))

    assert await repo.mark_converted(key, user_id=u1.id, ad_id=ad1.id) is True
    # тот же владелец может перепривязать слот к другому своему объявлению
    assert await repo.mark_converted(key, user_id=u1.id, ad_id=ad1b.id) is True
    assert await repo.get_converted_owner_and_ad(key) == (u1.id, ad1b.id)
    # чужой пользователь — конфликт, запись не меняется
    assert await repo.mark_converted(key, user_id=u2.id, ad_id=None) is False
    assert await repo.get_converted_owner_and_ad(key) == (u1.id, ad1b.id)
    assert await repo.is_converted(key) is True
    assert await repo.get_converted_set([key, slot(region.id, date(2030, 1, 2))]) == {
        key
    }

    # снять конверсию может только владелец
    await repo.unmark_converted(key, user_id=u2.id)
    assert await repo.is_converted(key) is True
    await repo.unmark_converted(key, user_id=u1.id)
    assert await repo.is_converted(key) is False
    assert await repo.get_converted_owner_and_ad(key) is None
    assert await repo.get_converted_set([]) == set()


async def test_concurrent_bookings_only_one_wins(session_factory):
    """Две независимые транзакции бронируют один слот одновременно:
    уникальный индекс + ON CONFLICT DO NOTHING гарантируют одного победителя."""
    import asyncio

    async with session_factory() as s:
        region = await make_region(s)
        u1 = await make_user(s, region.id)
        u2 = await make_user(s, region.id)
        ad1 = await make_ad(s, u1)
        ad2 = await make_ad(s, u2)
        await s.commit()

    key = slot(region.id, date(2030, 1, 1))

    async def attempt(user_id: int, ad_id: int) -> bool:
        async with session_factory() as s:
            ok = await SQLAlchemySlotBookingRepo(s).book(
                key, ad_id=ad_id, user_id=user_id
            )
            await asyncio.sleep(0.05)  # держим транзакцию открытой
            await s.commit()
            return ok

    results = await asyncio.gather(attempt(u1.id, ad1.id), attempt(u2.id, ad2.id))

    assert sorted(results) == [False, True]


async def test_store_with_corrupted_price_string_still_loads(session):
    """Баг редактирования писал в store_items цену строкой «1 000 000».
    Такие строки в проде не должны ломать загрузку магазина."""
    from sqlalchemy import update

    from src.infrastructure.database.models import AdModel

    region = await make_region(session)
    user = await make_user(session, region.id)
    ad = await make_ad(session, user, ad_type=AdType.STORE, plate="Х111ХХ01")
    await session.execute(
        update(AdModel)
        .where(AdModel.id == ad.id)
        .values(store_items=[{"plate": "Х111ХХ01", "price": "1 000 000"}])
    )
    await session.commit()
    session.expire_all()

    loaded = await SQLAlchemyAdRepo(session).get_by_id(ad.id)

    assert loaded.store_content.items[0].price.value == 1_000_000
