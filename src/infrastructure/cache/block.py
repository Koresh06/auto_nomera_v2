import json

from redis.asyncio import Redis

from src.application.ports.cache.block import BlockCache

_TTL_SECONDS = 300  # 5 минут; при промахе перечитаем из БД
_KEY = "block:{tg_id}"


class RedisBlockCache(BlockCache):
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get_flags(self, tg_id: int) -> tuple[bool, bool] | None:
        raw = await self.redis.get(_KEY.format(tg_id=tg_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return data["is_blocked"], data["is_payment_blocked"]

    async def set_flags(
        self, tg_id: int, *, is_blocked: bool, is_payment_blocked: bool
    ) -> None:
        payload = json.dumps(
            {"is_blocked": is_blocked, "is_payment_blocked": is_payment_blocked}
        )
        await self.redis.set(_KEY.format(tg_id=tg_id), payload, ex=_TTL_SECONDS)

    async def invalidate(self, tg_id: int) -> None:
        await self.redis.delete(_KEY.format(tg_id=tg_id))
