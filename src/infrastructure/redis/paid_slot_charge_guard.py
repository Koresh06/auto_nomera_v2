from datetime import timedelta

from redis.asyncio import Redis

from src.application.ports.slots.paid_slot_charge_guard import PaidSlotChargeGuard
from src.domain.value_objects.slot_key import SlotKey

# Сколько секунд повторный выбор того же слота считается двойным тапом.
# «Отмена» снимает блокировку раньше.
DOUBLE_TAP_WINDOW = timedelta(seconds=10)


def _key(user_id: int, slot: SlotKey) -> str:
    return (
        f"paid_slot_charge:{user_id}:{slot.region_id}:"
        f"{slot.local_day.isoformat()}:{slot.local_time.strftime('%H:%M')}"
    )


class RedisPaidSlotChargeGuard(PaidSlotChargeGuard):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def try_acquire(self, user_id: int, slot: SlotKey) -> bool:
        return bool(
            await self._redis.set(_key(user_id, slot), 1, nx=True, ex=DOUBLE_TAP_WINDOW)
        )

    async def release(self, user_id: int, slot: SlotKey) -> None:
        await self._redis.delete(_key(user_id, slot))


class InMemoryPaidSlotChargeGuard(PaidSlotChargeGuard):
    def __init__(self) -> None:
        self._held: set[str] = set()

    async def try_acquire(self, user_id: int, slot: SlotKey) -> bool:
        key = _key(user_id, slot)
        if key in self._held:
            return False
        self._held.add(key)
        return True

    async def release(self, user_id: int, slot: SlotKey) -> None:
        self._held.discard(_key(user_id, slot))
