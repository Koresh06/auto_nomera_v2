"""
Regression test for AUD-05: CheckHoldUseCase compared the tuple returned by
get_converted_owner_and_ad() directly against an int user_id, which is always
False. As a result, a user who had already paid for a slot (hold expired by
the time they confirmed) was incorrectly told "hold expired, pick again".
"""

from datetime import date, time

from src.application.use_cases.slots.check_hold import (
    CheckHoldRequest,
    CheckHoldUseCase,
)
from src.domain.value_objects.slot_key import SlotKey

SLOT = SlotKey(region_id=1, local_day=date(2026, 2, 12), local_time=time(10, 0))


class FakeHoldStore:
    def __init__(self, valid_for_user: int | None = None) -> None:
        self._valid_for_user = valid_for_user

    async def exists_for_user(self, *, slot: SlotKey, user_id: int) -> bool:
        return self._valid_for_user == user_id


class FakeConvertedRepo:
    def __init__(self, owner: tuple[int, int | None] | None = None) -> None:
        self._owner = owner

    async def get_converted_owner_and_ad(self, slot: SlotKey):
        return self._owner


async def test_check_hold_true_when_redis_hold_is_valid():
    use_case = CheckHoldUseCase(
        hold_store=FakeHoldStore(valid_for_user=100),
        converted_repo=FakeConvertedRepo(owner=None),
    )

    result = await use_case(CheckHoldRequest(region_id=1, slot=SLOT, user_id=100))

    assert result is True


async def test_check_hold_true_when_slot_already_converted_by_same_user():
    """The exact scenario from AUD-05: Redis hold expired, but the slot was
    already paid for and converted by this same user — must still be valid."""
    use_case = CheckHoldUseCase(
        hold_store=FakeHoldStore(valid_for_user=None),  # hold expired
        converted_repo=FakeConvertedRepo(owner=(100, 42)),
    )

    result = await use_case(CheckHoldRequest(region_id=1, slot=SLOT, user_id=100))

    assert result is True


async def test_check_hold_false_when_converted_by_a_different_user():
    use_case = CheckHoldUseCase(
        hold_store=FakeHoldStore(valid_for_user=None),
        converted_repo=FakeConvertedRepo(owner=(999, 42)),
    )

    result = await use_case(CheckHoldRequest(region_id=1, slot=SLOT, user_id=100))

    assert result is False


async def test_check_hold_false_when_no_hold_and_not_converted():
    use_case = CheckHoldUseCase(
        hold_store=FakeHoldStore(valid_for_user=None),
        converted_repo=FakeConvertedRepo(owner=None),
    )

    result = await use_case(CheckHoldRequest(region_id=1, slot=SLOT, user_id=100))

    assert result is False
