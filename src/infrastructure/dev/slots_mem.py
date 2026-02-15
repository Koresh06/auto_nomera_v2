from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Set, Tuple

from src.application.ports.slots.slot_hold_store import SlotHoldStore, HoldOwner
from src.application.ports.slots.slot_booking_repo import SlotBookingRepository
from src.application.ports.slots.slot_converted_repo import SlotConvertedRepository
from src.domain.value_objects.slot_key import SlotKey


@dataclass(frozen=True, slots=True)
class _HoldEntry:
    owner: HoldOwner
    expires_at_utc: datetime


class InMemorySlotHoldStore(SlotHoldStore):
    """
    Хранит HOLD в памяти с TTL.
    get_held_set(slots) возвращает множество SlotKey, которые сейчас held (и не протухли).
    """

    def __init__(self) -> None:
        self._holds: Dict[str, _HoldEntry] = {}

    def _k(self, slot: SlotKey) -> str:
        return f"{slot.region_id}:{slot.local_day.isoformat()}:{slot.local_time.isoformat()}"

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _purge_if_expired(self, key: str, entry: _HoldEntry, now_utc: datetime) -> bool:
        if entry.expires_at_utc <= now_utc:
            self._holds.pop(key, None)
            return True
        return False

    async def get(self, slot: SlotKey) -> HoldOwner | None:
        key = self._k(slot)
        entry = self._holds.get(key)
        if not entry:
            return None

        now_utc = self._now()
        if self._purge_if_expired(key, entry, now_utc):
            return None

        return entry.owner

    async def set(self, slot: SlotKey, owner: HoldOwner, ttl: timedelta) -> None:
        key = self._k(slot)
        now_utc = self._now()
        self._holds[key] = _HoldEntry(owner=owner, expires_at_utc=now_utc + ttl)

    async def delete(self, slot: SlotKey) -> None:
        self._holds.pop(self._k(slot), None)

    async def get_held_set(self, slots: Iterable[SlotKey]) -> set[SlotKey]:
        now_utc = self._now()
        held: set[SlotKey] = set()

        for slot in slots:
            key = self._k(slot)
            entry = self._holds.get(key)
            if not entry:
                continue
            if self._purge_if_expired(key, entry, now_utc):
                continue
            held.add(slot)

        return held


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

    async def mark_converted(self, slot: SlotKey, *, user_id: int, ad_id: int) -> None:
        self._converted.add(self._k(slot))

    async def get_converted_set(self, slots: Iterable[SlotKey]) -> set[SlotKey]:
        res: set[SlotKey] = set()
        for s in slots:
            if self._k(s) in self._converted:
                res.add(s)
        return res
