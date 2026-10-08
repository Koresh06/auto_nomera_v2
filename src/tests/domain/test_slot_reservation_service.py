from datetime import date, time, datetime, timezone, timedelta

import pytest

from src.domain.services.slots.slot_reservation_service import SlotReservationService
from src.domain.value_objects.slot_key import SlotKey
from src.domain.value_objects.hold_owner import HoldOwner
from src.domain.exceptions.slot_reservation import (
    SlotAlreadyHeld,
    SlotAlreadyBooked,
    SlotAlreadyConverted,
    SlotHoldNotFound,
)
from src.infrastructure.redis.holt_store.in_memory import InMemorySlotHoldStore
from src.infrastructure.repositories.slot.in_memory import (
    InMemorySlotBookingRepo,
    InMemorySlotConvertedRepo,
)


def make_service(hold_ttl: timedelta = timedelta(minutes=15)) -> SlotReservationService:
    return SlotReservationService(
        booking_repo=InMemorySlotBookingRepo(),
        converted_repo=InMemorySlotConvertedRepo(),
        hold_store=InMemorySlotHoldStore(),
        hold_ttl=hold_ttl,
    )


def make_slot(
    day: date = date(2026, 2, 12), t: time = time(10, 0), region_id: int = 1
) -> SlotKey:
    return SlotKey(region_id=region_id, local_day=day, local_time=t)


NOW = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)


async def test_hold_slot_free_and_not_system_paid_is_not_converted():
    service = make_service()
    slot = make_slot(t=time(10, 0))
    future = [slot, make_slot(t=time(14, 0)), make_slot(t=time(18, 0))]

    result = await service.hold_slot(
        slot=slot,
        user_id=100,
        ordered_future_slots=future,
        system_paid_slots_count=0,
        now_utc=NOW,
    )

    assert result.slot == slot
    assert result.is_system_paid is False
    assert result.is_converted is False
    assert result.hold_until_utc == NOW + timedelta(minutes=15)


async def test_hold_slot_within_system_paid_count_is_system_paid():
    service = make_service()
    slot = make_slot(t=time(10, 0))
    future = [slot, make_slot(t=time(14, 0)), make_slot(t=time(18, 0))]

    result = await service.hold_slot(
        slot=slot,
        user_id=1,
        ordered_future_slots=future,
        system_paid_slots_count=3,
        now_utc=NOW,
    )

    assert result.is_system_paid is True


async def test_hold_slot_fails_if_held_by_other_user():
    service = make_service()
    slot = make_slot()

    await service.hold_store.set(slot, HoldOwner(user_id=999), timedelta(minutes=15))

    with pytest.raises(SlotAlreadyHeld):
        await service.hold_slot(
            slot=slot,
            user_id=1,
            ordered_future_slots=[slot],
            system_paid_slots_count=0,
            now_utc=NOW,
        )


async def test_hold_slot_by_same_user_refreshes_hold():
    service = make_service()
    slot = make_slot()

    await service.hold_store.set(slot, HoldOwner(user_id=1), timedelta(minutes=15))

    # тот же пользователь — не должно быть исключения, hold продлевается
    result = await service.hold_slot(
        slot=slot,
        user_id=1,
        ordered_future_slots=[slot],
        system_paid_slots_count=0,
        now_utc=NOW,
    )
    assert result.slot == slot


async def test_hold_slot_loses_race_when_store_set_rejects(monkeypatch):
    """AUD-04: даже если предварительный get() не увидел конфликта, атомарный
    set() в хранилище может отказать (кто-то успел захватить слот первым).
    hold_slot должен превратить это в SlotAlreadyHeld, а не молча продолжить.
    """
    service = make_service()
    slot = make_slot()

    async def fake_set(_slot, _owner, _ttl):
        return False  # имитация проигранной гонки на уровне атомарного SET

    monkeypatch.setattr(service.hold_store, "set", fake_set)

    with pytest.raises(SlotAlreadyHeld):
        await service.hold_slot(
            slot=slot,
            user_id=1,
            ordered_future_slots=[slot],
            system_paid_slots_count=0,
            now_utc=NOW,
        )


async def test_book_after_payment_marks_booked_converted_and_releases_own_hold():
    service = make_service()
    slot = make_slot()
    owner = HoldOwner(user_id=10, ad_id=20)
    await service.hold_store.set(slot, owner, timedelta(minutes=15))

    await service.book_after_payment(slot=slot, user_id=10, ad_id=20)

    assert await service.booking_repo.is_booked(slot) is True
    assert await service.converted_repo.is_converted(slot) is True
    assert await service.hold_store.get(slot) is None


async def test_book_after_payment_is_idempotent_for_same_user():
    service = make_service()
    slot = make_slot()

    await service.book_after_payment(slot=slot, user_id=10, ad_id=20)
    # повторный вызов тем же пользователем (повтор webhook) не должен падать
    await service.book_after_payment(slot=slot, user_id=10, ad_id=20)

    assert await service.booking_repo.is_booked(slot) is True


async def test_book_after_payment_raises_if_booking_lost_to_another_user():
    """AUD-03: если слот уже забронирован ДРУГИМ пользователем, деньги не должны
    молча "раствориться" — book_after_payment обязан сообщить о конфликте."""
    service = make_service()
    slot = make_slot()
    await service.booking_repo.book(slot, ad_id=1, user_id=1)  # кто-то успел раньше

    with pytest.raises(SlotAlreadyBooked):
        await service.book_after_payment(slot=slot, user_id=2, ad_id=2)


async def test_book_after_payment_raises_if_converted_lost_to_another_user():
    """AUD-03: аналогично для converted_repo — другой владелец уже сконвертировал слот."""
    service = make_service()
    slot = make_slot()
    await service.converted_repo.mark_converted(slot=slot, user_id=1, ad_id=1)

    with pytest.raises(SlotAlreadyConverted):
        await service.book_after_payment(slot=slot, user_id=2, ad_id=2)


async def test_book_after_payment_requires_hold_owner_when_flagged():
    service = make_service()
    slot = make_slot()

    with pytest.raises(SlotHoldNotFound):
        await service.book_after_payment(
            slot=slot, user_id=1, ad_id=1, require_hold_owner=True
        )


async def test_release_hold_removes_own_hold():
    service = make_service()
    slot = make_slot()
    await service.hold_store.set(slot, HoldOwner(user_id=1), timedelta(minutes=15))

    await service.release_hold(slot=slot, user_id=1)

    assert await service.hold_store.get(slot) is None
