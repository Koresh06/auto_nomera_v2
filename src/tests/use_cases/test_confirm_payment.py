"""
Tests for ConfirmPaymentUseCase covering the fixes from the audit:

- AUD-07: idempotency — an already-PAID payment must not be reprocessed
  (guards against double balance top-up on a duplicate webhook/task delivery).
- AUD-14: applying a purchased service's effect (priority_publish /
  apply_service_to_published) must not crash the whole confirmation if it
  raises — the user still gets notified and teleported back.
- AUD-03/AUD-104: a slot payment that loses the booking/conversion race to
  another user must compensate the paid amount to the user's balance instead
  of silently vanishing or leaving the payment stuck.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta, time as time_
from decimal import Decimal

from src.application.use_cases.payment.confirm import (
    ConfirmPaymentRequest,
    ConfirmPaymentUseCase,
)
from src.domain.entities.ad import Ad
from src.domain.entities.payment import Payment
from src.domain.entities.publication import Publication
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.entities.user import User
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.enums.role import UserRole
from src.domain.exceptions.slot_reservation import SlotAlreadyBooked
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.slot_key import SlotKey
from src.infrastructure.redis.holt_store.in_memory import InMemorySlotHoldStore
from src.infrastructure.repositories.slot.in_memory import (
    InMemorySlotBookingRepo,
    InMemorySlotConvertedRepo,
)


class FakePaymentRepo:
    def __init__(self, payment: Payment) -> None:
        self._payment = payment
        self.saved: list[Payment] = []

    async def get_by_external_id_for_update(self, external_id: str) -> Payment | None:
        return self._payment if self._payment.external_id == external_id else None

    async def get_by_external_id(self, external_id: str) -> Payment | None:
        return await self.get_by_external_id_for_update(external_id)

    async def save(self, payment: Payment) -> None:
        self.saved.append(payment)


class FakeUserRepo:
    def __init__(self, user: User) -> None:
        self._user = user
        self.saved: list[User] = []

    async def get_by_id_for_update(self, user_id):

        return await self.get_by_id(user_id)

    async def get_by_id(self, user_id: int) -> User | None:
        return self._user if self._user.id == user_id else None

    async def save(self, user: User) -> None:
        self.saved.append(user)


class FakePublicationRepo:
    def __init__(self, publication: Publication | None = None) -> None:
        self._publication = publication
        self.saved: list[Publication] = []

    async def get_by_id(self, publication_id: int) -> Publication | None:
        if self._publication and self._publication.id == publication_id:
            return self._publication
        return None

    async def save(self, publication: Publication) -> None:
        self.saved.append(publication)


class FakeAdRepo:
    def __init__(self, ad: Ad | None = None) -> None:
        self._ad = ad

    async def get_by_id(self, ad_id: int) -> Ad | None:
        if self._ad and self._ad.id == ad_id:
            return self._ad
        return None


class FakeServiceDefRepo:
    def __init__(self, definition: ServiceDefinition) -> None:
        self._definition = definition

    async def get_by_type(self, service_type) -> ServiceDefinition:
        return self._definition


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


class FakeTeleporter:
    def __init__(self, *, fail: bool = False) -> None:
        self.started: list[dict] = []
        self._fail = fail

    async def start(self, *, user_id, chat_id, state_key, data=None) -> None:
        if self._fail:
            raise RuntimeError("teleport boom")
        self.started.append(
            {"user_id": user_id, "chat_id": chat_id, "state_key": state_key}
        )


class FakeNotificationService:
    def __init__(self) -> None:
        self.notified_users: list[tuple[int, str]] = []

    async def notify_user(self, *, tg_id: int, text: str, reply_markup=None) -> None:
        self.notified_users.append((tg_id, text))

    async def notify_admins(
        self, *, text: str, photo_id=None, reply_markup=None
    ) -> None:
        pass


@dataclass
class FakePaymentNotifier:
    user_notifications: list[tuple[Payment, dict | None]] = field(default_factory=list)
    admin_notifications: list[tuple[Payment, User]] = field(default_factory=list)

    async def notify_user(self, payment: Payment, extra: dict | None = None) -> None:
        self.user_notifications.append((payment, extra))

    async def notify_admins(self, payment: Payment, user: User) -> None:
        self.admin_notifications.append((payment, user))


class RaisingUseCase:
    """Imitates priority_publish/apply_service_to_published/confirm_paid_slot
    raising an exception when invoked."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls = 0

    async def __call__(self, command) -> None:
        self.calls += 1
        raise self._exc


class NoOpUseCase:
    def __init__(self) -> None:
        self.calls: list = []

    async def __call__(self, command) -> None:
        self.calls.append(command)


def make_payment(**overrides) -> Payment:
    defaults = dict(
        id=1,
        external_id="ext-123",
        user_id=1,
        method=PaymentMethod.YOOKASSA,
        amount=Decimal("500"),
        purpose=PaymentPurpose.BALANCE_TOPUP,
        status=PaymentStatus.PENDING,
        meta={},
    )
    defaults.update(overrides)
    return Payment(**defaults)


