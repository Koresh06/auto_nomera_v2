"""
Coverage for the slots use cases not already exercised elsewhere:
HoldSlotUseCase, ReleaseHoldUseCase, GetCalendarUseCase,
ConfirmPaidSlotFromBalanceUseCase.

Also a regression test for a newly found instance of the AUD-03 bug class:
ConfirmPaidSlotFromBalanceUseCase used to charge the user's balance and then
call converted_repo.mark_converted() without checking the result — a user
could be charged for a slot that someone else had just taken. Fixed by
checking conversion *before* charging.
"""

from datetime import timedelta

import pytest

from src.application.exceptions.region import RegionNotFoundException
from src.application.exceptions.user import UserNotFoundException
from src.application.use_cases.slots.confirm_paid_slot_from_balance import (
    ConfirmPaidSlotFromBalanceRequest,
    ConfirmPaidSlotFromBalanceUseCase,
)
from src.application.use_cases.slots.get_calendar import (
    GetCalendarRequest,
    GetCalendarUseCase,
)
from src.application.use_cases.slots.hold_slot import HoldSlotRequest, HoldSlotUseCase
from src.application.use_cases.slots.release_hold import (
    ReleaseHoldRequest,
    ReleaseHoldUseCase,
)
from src.domain.entities.region import Region
from src.domain.entities.user import User
from src.domain.enums.region import RegionStatus
from src.domain.enums.role import UserRole
from src.domain.exceptions.region import RegionDisabledError
from src.domain.exceptions.slot_reservation import SlotAlreadyConverted
from src.domain.exceptions.user import InsufficientBalance
from src.domain.services.region.region_guard import RegionGuard
from src.domain.services.slots.calendar_builder import CalendarBuilder
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.timezone_name import TimezoneName
from src.infrastructure.redis.holt_store.in_memory import InMemorySlotHoldStore
from src.infrastructure.repositories.slot.in_memory import (
    InMemorySlotBookingRepo,
    InMemorySlotConvertedRepo,
)
from src.utils.get_datetime_utc_now import get_datetime_utc_now


class FakeRegionRepo:
    def __init__(self, region: Region | None) -> None:
        self._region = region

    async def get_by_id(self, region_id: int) -> Region | None:
        if self._region and self._region.id == region_id:
            return self._region
        return None


class FakeUserRepo:
    def __init__(self, user: User | None) -> None:
        self._user = user
        self.saved: list[User] = []

    async def get_by_id(self, user_id: int) -> User | None:
        if self._user and self._user.id == user_id:
            return self._user
        return None

    async def save(self, user: User) -> None:
        self.saved.append(user)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_region(status: RegionStatus = RegionStatus.ACTIVE) -> Region:
    return Region(
        id=1,
        title="Test",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="testchannel",
        status=status,
        metadata=RegionMetadata(),
        settings=RegionSettings(),
    )


def make_user(**overrides) -> User:
    defaults = dict(
        id=1, tg_id=1, role=UserRole.USER, phone=None, region_id=1, balance=0
    )
    defaults.update(overrides)
    return User(**defaults)


# ---------- HoldSlotUseCase ----------


async def test_hold_slot_raises_when_region_not_found():
    use_case = HoldSlotUseCase(
        region_repo=FakeRegionRepo(None),
        calendar_builder=CalendarBuilder(),
        reservation_service=SlotReservationService(
            booking_repo=InMemorySlotBookingRepo(),
            converted_repo=InMemorySlotConvertedRepo(),
            hold_store=InMemorySlotHoldStore(),
            hold_ttl=timedelta(minutes=15),
        ),
        transaction_manager=FakeTransactionManager(),
    )

    from datetime import date, time

    with pytest.raises(RegionNotFoundException):
        await use_case(
            HoldSlotRequest(
                region_id=999,
                slot=SlotKey(
                    region_id=999, local_day=date(2026, 2, 12), local_time=time(10, 0)
                ),
                user_id=1,
            )
        )


async def test_hold_slot_commits_and_returns_result():
    region = make_region()
    now = get_datetime_utc_now()
    future = CalendarBuilder().generate_future_slots(region=region, now_utc=now)
    slot = future[0]
    tx = FakeTransactionManager()

    use_case = HoldSlotUseCase(
        region_repo=FakeRegionRepo(region),
        calendar_builder=CalendarBuilder(),
        reservation_service=SlotReservationService(
            booking_repo=InMemorySlotBookingRepo(),
            converted_repo=InMemorySlotConvertedRepo(),
            hold_store=InMemorySlotHoldStore(),
            hold_ttl=timedelta(minutes=15),
        ),
        transaction_manager=tx,
    )

    result = await use_case(
        HoldSlotRequest(region_id=1, slot=slot, user_id=100, now_utc=now)
    )

    assert result.slot == slot
    assert tx.commits == 1


