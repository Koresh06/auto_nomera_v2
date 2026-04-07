from __future__ import annotations

from typing import Iterable, Protocol

from src.domain.value_objects.slot_key import SlotKey


class SlotBookingRepository(Protocol):
    async def is_booked(self, slot: SlotKey) -> bool: ...

    async def book(self, slot: SlotKey, *, ad_id: int, user_id: int) -> None: ...

    async def get_booked_set(self, slot: Iterable[SlotKey]) -> set[SlotKey]: ...
