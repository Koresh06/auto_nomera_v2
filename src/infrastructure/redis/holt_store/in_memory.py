from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Set

from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.domain.value_objects.hold_owner import HoldOwner
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

    async def get_held_set(self, slots: Iterable[SlotKey]) -> Set[SlotKey]:
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
