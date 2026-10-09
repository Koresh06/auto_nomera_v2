"""Конкурентные нажатия, как в реальном Telegram: двойной тап по кнопке
приходит двумя параллельными callback'ами, а разные пользователи жмут
одновременно. Апдейты обрабатываются параллельно (как в polling aiogram)."""

import asyncio
from decimal import Decimal

import pytest

from sqlalchemy import select

from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.region_settings import RegionSettings
from src.infrastructure.database.models import PublicationModel, SlotBookingModel
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from ..factories import make_region, make_user
from .test_create_ad_flow import FREE_SLOT, PAID_SLOT, _fill_sale_until_calendar


async def _rows(session, model):
    q = select(model).execution_options(populate_existing=True)
    return list((await session.execute(q)).scalars().all())


async def _two_taps(u, label):
    """Два одинаковых callback'а на одно и то же сообщение одновременно."""
    await asyncio.gather(u.click(label), u.click(label))


async def test_double_tap_confirm_creates_one_publication(world, session):
    region = await make_region(
        session, settings=RegionSettings(system_paid_slots_count=0)
    )
    await make_user(session, region.id, tg_id=1001)
    await session.commit()
    u = world.user(1001)
    await _fill_sale_until_calendar(u)
    await u.click(FREE_SLOT)

    await _two_taps(u, "Подтвердить")

    pubs = [p for p in await _rows(session, PublicationModel)]
    scheduled = [p for p in pubs if p.status == PublicationStatus.SCHEDULED]
    assert len(scheduled) == 1, f"двойной тап создал {len(scheduled)} публикации"
    publish_jobs = [s for s in world.tasks.scheduled if s[0] == "publish_publication"]
    assert len(publish_jobs) == 1


async def test_double_tap_paid_slot_charges_once(world, session):
    region = await make_region(
        session, settings=RegionSettings(system_paid_slots_count=3)
    )
    await make_user(session, region.id, tg_id=1002, balance=Decimal("1000"))
    await session.commit()
    u = world.user(1002)
    await _fill_sale_until_calendar(u)

    await _two_taps(u, PAID_SLOT)

    session.expire_all()
    balance = (await SQLAlchemyUserRepo(session).get_by_tg_id(1002)).balance
    assert balance == Decimal("801"), f"списано {Decimal('1000') - balance}"


async def test_double_tap_priority_publish_charges_once(world, session):
    from .test_paid_services_flow import _create_ad_until_services

    u = await _create_ad_until_services(world, session, balance="1000")

    await _two_taps(u, "Вне очереди")

    session.expire_all()
    balance = (await SQLAlchemyUserRepo(session).get_by_tg_id(900)).balance
    assert balance == Decimal("701"), f"списано {Decimal('1000') - balance}"


async def test_two_users_racing_for_one_slot_get_one_booking(world, session):
    region = await make_region(
        session, settings=RegionSettings(system_paid_slots_count=0)
    )
    await make_user(session, region.id, tg_id=1011)
    await make_user(session, region.id, tg_id=1012)
    await session.commit()
    a, b = world.user(1011), world.user(1012)
    await _fill_sale_until_calendar(a, plate="А111АА77")
    await _fill_sale_until_calendar(b, plate="В222ВВ77")
    slot_label = a.find_button(FREE_SLOT)[1].text
    assert slot_label in b.last.button_texts

    await asyncio.gather(a.click(slot_label), b.click(slot_label))
    confirmations = [
        u for u in (a, b) if any("Подтвердить" in t for t in u.last.button_texts)
    ]
    await asyncio.gather(*(u.click("Подтвердить") for u in confirmations))

    bookings = await _rows(session, SlotBookingModel)
    scheduled = [
        p
        for p in await _rows(session, PublicationModel)
        if p.status == PublicationStatus.SCHEDULED
    ]
    hh = slot_label.rsplit("-", 1)[1]
    same_slot = [p for p in scheduled if p.slot_time.strftime("%H:%M") == hh]
    assert len(same_slot) <= 1, "два объявления в одном слоте"
    assert len(bookings) == len({(b.slot_day, b.slot_time) for b in bookings})


async def test_parallel_confirmation_of_two_payments_credits_both(world, session):
    """Воркер обрабатывает задачи параллельно: два разных пополнения одного
    пользователя не должны терять друг друга (lost update баланса)."""
    from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
    from src.domain.enums.payment import PaymentStatus

    from ..factories import make_payment

    region = await make_region(session)
    user = await make_user(session, region.id, tg_id=1021)
    for ext, amount in (("p-100", "100"), ("p-200", "200")):
        await make_payment(
            session,
            user,
            external_id=ext,
            amount=Decimal(amount),
            status=PaymentStatus.PENDING,
        )
    await session.commit()

    await asyncio.gather(
        world.mediator_call(ConfirmPaymentRequest(external_id="p-100")),
        world.mediator_call(ConfirmPaymentRequest(external_id="p-200")),
    )

    session.expire_all()
    balance = (await SQLAlchemyUserRepo(session).get_by_tg_id(1021)).balance
    assert balance == Decimal("300"), f"на балансе {balance}, а должно быть 300"


