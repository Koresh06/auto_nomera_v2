from __future__ import annotations

from datetime import timedelta
from typing import Iterable, Protocol, Set

from src.domain.value_objects.hold_owner import HoldOwner
from src.domain.value_objects.slot_key import SlotKey


class SlotHoldStore(Protocol):
    async def get(self, slot: SlotKey) -> HoldOwner | None:
        ...

    async def set(self, slot: SlotKey, owner: HoldOwner, ttl: timedelta) -> None:
        ...

    async def delete(self, slot: SlotKey) -> None:
        ...

    async def get_held_set(self, slots: Iterable[SlotKey]) -> Set[SlotKey]:
       ...