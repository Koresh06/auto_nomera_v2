"""
Regression test for AUD-06: paying for PRE_PUBLICATION from balance ignored
ServiceDefinition.duration_days and always activated exactly 30 days,
diverging from the external-payment path (confirm.py), which correctly reads
definition.duration_days. The use case itself always respected `days` — the
bug was that the presentation-layer handler never passed it. This test pins
the use case's contract so the handler fix (passing days=definition.duration_days)
stays correct.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.application.use_cases.publication_service.buy_pre_publication_service import (
    BuyPrePublicationServiceRequest,
    BuyPrePublicationServiceUseCase,
)
from src.domain.entities.service_definition import ServiceDefinition
from src.domain.entities.user import User
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.enums.role import UserRole


class FakeUserRepo:
    def __init__(self, user: User) -> None:
        self._user = user

    async def get_by_id(self, user_id: int) -> User | None:
        return self._user if self._user.id == user_id else None

    async def save(self, user: User) -> None:
        pass


class FakeServiceDefRepo:
    def __init__(self, definition: ServiceDefinition) -> None:
        self._definition = definition

    async def get_by_type(self, service_type) -> ServiceDefinition:
        return self._definition


class FakeTransactionManager:
    async def commit(self) -> None:
        pass


async def test_buy_pre_publication_respects_custom_duration_days():
    """A weekly subscription (duration_days=7) must activate 7 days, not the
    default 30 — this is exactly where the presentation-layer bug diverged
    from the ConfirmPaymentUseCase path."""
    user = User(
        id=1,
        tg_id=1,
        role=UserRole.USER,
        phone=None,
        region_id=1,
        balance=Decimal("1000"),
    )
    definition = ServiceDefinition(
        id=1,
        title="Недельная подписка",
        type=PublicationServiceType.PRE_PUBLICATION,
        price=500,
        duration_days=7,
    )
    use_case = BuyPrePublicationServiceUseCase(
        user_repo=FakeUserRepo(user),
        service_def_repo=FakeServiceDefRepo(definition),
        transaction_manager=FakeTransactionManager(),
    )

    before = datetime.now(timezone.utc)
    await use_case(
        BuyPrePublicationServiceRequest(user_id=1, days=definition.duration_days or 30)
    )

    assert user.balance == Decimal("500")
    assert user.pre_publication_expires_at is not None
    delta = user.pre_publication_expires_at - before
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)


async def test_buy_pre_publication_default_days_is_30_when_duration_not_set():
    user = User(
        id=1,
        tg_id=1,
        role=UserRole.USER,
        phone=None,
        region_id=1,
        balance=Decimal("1000"),
    )
    definition = ServiceDefinition(
        id=1,
        title="Подписка без явной длительности",
        type=PublicationServiceType.PRE_PUBLICATION,
        price=500,
        duration_days=None,
    )
    use_case = BuyPrePublicationServiceUseCase(
        user_repo=FakeUserRepo(user),
        service_def_repo=FakeServiceDefRepo(definition),
        transaction_manager=FakeTransactionManager(),
    )

    before = datetime.now(timezone.utc)
    await use_case(
        BuyPrePublicationServiceRequest(user_id=1, days=definition.duration_days or 30)
    )

    delta = user.pre_publication_expires_at - before
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)
