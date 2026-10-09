"""
Coverage for src/application/use_cases/payment/{create,get_by_external_id,
get_payment_details,mark}.py — previously entirely untested
(confirm.py is covered separately in test_confirm_payment.py).
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.application.dtos.payment import PaymentDetailItemDTO
from src.application.exceptions.payment import PaymentNotFoundByExternalException
from src.application.exceptions.user import (
    PaymentBlockedException,
    UserNotFoundException,
)
from src.application.ports.payment.provider import PaymentProvider
from src.application.services.payment.provider_registry import PaymentProviderRegistry
from src.application.use_cases.payment.create import (
    CreatePaymentRequest,
    CreatePaymentUseCase,
)
from src.application.use_cases.payment.get_by_external_id import (
    GetPaymentByExternalIdRequest,
    GetPaymentByExternalIdUseCase,
)
from src.application.use_cases.payment.get_payment_details import (
    GetPaymentDetailsRequest,
    GetPaymentDetailsUseCase,
)
from src.application.use_cases.payment.mark import (
    MarkPaymentFailedRequest,
    MarkPaymentFailedUseCase,
)
from src.domain.entities.payment import Payment
from src.domain.entities.user import User
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.domain.enums.period import StatsPeriod
from src.domain.enums.role import UserRole
from src.domain.exceptions.payment import PaymentProviderNotFoundException


class FakePaymentRepo:
    def __init__(self, payments: list[Payment] | None = None) -> None:
        self._by_external: dict[str, Payment] = {
            p.external_id: p for p in (payments or [])
        }
        self.created: list[Payment] = []
        self.saved: list[Payment] = []
        self.paid_rows: list[tuple] = []

    async def create(self, payment: Payment) -> Payment:
        self.created.append(payment)
        self._by_external[payment.external_id] = payment
        return payment

    async def get_by_external_id(self, external_id: str) -> Payment | None:
        return self._by_external.get(external_id)

    async def save(self, payment: Payment) -> None:
        self.saved.append(payment)

    async def list_paid_payments(self, *, since_utc, region_id):
        return self.paid_rows


class FakeUserRepo:
    def __init__(self, users: list[User] | None = None) -> None:
        self._store = {u.id: u for u in (users or [])}

    async def get_by_id_for_update(self, user_id):

        return await self.get_by_id(user_id)

    async def get_by_id(self, user_id: int) -> User | None:
        return self._store.get(user_id)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeProvider(PaymentProvider):
    def __init__(self, meta: dict | None = None) -> None:
        self.meta = meta or {"invoice_url": "https://pay.example/1"}
        self.calls: list[dict] = []

    async def create_invoice(
        self, *, user_id, amount, currency, description, external_id, **kwargs
    ):
        self.calls.append(
            {
                "user_id": user_id,
                "amount": amount,
                "currency": currency,
                "description": description,
                "external_id": external_id,
                **kwargs,
            }
        )
        return self.meta

    async def get_payment_instructions(self, payment: Payment) -> dict:
        return {}


def make_user(**overrides) -> User:
    defaults = dict(
        id=1, tg_id=1001, role=UserRole.USER, phone=None, region_id=1, balance=0
    )
    defaults.update(overrides)
    return User(**defaults)


def make_payment(**overrides) -> Payment:
    defaults = dict(
        external_id="ext-1",
        user_id=1,
        method=PaymentMethod.YOOKASSA,
        amount=Decimal("500"),
        purpose=PaymentPurpose.BALANCE_TOPUP,
    )
    defaults.update(overrides)
    return Payment(**defaults)


def make_registry(provider: FakeProvider | None = None) -> PaymentProviderRegistry:
    registry = PaymentProviderRegistry()
    registry.register(PaymentMethod.YOOKASSA, provider or FakeProvider())
    return registry


# ---------- CreatePaymentUseCase ----------


async def test_create_payment_raises_when_user_missing():
    use_case = CreatePaymentUseCase(
        payment_repo=FakePaymentRepo(),
        user_repo=FakeUserRepo([]),
        provider_registry=make_registry(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(UserNotFoundException):
        await use_case(
            CreatePaymentRequest(
                user_id=1,
                amount=Decimal("500"),
                method=PaymentMethod.YOOKASSA,
                purpose=PaymentPurpose.BALANCE_TOPUP,
            )
        )


async def test_create_payment_raises_when_user_payment_blocked():
    user = make_user(id=1, is_payment_blocked=True)
    use_case = CreatePaymentUseCase(
        payment_repo=FakePaymentRepo(),
        user_repo=FakeUserRepo([user]),
        provider_registry=make_registry(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(PaymentBlockedException):
        await use_case(
            CreatePaymentRequest(
                user_id=1,
                amount=Decimal("500"),
                method=PaymentMethod.YOOKASSA,
                purpose=PaymentPurpose.BALANCE_TOPUP,
            )
        )


async def test_create_payment_raises_when_provider_not_registered():
    user = make_user(id=1)
    use_case = CreatePaymentUseCase(
        payment_repo=FakePaymentRepo(),
        user_repo=FakeUserRepo([user]),
        provider_registry=PaymentProviderRegistry(),  # nothing registered
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(PaymentProviderNotFoundException):
        await use_case(
            CreatePaymentRequest(
                user_id=1,
                amount=Decimal("500"),
                method=PaymentMethod.YOOKASSA,
                purpose=PaymentPurpose.BALANCE_TOPUP,
            )
        )


async def test_create_payment_happy_path_creates_pending_payment():
    user = make_user(id=1, tg_id=777, phone="+79990000000")
    provider = FakeProvider(meta={"invoice_url": "https://pay.example/1"})
    payment_repo = FakePaymentRepo()
    tx = FakeTransactionManager()
    use_case = CreatePaymentUseCase(
        payment_repo=payment_repo,
        user_repo=FakeUserRepo([user]),
        provider_registry=make_registry(provider),
        transaction_manager=tx,
    )

    payment = await use_case(
        CreatePaymentRequest(
            user_id=1,
            amount=Decimal("500"),
            method=PaymentMethod.YOOKASSA,
            purpose=PaymentPurpose.BALANCE_TOPUP,
            description="top up",
            meta={"source": "bot"},
        )
    )

    assert payment.status == PaymentStatus.PENDING
    assert payment.meta == {"source": "bot", "invoice_url": "https://pay.example/1"}
    assert payment_repo.created == [payment]
    assert tx.committed is True
    assert provider.calls[0]["user_id"] == 1
    assert provider.calls[0]["phone"] == "+79990000000"
    assert provider.calls[0]["chat_id"] == 777


async def test_create_payment_manual_card_starts_waiting_confirmation():
    user = make_user(id=1)
    registry = PaymentProviderRegistry()
    registry.register(PaymentMethod.MANUAL_CARD, FakeProvider())
    use_case = CreatePaymentUseCase(
        payment_repo=FakePaymentRepo(),
        user_repo=FakeUserRepo([user]),
        provider_registry=registry,
        transaction_manager=FakeTransactionManager(),
    )

    payment = await use_case(
        CreatePaymentRequest(
            user_id=1,
            amount=Decimal("500"),
            method=PaymentMethod.MANUAL_CARD,
            purpose=PaymentPurpose.BALANCE_TOPUP,
        )
    )

    assert payment.status == PaymentStatus.WAITING_CONFIRMATION


# ---------- GetPaymentByExternalIdUseCase ----------


async def test_get_payment_by_external_id_raises_when_missing():
    use_case = GetPaymentByExternalIdUseCase(payment_repo=FakePaymentRepo())

    with pytest.raises(PaymentNotFoundByExternalException):
        await use_case(GetPaymentByExternalIdRequest(external_id="missing"))


async def test_get_payment_by_external_id_returns_payment():
    payment = make_payment(external_id="ext-42")
    use_case = GetPaymentByExternalIdUseCase(payment_repo=FakePaymentRepo([payment]))

    result = await use_case(GetPaymentByExternalIdRequest(external_id="ext-42"))

    assert result is payment


# ---------- GetPaymentDetailsUseCase ----------


async def test_get_payment_details_maps_rows_to_dtos():
    payment = make_payment(
        amount=Decimal("1000"),
        method=PaymentMethod.TELEGRAM_STARS,
        paid_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    repo = FakePaymentRepo()
    repo.paid_rows = [(payment, 999, "Full Name", "username1")]
    use_case = GetPaymentDetailsUseCase(payment_repo=repo)

    result = await use_case(GetPaymentDetailsRequest(period=StatsPeriod.ALL))

    assert result == [
        PaymentDetailItemDTO(
            tg_id=999,
            full_name="Full Name",
            username="username1",
            amount=Decimal("1000"),
            method_value=PaymentMethod.TELEGRAM_STARS.value,
            paid_at=payment.paid_at,
        )
    ]


async def test_get_payment_details_empty_when_no_rows():
    use_case = GetPaymentDetailsUseCase(payment_repo=FakePaymentRepo())

    result = await use_case(
        GetPaymentDetailsRequest(period=StatsPeriod.TODAY, region_id=1)
    )

    assert result == []


# ---------- MarkPaymentFailedUseCase ----------


async def test_mark_payment_failed_raises_when_missing():
    use_case = MarkPaymentFailedUseCase(
        payment_repo=FakePaymentRepo(), transaction_manager=FakeTransactionManager()
    )

    with pytest.raises(PaymentNotFoundByExternalException):
        await use_case(MarkPaymentFailedRequest(external_id="missing"))


async def test_mark_payment_failed_marks_pending_payment():
    payment = make_payment(external_id="ext-1", status=PaymentStatus.PENDING)
    repo = FakePaymentRepo([payment])
    tx = FakeTransactionManager()
    use_case = MarkPaymentFailedUseCase(payment_repo=repo, transaction_manager=tx)

    await use_case(MarkPaymentFailedRequest(external_id="ext-1"))

    assert payment.status == PaymentStatus.FAILED
    assert repo.saved == [payment]
    assert tx.committed is True


async def test_mark_payment_failed_is_noop_for_already_paid_payment():
    payment = make_payment(external_id="ext-1", status=PaymentStatus.PAID)
    repo = FakePaymentRepo([payment])
    tx = FakeTransactionManager()
    use_case = MarkPaymentFailedUseCase(payment_repo=repo, transaction_manager=tx)

    await use_case(MarkPaymentFailedRequest(external_id="ext-1"))

    assert payment.status == PaymentStatus.PAID
    assert repo.saved == []
    assert tx.committed is False
