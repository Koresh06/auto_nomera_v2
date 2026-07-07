from dataclasses import dataclass
from datetime import datetime, timedelta

from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.domain.exceptions.slot_reservation import (
    SlotAlreadyBooked,
    SlotAlreadyHeld,
    SlotHoldNotFound,
    SlotHoldOwnerMismatch,
)
from src.domain.services.slots.slot_pricing_policy import SlotPricingPolicy
from src.domain.value_objects.hold_owner import HoldOwner
from src.domain.value_objects.slot_key import SlotKey
from src.utils.get_datetime_utc_now import get_datetime_utc_now


@dataclass(slots=True)
class HoldResult:
    slot: SlotKey
    hold_until_utc: datetime
    is_system_paid: bool
    is_converted: bool


@dataclass(slots=True)
class SlotReservationService:
    booking_repo: SlotBookingRepository
    converted_repo: SlotConvertedRepository
    hold_store: SlotHoldStore

    pricing_policy: SlotPricingPolicy
    hold_ttl: timedelta

    async def hold_slot(
        self,
        *,
        slot: SlotKey,
        user_id: int,
        ordered_future_slots: list[SlotKey],
        now_utc: datetime | None = None,
    ) -> HoldResult:
        now = now_utc or get_datetime_utc_now()
        owner = HoldOwner(user_id=user_id)

        if await self.booking_repo.is_booked(slot):
            raise SlotAlreadyBooked()

        existing = await self.hold_store.get(slot)
        if existing is not None and existing != owner:
            raise SlotAlreadyHeld()

        converted_info = await self.converted_repo.get_converted_owner_and_ad(slot)
        is_converted = converted_info is not None

        hold_until = now + self.hold_ttl
        await self.hold_store.set(slot, owner, self.hold_ttl)

        is_system_paid = self.pricing_policy.is_system_paid(
            ordered_future_slots=ordered_future_slots,
            slot=slot,
        )

        return HoldResult(
            slot=slot,
            hold_until_utc=hold_until,
            is_system_paid=is_system_paid,
            is_converted=is_converted,
        )

    async def release_hold(
        self,
        *,
        slot: SlotKey,
        user_id: int,
    ) -> None:
        existing = await self.hold_store.get(slot)
        if existing is None:
            raise SlotHoldNotFound()

        if existing.user_id != user_id:
            raise SlotHoldOwnerMismatch()
        else:
            if existing != HoldOwner(user_id=user_id):
                raise SlotHoldOwnerMismatch()

        await self.hold_store.delete(slot)

    async def book_after_payment(
        self,
        *,
        slot: SlotKey,
        user_id: int,
        ad_id: int | None = None,
        require_hold_owner: bool = False,
    ) -> None:
        """
        Вызывается после успешного вебхука оплаты.
        По умолчанию НЕ требуем наличие активного hold (TTL мог истечь),
        но если slot уже booked -> ошибка.

        Если require_hold_owner=True — тогда требуем hold и совпадение owner.
        """
        owner = HoldOwner(user_id=user_id, ad_id=ad_id)

        if await self.booking_repo.is_booked(slot):
            raise SlotAlreadyBooked()

        if require_hold_owner:
            existing = await self.hold_store.get(slot)
            if existing is None:
                raise SlotHoldNotFound()
            if existing != owner:
                raise SlotHoldOwnerMismatch()

        # фиксируем booking в БД
        await self.booking_repo.book(slot, ad_id=ad_id, user_id=user_id)

        # снимаем hold, если он есть (неважно чей, но лучше аккуратно — снимем только если совпадает)
        existing = await self.hold_store.get(slot)
        if existing == owner:
            await self.hold_store.delete(slot)
