import json
from datetime import timedelta
from typing import Iterable, Set
from redis.asyncio import Redis

from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.domain.value_objects.hold_owner import HoldOwner
from src.domain.value_objects.slot_key import SlotKey


class RedisSlotHoldStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _k(self, slot: SlotKey) -> str:
        return f"hold:{slot.region_id}:{slot.local_day.isoformat()}:{slot.local_time.isoformat()}"

    async def get(self, slot: SlotKey) -> HoldOwner | None:
        data = await self._redis.get(self._k(slot))
        if not data:
            return None
        payload = json.loads(data)
        return HoldOwner(user_id=payload["user_id"], ad_id=payload.get("ad_id"))

    async def set(self, slot: SlotKey, owner: HoldOwner, ttl: timedelta) -> None:
        payload = json.dumps({"user_id": owner.user_id, "ad_id": owner.ad_id})
        await self._redis.set(self._k(slot), payload, ex=int(ttl.total_seconds()))

    async def delete(self, slot: SlotKey) -> None:
        await self._redis.delete(self._k(slot))

    async def get_held_set(self, slots: Iterable[SlotKey]) -> Set[SlotKey]:
        keys = [self._k(slot) for slot in slots]
        slots_list = list(slots)
        if not keys:
            return set()

        values = await self._redis.mget(*keys)
        return {
            slot
            for slot, value in zip(slots_list, values)
            if value is not None
        }