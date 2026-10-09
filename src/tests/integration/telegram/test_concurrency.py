"""Конкурентные нажатия, как в реальном Telegram: двойной тап по кнопке
приходит двумя параллельными callback'ами, а разные пользователи жмут
одновременно. Апдейты обрабатываются параллельно (как в polling aiogram)."""

import asyncio
from decimal import Decimal

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