def make_user(**overrides) -> User:
    defaults = dict(
        id=1,
        tg_id=1001,
        role=UserRole.USER,
        phone=None,
        region_id=1,
        balance=Decimal("0"),
    )
    defaults.update(overrides)
    return User(**defaults)


def make_use_case(
    *,
    payment: Payment,
    user: User,
    publication: Publication | None = None,
    ad: Ad | None = None,
    service_def: ServiceDefinition | None = None,
    confirm_paid_slot=None,
    apply_service_to_published=None,
    priority_publish=None,
    reservation_service: SlotReservationService | None = None,
    teleporter_fails: bool = False,
) -> tuple[ConfirmPaymentUseCase, dict]:
    payment_repo = FakePaymentRepo(payment)
    user_repo = FakeUserRepo(user)
    publication_repo = FakePublicationRepo(publication)
    if ad is None and publication is not None:
        ad = Ad(
            id=publication.ad_id,
            user_id=user.id,
            region_id=publication.region_id,
            ad_type=AdType.SALE,
            status=AdStatus.PUBLISHED,
        )
    ad_repo = FakeAdRepo(ad)
    service_def_repo = FakeServiceDefRepo(
        service_def
        or ServiceDefinition(
            id=1,
            title="Test service",
            type=PublicationServiceType.PRIORITY_PUBLISH,
            price=100,
        )
    )
    tx = FakeTransactionManager()
    teleporter = FakeTeleporter(fail=teleporter_fails)
    notifier = FakePaymentNotifier()
    notification_service = FakeNotificationService()
    reservation = reservation_service or SlotReservationService(
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=InMemorySlotConvertedRepo(),
        hold_store=InMemorySlotHoldStore(),
        hold_ttl=timedelta(minutes=15),
    )

    use_case = ConfirmPaymentUseCase(
        payment_repo=payment_repo,
        user_repo=user_repo,
        publication_repo=publication_repo,
        ad_repo=ad_repo,
        service_def_repo=service_def_repo,
        confirm_paid_slot=confirm_paid_slot or NoOpUseCase(),
        apply_service_to_published=apply_service_to_published or NoOpUseCase(),
        priority_publish=priority_publish or NoOpUseCase(),
        reservation_service=reservation,
        teleporter=teleporter,
        notification_service=notification_service,
        payment_notifier=notifier,
        transaction_manager=tx,
    )
    ctx = {
        "payment_repo": payment_repo,
        "user_repo": user_repo,
        "publication_repo": publication_repo,
        "tx": tx,
        "teleporter": teleporter,
        "notifier": notifier,
        "notification_service": notification_service,
    }
    return use_case, ctx


async def test_confirm_payment_is_idempotent_for_already_paid():
    payment = make_payment(status=PaymentStatus.PAID)
    user = make_user(balance=Decimal("0"))
    use_case, ctx = make_use_case(payment=payment, user=user)

    await use_case(ConfirmPaymentRequest(external_id="ext-123"))

    # не должно быть ни top_up, ни сохранений, ни уведомлений — платёж уже обработан
    assert ctx["user_repo"].saved == []
    assert ctx["notifier"].user_notifications == []
    assert ctx["tx"].commits == 0


async def test_confirm_payment_balance_topup_tops_up_user_balance():
    payment = make_payment(purpose=PaymentPurpose.BALANCE_TOPUP, amount=Decimal("300"))
    user = make_user(balance=Decimal("100"))
    use_case, ctx = make_use_case(payment=payment, user=user)

    await use_case(ConfirmPaymentRequest(external_id="ext-123"))

    assert user.balance == Decimal("400")
    assert payment.status == PaymentStatus.PAID
    assert len(ctx["notifier"].user_notifications) == 1
    assert (
        ctx["teleporter"].started == []
    )  # no return_to in meta — nothing to teleport to


async def test_confirm_payment_publication_service_effect_failure_does_not_crash():
    """AUD-14: priority_publish raising must not abort the whole confirmation —
    payment stays PAID, service stays attached, user still gets notified."""
    publication = Publication(
        id=5, ad_id=1, region_id=1, status=PublicationStatus.SCHEDULED
    )
    payment = make_payment(
        purpose=PaymentPurpose.PUBLICATION_SERVICE,
        purpose_id=5,
        meta={"service_type": PublicationServiceType.PRIORITY_PUBLISH.value},
    )
    user = make_user()
    definition = ServiceDefinition(
        id=1,
        title="Вне очереди",
        type=PublicationServiceType.PRIORITY_PUBLISH,
        price=200,
        duration_days=None,
    )
    failing_priority_publish = RaisingUseCase(RuntimeError("boom"))

    use_case, ctx = make_use_case(
        payment=payment,
        user=user,
        publication=publication,
        service_def=definition,
        priority_publish=failing_priority_publish,
    )

    # не должно бросить исключение наружу
    await use_case(ConfirmPaymentRequest(external_id="ext-123"))

    assert failing_priority_publish.calls == 1
    assert payment.status == PaymentStatus.PAID
    assert len(publication.services) == 1
    assert publication.services[0].type == PublicationServiceType.PRIORITY_PUBLISH
    # уведомление и телепорт всё равно должны произойти
    assert len(ctx["notifier"].user_notifications) == 1


