import json
from datetime import timedelta
from typing import Iterable, Set
from redis.asyncio import Redis

from src.application.ports.slots.slot_hold_store import SlotHoldStore
from src.domain.value_objects.hold_owner import HoldOwner
from src.domain.value_objects.slot_key import SlotKey

# Атомарный захват hold'а: ставим значение, только если ключа ещё нет,
# либо если ключ уже принадлежит тому же user_id (переиспользование/продление
# своего же hold'а). Если ключ занят ДРУГИМ user_id — отказываем.
# Выполняется одним EVAL, поэтому гонка "GET потом SET" невозможна.
_ACQUIRE_HOLD_SCRIPT = """
local current = redis.call('GET', KEYS[1])
if current then
    local ok, obj = pcall(cjson.decode, current)
    if ok and obj and obj['user_id'] == tonumber(ARGV[2]) then
        redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3])
        return 1
    end
    return 0
end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3])
return 1
"""


class RedisSlotHoldStore(SlotHoldStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._acquire_script = redis.register_script(_ACQUIRE_HOLD_SCRIPT)

    def _k(self, slot: SlotKey) -> str:
        return f"hold:{slot.region_id}:{slot.local_day.isoformat()}:{slot.local_time.strftime('%H:%M')}"

    async def get(self, slot: SlotKey) -> HoldOwner | None:
        data = await self._redis.get(self._k(slot))
        if not data:
            return None
        payload = json.loads(data)
        return HoldOwner(user_id=payload["user_id"])

    async def set(self, slot: SlotKey, owner: HoldOwner, ttl: timedelta) -> bool:
        payload = json.dumps({"user_id": owner.user_id})
        result = await self._acquire_script(
            keys=[self._k(slot)],
            args=[payload, owner.user_id, int(ttl.total_seconds())],
        )
        return bool(result)

    async def delete(self, slot: SlotKey) -> None:
        await self._redis.delete(self._k(slot))

    async def get_held_set(self, slots: Iterable[SlotKey]) -> Set[SlotKey]:
        keys = [self._k(slot) for slot in slots]
        slots_list = list(slots)
        if not keys:
            return set()

        values = await self._redis.mget(*keys)
        return {slot for slot, value in zip(slots_list, values) if value is not None}

    async def exists_for_user(self, slot: SlotKey, user_id: int) -> bool:
        owner = await self.get(slot)
        return owner is not None and owner.user_id == user_id
