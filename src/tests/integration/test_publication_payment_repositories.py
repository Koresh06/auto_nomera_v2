"""Репозитории публикаций и платежей против настоящего Postgres."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.application.exceptions.payment import PaymentNotFoundByIdException
from src.application.exceptions.publication import PublicationNotFoundException
from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.ad import AdType
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.infrastructure.repositories.payment.sqlalchemy import SQLAlchemyPaymentRepo
from src.infrastructure.repositories.publication.sqlalchemy import (
    SQLAlchemyPublicationRepo,
)

from .factories import (
    make_ad,
    make_payment,
    make_publication,
    make_region,
    make_user,
    slot,
)

NOW = datetime.now(timezone.utc)


async def _world(session):
    region = await make_region(session)
    user = await make_user(session, region.id)
    ad = await make_ad(session, user)
    return region, user, ad


# ---------------------------------------------------------------- publications


async def test_publication_roundtrip_with_slot_and_services(session):
    region, _, ad = await _world(session)
    key = slot(region.id, date(2030, 5, 1), 14)
    pub = await make_publication(
        session,
        ad,
        slot_key=key,
        services=[
            PublicationService(
                type=PublicationServiceType.PIN, price_paid=300, params={"days": 2}
            )
        ],
    )
    await session.commit()

    loaded = await SQLAlchemyPublicationRepo(session).get_by_id(pub.id)

    assert loaded.slot == key
    assert loaded.status == PublicationStatus.SCHEDULED
    assert len(loaded.services) == 1
    svc = loaded.services[0]
    assert svc.id > 0
    assert (svc.type, svc.price_paid, svc.params) == (
        PublicationServiceType.PIN,
        300,
        {"days": 2},
    )


async def test_publication_save_updates_fields_and_adds_service(session_factory):
    async with session_factory() as s:
        _, _, ad = await _world(s)
        pub = await make_publication(s, ad)
        await s.commit()

    async with session_factory() as s:
        repo = SQLAlchemyPublicationRepo(s)
        pub = await repo.get_by_id(pub.id)
        pub.mark_publishing()
        pub.mark_published(message_id=555, published_at_utc=NOW)
        pub.set_scheduler_job("job-1")
        pub.add_service(PublicationService(type=PublicationServiceType.HIGHLIGHT))
        await repo.save(pub)
        await s.commit()

    async with session_factory() as s:
        loaded = await SQLAlchemyPublicationRepo(s).get_by_id(pub.id)
    assert loaded.status == PublicationStatus.PUBLISHED
    assert loaded.channel_message_id == 555
    assert loaded.scheduler_job_id == "job-1"
    assert [x.type for x in loaded.services] == [PublicationServiceType.HIGHLIGHT]


async def test_service_status_change_is_persisted(session_factory):
    async with session_factory() as s:
        _, _, ad = await _world(s)
        pub = await make_publication(
            s, ad, services=[PublicationService(type=PublicationServiceType.PIN)]
        )
        await s.commit()

    async with session_factory() as s:
        repo = SQLAlchemyPublicationRepo(s)
        pub = await repo.get_by_id(pub.id)
        pub.services[0].mark_used()
        await repo.save(pub)
        await s.commit()

    async with session_factory() as s:
        loaded = await SQLAlchemyPublicationRepo(s).get_by_id(pub.id)
    assert loaded.services[0].status == PublicationServiceStatus.USED


async def test_in_place_service_params_mutation_is_persisted(session_factory):
    """PinStrategy пишет ``service.params["unpin_at_utc"] = ...`` на месте.
    Изменение обязано дойти до БД, иначе время открепления теряется."""
    async with session_factory() as s:
        _, _, ad = await _world(s)
        pub = await make_publication(
            s,
            ad,
            services=[
                PublicationService(type=PublicationServiceType.PIN, params={"days": 1})
            ],
        )
        await s.commit()

    async with session_factory() as s:
        repo = SQLAlchemyPublicationRepo(s)
        pub = await repo.get_by_id(pub.id)
        pub.services[0].params["unpin_at_utc"] = "2030-01-01T00:00:00+00:00"
        pub.services[0].mark_used()
        await repo.save(pub)
        await s.commit()

    async with session_factory() as s:
        loaded = await SQLAlchemyPublicationRepo(s).get_by_id(pub.id)
    assert loaded.services[0].params == {
        "days": 1,
        "unpin_at_utc": "2030-01-01T00:00:00+00:00",
    }


async def test_publication_save_missing_raises(session):
    with pytest.raises(PublicationNotFoundException):
        await SQLAlchemyPublicationRepo(session).save(
            Publication(id=999, ad_id=1, region_id=1)
        )


async def test_list_scheduled_by_ad_and_autopublish_series(session):
    _, user, ad = await _world(session)
    other = await make_ad(session, user, plate="В2")
    parent = await make_publication(session, ad)
    child = await make_publication(session, ad, is_child=True)
    await make_publication(
        session, other, is_child=True, status=PublicationStatus.PUBLISHED
    )
    repo = SQLAlchemyPublicationRepo(session)

    assert {p.id for p in await repo.list_scheduled_by_ad(ad.id)} == {
        parent.id,
        child.id,
    }
    assert await repo.get_ad_ids_with_active_autopublish_series([ad.id, other.id]) == {
        ad.id
    }
    assert await repo.get_ad_ids_with_active_autopublish_series([]) == set()


async def test_list_by_user_returns_latest_live_publication_per_ad(session):
    region, user, ad = await _world(session)
    store = await make_ad(session, user, ad_type=AdType.STORE, plate="С1")
    old = await make_publication(session, ad, status=PublicationStatus.PUBLISHED)
    newest = await make_publication(session, ad)
    await make_publication(session, ad, status=PublicationStatus.CANCELED)
    store_pub = await make_publication(session, store)
    repo = SQLAlchemyPublicationRepo(session)

    rows = await repo.list_by_user(user.id, region.id)

    ids = {p.id: (plate, shop) for p, plate, shop in rows}
    assert set(ids) == {newest.id, store_pub.id}
    assert ids[newest.id] == ("А123ВС77", None)
    assert ids[store_pub.id] == (None, "Shop")

    all_rows = await repo.list_all_by_user(user.id, region.id)
    assert {p.id for p, _, _ in all_rows} == {old.id, newest.id, store_pub.id}


async def test_count_scheduled_by_user_and_find_last_by_plate(session):
    region, user, ad = await _world(session)
    since = NOW - timedelta(days=1)
    await make_publication(session, ad, publish_at_utc=NOW)
    last = await make_publication(session, ad, publish_at_utc=NOW + timedelta(hours=5))
    await make_publication(
        session, ad, status=PublicationStatus.CANCELED, publish_at_utc=NOW
    )
    await make_publication(session, ad, publish_at_utc=NOW - timedelta(days=3))
    repo = SQLAlchemyPublicationRepo(session)

    assert (
        await repo.count_scheduled_by_user(user.id, region.id, AdType.SALE, since) == 2
    )
    assert (
        await repo.count_scheduled_by_user(user.id, region.id, AdType.BUY, since) == 0
    )
    found = await repo.find_last_by_plate(user.id, region.id, "А123ВС77", since)
    assert found.id == last.id
    assert await repo.find_last_by_plate(user.id, region.id, "НЕТ", since) is None


async def test_list_pre_publication_window(session):
    region, _, ad = await _world(session)
    inside = await make_publication(
        session, ad, publish_at_utc=NOW + timedelta(hours=1)
    )
    await make_publication(session, ad, publish_at_utc=NOW + timedelta(days=3))
    await make_publication(
        session, ad, publish_at_utc=NOW + timedelta(hours=1), is_child=True
    )
    await make_publication(session, ad, publish_at_utc=NOW - timedelta(hours=1))

    rows = await SQLAlchemyPublicationRepo(session).list_pre_publication(
        region.id, NOW, NOW + timedelta(days=1)
    )

    assert [p.id for p in rows] == [inside.id]


async def test_publication_stats(session):
    r1, user, ad = await _world(session)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    u2 = await make_user(session, r2.id)
    ad2 = await make_ad(session, u2, ad_type=AdType.BUY)
    await make_ad(session, user, ad_type=AdType.URGENT_BUYOUT)
    await make_publication(session, ad)
    await make_publication(session, ad, status=PublicationStatus.PUBLISHED)
    await make_publication(session, ad2)
    repo = SQLAlchemyPublicationRepo(session)

    stats = await repo.get_stats()
    assert stats.total == 3
    assert {s.status: s.count for s in stats.by_status} == {
        PublicationStatus.SCHEDULED: 2,
        PublicationStatus.PUBLISHED: 1,
    }
    assert {t.ad_type: t.count for t in stats.by_ad_type} == {
        AdType.SALE: 2,
        AdType.BUY: 1,
        AdType.URGENT_BUYOUT: 1,
    }
    assert (stats.top_region_title, stats.top_region_count) == ("Москва", 2)

    regional = await repo.get_stats(region_id=r2.id)
    assert regional.total == 1
    assert regional.top_region_title is None

    empty = await repo.get_stats(since_utc=NOW + timedelta(days=10))
    assert empty.total == 0 and empty.top_region_title is None


async def test_list_scheduled_by_region_flags_paid_slots(session):
    region, user, ad = await _world(session)
    paid_key = slot(region.id, date(2030, 5, 1), 10)
    free_key = slot(region.id, date(2030, 5, 1), 14)
    at = datetime(2030, 5, 1, 7, tzinfo=timezone.utc)
    paid_pub = await make_publication(session, ad, slot_key=paid_key, publish_at_utc=at)
    free_pub = await make_publication(
        session, ad, slot_key=free_key, publish_at_utc=at + timedelta(hours=4)
    )
    # Платёж за слот — в том формате meta, который пишет ad_handlers
    await make_payment(
        session,
        user,
        external_id="slot-1",
        purpose=PaymentPurpose.SLOT,
        meta={
            "return_data": {
                "ad_id": ad.id,
                "slot": {
                    "region_id": region.id,
                    "slot_day": "2030-05-01",
                    "slot_time": "10:00:00",
                },
                "is_paid": True,
            }
        },
    )
    # Неоплаченный и «чужой» по смыслу платежи не должны давать флаг
    await make_payment(
        session,
        user,
        external_id="slot-2",
        purpose=PaymentPurpose.SLOT,
        status=PaymentStatus.PENDING,
        meta={
            "return_data": {
                "ad_id": ad.id,
                "slot": {"slot_day": "2030-05-01", "slot_time": "14:00:00"},
            }
        },
    )
    # Платежи других назначений без slot в return_data не ломают cast'ы
    await make_payment(session, user, external_id="topup", meta={})
    await make_payment(
        session,
        user,
        external_id="svc",
        purpose=PaymentPurpose.PUBLICATION_SERVICE,
        meta={"return_data": {"publication_id": paid_pub.id}},
    )
    urgent = await make_ad(session, user, ad_type=AdType.URGENT_BUYOUT)
    await make_publication(session, urgent, publish_at_utc=at)

    rows = await SQLAlchemyPublicationRepo(session).list_scheduled_by_region(
        region.id, at - timedelta(days=1), at + timedelta(days=1)
    )

    by_id = {r[0].id: r for r in rows}
    assert list(by_id) == [paid_pub.id, free_pub.id]
    assert by_id[paid_pub.id][6] is True
    assert by_id[free_pub.id][6] is False
    assert by_id[paid_pub.id][1:6] == (
        "А123ВС77",
        AdType.SALE,
        "seller",
        user.tg_id,
        None,
    )


async def test_list_scheduled_for_catalog_and_count(session):
    region, user, ad = await _world(session)
    pub = await make_publication(session, ad)
    await make_publication(session, ad, is_child=True)
    await make_publication(session, ad, status=PublicationStatus.PUBLISHED)
    urgent = await make_ad(session, user, ad_type=AdType.URGENT_BUYOUT)
    await make_publication(session, urgent)
    repo = SQLAlchemyPublicationRepo(session)

    rows = await repo.list_scheduled_for_catalog(region.id)

    assert [(p.id, a.id, tg) for p, a, tg in rows] == [(pub.id, ad.id, user.tg_id)]
    # count_scheduled не фильтрует срочный выкуп — только детей серии
    assert await repo.count_scheduled() == 2
    assert await repo.count_scheduled(region_id=region.id + 1) == 0


async def test_count_services(session):
    _, _, ad = await _world(session)
    await make_publication(
        session,
        ad,
        services=[
            PublicationService(type=PublicationServiceType.PIN),
            PublicationService(
                type=PublicationServiceType.HIGHLIGHT,
                status=PublicationServiceStatus.USED,
            ),
            PublicationService(
                type=PublicationServiceType.AUTOPUBLISH,
                status=PublicationServiceStatus.CANCELED,
            ),
        ],
    )

    total, by_type = await SQLAlchemyPublicationRepo(session).count_services()

    assert total == 2
    assert dict(by_type) == {
        PublicationServiceType.PIN: 1,
        PublicationServiceType.HIGHLIGHT: 1,
    }


async def test_list_overdue_scheduled_today_uses_region_timezone(session):
    msk = await make_region(session)
    vlad = await make_region(
        session, title="Владивосток", tz="Asia/Vladivostok", channel_id=-3
    )
    u_msk = await make_user(session, msk.id)
    u_vlad = await make_user(session, vlad.id)
    ad_msk = await make_ad(session, u_msk)
    ad_vlad = await make_ad(session, u_vlad)

    # «Сейчас» = 2030-05-01 12:00 UTC: в Москве 15:00 1 мая,
    # во Владивостоке 22:00 1 мая (UTC+10).
    now = datetime(2030, 5, 1, 12, tzinfo=timezone.utc)
    # 14:30 UTC 30 апреля: Москва — 30 апреля (не сегодня),
    # Владивосток — 00:30 1 мая (сегодня).
    t = datetime(2030, 4, 30, 14, 30, tzinfo=timezone.utc)
    p_msk = await make_publication(session, ad_msk, publish_at_utc=t)
    p_vlad = await make_publication(session, ad_vlad, publish_at_utc=t)
    p_msk_today = await make_publication(
        session, ad_msk, publish_at_utc=datetime(2030, 5, 1, 6, tzinfo=timezone.utc)
    )

    rows = await SQLAlchemyPublicationRepo(session).list_overdue_scheduled_today(now)

    ids = [r[0].id for r in rows]
    assert p_vlad.id in ids
    assert p_msk_today.id in ids
    assert p_msk.id not in ids


# ---------------------------------------------------------------- payments


async def test_payment_create_get_save_roundtrip(session):
    _, user, _ = await _world(session)
    repo = SQLAlchemyPaymentRepo(session)
    p = await make_payment(
        session,
        user,
        external_id="ext-1",
        status=PaymentStatus.PENDING,
        amount=Decimal("199.99"),
        meta={"return_data": {"x": 1}},
    )

    loaded = await repo.get_by_external_id("ext-1")
    assert loaded.id == p.id
    assert loaded.amount == Decimal("199.99")
    assert loaded.meta == {"return_data": {"x": 1}}
    assert await repo.get_by_external_id("nope") is None

    loaded.mark_paid(NOW)
    await repo.save(loaded)
    await session.commit()
    locked = await repo.get_by_external_id_for_update("ext-1")
    assert locked.status == PaymentStatus.PAID
    assert locked.paid_at is not None

    loaded.id = 999
    with pytest.raises(PaymentNotFoundByIdException):
        await repo.save(loaded)


async def test_payment_external_id_is_unique(session):
    from sqlalchemy.exc import IntegrityError

    _, user, _ = await _world(session)
    await make_payment(session, user, external_id="dup")
    with pytest.raises(IntegrityError):
        await make_payment(session, user, external_id="dup")


async def test_payment_stats_and_breakdown(session):
    r1, u1, _ = await _world(session)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    u2 = await make_user(session, r2.id)
    await make_payment(session, u1, external_id="a", amount=Decimal("100"))
    await make_payment(session, u1, external_id="b", amount=Decimal("50"))
    await make_payment(
        session,
        u2,
        external_id="c",
        amount=Decimal("300"),
        method=PaymentMethod.TELEGRAM_STARS,
        meta={"stars_amount": 150},
    )
    await make_payment(
        session,
        u2,
        external_id="d",
        amount=Decimal("1000"),
        status=PaymentStatus.PENDING,
    )
    repo = SQLAlchemyPaymentRepo(session)

    stats = await repo.get_stats()
    assert stats.total_count == 3
    assert stats.total_amount == Decimal("450")
    assert stats.stars_total == 150
    assert {m.method: m.amount for m in stats.by_method} == {
        PaymentMethod.YOOKASSA: Decimal("150"),
        PaymentMethod.TELEGRAM_STARS: Decimal("300"),
    }
    assert stats.top_region.region_title == "СПб"

    regional = await repo.get_stats(region_id=r1.id)
    assert regional.total_count == 2
    assert regional.total_amount == Decimal("150")
    assert regional.stars_total == 0
    assert regional.top_region is None

    breakdown = await repo.get_region_breakdown()
    assert [(b.region_title, b.count, b.amount) for b in breakdown] == [
        ("СПб", 1, Decimal("300")),
        ("Москва", 2, Decimal("150")),
    ]

    future = await repo.get_stats(since_utc=NOW + timedelta(days=1))
    assert future.total_count == 0 and future.total_amount == Decimal("0")


async def test_list_paid_payments(session):
    r1, u1, _ = await _world(session)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    u2 = await make_user(session, r2.id, username="u2")
    await make_payment(session, u1, external_id="old", paid_at=NOW - timedelta(days=2))
    await make_payment(session, u2, external_id="new", paid_at=NOW)
    await make_payment(session, u2, external_id="pending", status=PaymentStatus.PENDING)
    repo = SQLAlchemyPaymentRepo(session)

    rows = await repo.list_paid_payments()
    assert [(p.external_id, tg) for p, tg, _, _ in rows] == [
        ("new", u2.tg_id),
        ("old", u1.tg_id),
    ]
    assert rows[0][3] == "u2"

    only_r1 = await repo.list_paid_payments(region_id=r1.id)
    assert [p.external_id for p, *_ in only_r1] == ["old"]
    recent = await repo.list_paid_payments(since_utc=NOW - timedelta(days=1))
    assert [p.external_id for p, *_ in recent] == ["new"]