# ---------- ReleaseHoldUseCase ----------


async def test_release_hold_delegates_to_reservation_service():
    hold_store = InMemorySlotHoldStore()
    reservation_service = SlotReservationService(
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=InMemorySlotConvertedRepo(),
        hold_store=hold_store,
        hold_ttl=timedelta(minutes=15),
    )
    from src.domain.value_objects.hold_owner import HoldOwner
    from datetime import date, time

    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))
    await hold_store.set(slot, HoldOwner(user_id=1), timedelta(minutes=15))

    tx = FakeTransactionManager()
    use_case = ReleaseHoldUseCase(
        reservation_service=reservation_service, transaction_manager=tx
    )

    await use_case(ReleaseHoldRequest(slot=slot, user_id=1))

    assert await hold_store.get(slot) is None
    assert tx.commits == 1


# ---------- GetCalendarUseCase ----------


async def test_get_calendar_raises_when_region_disabled():
    region = make_region(status=RegionStatus.DISABLED)
    use_case = GetCalendarUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        region_repo=FakeRegionRepo(region),
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=InMemorySlotConvertedRepo(),
        hold_store=InMemorySlotHoldStore(),
        calendar_builder=CalendarBuilder(),
    )

    with pytest.raises(RegionDisabledError):
        await use_case(GetCalendarRequest(region_id=1))


async def test_get_calendar_returns_slots_for_active_region():
    region = make_region()
    use_case = GetCalendarUseCase(
        region_guard=RegionGuard(FakeRegionRepo(region)),
        region_repo=FakeRegionRepo(region),
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=InMemorySlotConvertedRepo(),
        hold_store=InMemorySlotHoldStore(),
        calendar_builder=CalendarBuilder(),
    )

    result = await use_case(GetCalendarRequest(region_id=1))

    assert result.region_id == 1
    assert len(result.slots) > 0
    assert all(s.id for s in result.slots)


# ---------- ConfirmPaidSlotFromBalanceUseCase ----------


async def test_confirm_paid_slot_from_balance_raises_for_unknown_user():
    use_case = ConfirmPaidSlotFromBalanceUseCase(
        user_repo=FakeUserRepo(None),
        converted_repo=InMemorySlotConvertedRepo(),
        transaction_manager=FakeTransactionManager(),
    )
    from datetime import date, time

    with pytest.raises(UserNotFoundException):
        await use_case(
            ConfirmPaidSlotFromBalanceRequest(
                user_id=1,
                slot=SlotKey(
                    region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0)
                ),
                amount=199,
            )
        )


async def test_confirm_paid_slot_from_balance_charges_and_converts_on_success():
    from datetime import date, time

    user = make_user(balance=500)
    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))
    converted_repo = InMemorySlotConvertedRepo()
    tx = FakeTransactionManager()

    use_case = ConfirmPaidSlotFromBalanceUseCase(
        user_repo=FakeUserRepo(user),
        converted_repo=converted_repo,
        transaction_manager=tx,
    )

    await use_case(ConfirmPaidSlotFromBalanceRequest(user_id=1, slot=slot, amount=199))

    assert user.balance == 301
    assert await converted_repo.is_converted(slot) is True
    assert tx.commits == 1


async def test_confirm_paid_slot_from_balance_raises_without_charging_on_conflict():
    """The AUD-03-class bug found while adding this test: if another user
    already converted the slot, the balance must NOT be touched."""
    from datetime import date, time

    user = make_user(balance=500)
    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))
    converted_repo = InMemorySlotConvertedRepo()
    await converted_repo.mark_converted(slot=slot, user_id=999, ad_id=42)

    use_case = ConfirmPaidSlotFromBalanceUseCase(
        user_repo=FakeUserRepo(user),
        converted_repo=converted_repo,
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(SlotAlreadyConverted):
        await use_case(
            ConfirmPaidSlotFromBalanceRequest(user_id=1, slot=slot, amount=199)
        )

    assert user.balance == 500  # untouched


async def test_confirm_paid_slot_from_balance_insufficient_balance_raises():
    from datetime import date, time

    user = make_user(balance=50)
    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))

    use_case = ConfirmPaidSlotFromBalanceUseCase(
        user_repo=FakeUserRepo(user),
        converted_repo=InMemorySlotConvertedRepo(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(InsufficientBalance):
        await use_case(
            ConfirmPaidSlotFromBalanceRequest(user_id=1, slot=slot, amount=199)
        )
