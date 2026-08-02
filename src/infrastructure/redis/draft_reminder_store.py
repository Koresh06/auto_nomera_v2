from dataclasses import dataclass

import redis.asyncio as aioredis

from src.application.ports.ad.draft_reminder_store import DraftReminderStore


KEY_PREFIX = "publish_in_progress"


@dataclass(slots=True)
class RedisDraftReminderStore(DraftReminderStore):
    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _key(self, user_id: int) -> str:
        return f"{KEY_PREFIX}:{user_id}"

    async def set_job_id(self, user_id: int, job_id: str, ttl_seconds: int) -> None:
        await self._redis.set(self._key(user_id), job_id, ex=ttl_seconds)

    async def get_job_id(self, user_id: int) -> str | None:
        value = await self._redis.get(self._key(user_id))
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else value

    async def delete(self, user_id: int) -> None:
        await self._redis.delete(self._key(user_id))
