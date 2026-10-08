from typing import Dict, Iterable

from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository

from src.domain.value_objects.slot_key import SlotKey


class InMemorySlotBookingRepo(SlotBookingRepository):
    """
    Booked слоты — dict slot_key -> (user_id, ad_id), эмулирует уникальный
    констрейнт (region_id, slot_day, slot_time) из SlotBookingModel.
    """

    def __init__(self) -> None:
        self._booked: Dict[str, tuple[int, int]] = {}

    def _k(self, slot: SlotKey) -> str:
        return f"{slot.region_id}:{slot.local_day.isoformat()}:{slot.local_time.isoformat()}"

    async def is_booked(self, slot: SlotKey) -> bool:
        return self._k(slot) in self._booked

    async def book(self, slot: SlotKey, *, ad_id: int, user_id: int) -> bool:
        key = self._k(slot)
        if key in self._booked:
            return False
        self._booked[key] = (user_id, ad_id)
        return True

    async def get_booked_set(self, slot: Iterable[SlotKey]) -> set[SlotKey]:
        res: set[SlotKey] = set()
        for s in slot:
            if self._k(s) in self._booked:
                res.add(s)
        return res

    async def get_booking_owner(self, slot: SlotKey) -> int | None:
        entry = self._booked.get(self._k(slot))
        return entry[0] if entry else None


class InMemorySlotConvertedRepo(SlotConvertedRepository):
    """
    Converted слоты — dict slot_key -> (user_id, ad_id), эмулирует
    ON CONFLICT DO UPDATE WHERE user_id=:user_id из SlotConvertedModel:
    повторный вызов тем же user_id обновляет запись, другим user_id — не трогает.
    """

    def __init__(self) -> None:
        self._converted: Dict[str, tuple[int, int | None]] = {}

    def _k(self, slot: SlotKey) -> str:
        return f"{slot.region_id}:{slot.local_day.isoformat()}:{slot.local_time.isoformat()}"

    async def is_converted(self, slot: SlotKey) -> bool:
        return self._k(slot) in self._converted

    async def mark_converted(
        self, slot: SlotKey, *, user_id: int, ad_id: int | None = None
    ) -> bool:
        key = self._k(slot)
        existing = self._converted.get(key)
        if existing is not None and existing[0] != user_id:
            return False
        self._converted[key] = (user_id, ad_id)
        return True

    async def unmark_converted(self, slot: SlotKey, user_id: int) -> None:
        self._converted.pop(self._k(slot), None)

    async def get_converted_set(self, slots: Iterable[SlotKey]) -> set[SlotKey]:
        res: set[SlotKey] = set()
        for s in slots:
            if self._k(s) in self._converted:
                res.add(s)
        return res

    async def get_converted_owner_and_ad(
        self, slot: SlotKey
    ) -> tuple[int, int | None] | None:
        return self._converted.get(self._k(slot))
