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
    pricing_changed_to_converted: bool


@dataclass(slots=True)
class SlotReservationService:
    booking_repo: SlotBookingRepository
    converted_repo: SlotConvertedRepository
    hold_store: SlotHoldStore

    pricing_policy: SlotPricingPolicy
    hold_ttl: timedelta = timedelta(minutes=15)

    async def hold_slot(
        self,
        *,
        slot: SlotKey,
        user_id: int,
        ad_id: int | None = None,
        ordered_future_slots: list[SlotKey],
        now_utc: datetime | None = None,
    ) -> HoldResult:
        """
        Логика на нажатие кнопки:
        - если booked -> ошибка
        - если hold другого -> ошибка
        - если hold этого же owner -> продлеваем TTL
        - если слот не system и не converted -> mark converted (для всех в регионе)
        """
        now = now_utc or get_datetime_utc_now()
        owner = HoldOwner(user_id=user_id, ad_id=ad_id)

        # 1) booked?
        if await self.booking_repo.is_booked(slot):
            raise SlotAlreadyBooked()

        # 2) hold?
        existing = await self.hold_store.get(slot)
        if existing is not None and existing != owner:
            raise SlotAlreadyHeld()

        # 3) поставить/продлить hold
        hold_until = now + self.hold_ttl
        await self.hold_store.set(slot, owner, self.hold_ttl)

        # 4) pricing converted?
        # system paid считается политикой, converted — хранится как состояние
        is_system_paid = self.pricing_policy.is_system_paid(
            ordered_future_slots=ordered_future_slots, slot=slot
        )
        is_converted = await self.converted_repo.is_converted(slot)

        pricing_changed = False
        if (not is_system_paid) and (not is_converted):
            await self.converted_repo.mark_converted(slot, user_id=user_id, ad_id=ad_id)
            pricing_changed = True

        return HoldResult(
            slot=slot,
            hold_until_utc=hold_until,
            pricing_changed_to_converted=pricing_changed,
        )

    async def release_hold(
        self,
        *,
        slot: SlotKey,
        user_id: int,
        ad_id: int | None = None,
    ) -> None:
        existing = await self.hold_store.get(slot)
        if existing is None:
            raise SlotHoldNotFound()

        if ad_id is None:
            if existing.user_id != user_id:
                raise SlotHoldOwnerMismatch()
        else:
            if existing != HoldOwner(user_id=user_id, ad_id=ad_id):
                raise SlotHoldOwnerMismatch()

        await self.hold_store.delete(slot)
        await self.converted_repo.unmark_converted(slot)

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
