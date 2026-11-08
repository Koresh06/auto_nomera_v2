"""Журнал баланса на настоящих use case'ах и БД: запись появляется вместе с
изменением баланса и только если оно закоммичено."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
from src.application.use_cases.publication_service.buy_pre_publication_service import (
    BuyPrePublicationServiceRequest,
)
from src.application.use_cases.publication_service.buy_publication_service import (
    BuyPublicationServiceRequest,
)
from src.application.use_cases.slots.confirm_paid_slot_from_balance import (
    ConfirmPaidSlotFromBalanceRequest,
)
from src.application.use_cases.user.admin_adjust_balance import (
    AdminAdjustBalanceCommand,
)
from src.domain.enums.ad import AdType
from src.domain.enums.balance import BalanceTransactionKind as Kind
from src.domain.enums.payment import PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.exceptions.user import InsufficientBalance
from src.infrastructure.database.models import BalanceTransactionModel

from ..factories import (
    make_ad,
    make_payment,
    make_publication,
    make_region,
    make_user,
    slot,
)


async def _rows(session):
    session.expire_all()
    result = await session.execute(
        select(BalanceTransactionModel).order_by(BalanceTransactionModel.id)
    )
    return list(result.scalars())


async def _setup(session, balance="1000"):
    home = await make_region(session, title="Дом", channel_id=-1)
    other = await make_region(session, title="Чужой", channel_id=-2)
    user = await make_user(session, home.id, tg_id=555, balance=Decimal(balance))
    await session.commit()
    return home, other, user


async def test_admin_adjustments_are_journaled(world, session):
    home, _, user = await _setup(session)

    await world.mediator_call(
        AdminAdjustBalanceCommand(user_id=user.id, amount=Decimal("200"))
    )
    await world.mediator_call(
        AdminAdjustBalanceCommand(user_id=user.id, amount=Decimal("-50"))
    )

    rows = await _rows(session)
    assert [(r.kind, r.amount, r.balance_after) for r in rows] == [
        (Kind.ADMIN_CREDIT, Decimal("200"), Decimal("1200")),
        (Kind.ADMIN_DEBIT, Decimal("-50"), Decimal("1150")),
    ]
    assert {r.region_id for r in rows} == {home.id}


async def test_slot_purchase_is_journaled_in_the_slot_region(world, session):
    _, other, user = await _setup(session)
    key = slot(other.id, date.today() + timedelta(days=1))

    charged = await world.mediator_call(
        ConfirmPaidSlotFromBalanceRequest(
            user_id=user.id, slot=key, amount=Decimal("300")
        )
    )

    assert charged is True
    [row] = await _rows(session)
    assert (row.kind, row.amount) == (Kind.SLOT_PURCHASE, Decimal("-300"))
    assert row.region_id == other.id
    assert row.balance_after == Decimal("700")
    assert row.description.startswith("Слот ")


async def test_double_tap_on_slot_writes_one_record(world, session):
    _, other, user = await _setup(session)
    request = ConfirmPaidSlotFromBalanceRequest(
        user_id=user.id,
        slot=slot(other.id, date.today() + timedelta(days=1)),
        amount=Decimal("300"),
    )

    assert await world.mediator_call(request) is True
    assert await world.mediator_call(request) is False

    assert len(await _rows(session)) == 1


async def test_failed_charge_leaves_no_record(world, session):
    _, other, user = await _setup(session, balance="10")

    with pytest.raises(InsufficientBalance):
        await world.mediator_call(
            ConfirmPaidSlotFromBalanceRequest(
                user_id=user.id,
                slot=slot(other.id, date.today() + timedelta(days=1)),
                amount=Decimal("300"),
            )
        )

    assert await _rows(session) == []


async def test_service_purchase_is_journaled_in_the_publication_region(world, session):
    _, other, user = await _setup(session)
    ad = await make_ad(session, user, region_id=other.id)
    pub = await make_publication(session, ad, status=PublicationStatus.SCHEDULED)
    await session.commit()

    await world.mediator_call(
        BuyPublicationServiceRequest(
            publication_id=pub.id,
            service_type=PublicationServiceType.PIN,
            user_id=user.id,
        )
    )

    [row] = await _rows(session)
    assert row.kind == Kind.SERVICE_PURCHASE
    assert row.amount < 0
    assert (row.region_id, row.publication_id) == (other.id, pub.id)
    assert row.description


async def test_pre_publication_purchase_is_journaled(world, session):
    home, _, user = await _setup(session, balance="100000")

    await world.mediator_call(BuyPrePublicationServiceRequest(user_id=user.id, days=30))

    [row] = await _rows(session)
    assert row.kind == Kind.PRE_PUBLICATION_PURCHASE
    assert row.region_id == home.id
    assert row.balance_after == Decimal("100000") + row.amount


async def test_external_topup_is_journaled_once(world, session):
    _, _, user = await _setup(session)
    payment = await make_payment(
        session,
        user,
        external_id="topup",
        amount=Decimal("250"),
        status=PaymentStatus.PENDING,
    )
    await session.commit()

    request = ConfirmPaymentRequest(external_id="topup")
    await world.mediator_call(request)
    await world.mediator_call(request)  # повторный webhook

    [row] = await _rows(session)
    assert (row.kind, row.amount) == (Kind.TOPUP, Decimal("250"))
    assert row.payment_id == payment.id
    assert row.balance_after == Decimal("1250")


@pytest.mark.allow_bot_errors  # компенсация намеренно логируется как ERROR
async def test_compensation_is_journaled_with_the_payment(world, session):
    _, other, user = await _setup(session)
    ad = await make_ad(session, user, ad_type=AdType.STORE, region_id=other.id)
    pub = await make_publication(session, ad, status=PublicationStatus.PUBLISHED)
    payment = await make_payment(
        session,
        user,
        external_id="comp",
        amount=Decimal("150"),
        status=PaymentStatus.PENDING,
        purpose=PaymentPurpose.PUBLICATION_SERVICE,
        purpose_id=pub.id,
        meta={"service_type": PublicationServiceType.HIGHLIGHT.value},
    )
    await session.commit()

    await world.mediator_call(ConfirmPaymentRequest(external_id="comp"))

    [row] = await _rows(session)
    assert (row.kind, row.payment_id) == (Kind.COMPENSATION, payment.id)
    assert row.region_id == other.id


async def test_journal_replays_to_the_real_balance(world, session):
    """Главный инвариант: сумма журнала равна изменению баланса."""
    _, other, user = await _setup(session)
    start = Decimal("1000")
    await world.mediator_call(
        AdminAdjustBalanceCommand(user_id=user.id, amount=Decimal("500"))
    )
    await world.mediator_call(
        ConfirmPaidSlotFromBalanceRequest(
            user_id=user.id,
            slot=slot(other.id, date.today() + timedelta(days=1)),
            amount=Decimal("120"),
        )
    )
    await world.mediator_call(
        AdminAdjustBalanceCommand(user_id=user.id, amount=Decimal("-30"))
    )

    rows = await _rows(session)
    assert rows[-1].balance_after == start + sum(r.amount for r in rows)
