from typing import Iterable, Set

from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository

from src.domain.value_objects.slot_key import SlotKey


class InMemorySlotBookingRepo(SlotBookingRepository):
    """
    Booked слоты — просто set.
    get_booked_set(slots) возвращает только те SlotKey, которые booked.
    """

    def __init__(self) -> None:
        self._booked: Set[str] = set()

    def _k(self, slot: SlotKey) -> str:
        return f"{slot.region_id}:{slot.local_day.isoformat()}:{slot.local_time.isoformat()}"

    async def is_booked(self, slot: SlotKey) -> bool:
        return self._k(slot) in self._booked

    async def book(self, slot: SlotKey, *, ad_id: int, user_id: int) -> None:
        # ad_id/user_id можно сохранить отдельно для аудита, но для моков достаточно отметки
        self._booked.add(self._k(slot))

    async def get_booked_set(self, slot: Iterable[SlotKey]) -> set[SlotKey]:
        res: set[SlotKey] = set()
        for s in slot:
            if self._k(s) in self._booked:
                res.add(s)
        return res


class InMemorySlotConvertedRepo(SlotConvertedRepository):
    """
    Converted слоты — set.
    get_converted_set(slots) возвращает только те SlotKey, которые converted.
    """

    def __init__(self) -> None:
        self._converted: Set[str] = set()

    def _k(self, slot: SlotKey) -> str:
        return f"{slot.region_id}:{slot.local_day.isoformat()}:{slot.local_time.isoformat()}"

    async def is_converted(self, slot: SlotKey) -> bool:
        return self._k(slot) in self._converted

    async def mark_converted(self, slot: SlotKey, *, user_id: int, ad_id: int | None = None) -> None:
        self._converted.add(self._k(slot))

    async def unmark_converted(self, slot: SlotKey, user_id: int) -> None:
        self._converted.discard(self._k(slot))

    async def get_converted_set(self, slots: Iterable[SlotKey]) -> set[SlotKey]:
        res: set[SlotKey] = set()
        for s in slots:
            if self._k(s) in self._converted:
                res.add(s)
        return res