async def test_confirm_payment_slot_conflict_compensates_balance():
    """AUD-03: confirm_paid_slot loses the race -> money goes to user balance,
    notify_user is called with slot_conflict flag so the user sees why."""
    publication = Publication(
        id=7,
        ad_id=1,
        region_id=1,
        status=PublicationStatus.AWAITING_PAYMENT,
    )
    payment = make_payment(
        purpose=PaymentPurpose.SLOT,
        purpose_id=7,
        amount=Decimal("199"),
    )
    user = make_user(balance=Decimal("50"))
    failing_confirm_slot = RaisingUseCase(SlotAlreadyBooked())

    use_case, ctx = make_use_case(
        payment=payment,
        user=user,
        publication=publication,
        confirm_paid_slot=failing_confirm_slot,
    )

    await use_case(ConfirmPaymentRequest(external_id="ext-123"))

    assert failing_confirm_slot.calls == 1
    assert user.balance == Decimal("249")  # 50 + 199 compensated
    assert payment.status == PaymentStatus.PAID
    assert len(ctx["notifier"].user_notifications) == 1
    _, extra = ctx["notifier"].user_notifications[0]
    assert extra["slot_conflict"] is True
    assert extra["compensated_amount"] == Decimal("199")


async def test_confirm_payment_slot_without_publication_conflict_compensates_balance():
    """Second SLOT sub-branch (no purpose_id yet, pre-publication slot payment):
    if mark_converted loses to a different owner, compensate instead of silently
    leaving the user with a slot that isn't actually theirs."""
    other_owner_converted = InMemorySlotConvertedRepo()
    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time_(10, 0))
    await other_owner_converted.mark_converted(slot=slot, user_id=999, ad_id=42)

    reservation = SlotReservationService(
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=other_owner_converted,
        hold_store=InMemorySlotHoldStore(),
        hold_ttl=timedelta(minutes=15),
    )

    payment = make_payment(
        purpose=PaymentPurpose.SLOT,
        purpose_id=None,
        amount=Decimal("199"),
        meta={
            "return_data": {
                "slot": {
                    "region_id": 1,
                    "slot_day": "2026-02-12",
                    "slot_time": "10:00:00",
                }
            }
        },
    )
    user = make_user(balance=Decimal("0"))

    use_case, ctx = make_use_case(
        payment=payment,
        user=user,
        reservation_service=reservation,
    )

    await use_case(ConfirmPaymentRequest(external_id="ext-123"))

    assert user.balance == Decimal("199")
    _, extra = ctx["notifier"].user_notifications[0]
    assert extra["slot_conflict"] is True


async def test_confirm_payment_highlight_for_store_compensates_balance():
    """AUD-19: paying for HIGHLIGHT externally (YooKassa/Stars) for a STORE
    ad must not silently apply a no-op service — compensate to balance and
    notify, same pattern as the slot-conflict case."""
    publication = Publication(
        id=5, ad_id=1, region_id=1, status=PublicationStatus.PUBLISHED
    )
    payment = make_payment(
        purpose=PaymentPurpose.PUBLICATION_SERVICE,
        purpose_id=5,
        amount=Decimal("150"),
        meta={"service_type": PublicationServiceType.HIGHLIGHT.value},
    )
    user = make_user(balance=Decimal("0"))
    store_ad = Ad(
        id=1, user_id=1, region_id=1, ad_type=AdType.STORE, status=AdStatus.READY
    )
    definition = ServiceDefinition(
        id=1, title="Выделение", type=PublicationServiceType.HIGHLIGHT, price=150
    )

    use_case, ctx = make_use_case(
        payment=payment,
        user=user,
        publication=publication,
        ad=store_ad,
        service_def=definition,
    )

    await use_case(ConfirmPaymentRequest(external_id="ext-123"))

    assert user.balance == Decimal("150")
    assert len(publication.services) == 0
    _, extra = ctx["notifier"].user_notifications[0]
    assert extra["service_not_allowed"] is True
    assert extra["compensated_amount"] == Decimal("150")


async def test_confirm_payment_teleport_failure_sends_fallback_notification():
    """AUD-22: if teleporting the user back fails, they must still get a
    fallback message telling them the payment succeeded — not nothing."""
    payment = make_payment(
        purpose=PaymentPurpose.BALANCE_TOPUP,
        amount=Decimal("300"),
        meta={
            "return_to": {"user_id": 1001, "chat_id": 1001},
            "return_state": "SomeSG:state",
        },
    )
    user = make_user(balance=Decimal("0"))
    use_case, ctx = make_use_case(payment=payment, user=user, teleporter_fails=True)

    await use_case(ConfirmPaymentRequest(external_id="ext-123"))

    assert ctx["teleporter"].started == []
    assert len(ctx["notification_service"].notified_users) == 1
    tg_id, text = ctx["notification_service"].notified_users[0]
    assert tg_id == 1001
    assert "/start" in text
