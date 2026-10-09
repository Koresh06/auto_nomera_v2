"""RedisSlotHoldStore на fakeredis с настоящим Lua-движком (EVAL)."""

import asyncio
from datetime import date, time, timedelta

import fakeredis
import pytest

from src.domain.value_objects.hold_owner import HoldOwner
from src.domain.value_objects.slot_key import SlotKey
from src.infrastructure.redis.holt_store.redis import RedisSlotHoldStore


def key(hh: int = 10, day: int = 1) -> SlotKey:
    return SlotKey(region_id=1, local_day=date(2030, 1, day), local_time=time(hh))


@pytest.fixture
def redis():
    return fakeredis.FakeAsyncRedis()


@pytest.fixture
def store(redis):
    return RedisSlotHoldStore(redis)


async def test_set_get_delete(store):
    assert await store.get(key()) is None
    assert await store.set(key(), HoldOwner(user_id=1), timedelta(minutes=5))
    assert await store.get(key()) == HoldOwner(user_id=1)
    await store.delete(key())
    assert await store.get(key()) is None


async def test_hold_is_exclusive_but_owner_can_extend(store, redis):
    ttl = timedelta(minutes=5)
    assert await store.set(key(), HoldOwner(user_id=1), ttl) is True
    assert await store.set(key(), HoldOwner(user_id=2), ttl) is False
    assert await store.get(key()) == HoldOwner(user_id=1)

    assert await store.set(key(), HoldOwner(user_id=1), timedelta(minutes=30)) is True
    assert await redis.ttl(store._k(key())) > 5 * 60


async def test_hold_expires(store, redis):
    await store.set(key(), HoldOwner(user_id=1), timedelta(seconds=60))
    assert 0 < await redis.ttl(store._k(key())) <= 60


async def test_concurrent_holds_single_winner(store):
    results = await asyncio.gather(
        *(
            store.set(key(), HoldOwner(user_id=uid), timedelta(minutes=5))
            for uid in range(1, 21)
        )
    )
    assert results.count(True) == 1


async def test_corrupted_value_is_not_overwritten(store, redis):
    await redis.set(store._k(key()), "not-json")
    assert await store.set(key(), HoldOwner(user_id=1), timedelta(minutes=5)) is False


async def test_exists_for_user(store):
    await store.set(key(), HoldOwner(user_id=1), timedelta(minutes=5))
    assert await store.exists_for_user(key(), 1) is True
    assert await store.exists_for_user(key(), 2) is False
    assert await store.exists_for_user(key(hh=11), 1) is False


async def test_get_held_set_with_list(store):
    await store.set(key(10), HoldOwner(user_id=1), timedelta(minutes=5))
    await store.set(key(14, day=2), HoldOwner(user_id=2), timedelta(minutes=5))

    held = await store.get_held_set([key(10), key(14), key(14, day=2)])

    assert held == {key(10), key(14, day=2)}
    assert await store.get_held_set([]) == set()


async def test_get_held_set_accepts_one_shot_iterables(store):
    """Порт принимает ``Iterable[SlotKey]`` — генератор не должен
    «теряться» и превращать занятые слоты в свободные."""
    await store.set(key(10), HoldOwner(user_id=1), timedelta(minutes=5))

    held = await store.get_held_set(k for k in [key(10), key(14)])

    assert held == {key(10)}