async def test_parallel_purchases_cannot_overdraw_balance(world, session):
    """Баланса хватает на одну услугу, пользователь параллельно покупает две
    (два устройства / двойной тап по разным кнопкам)."""
    from src.application.use_cases.publication_service.buy_publication_service import (
        BuyPublicationServiceRequest,
    )
    from src.domain.enums.publication_service import PublicationServiceType

    from ..factories import make_ad, make_publication

    region = await make_region(session)
    user = await make_user(session, region.id, tg_id=1022, balance=Decimal("500"))
    ad = await make_ad(session, user)
    pub = await make_publication(session, ad)
    await session.commit()

    results = await asyncio.gather(
        world.mediator_call(
            BuyPublicationServiceRequest(
                publication_id=pub.id,
                service_type=PublicationServiceType.PIN,  # 499
                user_id=user.id,
            )
        ),
        world.mediator_call(
            BuyPublicationServiceRequest(
                publication_id=pub.id,
                service_type=PublicationServiceType.HIGHLIGHT,  # 299
                user_id=user.id,
            )
        ),
        return_exceptions=True,
    )

    session.expire_all()
    balance = (await SQLAlchemyUserRepo(session).get_by_tg_id(1022)).balance
    bought = [r for r in results if not isinstance(r, Exception)]
    assert len(bought) == 1, f"куплено {len(bought)} услуг, остаток {balance}"
    assert balance in (Decimal("1"), Decimal("201")), balance


# второй тап приходит в уже закрытый диалог -> UnknownIntent (алерт «ошибка»)
@pytest.mark.allow_bot_errors
async def test_double_tap_buy_subscription_charges_once(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=1031, balance=Decimal("5000"))
    await session.commit()
    u = world.user(1031)
    await u.send("/start")
    await u.click("Ранний доступ")
    await u.click("Получить доступ")

    await _two_taps(u, "Подключить подписку")

    session.expire_all()
    user = await SQLAlchemyUserRepo(session).get_by_tg_id(1031)
    assert user.balance == Decimal("3001"), f"списано {Decimal('5000') - user.balance}"


# второй тап приходит в уже закрытый диалог -> UnknownIntent (алерт «ошибка»)
@pytest.mark.allow_bot_errors
async def test_double_tap_admin_balance_confirm_applies_once(world, session):
    from .conftest import ADMIN_TG_ID

    region = await make_region(session)
    await make_user(session, region.id, tg_id=ADMIN_TG_ID)
    await make_user(session, region.id, tg_id=1032, balance=Decimal("0"))
    await session.commit()
    admin = world.admin()
    await admin.send("/admin")
    await admin.click("Баланс пользователей")
    await admin.send("1032")
    await admin.click("Изменить баланс")
    await admin.send("+500")

    await _two_taps(admin, "Подтвердить")

    session.expire_all()
    user = await SQLAlchemyUserRepo(session).get_by_tg_id(1032)
    assert user.balance == Decimal("500"), f"начислено {user.balance}"


async def test_double_tap_save_store_items_adds_once(world, session):
    from .test_store_flow import _add_items, _create_store, _new_user, _store

    u = await _new_user(world, session)
    await _create_store(u)
    await _add_items(u, "х111хх01-1000\nо100оо77-2000")

    await _two_taps(u, "Сохранить")

    store = await _store(session)
    assert len(store.store_items) == 2, store.store_items


# второй тап приходит в уже закрытый диалог -> UnknownIntent (алерт «ошибка»)
@pytest.mark.allow_bot_errors
async def test_double_tap_service_from_menu_charges_once(world, session):
    from datetime import datetime, timedelta, timezone

    from ..factories import make_ad, make_publication

    region = await make_region(session)
    me = await make_user(session, region.id, tg_id=1033, balance=Decimal("5000"))
    ad = await make_ad(session, me, plate="А002АА77")
    await make_publication(
        session, ad, publish_at_utc=datetime.now(timezone.utc) + timedelta(days=2)
    )
    await session.commit()
    u = world.user(1033)
    await u.send("/start")
    await u.click("Продать быстрее")
    await u.click("Закрепление")
    await u.click("А002АА77")

    await _two_taps(u, "Подключить")

    session.expire_all()
    user = await SQLAlchemyUserRepo(session).get_by_tg_id(1033)
    assert user.balance == Decimal("4501"), f"списано {Decimal('5000') - user.balance}"
