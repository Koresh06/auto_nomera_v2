import pytest
from datetime import date, time, datetime, timezone, timedelta

from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.hold_owner import HoldOwner
from src.domain.exceptions.slot_reservation import SlotAlreadyHeld, SlotAlreadyBooked
from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository


class InMemoryHoldStore(SlotHoldStore):
    def __init__(self):
        self._holds: dict[SlotKey, HoldOwner] = {}

    async def get(self, slot: SlotKey) -> HoldOwner | None:
        return self._holds.get(slot)

    async def set(self, slot: SlotKey, owner: HoldOwner, ttl: timedelta) -> None:
        # TTL не симулируем, это доменный тест
        self._holds[slot] = owner

    async def delete(self, slot: SlotKey) -> None:
        self._holds.pop(slot, None)


class InMemoryBookingRepo(SlotBookingRepository):
    def __init__(self):
        self._booked: set[SlotKey] = set()

    async def is_booked(self, slot: SlotKey) -> bool:
        return slot in self._booked

    async def book(self, slot: SlotKey, *, ad_id: int, user_id: int) -> None:
        self._booked.add(slot)


class InMemoryConvertedRepo(SlotConvertedRepository):
    def __init__(self):
        self._converted: set[SlotKey] = set()

    async def is_converted(self, slot: SlotKey) -> bool:
        return slot in self._converted

    async def mark_converted(self, slot: SlotKey, *, user_id: int, ad_id: int) -> None:
        self._converted.add(slot)


@pytest.mark.asyncio
async def test_hold_free_slot_sets_hold_and_converts_if_not_system():
    policy = SlotPricingPolicy(system_paid_count=3)
    service = SlotReservationService(
        booking_repo=InMemoryBookingRepo(),
        converted_repo=InMemoryConvertedRepo(),
        hold_store=InMemoryHoldStore(),
        pricing_policy=policy,
        hold_ttl=timedelta(minutes=15),
    )

    region_id = 1
    future = [
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(10, 0)
        ),
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(14, 0)
        ),
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(18, 0)
        ),
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 13), local_time=time(10, 0)
        ),  # НЕ system
    ]

    now = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)
    result = await service.hold_slot(
        slot=future[3],
        user_id=100,
        ad_id=200,
        ordered_future_slots=future,
        now_utc=now,
    )

    assert result.slot == future[3]
    assert result.pricing_changed_to_converted is True


@pytest.mark.asyncio
async def test_hold_system_paid_slot_does_not_convert():
    policy = SlotPricingPolicy(system_paid_count=3)
    converted_repo = InMemoryConvertedRepo()
    hold_store = InMemoryHoldStore()

    service = SlotReservationService(
        booking_repo=InMemoryBookingRepo(),
        converted_repo=converted_repo,
        hold_store=hold_store,
        pricing_policy=policy,
    )

    region_id = 1
    future = [
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(10, 0)
        ),  # system
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(14, 0)
        ),  # system
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 12), local_time=time(18, 0)
        ),  # system
        SlotKey(
            region_id=region_id, local_day=date(2026, 2, 13), local_time=time(10, 0)
        ),
    ]

    now = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)
    result = await service.hold_slot(
        slot=future[0],
        user_id=1,
        ad_id=2,
        ordered_future_slots=future,
        now_utc=now,
    )

    assert result.pricing_changed_to_converted is False
    assert await converted_repo.is_converted(future[0]) is False


@pytest.mark.asyncio
async def test_hold_slot_fails_if_held_by_other_user():
    policy = SlotPricingPolicy(system_paid_count=3)
    hold_store = InMemoryHoldStore()

    service = SlotReservationService(
        booking_repo=InMemoryBookingRepo(),
        converted_repo=InMemoryConvertedRepo(),
        hold_store=hold_store,
        pricing_policy=policy,
    )

    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))
    future = [slot]

    await hold_store.set(
        slot, HoldOwner(user_id=999, ad_id=888), ttl=timedelta(minutes=15)
    )

    with pytest.raises(SlotAlreadyHeld):
        await service.hold_slot(
            slot=slot,
            user_id=1,
            ad_id=2,
            ordered_future_slots=future,
            now_utc=datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc),
        )


@pytest.mark.asyncio
async def test_hold_slot_fails_if_booked():
    policy = SlotPricingPolicy(system_paid_count=3)
    booking_repo = InMemoryBookingRepo()
    service = SlotReservationService(
        booking_repo=booking_repo,
        converted_repo=InMemoryConvertedRepo(),
        hold_store=InMemoryHoldStore(),
        pricing_policy=policy,
    )

    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))
    await booking_repo.book(slot, ad_id=1, user_id=1)

    with pytest.raises(SlotAlreadyBooked):
        await service.hold_slot(
            slot=slot,
            user_id=1,
            ad_id=1,
            ordered_future_slots=[slot],
            now_utc=datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc),
        )


@pytest.mark.asyncio
async def test_book_after_payment_marks_booked_and_releases_own_hold():
    policy = SlotPricingPolicy(system_paid_count=3)
    booking_repo = InMemoryBookingRepo()
    hold_store = InMemoryHoldStore()

    service = SlotReservationService(
        booking_repo=booking_repo,
        converted_repo=InMemoryConvertedRepo(),
        hold_store=hold_store,
        pricing_policy=policy,
    )

    slot = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))
    await hold_store.set(
        slot, HoldOwner(user_id=10, ad_id=20), ttl=timedelta(minutes=15)
    )

    await service.book_after_payment(
        slot=slot,
        user_id=10,
        ad_id=20,
        now_utc=datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc),
    )

    assert await booking_repo.is_booked(slot) is True
    assert await hold_store.get(slot) is None
