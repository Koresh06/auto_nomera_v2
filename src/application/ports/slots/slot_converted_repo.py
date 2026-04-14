from __future__ import annotations

from typing import Iterable, Protocol

from src.domain.value_objects.slot_key import SlotKey


class SlotConvertedRepository(Protocol):
    async def is_converted(self, slot: SlotKey) -> bool: ...

    async def mark_converted(
        self,
        slot: SlotKey,
        *,
        user_id: int,
        ad_id: int,
    ) -> None: ...

    async def unmark_converted(self, slot: SlotKey) -> None: ...

    async def get_converted_set(self, slots: Iterable[SlotKey]) -> set[SlotKey]: ...
